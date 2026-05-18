from bs4 import BeautifulSoup
import time
import os
import requests

# 1. Création d'un dossier pour ranger proprement les fichiers textes
dossier_destination = "wiki/champions"
if not os.path.exists(dossier_destination):
    os.makedirs(dossier_destination)

champions = [
    "Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Ambessa", "Amumu", "Anivia", "Annie", "Aphelios", "Ashe", "Aurelion Sol", "Aurora", "Azir",
    "Bard", "Bel'Veth", "Blitzcrank", "Brand", "Braum", "Briar",
    "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki",
    "Darius", "Diana", "Dr. Mundo", "Draven",
    "Ekko", "Elise", "Evelynn", "Ezreal",
    "Fiddlesticks", "Fiora", "Fizz",
    "Galio", "Gangplank", "Garen", "Gnar", "Gragas", "Graves", "Gwen",
    "Hecarim", "Heimerdinger", "Hwei",
    "Illaoi", "Irelia", "Ivern",
    "Janna", "Jarvan IV", "Jax", "Jayce", "Jhin", "Jinx",
    "K'Sante", "Kai'Sa", "Kalista", "Karma", "Karthus", "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix", "Kindred", "Kled", "Kog'Maw",
    "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra", "Lucian", "Lulu", "Lux",
    "Malphite", "Malzahar", "Maokai", "Master Yi", "Mel", "Milio", "Miss Fortune", "Mordekaiser", "Morgana",
    "Naafiri", "Nami", "Nasus", "Nautilus", "Neeko", "Nidalee", "Nilah", "Nocturne", "Nunu & Willump",
    "Olaf", "Orianna", "Ornn",
    "Pantheon", "Poppy", "Pyke",
    "Qiyana", "Quinn",
    "Rakan", "Rammus", "Rek'Sai", "Rell", "Renata Glasc", "Renekton", "Rengar", "Riven", "Rumble", "Ryze",
    "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen", "Shyvana", "Singed", "Sion", "Sivir", "Skarner", "Smolder", "Sona", "Soraka", "Swain", "Sylas", "Syndra",
    "Tahm Kench", "Taliyah", "Talon", "Taric", "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate", "Twitch",
    "Urgot",
    "Varus", "Vayne", "Veigar", "Vel'Koz", "Vex", "Vi", "Viego", "Viktor", "Vladimir", "Volibear",
    "Warwick", "Wukong",
    "Xayah", "Xin Zhao",
    "Yasuo", "Yone", "Yorick", "Yuumi",
    "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
]

for nom in champions:
    print(f"Scraping en cours pour {nom}...")
    
    # Rappel : L'URL canonique utilise souvent /LoL à la fin
    url = f"https://leagueoflegends.fandom.com/wiki/{nom}"
    
    try:
        headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # On ajoute l'argument headers= à notre requête
        reponse = requests.get(url, headers=headers)
        
        # Vérifier que la page existe (Code 200 = OK)
        if reponse.status_code == 200:
            soup = BeautifulSoup(reponse.content, 'html.parser')
            
            # Cibler UNIQUEMENT la zone de l'article (exclut les menus Fandom)
            contenu_principal = soup.find('div', class_='mw-parser-output')
            
            if contenu_principal:
                # Extraire le texte en insérant des retours à la ligne entre les balises HTML
                texte_brut = contenu_principal.get_text(separator='\n', strip=True)
                
                # Définir le chemin d'enregistrement (ex: champions_textes/Aatrox.txt)
                chemin_fichier = os.path.join(dossier_destination, f"{nom}.txt")
                
                # 2. Enregistrer le texte dans le fichier
                # L'encodage utf-8 est indispensable pour les apostrophes et accents
                with open(chemin_fichier, "w", encoding="utf-8") as fichier:
                    fichier.write(texte_brut)
                    
                print(f"   -> Fichier {nom}.txt créé avec succès !")
            else:
                print(f"   -> Avertissement : Contenu principal introuvable pour {nom}.")
        else:
             print(f"   -> Erreur {reponse.status_code} : La page de {nom} n'existe pas ou l'URL est incorrecte.")
             
    except Exception as e:
        print(f"   -> Erreur lors de la requête pour {nom}: {e}")

    # 3. La pause vitale pour éviter le bannissement d'IP
    time.sleep(1)

print("Terminé !")