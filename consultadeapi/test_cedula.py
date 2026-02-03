import requests
import json

url = 'https://api.panamaemprende.gob.pa/api/consulta/multiple/8-237-715'
headers = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

r = requests.get(url, headers=headers)
data = r.json()

# Guardamos todo para análisis
with open('resultado_8-237-715.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

empresas = data.get('data', {}).get('data', [])
print(f"Total empresas encontradas: {len(empresas)}\n")

for e in empresas:
    nombre = e.get('nombreComercial')
    id_emp = e.get('id_empresa')
    print(f"Empresa: {nombre}")
    print(f"PDF: https://www.panamaemprende.gob.pa/Empresa/pdf/{id_emp}")
    print("-" * 40)
