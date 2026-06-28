import requests
import json
import urllib3
urllib3.disable_warnings()

url = "http://www.funvisis.gob.ve/maravilla.json"
print("Extrayendo la estructura CRUDA de maravilla.json...\n")

try:
    datos = requests.get(url, verify=False, timeout=10).json()
    
    # Buscamos el primer elemento real de la lista
    if isinstance(datos, list) and len(datos) > 0:
        primer_sismo = datos[0]
    elif isinstance(datos, dict) and 'features' in datos and len(datos['features']) > 0:
        primer_sismo = datos['features'][0]
    else:
        primer_sismo = datos
        
    print("=== CONTENIDO EXACTO DEL PRIMER SISMO ===")
    print(json.dumps(primer_sismo, indent=4, ensure_ascii=False))
    
except Exception as e:
    print(f"Error crítico: {e}")