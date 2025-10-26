"""corpus_stats_full.py Считает характеристики итогового корпуса corpus_cities_raw.txt:
байты, символы, слова (токены), уникальные слова (types), TTR, топ-50 слов, энтропию по символам, размер gzip.

"""

import re, math, gzip
from collections import Counter
from pathlib import Path
p = Path("corpus_cities_raw.txt")
assert p.exists(), "Создайте файл corpus_cities_raw.txt (cat cities/*.txt > ...)"
raw = p.read_text(encoding='utf-8', errors='ignore')
bytes_size = p.stat().st_size
chars = len(raw)
chars_no_spaces = len(re.sub(r'\s','', raw))
tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9']+", raw.lower())
num_tokens = len(tokens)
vocab = Counter(tokens)
num_types = len(vocab)
ttr = num_types / num_tokens if num_tokens else 0.0
top50 = vocab.most_common(50)
freq = Counter(raw)
H = 0.0
for c, cnt in freq.items():
    p_c = cnt / chars
    H -= p_c * math.log2(p_c)
gz = gzip.compress(raw.encode('utf-8'), compresslevel=9)
gzip_size = len(gz)
print("Bytes:", bytes_size, "(", bytes_size/1024/1024, "MB )")
print("Chars:", chars, "Chars (no spaces):", chars_no_spaces)
print("Tokens:", num_tokens, "Types:", num_types, "TTR:", round(ttr,4))
print("Top 50 words:", top50[:50])
print("Shannon entropy (bits/char):", round(H,3))
print("Gzip size (bytes):", gzip_size, "(", gzip_size/1024/1024, "MB )")
