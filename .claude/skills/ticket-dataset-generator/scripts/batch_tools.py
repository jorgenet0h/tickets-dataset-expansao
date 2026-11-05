#!/usr/bin/env python3
"""
Ferramentas de apoio para geração de datasets sintéticos de tickets em lotes.

Este script cuida da parte mecânica e repetitiva (escrever CSV com ticket_id
sequencial, consolidar múltiplos lotes, checar duplicatas e balanceamento por
categoria) para que o trabalho criativo de escrever os tickets em si fique
inteiramente no texto gerado pelo modelo, não em código.

Uso:
  # Escreve um lote (JSON -> CSV), atribuindo ticket_id sequencial
  python batch_tools.py write --data lote1.json --out lote1_zero_shot.csv --start-id 1

  # Consolida vários lotes em um único arquivo, com verificação
  python batch_tools.py consolidate --inputs lote1.csv lote2.csv lote3.csv --out consolidado.csv

  # Descobre o próximo ticket_id livre e lista e-mails/nomes já usados
  # (útil antes de escrever um novo lote, para não repetir)
  python batch_tools.py status --inputs lote1.csv lote2.csv
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

# No Windows o console costuma usar cp1252, que não codifica emojis (✅, 📦, ⚠️)
# e derrubava o script no print, depois de o arquivo já ter sido escrito.
# Força UTF-8 na saída; errors="replace" garante que nunca mais levante exceção.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

FIELDS = [
    "ticket_id",
    "nome_remetente",
    "email_remetente",
    "categoria",
    "assunto_email",
    "corpo_email",
    "data_envio",
]


def write_batch(data_path, out_path, start_id):
    """Lê uma lista de tickets (JSON, sem ticket_id) e escreve um CSV com
    ticket_id sequencial a partir de start_id.

    O JSON de entrada é uma lista de objetos com as chaves: nome_remetente,
    email_remetente, categoria, assunto_email, corpo_email, data_envio.
    """
    with open(data_path, encoding="utf-8") as f:
        rows = json.load(f)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(FIELDS)
        for i, row in enumerate(rows, start=start_id):
            w.writerow([
                i,
                row["nome_remetente"],
                row["email_remetente"],
                row["categoria"],
                row["assunto_email"],
                row["corpo_email"],
                row["data_envio"],
            ])

    last_id = start_id + len(rows) - 1
    print(f"✅ {len(rows)} tickets escritos em {out_path} (ticket_id {start_id}–{last_id})")
    print(f"   Próximo ticket_id livre: {last_id + 1}")


def _read_rows(paths):
    all_rows = []
    header = None
    for p in paths:
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
            all_rows.extend(reader)
    return all_rows, header


def _report(all_rows, label=""):
    emails = [r["email_remetente"] for r in all_rows]
    texts = [(r["assunto_email"], r["corpo_email"]) for r in all_rows]
    cats = Counter(r["categoria"] for r in all_rows)

    dup_emails = len(emails) - len(set(emails))
    dup_texts = len(texts) - len(set(texts))

    print(f"{label}Total de tickets: {len(all_rows)}")
    print(f"  E-mails únicos: {len(set(emails))}/{len(emails)} (duplicados: {dup_emails})")
    print(f"  Textos únicos (assunto+corpo): {len(set(texts))}/{len(texts)} (duplicados: {dup_texts})")
    print("  Distribuição por categoria:")
    for cat, n in sorted(cats.items()):
        print(f"    {cat}: {n}")
    if dup_emails or dup_texts:
        print("  ⚠️  Duplicatas encontradas — revise antes de usar para treino ou publicar.")
    return dup_emails, dup_texts


def consolidate(input_paths, out_path):
    all_rows, header = _read_rows(input_paths)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(all_rows)

    print(f"📦 Consolidado em {out_path}")
    _report(all_rows)


def status(input_paths):
    if not input_paths:
        print("Nenhum lote existente — comece do ticket_id 1.")
        return
    all_rows, _ = _read_rows(input_paths)
    if not all_rows:
        print("Arquivos vazios — comece do ticket_id 1.")
        return

    max_id = max(int(r["ticket_id"]) for r in all_rows)
    print(f"Próximo ticket_id livre: {max_id + 1}")
    _report(all_rows, label="")
    print("\nNomes e e-mails já usados (para não repetir no próximo lote):")
    for r in all_rows:
        print(f"  {r['nome_remetente']} <{r['email_remetente']}>")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_write = sub.add_parser("write", help="Escreve um lote (JSON) em CSV com ticket_id sequencial")
    p_write.add_argument("--data", required=True, help="JSON com lista de tickets (sem ticket_id)")
    p_write.add_argument("--out", required=True, help="Caminho do CSV de saída")
    p_write.add_argument("--start-id", type=int, required=True, help="Primeiro ticket_id deste lote")

    p_cons = sub.add_parser("consolidate", help="Consolida vários CSVs de lote em um único arquivo, com verificação")
    p_cons.add_argument("--inputs", nargs="+", required=True, help="CSVs de lote a consolidar, em ordem")
    p_cons.add_argument("--out", required=True, help="Caminho do CSV consolidado de saída")

    p_status = sub.add_parser("status", help="Mostra próximo ticket_id livre e nomes/e-mails já usados")
    p_status.add_argument("--inputs", nargs="*", default=[], help="CSVs de lote já existentes (pode ser vazio)")

    args = parser.parse_args()
    if args.command == "write":
        write_batch(args.data, args.out, args.start_id)
    elif args.command == "consolidate":
        consolidate(args.inputs, args.out)
    elif args.command == "status":
        status(args.inputs)


if __name__ == "__main__":
    main()
