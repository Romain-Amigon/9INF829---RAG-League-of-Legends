import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import json
import time
import os

def rechercher_et_transcrire(requete, nombre_videos=3, langues=['fr', 'en']):
    fichier_historique = "ids_deja_traites.txt"
    ids_traites = set()

    if os.path.exists(fichier_historique):
        with open(fichier_historique, 'r', encoding='utf-8') as f:
            ids_traites = set(f.read().splitlines())

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
    }

    print(f"Recherche de {nombre_videos} vidéos pour la requête : '{requete}'...")
    video_details = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_query = f"ytsearch{nombre_videos}:{requete}"
        resultats = ydl.extract_info(search_query, download=False)
        
        if 'entries' in resultats:
            for video in resultats['entries']:
                if video['id'] not in ids_traites:
                    video_details.append({
                        'id': video['id'],
                        'titre': video.get('title', 'Titre inconnu'),
                        'url': video.get('url', f"https://www.youtube.com/watch?v={video['id']}")
                    })

    print(f"{len(video_details)} nouvelles vidéos trouvées. Début de l'extraction...\n")
    
    nom_fichier = f"transcriptions_{requete.replace(' ', '_')}.json"
    transcriptions_sauvegardees = []
    
    if os.path.exists(nom_fichier):
        with open(nom_fichier, 'r', encoding='utf-8') as f:
            try:
                transcriptions_sauvegardees = json.load(f)
            except json.JSONDecodeError:
                pass
                
    ytt_api = YouTubeTranscriptApi()

    for detail in video_details:
        vid_id = detail['id']
        print(f"Traitement de : {detail['titre']} (ID: {vid_id})")
        
        try:
            transcript = ytt_api.fetch(vid_id, languages=langues)
            texte_complet = " ".join([snippet.text for snippet in transcript])
            
            detail['transcription'] = texte_complet
            transcriptions_sauvegardees.append(detail)
            print(f"  -> Succès : {len(texte_complet)} caractères extraits.\n")
            with open(fichier_historique, 'a', encoding='utf-8') as f:
                f.write(f"{vid_id}\n")

            with open(nom_fichier, 'w', encoding='utf-8') as f:
                json.dump(transcriptions_sauvegardees, f, ensure_ascii=False, indent=4)
            
        except Exception as e:
            print(f"  -> Échec sur {vid_id}. L'erreur exacte est : {type(e).__name__} - {e}\n")
        

        time.sleep(40)

    print(f"Terminé ! Les résultats sont sauvegardés dans {nom_fichier}")

if __name__ == "__main__":
    rechercher_et_transcrire("league of legends", nombre_videos=5_0000)