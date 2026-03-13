import requests, json

resp = requests.get('http://127.0.0.1:8000/fetch-news?q=AI')
data = resp.json()

with open('api_results.json', 'w') as f:
    json.dump([{'i': i, 'title': d['title'][:70], 'thumb': d['thumbnail'][:100] if d['thumbnail'] else '', 'has_img': bool(d['thumbnail'] and d['thumbnail'].startswith('http'))} for i, d in enumerate(data)], f, indent=2)

print('Done. Check api_results.json')
