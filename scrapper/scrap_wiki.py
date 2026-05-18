import requests
from bs4 import BeautifulSoup

url = "https://leagueoflegends.fandom.com/wiki/Ahri"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

skills = soup.find_all('div', class_='skill')
for skill in skills:
    print(skill.get_text(strip=True))