import requests
from bs4 import BeautifulSoup

url = "https://www.leagueoflegends.com/fr-fr/news/game-updates/patch-14-1-notes/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

sections = soup.find_all(['h2', 'h3', 'p', 'li'])

for section in sections:
    print(section.get_text(strip=True))