import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/AI/image-gen-studio/storage/providers.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data['providers']:
    has_key = 'YES' if p.get('api_key') else 'NO'
    print(f"{p['id']} | {p['type']} | display={p.get('display_name','')} | name={p['name']} | enabled={p.get('enabled',True)} | key={has_key}")
