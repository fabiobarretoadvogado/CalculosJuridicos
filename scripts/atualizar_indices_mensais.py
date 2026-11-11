"""Consulta INPC/IGP-M no BCB; atualiza somente seus JSON canônicos, sem publicar."""
import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from liquidacao_custom.index_data.validation import monthly


def update(name, consultation, *, check_only=False):
    series = {"inpc": 188, "igpm": 189}[name]
    path = ROOT / "backend/data" / (name + "_oficial.json")
    previous = json.loads(path.read_text(encoding="utf-8"))
    if consultation.isoformat() < previous["obtido_em"] or consultation > date.today():
        raise ValueError("A consulta não pode retroceder ou ser futura.")
    start = date.fromisoformat(min(previous[name]) + "-01")
    query = urlencode({"formato": "json", "dataInicial": start.strftime("%d/%m/%Y"),
                       "dataFinal": consultation.strftime("%d/%m/%Y")})
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?{query}"
    with urlopen(url, timeout=45) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Resposta oficial excede o limite.")
    records = json.loads(raw)
    rates = {datetime.strptime(row["data"], "%d/%m/%Y").strftime("%Y-%m"): row["valor"] for row in records}
    if len(rates) != len(records):
        raise ValueError("Competência oficial duplicada.")
    monthly(rates)
    if not set(previous[name]).issubset(rates) or max(rates) > consultation.strftime("%Y-%m"):
        raise ValueError("A fonte reduziria a cobertura ou contém competência futura.")
    data = {**previous, "serie": series, "obtido_em": consultation.isoformat(),
            "urls_consultadas": [url], name: dict(sorted(rates.items())),
            "sha256_resposta_oficial": hashlib.sha256(raw).hexdigest()}
    if not check_only:
        temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"{name.upper()}: {len(rates)} competências, {min(rates)} a {max(rates)}; "
          + ("conferido sem gravação" if check_only else "JSON canônico atualizado"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serie", choices=("inpc", "igpm", "ambos"), default="ambos")
    parser.add_argument("--consulta", type=date.fromisoformat, default=date.today())
    parser.add_argument("--verificar", action="store_true")
    args = parser.parse_args()
    for name in (("inpc", "igpm") if args.serie == "ambos" else (args.serie,)):
        update(name, args.consulta, check_only=args.verificar)
