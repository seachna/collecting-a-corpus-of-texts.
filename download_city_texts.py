""" download_city_texts.py Скачивает страницы по списку URL из city_links.txt, извлекает основной текст и
сохраняет каждый город в отдельный файл в папке cities/.
"""
import requests, time, os, re
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, unquote
outdir = Path("cities")
outdir.mkdir(exist_ok=True)
headers = {"User-Agent":"CorpusBot/1.0 (student@example.com)"}
with open("city_links.txt", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]
for i, url in enumerate(urls, start=1):
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.find(id="mw-content-text")
        if not content:
            content = soup.body
        # собираем только параграфы и заголовки (p, h1..h3, li)
        parts = []
        for tag in content.find_all(['h1','h2','h3','p','li']):
            text = tag.get_text(separator=" ", strip=True)
            if text:
                parts.append(text)
        text = "\n\n".join(parts)
        # очистка лишних пробелов
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        # сделаем безопасное имя файла: взять последний сегмент URL
        name = unquote(urlparse(url).path.split("/")[-1])
        fname = outdir / f"{i:04d}_{name}.txt"
        with open(fname, "w", encoding="utf-8") as out:
            out.write(text)
        print(f"[{i}/{len(urls)}] Saved {fname} ({len(text)} chars)")
    except Exception as e:
        print(f"[{i}] ERROR downloading {url}: {e}")
    time.sleep(1.2)  # пауза между запросами
