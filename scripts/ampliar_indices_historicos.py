"""Amplia IPCA/IPCA-E com respostas oficiais arquivadas, sem publicar pacotes."""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from liquidacao_custom.index_data.validation import bcb_values


def ampliar():
    directory = ROOT / "backend/data"
    ipca = json.loads((directory / "ipca_oficial.json").read_text(encoding="utf-8"))
    snapshot = json.loads((directory / "indices_simplificados.json").read_text(encoding="utf-8"))
    consultation = date.today().isoformat()
    fetched = {}
    for key, series, start, filename in (
        ("ipca", 433, "01/01/1980", "bcb_ipca_1980_2026.json"),
        ("ipcae_taxas", 10764, "01/01/1992", "bcb_ipcae_1992_2026.json"),
    ):
        previous = ipca["ipca"] if key == "ipca" else snapshot[key]
        end = date.fromisoformat(max(previous) + "-01")
        query = urlencode({"formato": "json", "dataInicial": start, "dataFinal": end.strftime("%d/%m/%Y")})
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?{query}"
        with urlopen(url, timeout=45) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("Resposta oficial excede o limite.")
        rates = bcb_values(json.loads(raw), monthly_series=True)
        from decimal import Decimal
        if not set(previous).issubset(rates) or any(Decimal(str(v)) != Decimal(str(rates[k])) for k, v in previous.items()):
            raise ValueError(f"A série {series} diverge dos valores já utilizados. Revisão necessária.")
        if min(rates) != {"ipca": "1980-01", "ipcae_taxas": "1992-01"}[key]:
            raise ValueError("A fonte não retornou o início histórico esperado.")
        fetched[key] = (filename, raw, rates, {"serie": series, "obtido_em": consultation,
            "url_dados": url, "sha256_resposta_oficial": hashlib.sha256(raw).hexdigest(),
            "primeira_competencia": min(rates), "ultima_competencia": max(rates)})
    # Somente gravar depois de conciliar integralmente as duas séries.
    for filename, raw, _, _ in fetched.values():
        (directory / "fontes" / filename).write_bytes(raw)
    filename, _, rates, metadata = fetched["ipca"]
    ipca.update(ipca=dict(sorted(rates.items())), fonte_historica={**metadata, "arquivo": filename})
    ipca.update(obtido_em=consultation, sha256_resposta_oficial=metadata["sha256_resposta_oficial"],
        urls_consultadas=[metadata["url_dados"]])
    ipca["fontes"]["ipca"] = metadata["url_dados"]
    (directory / "ipca_oficial.json").write_text(json.dumps(ipca, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    filename, _, rates, metadata = fetched["ipcae_taxas"]
    metadata["arquivo"] = filename
    (directory / "fontes/ipcae_historico_fonte.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Consulta corrente das demais séries e IPCA-15 é preservada.
    print(f"IPCA: {len(ipca['ipca'])} competências; IPCA-E histórico conciliado: {len(rates)} competências.")


if __name__ == "__main__":
    ampliar()
