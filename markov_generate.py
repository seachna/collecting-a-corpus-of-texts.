from pathlib import Path
import argparse
import csv
import random
import sys
import re
from collections import defaultdict, Counter

# настройка алфавита: русские буквы и выбранные знаки
RUSSIAN_LETTERS = list("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
ALLOWED_SYMBOLS = set(RUSSIAN_LETTERS + [' ', '.', ',', '!', '?'])

def normalize_text(raw: str) -> str:
    """
    Приводит текст к нижнему регистру, оставляет только разрешённые символы,
    заменяя остальные на пробелы, и сворачивает множественные пробелы в один.
    """
    s = raw.lower()
    out_chars = []
    for ch in s:
        if ch in ALLOWED_SYMBOLS:
            out_chars.append(ch)
        else:
            out_chars.append(' ')
    res = ''.join(out_chars)
    res = re.sub(r'\s+', ' ', res)
    return res.strip()

def load_probs_from_csv(probs_dir: Path, k: int):
    """
    Загружает CSV outputs/prob_k{k}.csv.
    Для k>=1: формат context,next,count,probability.
    Для k=0: формат symbol,count,probability.
    Возвращает словарь context -> (list_nexts, list_probs).
    """
    path = probs_dir / f"prob_k{k}.csv"
    if not path.exists():
        return None
    mapping = defaultdict(lambda: ([], []))
    if k == 0:
        with path.open("r", encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            syms = []
            probs = []
            for row in reader:
                if not row:
                    continue
                sym = row[0]
                p = float(row[2]) if len(row) > 2 else 0.0
                syms.append(sym)
                probs.append(p)
        mapping[''] = (syms, probs)
        return mapping
    with path.open("r", encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row:
                continue
            context = row[0]
            nxt = row[1]
            prob = float(row[3]) if len(row) > 3 else None
            lst, w = mapping[context]
            lst.append(nxt)
            w.append(prob)
    return mapping

def build_counts_from_corpus(corpus_path: Path, k: int):
    """
    Пересчёт частот контекст->next для данного k из корпуса.
    Возвращает mapping context -> (list_nexts, list_probs).
    """
    raw = corpus_path.read_text(encoding='utf-8', errors='ignore')
    text = normalize_text(raw)
    n = len(text)
    counts = defaultdict(Counter)
    for i in range(k, n):
        ctx = text[i-k:i]
        nxt = text[i]
        if all(ch in ALLOWED_SYMBOLS for ch in ctx) and nxt in ALLOWED_SYMBOLS:
            counts[ctx][nxt] += 1
    mapping = {}
    for ctx, cnt in counts.items():
        total = sum(cnt.values())
        nexts = []
        probs = []
        for ch, c in cnt.items():
            nexts.append(ch)
            probs.append(c/total)
        mapping[ctx] = (nexts, probs)
    if k == 0:
        counter0 = Counter(text)
        total0 = sum(counter0[ch] for ch in counter0 if ch in ALLOWED_SYMBOLS)
        syms = []
        probs = []
        for ch, c in counter0.most_common():
            if ch in ALLOWED_SYMBOLS:
                syms.append(ch)
                probs.append(c/total0)
        return {'': (syms, probs)}
    return mapping

def sample_next(nexts, probs):
    """
    Выбор следующего символа с учётом вероятностей.
    Если вероятности отсутствуют, выбирается случайный символ равновероятно.
    """
    if not nexts:
        return None
    if any(p is None for p in probs):
        return random.choice(nexts)
    return random.choices(nexts, weights=probs, k=1)[0]

def generate_text(mapping, k, seed, length, fallback_mapping=None):
    """
    Генерация текста длины length.
    mapping: словарь для текущего k; fallback_mapping: словари для меньших k (k-1...0).
    При отсутствии контекста используется бэкофф к меньшему k.
    """
    out = seed
    seed_norm = normalize_text(seed)
    if len(seed_norm) == 0:
        if isinstance(fallback_mapping, dict) and 0 in fallback_mapping and '' in fallback_mapping[0]:
            syms, probs = fallback_mapping[0]['']
            out += sample_next(syms, probs)
        else:
            out += ' '
        seed_norm = normalize_text(out)
    cur = seed_norm
    if len(cur) < k:
        cur = (' ' * (k - len(cur))) + cur
    for _ in range(length):
        context = cur[-k:] if k > 0 else ''
        chosen = None
        kk = k
        while kk >= 0:
            if kk == 0:
                map0 = fallback_mapping.get(0) if isinstance(fallback_mapping, dict) else None
                if map0 and '' in map0:
                    nexts, probs = map0['']
                    chosen = sample_next(nexts, probs)
                    break
                if context == '' and '' in mapping:
                    nexts, probs = mapping['']
                    chosen = sample_next(nexts, probs)
                    break
                chosen = ' '
                break
            ctx_try = context[-kk:]
            if isinstance(fallback_mapping, dict) and kk in fallback_mapping:
                mm = fallback_mapping[kk]
                if ctx_try in mm:
                    nexts, probs = mm[ctx_try]
                    chosen = sample_next(nexts, probs)
                    break
            if kk == k and ctx_try in mapping:
                nexts, probs = mapping[ctx_try]
                chosen = sample_next(nexts, probs)
                break
            kk -= 1
        if chosen is None:
            chosen = ' '
        out += chosen
        cur += chosen
    return out

def parse_args():
    """
    Разбор аргументов командной строки.
    """
    p = argparse.ArgumentParser(description="Генерация текста по Маркову (использует prob_k CSV из outputs/)")
    p.add_argument("--k", type=int, default=3, help="Порядок цепи Маркова (k).")
    p.add_argument("--length", type=int, default=400, help="Длина генерируемого текста (символов).")
    p.add_argument("--seed", type=str, default=" ", help="Начальная seed-строка.")
    p.add_argument("--seedfile", type=str, default=None, help="Файл с seed-текстом.")
    p.add_argument("--probs", type=str, default="outputs", help="Папка с prob_k{K}.csv (outputs).")
    p.add_argument("--corpus", type=str, default=None, help="Путь к корпусу, если нужно пересчитать распределения.")
    p.add_argument("--recompute", action="store_true", help="Пересчитать распределения из корпуса, если prob_k нет.")
    p.add_argument("--out", type=str, default=None, help="Записать результат в файл.")
    return p.parse_args()

def main():
    args = parse_args()
    k = args.k
    length = args.length
    seed = args.seed
    if args.seedfile:
        seed = Path(args.seedfile).read_text(encoding='utf-8', errors='ignore')
    probs_dir = Path(args.probs)
    mapping = load_probs_from_csv(probs_dir, k)
    fallback = {}
    for kk in range(k-1, -1, -1):
        m = load_probs_from_csv(probs_dir, kk)
        if m:
            fallback[kk] = m
    if mapping is None:
        if args.corpus and args.recompute:
            print("CSV для k=", k, " не найдены. Пересчитываем распределения из корпуса...")
            mapping = build_counts_from_corpus(Path(args.corpus), k)
            for kk in range(k-1, -1, -1):
                fallback[kk] = build_counts_from_corpus(Path(args.corpus), kk)
        else:
            print(f"Файл {probs_dir}/prob_k{k}.csv не найден и --recompute не указан. Завершаю.", file=sys.stderr)
            sys.exit(1)
    if 0 not in fallback:
        m0 = load_probs_from_csv(probs_dir, 0)
        if m0:
            fallback[0] = m0
    generated = generate_text(mapping, k, seed, length, fallback_mapping=fallback)
    if args.out:
        Path(args.out).write_text(generated, encoding='utf-8')
        print(f"Сохранено в {args.out}")
    else:
        print("\nСгенерированный текст\n")
        print(generated)
        print("\nКонец\n")

if __name__ == "__main__":
    main()
