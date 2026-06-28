import requests
import urllib3
urllib3.disable_warnings()

print("Descargando el GeoJSON de FUNVISIS...\n")
url = "http://www.funvisis.gob.ve/data/venezuela.geojson"

try:
    datos = requests.get(url, verify=False).json()
    sismo_ejemplo = datos['features'][0]['properties']
    
    print("=== ESTRUCTURA SECRETA DE FUNVISIS ===")
    for llave, valor in sismo_ejemplo.items():
        print(f"Variable: '{llave}' -> Contenido: {valor}")
        
except Exception as e:
    print(f"Error: {e}")