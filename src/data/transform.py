import json
import os
from fpdf import FPDF

dossier_rag = "rag"
os.makedirs(dossier_rag, exist_ok=True)

for doc in os.listdir('raw'):
    chemin_brut = os.path.join('raw', doc)
    
    if "summonerschool" in doc:
        with open(chemin_brut, "r", encoding="utf-8") as f:
            posts = json.load(f)
        
        for i, post in enumerate(posts):
            chemin_fichier = os.path.join(dossier_rag, f"reddit_{i}.pdf")
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            titre = str(post.get('titre', ''))
            score = str(post.get('score', ''))
            texte = str(post.get('texte', ''))
            
            titre_propre = titre.encode('latin-1', 'replace').decode('latin-1')
            texte_propre = texte.encode('latin-1', 'replace').decode('latin-1')
            
            # ... (votre code d'initialisation FPDF reste identique) ...

            pdf.multi_cell(0, 10, txt=f"Title: {titre_propre}")
            pdf.multi_cell(0, 10, txt=f"Score: {score}")
            pdf.multi_cell(0, 10, txt="--- POST CONTENT ---")
            pdf.multi_cell(0, 10, txt=texte_propre)
            
            # Ajout de la boucle pour les commentaires
            commentaires = post.get('commentaires', [])
            if commentaires:
                pdf.multi_cell(0, 10, txt="\n--- TOP COMMENTS ---")
                for c, com in enumerate(commentaires):
                    texte_com_propre = str(com.get('texte', '')).encode('latin-1', 'replace').decode('latin-1')
                    score_com = com.get('score', 0)
                    pdf.multi_cell(0, 10, txt=f"\n[Comment {c+1} | Score: {score_com}]")
                    pdf.multi_cell(0, 10, txt=texte_com_propre)
            
            pdf.output(chemin_fichier)
            
    elif "transcriptions" in doc:
        with open(chemin_brut, "r", encoding="utf-8") as f:
            videos = json.load(f)
        
        for i, video in enumerate(videos):
            chemin_fichier = os.path.join(dossier_rag, f"transcription_{i}.txt")
            
            with open(chemin_fichier, "w", encoding="utf-8") as f:
                f.write(f"Title: {video.get('titre', '')}\n")
                f.write(f"URL: {video.get('url', '')}\n\n")
                f.write(f"Content:\n{video.get('transcription', '')}\n")