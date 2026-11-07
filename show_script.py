from pipeline.veille import fetch_all_rss
from pipeline.selection import run_selection
from pipeline.script import generer_script_safe
from datetime import datetime
import json

articles = fetch_all_rss(36)
selected = run_selection(articles)

if selected:
    if isinstance(selected.get('date'), datetime):
        selected['date'] = selected['date'].strftime('%d/%m/%Y')
    
    script = generer_script_safe(selected)
    
    # Save to file
    with open('output/script_latest.json', 'w', encoding='utf-8') as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    
    print('Script saved to output/script_latest.json')
    print()
    print('=== FR ===')
    print(f"Titre: {script['fr']['titre']}")
    for k, v in script['fr']['blocs'].items():
        print(f"  {k}: {v}")
    print()
    print('=== EN ===')
    print(f"Titre: {script['en']['titre']}")
    for k, v in script['en']['blocs'].items():
        print(f"  {k}: {v}")
    print()
    print('=== ES ===')
    print(f"Titre: {script['es']['titre']}")
    for k, v in script['es']['blocs'].items():
        print(f"  {k}: {v}")
    print()
    print('Hashtags:', script.get('hashtags', {}))