import argparse
from collections import Counter, defaultdict
from pathlib import Path
import math
import csv
import re
import sys

# Русские буквы в нижнем регистре 
RUSSIAN_LETTERS = list("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
# Разрешённые символы: буквы + пробел + знаки пунктуации
ALLOWED_SYMBOLS = set(RUSSIAN_LETTERS + [' ', '.', ',', '!', '?'])
SPACE = ' '

def normalize_text(raw: str) -> str:
    #перевод в нижний регистр, замена всех символов, не входящих в ALLOWED_SYMBOLS, на пробел,
    #сворачивание последовательностей пробельных символов в один пробел, обрезка начальных/конечных пробелов
    s = raw.lower()  # привести всё к нижнему регистру
    out_chars = []
    for ch in s:
        if ch in ALLOWED_SYMBOLS:
            out_chars.append(ch)
        else:
            # заменяем цифры, скобки, кавычки и т.д. на пробел
            out_chars.append(' ')
    res = ''.join(out_chars)
    # заменить любую последовательность пробельных символов на один пробел
    res = re.sub(r'\s+', ' ', res)
    return res.strip()

def conditional_entropy_from_counters(context_counts):
    #Вычислить среднюю условную энтропию 
    #Формула: H = sum_c P(c) * H(next | c), где P(c) = total_count(c) / total_transitions
    total_transitions = 0
    for cnt in context_counts.values():
        total_transitions += sum(cnt.values())
    if total_transitions == 0:
        return 0.0
    H = 0.0
    for cnt in context_counts.values():
        s = sum(cnt.values())
        p_c = s / total_transitions
        # энтропия для данного контекста c
        h_c = 0.0
        for v in cnt.values():
            p = v / s
            h_c -= p * math.log2(p)
        H += p_c * h_c
    return H

def save_probabilities_k0(counter0: Counter, total0: int, out_csv: Path):
    #Сохранить распределение символов 
    with out_csv.open("w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["symbol", "count", "probability"])
        # сортируем по убыванию частоты
        for sym, c in sorted(counter0.items(), key=lambda x: -x[1]):
            if sym in ALLOWED_SYMBOLS:
                p = c / total0 if total0 > 0 else 0.0
                writer.writerow([sym, c, f"{p:.6f}"])
    print(f"Сохранены вероятности k=0 в {out_csv}")

def process_corpus(corpus_path: Path, max_k: int = 16, min_count: int = 1, outputs_dir: Path = Path("outputs")):
    #загружает корпус, нормализует текст, cчитает частоты для k = 0..max_k, сохраняет CSV с условными вероятностями и текстовые summary-файлы
    #Параметры: corpus_path -- путь к файлу корпуса (utf-8), max_k -- максимальный порядок марковской цепи
    #min_count -- минимальное суммарное число переходов для контекста (фильтрация), outputs_dir -- папка для результатов
    if not corpus_path.exists():
        print(f"Ошибка: файл корпуса не найден: {corpus_path}", file=sys.stderr)
        return

    print(f"Загрузка корпуса: {corpus_path}")
    raw = corpus_path.read_text(encoding='utf-8', errors='ignore')

    print("Нормализация текста...")
    text = normalize_text(raw)
    n = len(text)
    print(f"Длина нормализованного текста: {n} символов")

    outputs_dir.mkdir(exist_ok=True, parents=True)

    # k = 0: распределение одиночных символов
    counter0 = Counter(text)
    total0 = sum(counter0[ch] for ch in counter0 if ch in ALLOWED_SYMBOLS)
    print(f"Всего символов (k=0, учтённые): {total0}")
    save_probabilities_k0(counter0, total0, outputs_dir / "prob_k0.csv")

    # k >= 1: контексты и переходы 
    for k in range(1, max_k + 1):
        print("\n" + "="*60)
        print(f"Обработка порядка k = {k} ...")
        context_counts = defaultdict(Counter)
        transitions = 0

        #позиция i — индекс следующего символа,
        #контекст — text[i-k:i]
        for i in range(k, n):
            context = text[i-k:i]
            next_ch = text[i]
            # учитываем только те случаи, где контекст и следующий символ состоят из разрешённых символов
            if all((ch in ALLOWED_SYMBOLS) for ch in context) and (next_ch in ALLOWED_SYMBOLS):
                context_counts[context][next_ch] += 1
                transitions += 1

        print(f"Найдено переходов (всего) для k={k}: {transitions}")

        # фильтрация по минимальному числу вхождений контекста (если задано)
        if min_count > 1:
            before = len(context_counts)
            context_counts = {c: cnt for c, cnt in context_counts.items() if sum(cnt.values()) >= min_count}
            after = len(context_counts)
            print(f"Отфильтровано контекстов с суммой < {min_count}: {before} -> {after}")

        # Сохранение CSV с вероятностями: context,next,count,probability
        out_csv = outputs_dir / f"prob_k{k}.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as csvf:
            writer = csv.writer(csvf)
            writer.writerow(["context", "next", "count", "probability"])
            # проходим по каждому контексту и записываем распределение условной вероятности
            for context, cnt in context_counts.items():
                s = sum(cnt.values())
                # пропускаем пустые (на всякий случай)
                if s == 0:
                    continue
                for nxt, c in cnt.items():
                    prob = c / s
                    writer.writerow([context, nxt, c, f"{prob:.6f}"])

        # Сохранение сводного файла summary (кол-во контекстов, условная энтропия и т.д.)
        H_cond = conditional_entropy_from_counters(context_counts)
        num_contexts = len(context_counts)
        summary_path = outputs_dir / f"summary_k{k}.txt"
        with summary_path.open("w", encoding="utf-8") as fsum:
            fsum.write(f"k = {k}\n")
            fsum.write(f"Total transitions counted: {transitions}\n")
            fsum.write(f"Number of contexts (unique): {num_contexts}\n")
            fsum.write(f"Conditional entropy H(next|context): {H_cond:.6f} bits\n")
            fsum.write("\nTop contexts by total count (up to 20):\n")
            # выбираем топ-контекстов по суммарным вхождениям
            top_contexts = sorted(context_counts.items(), key=lambda x: -sum(x[1].values()))[:20]
            for context, cnt in top_contexts:
                s = sum(cnt.values())
                fsum.write(f"Context '{context}' ({s} occurrences): top next -> ")
                topn = cnt.most_common(5)
                fsum.write(", ".join([f"'{ch}':{c}({c/s:.3f})" for ch, c in topn]) + "\n")

        print(f"Сохранены файлы: {out_csv} и {summary_path}")

    total_counts = sum(counter0.values())
    H0 = 0.0
    for ch, c in counter0.items():
        if ch in ALLOWED_SYMBOLS and c > 0:
            p = c / total_counts
            H0 -= p * math.log2(p)
    with (outputs_dir / "overall_summary.txt").open("w", encoding="utf-8") as osf:
        osf.write(f"Corpus length (chars): {n}\n")
        osf.write(f"Unique symbols (allowed): {len(ALLOWED_SYMBOLS)}\n")
        osf.write(f"Total counts (k=0): {total_counts}\n")
        osf.write(f"Entropy H0 (single char): {H0:.6f} bits\n")

    print("\nГотово. Результаты записаны в папку:", outputs_dir)


def parse_args():
    #Разбор аргументов командной строки
    p = argparse.ArgumentParser(description="Вычисление марковских условных вероятностей для k=0..K")
    p.add_argument("--corpus", required=True, help="Путь к файлу корпуса (UTF-8)")
    p.add_argument("--max_k", type=int, default=16, help="Максимальный порядок k (по умолчанию 16)")
    p.add_argument("--min_count", type=int, default=1, help="Минимальная суммарная частота контекста для сохранения (по умолчанию 1)")
    p.add_argument("--outputs", default="outputs", help="Папка для вывода CSV и summary")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    corpus_path = Path(args.corpus)
    process_corpus(corpus_path, max_k=args.max_k, min_count=args.min_count, outputs_dir=Path(args.outputs))
