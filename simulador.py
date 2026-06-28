import json
from supabase import create_client, Client
from sismo import on_message # Importamos la lógica visual de tu script principal

# ================= CREDENCIALES SUPABASE =================
# Pega aquí los datos que copiaste en el Paso 2
SUPABASE_URL = "https://nbvjpqmqceencnjmtfng.supabase.co"
SUPABASE_KEY = "sb_publishable_QvN-m2HxKJUV2nHdF_wKqQ_VyAv1Zn2"

# Inicializamos el cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# =========================================================

# Simulamos el paquete JSON exacto que enviará el servidor en vivo
payload_falso = {
    "action": "create",
    "data": {
        "properties": {
            "unid": "test_maracay_2026",
            "mag": 5.0,
            "time": "2026-06-27T19:20:00.0Z", # Hora UTC
            "lat": 10.25,
            "lon": -67.60,
            "depth": 41,
            "flynn_region": "MARACAY (41KM N), VENEZUELA"
        }
    }
}

print("Iniciando prueba de inyección hacia la nube...")
props = payload_falso["data"]["properties"]

# Intentamos guardar el sismo simulado en la base de datos de Supabase
try:
    print("[1/2] Conectando con Supabase e insertando fila...")
    respuesta = supabase.table("historial_sismos").insert({
        "region": props["flynn_region"],
        "magnitud": props["mag"],
        "profundidad": props["depth"],
        "latitud": props["lat"],
        "longitud": props["lon"],
        "hora_local": "03:20 pm" # Conversión estática para la prueba
    }).execute()
    print("[✓] ¡Éxito! El sismo ha sido guardado de forma permanente en Supabase.")
    
except Exception as e:
    print(f"[X] Error de conexión con Supabase: {e}")

print("\n[2/2] Ejecutando interfaz visual en consola:")
# Convertimos el payload a string para alimentar tu función nativa
mensaje_ws = json.dumps(payload_falso)
on_message(None, mensaje_ws)

print("\nPrueba de arquitectura finalizada.")