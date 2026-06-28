import websocket
import re
import json
import requests
import threading
import time
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# Desactivar advertencias SSL para la web de FUNVISIS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURACIÓN GENERAL =================
LAT_MIN, LAT_MAX = 0.5, 13.5
LON_MIN, LON_MAX = -74.0, -59.0
MAGNITUD_MINIMA = 2.0 

# === CREDENCIALES TELEGRAM ===
TELEGRAM_TOKEN = "8811336841:AAH-2tiy2Dh0NsGXLJfPHaGqA_lE4J5ygqY"
TELEGRAM_CHAT_ID = "1292808439"

# ================= CREDENCIALES SUPABASE =================
SUPABASE_URL = "https://nbvjpqmqceencnjmtfng.supabase.co"
SUPABASE_KEY = "sb_publishable_QvN-m2HxKJUV2nHdF_wKqQ_VyAv1Zn2"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# =========================================================

# --- 1. MÓDULOS DE BASE DE DATOS Y ALERTAS ---

def verificar_duplicado(hora):
    """Evita guardar el mismo sismo dos veces al raspar la web varias veces."""
    try:
        respuesta = supabase.table("historial_sismos").select("id").eq("hora_local", hora).execute()
        return len(respuesta.data) > 0
    except:
        return False

def guardar_historial_supabase(region, mag, depth, lat, lon, hora):
    if verificar_duplicado(hora):
        return # Si ya existe, lo ignoramos silenciosamente
        
    try:
        supabase.table("historial_sismos").insert({
            "region": region, "magnitud": float(mag), "profundidad": int(float(depth)),
            "latitud": round(float(lat), 4), "longitud": round(float(lon), 4), "hora_local": hora
        }).execute()
        print(f"[✓] BD Actualizada: Mag {mag} en {region}")
    except Exception as e:
        print(f"[!] Error guardando en BD: {e}")

def enviar_alerta_telegram(region, mag, lat, lon):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    mensaje = (
        f"🚨 <b>¡ALERTA SÍSMICA NACIONAL!</b> 🚨\n\n"
        f"📍 <b>Región:</b> {region}\n"
        f"📈 <b>Magnitud:</b> {mag}\n\n"
        f"🧭 <i>Coordenadas: {lat}, {lon}</i>"
    )
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# --- 2. MÓDULOS DE RECUPERACIÓN HISTÓRICA (BACKFILL) ---

def sincronizar_emsc():
    """Descarga el historial del día de la red Europea."""
    print("[+] Sincronizando historial global (EMSC)...")
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    url = f"https://www.seismicportal.eu/fdsnws/event/1/query?format=json&start={hoy_str}&minlat={LAT_MIN}&maxlat={LAT_MAX}&minlon={LON_MIN}&maxlon={LON_MAX}&minmag={MAGNITUD_MINIMA}"
    try:
        datos = requests.get(url, timeout=10).json().get("features", [])
        for s in datos:
            p, g = s["properties"], s["geometry"]
            t = p["time"]
            if t.endswith('Z'): t = t[:-1] + '+00:00'
            hora = datetime.fromisoformat(t).astimezone(timezone(timedelta(hours=-4))).strftime("%I:%M %p").lower()
            guardar_historial_supabase(p.get("flynn_region", "VENEZUELA").upper(), p["mag"], g["coordinates"][2], g["coordinates"][1], g["coordinates"][0], hora)
    except:
        print("[-] Falló sincronización EMSC.")

