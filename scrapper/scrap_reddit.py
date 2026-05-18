import requests
import json
import time

# 1. On construit l'URL de recherche en ajoutant .json
# q=wave+management (la recherche) | restrict_sr=on (limiter au subreddit) | limit=5 (nombre de posts)
url = "https://www.reddit.com/r/summonerschool/search.json?q=matchup&restrict_sr=on&limit=10000"

# 2. Le User-Agent est OBLIGATOIRE, sinon Reddit renvoie une erreur 429 (Too Many Requests)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print("Récupération des données...")
reponse = requests.get(url, headers=headers)

if reponse.status_code == 200:
    donnees_json = reponse.json()
    
    # 3. Naviguer dans le dictionnaire JSON de Reddit
    posts = donnees_json['data']['children']
    
    donnees_sauvegarde = []
    
    for post in posts:
        titre = post['data']['title']
        texte = post['data']['selftext'] # selftext = le contenu du post
        score = post['data']['score']
        
        print(f"\n--- {titre} (Score: {score}) ---")
        # On affiche juste les 100 premiers caractères pour vérifier
        print(texte[:100] + "...") 
        
        donnees_sauvegarde.append({
            "titre": titre,
            "texte": texte,
            "score": score
        })
        
    # Optionnel : Sauvegarder en fichier texte/JSON pour votre RAG
    with open("summonerschool_matchups.json", "w", encoding="utf-8") as f:
         json.dump(donnees_sauvegarde, f, ensure_ascii=False, indent=4)
         
elif reponse.status_code == 429:
    print("Erreur 429 : Reddit vous demande de ralentir (Rate Limit).")
else:
    print(f"Erreur : {reponse.status_code}")