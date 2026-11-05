#!/usr/bin/env python3
"""
Mede a diversidade textual de datasets de tickets: Self-BLEU-2/3/4 e Distinct-1/2/3.

Self-BLEU: média do BLEU de cada ticket contra todos os outros do mesmo conjunto.
  Quanto MENOR, mais diverso (valores altos indicam textos parecidos entre si).
Distinct-n: proporção de n-gramas únicos sobre o total de n-gramas.
  Quanto MAIOR, mais diverso.

A tokenização põe tudo em minúsculas e remove acentos, então "não" e "nao" contam
como a mesma palavra (importante ao comparar estilos formal e casual).

Uso:
  # Um ou mais conjuntos, cada um como rotulo=caminho.csv
  python diversity.py --inputs zero-shot=lote1_zero_shot.csv few-shot=lote1_few_shot.csv

  # Usar assunto + corpo em vez de só o corpo
  python diversity.py --inputs a=a.csv b=b.csv --fields assunto_email corpo_email

  # Conferir a implementação contra o NLTK (se instalado)
  python diversity.py --inputs a=a.csv --check-nltk

Cuidados ao interpretar: com poucas centenas de tickets as diferenças pequenas não
são significativas; Self-BLEU por categoria usa menos referências e por isso dá
valores menores que o global; textos mais curtos tendem a ter Distinct-n menor.
"""
import argparse
import csv
import math
import re
import sys
import unicodedata
from collections import Counter

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def tok(s):
    """Minúsculas, sem acentos, só palavras (letras/dígitos)."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"\w+", s)


def ngrams(t, n):
    return Counter(tuple(t[i:i + n]) for i in range(len(t) - n + 1))


def bleu(hyp, refs, N):
    """BLEU-N com pesos uniformes, contagem clipada contra o máximo entre as
    referências, brevity penalty pela referência de comprimento mais próximo e
    suavização tipo 'method1' do NLTK (epsilon 0.1 quando a contagem é zero)."""
    if len(hyp) < N:
        return None
    logs = 0.0
    for n in range(1, N + 1):
        h = ngrams(hyp, n)
        total = sum(h.values())
        maxref = Counter()
        for r in refs:
            for g, c in ngrams(r, n).items():
                if c > maxref[g]:
                    maxref[g] = c
        clipped = sum(min(c, maxref[g]) for g, c in h.items())
        p = (clipped if clipped else 0.1) / total
        logs += math.log(p) / N
    hl = len(hyp)
    rl = min((len(r) for r in refs), key=lambda L: (abs(L - hl), L))
    bp = 1.0 if hl > rl else math.exp(1 - rl / hl)
    return bp * math.exp(logs)


def self_bleu(docs, N):
    toks = [tok(d) for d in docs]
    scores = [bleu(t, toks[:i] + toks[i + 1:], N) for i, t in enumerate(toks)]
    scores = [s for s in scores if s is not None]
    return sum(scores) / len(scores)


def distinct(docs, n):
    seen, total = set(), 0
    for d in docs:
        g = ngrams(tok(d), n)
        seen.update(g)
        total += sum(g.values())
    return len(seen) / total


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_inputs(items):
    out = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--inputs espera rotulo=caminho.csv, recebi: {item}")
        label, path = item.split("=", 1)
        out[label] = load(path)
    return out


def report(data, fields):
    getter = lambda r: " ".join(r[f] for f in fields)
    cols = ["Self-BLEU-2", "Self-BLEU-3", "Self-BLEU-4", "Distinct-1", "Distinct-2", "Distinct-3"]
    print(f"Campos: {' + '.join(fields)}\n")
    print(f"{'conjunto':<12}{'tickets':>8}{'tokens/ticket':>15}" + "".join(f"{c:>13}" for c in cols))
    for label, rows in data.items():
        docs = [getter(r) for r in rows]
        avg = sum(len(tok(d)) for d in docs) / len(docs)
        vals = [self_bleu(docs, 2), self_bleu(docs, 3), self_bleu(docs, 4),
                distinct(docs, 1), distinct(docs, 2), distinct(docs, 3)]
        print(f"{label:<12}{len(docs):>8}{avg:>15.1f}" + "".join(f"{v:>13.4f}" for v in vals))

    cats = sorted({r["categoria"] for rows in data.values() for r in rows})
    print("\nSelf-BLEU-4 dentro de cada categoria (referências = só tickets da mesma categoria):")
    print(f"{'categoria':<16}" + "".join(f"{label:>14}" for label in data))
    for c in cats:
        line = f"{c:<16}"
        for rows in data.values():
            docs = [getter(r) for r in rows if r["categoria"] == c]
            line += f"{self_bleu(docs, 4):>14.4f}" if len(docs) > 1 else f"{'n/a':>14}"
        print(line)


def check_nltk(data, fields):
    try:
        from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
    except ImportError:
        print("\n[nltk não instalado: sem conferência cruzada]")
        return
    sm = SmoothingFunction().method1
    for label, rows in data.items():
        docs = [" ".join(r[f] for f in fields) for r in rows]
        toks = [tok(d) for d in docs]
        ref = sum(sentence_bleu(toks[:i] + toks[i + 1:], t, weights=(.25,) * 4, smoothing_function=sm)
                  for i, t in enumerate(toks)) / len(toks)
        print(f"[conferência NLTK] {label}: Self-BLEU-4 = {ref:.4f} (nossa implementação: {self_bleu(docs, 4):.4f})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inputs", nargs="+", required=True, help="um ou mais rotulo=caminho.csv")
    p.add_argument("--fields", nargs="+", default=["corpo_email"], help="colunas de texto (padrão: corpo_email)")
    p.add_argument("--check-nltk", action="store_true", help="conferir Self-BLEU-4 contra o NLTK, se instalado")
    args = p.parse_args()
    data = parse_inputs(args.inputs)
    report(data, args.fields)
    if args.check_nltk:
        check_nltk(data, args.fields)


if __name__ == "__main__":
    main()