def raspar_funvisis():
    """Descarga los microsismos leyendo la plantilla de 'contactos' que FUNVISIS usa para sismos."""
    print("[+] Consumiendo API interna de FUNVISIS (maravilla.json)...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = "http://www.funvisis.gob.ve/maravilla.json"
        respuesta = requests.get(url, headers=headers, verify=False, timeout=15)
        datos = respuesta.json()

        # Extraemos la lista
        lista_sismos = []
        if isinstance(datos, list):
            lista_sismos = datos
        elif isinstance(datos, dict) and 'features' in datos:
            lista_sismos = datos['features']

        sismos_recuperados = 0
        hoy_ddmm = datetime.now(timezone(timedelta(hours=-4))).strftime("%d-%m-%Y") # ej: 28-06-2026

        for item in lista_sismos:
            try:
                props = item.get("properties", {})
                
                # 1. Filtro de Fecha (Disfrazada como 'postalCode')
                fecha_str = props.get("postalCode", "")
                if fecha_str != hoy_ddmm:
                    continue # Saltamos todo lo que no sea estrictamente de HOY

                # 2. Extracción de Magnitud (Disfrazada como 'phone')
                mag_str = props.get("phone", "0")
                mag = float(mag_str.replace(',', '.'))
                
                # 3. Extracción de Profundidad (Disfrazada como 'phoneFormatted')
                prof_str = props.get("phoneFormatted", "5").replace('km', '').replace(' ', '')
                prof = int(float(prof_str))

                # 4. Extracción de Región (Disfrazada como 'address')
                region = props.get("address", "REGIÓN DESCONOCIDA").strip().upper()
                if "VENEZUELA" not in region:
                    region += ", VENEZUELA"

                # 5. Coordenadas
                lat = float(props.get("lat", 10.0))
                lon = float(props.get("long", -66.0))

                # 6. Procesamiento de Hora (Disfrazada como 'city', formato 24h ej: "12:29")
                hora_str = props.get("city", "00:00").strip()
                h, m = hora_str.split(':')
                fecha_obj = datetime.strptime(f"{h}:{m}", "%H:%M")
                hora_app = fecha_obj.strftime("%I:%M %p").lower()

                # 7. Guardar en Supabase
                guardar_historial_supabase(region, mag, prof, lat, lon, hora_app)
                sismos_recuperados += 1

            except Exception as e:
                # Tolerancia a fallos: si un sismo viene sin datos, lo ignoramos y seguimos
                continue

        if sismos_recuperados > 0:
            print(f"[✓] Se inyectaron {sismos_recuperados} sismos locales (¡Misterio resuelto!).")
        else:
            print("[-] No hay microsismos nuevos el día de hoy en maravilla.json.")

    except Exception as e:
        print(f"[-] Falló conexión con maravilla.json: {e}")

# --- 3. RUTINA EN SEGUNDO PLANO ---

def tarea_programada():
    """Hilo que se ejecuta cada 30 minutos de forma invisible."""
    while True:
        time.sleep(1800) # Pausa de 30 minutos (1800 segundos)
        print("\n[Hilo] Ejecutando escaneo silencioso de FUNVISIS...")
        raspar_funvisis()

# --- 4. ESCUCHA EN TIEMPO REAL (WEBSOCKETS) ---

def on_message(ws, message):
    try:
        info = json.loads(message).get('data', {}).get('properties', {})
        lat, lon, mag, depth = info.get('lat'), info.get('lon'), info.get('mag'), info.get('depth')
        region, t = info.get('flynn_region'), info.get('time')
        
        if t.endswith('Z'): t = t[:-1] + '+00:00'
        hora_app = datetime.fromisoformat(t).astimezone(timezone(timedelta(hours=-4))).strftime("%I:%M %p").lower()
        
        if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
            if mag >= MAGNITUD_MINIMA:
                print(f"\n🚨 EVENTO EN VIVO: {region.upper()} | Mag: {mag}")
                guardar_historial_supabase(region, mag, depth, lat, lon, hora_app)
                # Solo disparamos push de Telegram si el sismo es fuerte (>= 3.5) para no saturarte
                if mag >= 3.5: 
                    enviar_alerta_telegram(region, mag, lat, lon)
    except:
        pass

def on_error(ws, error): print(f"\n[!] Error WebSocket: {error}")
def on_close(ws, close_status_code, close_msg): print("\n[!] Conexión cerrada.")
def on_open(ws):
    print("\n" + "="*60 + "\n🇻🇪 SISTEMA DE ALERTA SÍSMICA NACIONAL - EN LÍNEA\n" + "="*60)
    print("Túnel persistente abierto. Escuchando actividad global...")

if __name__ == "__main__":
    print("Iniciando secuencia de arranque de SismoVE...")
    
    # 1. Ejecutamos la recolección de datos inicial (Antes de abrir el túnel)
    sincronizar_emsc()
    raspar_funvisis()
    
    # 2. Iniciamos el trabajador silencioso en un Hilo separado
    hilo_scraper = threading.Thread(target=tarea_programada, daemon=True)
    hilo_scraper.start()
    
    # 3. Lanzamos el demonio principal (Esto bloquea la consola para siempre)
    url = "wss://www.seismicportal.eu/standing_order/websocket"
    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever(ping_interval=60, ping_timeout=10)