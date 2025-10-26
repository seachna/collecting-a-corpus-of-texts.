"""get_city_links.py Получает список ссылок на страницы городов России со страницы "Список городов России"
и сохраняет их в файл city_links.txt (по одной ссылке в строке).
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
BASE = "https://ru.wikipedia.org"
LIST_URL = "https://ru.wikipedia.org/wiki/Список_городов_России"
resp = requests.get(LIST_URL, headers={"User-Agent":"CorpusBot/1.0 (student@example.com)"})
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")
links = set()
# На странице есть таблицы с ссылками — находим все <a> внутри статьи, фильтруем внутренние ссылки
content = soup.find(id="mw-content-text")
for a in content.find_all("a", href=True):
    href = a['href']
        if href.startswith("/wiki/") and not any(prefix in href for prefix in (":", "/File:", "/Категория:", "/Служебная:")):
        full = urljoin(BASE, href)
        links.add(full)
links = sorted(links)
with open("city_links.txt", "w", encoding="utf-8") as f:
    for u in links:
        f.write(u + "\n")
print(f"Found {len(links)} links. Saved to city_links.txt")
