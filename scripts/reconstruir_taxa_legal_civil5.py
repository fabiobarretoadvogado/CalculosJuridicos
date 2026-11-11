"""Consulta fontes históricas oficiais e grava somente a base exclusiva do Civil 5."""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from liquidacao_custom.index_data.taxa_legal_reconstruida import ARQUIVO, FONTES, METODOLOGIA, reconstruir_fontes, validar_reconstrucao


def gerar(directory):
    queries = [(1178, "01/05/2000", "31/12/2009"), (1178, "01/01/2010", "31/12/2019"),
               (1178, "01/01/2020", "30/11/2024"), (7478, "01/05/2000", "30/11/2024")]

    def fetch(item):
        name, (series, start, end) = item
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?" + urlencode(
            {"formato": "json", "dataInicial": start, "dataFinal": end})
        with urlopen(url, timeout=45) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024 or not isinstance(json.loads(raw), list):
            raise ValueError("Resposta histórica oficial inválida.")
        return name, raw, url

    results = list(ThreadPoolExecutor(max_workers=4).map(fetch, zip(FONTES, queries)))
    for name, raw, _ in results:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    reconstructed = reconstruir_fontes(directory)
    historic = {k: v for k, v in reconstructed.items() if k <= "2024-08"}
    snapshot = {"obtido_em": date.today().isoformat(), "metodologia": METODOLOGIA,
        "series": {"selic": 1178, "ipca15": 7478},
        "fontes": {"selic_diaria_anualizada": "https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=1178",
                   "ipca15_reconstrucao": "https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=7478"},
        "urls_consultadas": {name: url for name, _, url in results},
        "sha256_fontes": {name: hashlib.sha256(raw).hexdigest() for name, raw, _ in results},
        "taxa_legal": {k: v["taxa_mensal"] for k, v in historic.items()}, "memoria_formacao": historic,
        "verificacao_publicada": {k: reconstructed[k] for k in ("2024-08", "2024-09", "2024-10", "2024-11", "2024-12")},
        "observacao": "Taxa Legal reconstruída até 29/08/2024. Não representa taxa publicada nem altera o início da vigência normativa."}
    path = directory / ARQUIVO
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validar_reconstrucao(directory)
    print(json.dumps({"arquivo": str(path), "competencias": len(historic), "inicio_juros": min(historic) + "-01",
                      "fim_reconstrucao": "2024-08-29", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "comparacoes_oficiais_exatas": 5}, ensure_ascii=False))


if __name__ == "__main__":
    gerar(ROOT / "backend/data")
