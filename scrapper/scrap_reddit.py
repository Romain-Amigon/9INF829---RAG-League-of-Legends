import requests
import json
import time

# 1. Configuration initiale
for mot_cle in [ "build", " champions"] :
    url_recherche = f"https://www.reddit.com/r/summonerschool/search.json?q={mot_cle}&restrict_sr=on&limit=10000" # Limité à 5 pour le test
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Recherche des posts pour '{mot_cle}'...")
    reponse = requests.get(url_recherche, headers=headers)
    
    if reponse.status_code == 200:
        donnees_json = reponse.json()
        posts = donnees_json['data']['children']
        donnees_sauvegarde = []
        
        for i, post in enumerate(posts):
            titre = post['data']['title']
            texte_post = post['data']['selftext']
            score = post['data']['score']
            permalink = post['data']['permalink'] # Le lien interne du post
            
            print(f"\n[{i+1}/{len(posts)}] Traitement de : {titre}")
            
            post_complet = {
                "titre": titre,
                "score_post": score,
                "texte": texte_post,
                "commentaires": []
            }
            
            # 2. La DEUXIÈME requête pour récupérer les commentaires de CE post
            # On ajoute .json à la fin du permalink
            url_commentaires = f"https://www.reddit.com{permalink}.json"
            
            # OBLIGATOIRE : Pause pour ne pas se faire bannir par Reddit
            time.sleep(4) 
            
            reponse_commentaires = requests.get(url_commentaires, headers=headers)
            
            if reponse_commentaires.status_code == 200:
                donnees_com = reponse_commentaires.json()
                
                # Reddit renvoie une liste de 2 éléments : [données du post, données des commentaires]
                # On navigue dans l'élément [1] pour les commentaires
                arbre_commentaires = donnees_com[1]['data']['children']
                
                # On boucle sur les commentaires (limité aux 5 premiers pour ne pas polluer)
                for com in arbre_commentaires[:5]:
                    # Certains éléments sont des "MoreComments" (cliquer pour voir plus), on les ignore
                    if com['kind'] == 't1': 
                        texte_com = com['data'].get('body', '')
                        score_com = com['data'].get('score', 0)
                        
                        if texte_com and texte_com != '[deleted]':
                            post_complet["commentaires"].append({
                                "score": score_com,
                                "texte": texte_com
                            })
                            
                print(f" -> {len(post_complet['commentaires'])} commentaires récupérés.")
            else:
                print(f" -> Échec de la récupération des commentaires (Erreur {reponse_commentaires.status_code})")
                
            donnees_sauvegarde.append(post_complet)
    
        # 3. Sauvegarde de l'ensemble
        nom_fichier = f"summonerschool_{mot_cle}.json"
        with open(nom_fichier, "w", encoding="utf-8") as f:
             json.dump(donnees_sauvegarde, f, ensure_ascii=False, indent=4)
             
        print(f"\nTerminé ! Données sauvegardées dans {nom_fichier}")
    
    elif reponse.status_code == 429:
        print("Erreur 429 : Reddit vous demande de ralentir (Rate Limit).")
    else:
        print(f"Erreur HTTP lors de la recherche : {reponse.status_code}")