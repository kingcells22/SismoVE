import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("Iniciando prueba de penetración a FUNVISIS...")
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    respuesta = requests.get("http://www.funvisis.gob.ve/", headers=headers, verify=False, timeout=15)
    html = respuesta.text
    
    soup = BeautifulSoup(html, 'html.parser')
    filas = soup.find_all('tr')
    
    print(f"[✓] Conexión exitosa. Se encontraron {len(filas)} filas HTML (<tr>).")
    
    # Vamos a imprimir en crudo las primeras 5 filas que tengan suficientes columnas
    contador = 0
    for f in filas:
        columnas = f.find_all('td')
        if len(columnas) >= 5:
            print(f"\n--- Analizando Fila ---")
            print(f"Columna 0 (Fecha): '{columnas[0].text.strip()}'")
            print(f"Columna 1 (Hora): '{columnas[1].text.strip()}'")
            print(f"Columna 2 (Mag): '{columnas[2].text.strip()}'")
            print(f"Columna 3 (Prof): '{columnas[3].text.strip()}'")
            print(f"Columna 4 (Región): '{columnas[4].text.strip()}'")
            contador += 1
            if contador >= 5: 
                break

    if contador == 0:
        print("\n[!] No se encontró ninguna tabla con el formato esperado. FUNVISIS cambió su diseño web.")

except Exception as e:
    print(f"\n[X] Error crítico conectando con FUNVISIS: {e}")