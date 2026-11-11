"""Regera a base a partir das séries oficiais arquivadas."""
import hashlib
import json
from calendar import monthrange
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from liquidacao_custom.index_data.validation import bcb_values, conciliar_historico

ROOT = Path(__file__).resolve().parent
fonte_ipca15 = json.loads((ROOT / "ipca15_fonte.json").read_text(encoding="utf-8-sig"))
ipca15 = json.loads((ROOT / "bcb_ipca15_2009_2026.json").read_text(encoding="utf-8-sig"))
taxas_ipcae = {
    datetime.strptime(item["data"], "%d/%m/%Y").strftime("%Y-%m"): item["valor"]
    for item in ipca15
}
assert len(taxas_ipcae) == len(ipca15)
assert taxas_ipcae["2009-07"] == "0.22"
assert taxas_ipcae["2021-03"] == "0.93"
assert taxas_ipcae["2025-09"] == "0.48"
assert taxas_ipcae[fonte_ipca15["ultima_competencia"]] == ipca15[-1]["valor"]
fonte_ipcae_historico = json.loads((ROOT / "ipcae_historico_fonte.json").read_text(encoding="utf-8-sig"))
ipcae_historico = bcb_values(
    json.loads((ROOT / fonte_ipcae_historico["arquivo"]).read_text(encoding="utf-8-sig")), monthly_series=True)
taxas_ipcae = conciliar_historico(ipcae_historico, taxas_ipcae)
selic = json.loads((ROOT / "bcb_selic_mensal.json").read_text(encoding="utf-8-sig"))
poupanca_recente = json.loads((ROOT / "bcb_poupanca_depositos_2021_2026.json").read_text(encoding="utf-8-sig"))
poupanca_fonte = json.loads((ROOT / "poupanca_depositos_fonte.json").read_text(encoding="utf-8-sig"))
meta_selic = json.loads((ROOT / "bcb_meta_selic.json").read_text(encoding="utf-8-sig"))
assert len(selic) >= 57
assert selic and datetime.strptime(selic[-1]["data"], "%d/%m/%Y").date() <= datetime.now().date()
assert poupanca_recente[0] == {"data": "09/12/2021", "dataFim": "09/01/2022", "valor": "0.5655"}
ultima_selic = datetime.strptime(selic[-1]["data"], "%d/%m/%Y")
fim_selic = ultima_selic.replace(day=monthrange(ultima_selic.year, ultima_selic.month)[1]).strftime("%d/%m/%Y")
inicio_meta_selic = meta_selic[0]["data"]
fim_meta_selic = meta_selic[-1]["data"]
poupanca = (
    json.loads((ROOT / "bcb_poupanca_total_2009_2012.json").read_text(encoding="utf-8-sig"))
    + json.loads((ROOT / "bcb_poupanca_total_2012_2016.json").read_text(encoding="utf-8-sig"))
    + json.loads((ROOT / "bcb_poupanca_total_2017_2021.json").read_text(encoding="utf-8-sig"))
    + poupanca_recente
)
assert len({x["data"] for x in poupanca}) == len(poupanca)
assert all(datetime.strptime(x["dataFim"], "%d/%m/%Y") > datetime.strptime(x["data"], "%d/%m/%Y") for x in poupanca)
# Nenhum percentual é projetado: o snapshot cobre apenas os dias publicados.
snapshot = {
    "obtido_em": fonte_ipca15["obtido_em"],
    "selic": {datetime.strptime(x["data"], "%d/%m/%Y").strftime("%Y-%m"): x["valor"] for x in selic},
    "ipcae_taxas": taxas_ipcae,
    "poupanca_total": {datetime.strptime(x["data"], "%d/%m/%Y").date().isoformat(): x["valor"] for x in poupanca},
    "poupanca_periodos": {datetime.strptime(x["data"], "%d/%m/%Y").date().isoformat(): datetime.strptime(x["dataFim"], "%d/%m/%Y").date().isoformat() for x in poupanca},
    "fontes": {
        "selic": f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json&dataInicial=01/12/2021&dataFinal={fim_selic}",
        "ipcae": fonte_ipca15["url_dados"],
        "ipcae_historico": fonte_ipcae_historico["url_dados"],
        "ipcae_ibge": fonte_ipca15["url_produtor"],
        "ipcae_serie_bcb": fonte_ipca15["url_serie"],
        "poupanca_total": poupanca_fonte["fonte"],
        "meta_selic": f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial={inicio_meta_selic}&dataFinal={fim_meta_selic}",
        "poupanca_regra": "https://www.bcb.gov.br/meubc/faqs/p/como-sao-remunerados-os-depositos-da-poupanca",
        "poupanca_2009_2012": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.25/dados?formato=json&dataInicial=01/07/2009&dataFinal=03/05/2012",
        "poupanca_2012_2016": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados?formato=json&dataInicial=04/05/2012&dataFinal=31/12/2016",
        "poupanca_2017_2021": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados?formato=json&dataInicial=01/01/2017&dataFinal=08/12/2021",
        "tema_905": "https://processo.stj.jus.br/repetitivos/temas_repetitivos/pesquisa.jsp?cod_tema_final=905&cod_tema_inicial=905&novaConsulta=true&tipo_pesquisa=T",
    },
    "sha256_fontes": {
        nome: hashlib.sha256((ROOT / nome).read_bytes()).hexdigest()
        for nome in (
            "bcb_ipca15_2009_2026.json",
            "ipca15_fonte.json",
            fonte_ipcae_historico["arquivo"],
            "ipcae_historico_fonte.json",
            "bcb_selic_mensal.json",
            "bcb_poupanca_total_2009_2012.json",
            "bcb_poupanca_total_2012_2016.json",
            "bcb_poupanca_total_2017_2021.json",
            "bcb_poupanca_depositos_2021_2026.json",
            "bcb_poupanca_total.json",
            "bcb_meta_selic.json",
        )
    },
}
(ROOT.parent / "indices_simplificados.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Snapshot: {len(selic)} taxas SELIC, {len(taxas_ipcae)} taxas IPCA-15/IPCA-E, {len(poupanca)} taxas totais da poupança (TR incluída).")
