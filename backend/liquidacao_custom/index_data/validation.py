"""Validação estrutural e conciliação das bases distribuídas."""
from __future__ import annotations

import csv
import hashlib
import json
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .store import FILES, FILES_HISTORICOS
from .series import selic_values


def read_json(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8-sig"))


def monthly(values, *, nonnegative=False):
    if not isinstance(values, dict) or not values:
        raise ValueError("Série mensal vazia.")
    dates = []
    for key, value in sorted(values.items()):
        day = date.fromisoformat(key + "-01")
        if day.strftime("%Y-%m") != key:
            raise ValueError("Competência inválida.")
        rate = Decimal(str(value))
        if not rate.is_finite() or rate <= -100 or (nonnegative and rate < 0):
            raise ValueError("Taxa inválida.")
        dates.append(day.year * 12 + day.month)
    if dates != list(range(dates[0], dates[-1] + 1)):
        raise ValueError("Há lacunas nas competências mensais.")
    return values


def bcb_values(records, *, monthly_series=False):
    result = {}
    for row in records:
        day = datetime.strptime(row["data"], "%d/%m/%Y").date()
        key = day.strftime("%Y-%m") if monthly_series else day.isoformat()
        if key in result:
            raise ValueError("Registro duplicado na fonte oficial.")
        rate = Decimal(str(row["valor"]))
        if not rate.is_finite() or rate <= -100:
            raise ValueError("Taxa inválida na fonte oficial.")
        if "dataFim" in row and datetime.strptime(row["dataFim"], "%d/%m/%Y").date() <= day:
            raise ValueError("Período inválido da poupança.")
        result[key] = row["valor"]
    if not result:
        raise ValueError("Fonte oficial vazia.")
    if monthly_series:
        monthly(result)
    return result


def _equal(left, right):
    return set(left) == set(right) and all(Decimal(str(left[k])) == Decimal(str(right[k])) for k in left)


def conciliar_historico(historico, vigente):
    """Preserva os dados da fonte vigente no trecho comum."""
    for competencia in historico.keys() & vigente.keys():
        if Decimal(str(historico[competencia])) != Decimal(str(vigente[competencia])):
            raise ValueError("Séries oficiais divergentes na competência " + competencia)
    return monthly({**historico, **vigente})


def validate_directory(directory: Path, files=FILES):
    for name in files:
        if not (directory / name).is_file():
            raise ValueError("Arquivo obrigatório ausente: " + name)
    snapshot = read_json(directory, "indices_simplificados.json")
    consultation = date.fromisoformat(snapshot["obtido_em"])
    if consultation > date.today():
        raise ValueError("Data de consulta futura.")
    for key in ("selic", "ipcae_taxas"):
        monthly(snapshot[key], nonnegative=key == "selic")
        if max(snapshot[key]) > consultation.strftime("%Y-%m"):
            raise ValueError("Competência posterior à consulta.")
    for name, digest in snapshot["sha256_fontes"].items():
        relative = "fontes/" + name
        if relative not in files or hashlib.sha256((directory / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Hash da fonte oficial divergente: " + name)
    ipca15 = bcb_values(read_json(directory, "fontes/bcb_ipca15_2009_2026.json"), monthly_series=True)
    has_history = set(FILES_HISTORICOS).issubset(files)
    ipcae = ipca15
    if has_history:
        historical = bcb_values(read_json(directory, FILES_HISTORICOS[1]), monthly_series=True)
        ipcae = conciliar_historico(historical, ipca15)
    if not _equal(snapshot["ipcae_taxas"], ipcae):
        raise ValueError("Snapshot diverge das fontes do IPCA-E.")
    selic = bcb_values(read_json(directory, "fontes/bcb_selic_mensal.json"), monthly_series=True)
    if not _equal(snapshot["selic"], selic):
        raise ValueError("Snapshot diverge da fonte da SELIC.")
    ipca_meta = read_json(directory, "fontes/ipca15_fonte.json")
    if (ipca_meta["serie"] != 7478 or ipca_meta["ultima_competencia"] != max(ipca15)
            or ipca_meta["primeira_competencia"] != min(ipca15)
            or ipca_meta["obtido_em"] != snapshot["obtido_em"]):
        raise ValueError("Metadados do IPCA-E inconsistentes.")
    if has_history:
        for metadata, filename, series, key, first in (
            (read_json(directory, "fontes/ipcae_historico_fonte.json"), "bcb_ipcae_1992_2026.json", 10764, "ipcae_taxas", "1992-01"),
            (read_json(directory, "ipca_oficial.json")["fonte_historica"], "bcb_ipca_1980_2026.json", 433, "ipca", "1980-01"),
        ):
            raw = (directory / "fontes" / filename).read_bytes()
            values = bcb_values(json.loads(raw), monthly_series=True)
            if (metadata["serie"] != series or metadata["arquivo"] != filename
                    or metadata["sha256_resposta_oficial"] != hashlib.sha256(raw).hexdigest()
                    or metadata["primeira_competencia"] != min(values) or min(values) != first or metadata["ultima_competencia"] != max(values)
                    or date.fromisoformat(metadata["obtido_em"]) > date.today()):
                raise ValueError("Fonte histórica inconsistente: " + filename)
            canonical = snapshot[key] if key == "ipcae_taxas" else read_json(directory, "ipca_oficial.json")[key]
            if min(canonical) != first or any(k not in canonical or Decimal(str(canonical[k])) != Decimal(str(v)) for k, v in values.items()):
                raise ValueError("Série histórica diverge da base canônica: " + key)
    sources = ["bcb_poupanca_total_2009_2012", "bcb_poupanca_total_2012_2016",
               "bcb_poupanca_total_2017_2021", "bcb_poupanca_depositos_2021_2026"]
    records = [row for source in sources for row in read_json(directory, "fontes/" + source + ".json")]
    rates = bcb_values(records)
    periods = {datetime.strptime(row["data"], "%d/%m/%Y").date().isoformat():
               datetime.strptime(row["dataFim"], "%d/%m/%Y").date().isoformat() for row in records}
    if not _equal(snapshot["poupanca_total"], rates) or snapshot["poupanca_periodos"] != periods:
        raise ValueError("Snapshot da poupança diverge das fontes.")
    if max(rates) > snapshot["obtido_em"]:
        raise ValueError("Poupança posterior à consulta.")
    deposit_meta = read_json(directory, "fontes/poupanca_depositos_fonte.json")
    deposit_consultation = date.fromisoformat(deposit_meta["obtido_em"])
    if deposit_consultation > date.today() or deposit_meta["serie"] != 195:
        raise ValueError("Metadados da poupança inválidos.")
    if any("fontes/" + name not in files for name in deposit_meta["arquivos"]):
        raise ValueError("Fonte da poupança fora do pacote.")
    if set(deposit_meta["arquivos"]) != {"bcb_poupanca_total_2012_2016.json", "bcb_poupanca_total_2017_2021.json", "bcb_poupanca_depositos_2021_2026.json"}:
        raise ValueError("A lista de fontes da poupança alteraria sua cobertura.")
    if any(Decimal(str(v)) < 0 for v in snapshot["poupanca_total"].values()):
        raise ValueError("Taxa negativa da poupança.")
    deposits = bcb_values([row for name in deposit_meta["arquivos"] for row in read_json(directory, "fontes/" + name)])
    if max(deposits) > deposit_meta["obtido_em"]:
        raise ValueError("Atualize a data de consulta dos metadados da poupança.")
    official_files = [("ipca_oficial.json", "ipca"), ("taxa_legal_oficial.json", "taxa_legal")]
    official_files.extend([(name + "_oficial.json", name) for name in ("inpc", "igpm")])
    for name, key in official_files:
        data = read_json(directory, name)
        monthly(data[key], nonnegative=key == "taxa_legal")
        if key in ("inpc", "igpm"):
            if data["serie"] != {"inpc": 188, "igpm": 189}[key] or not data["fontes"].get(key):
                raise ValueError("Fonte oficial inválida: " + name)
        if key == "taxa_legal" and any(Decimal(str(v)).as_tuple().exponent < -6 for v in data[key].values()):
            raise ValueError("A Taxa Legal deve preservar até seis casas decimais.")
        obtained = date.fromisoformat(data["obtido_em"])
        if obtained > date.today() or max(data[key]) > obtained.strftime("%Y-%m"):
            raise ValueError("Consulta ou competência futura: " + name)
    historic = read_json(directory, "selic_historica.json")
    history = bcb_values(historic["selic"], monthly_series=True)
    monthly({**history, **snapshot["selic"]}, nonnegative=True)
    ec = read_json(directory, "indices_ec136.json")
    for field in ("obtido_em", "selic_obtido_em"):
        if field in ec and date.fromisoformat(ec[field]) > date.today():
            raise ValueError("Consulta futura na série EC 136.")
    for key, official in (("selic", snapshot["selic"]), ("ipca", read_json(directory, "ipca_oficial.json")["ipca"])):
        rates = bcb_values(ec[key], monthly_series=True)
        if any(k not in official or Decimal(str(v)) != Decimal(str(official[k])) for k, v in rates.items()):
            raise ValueError("Série EC 136 diverge da série oficial: " + key)
    selic_values(directory)  # Conferir toda a união, inclusive o histórico.
    from .taxa_legal_reconstruida import validar_reconstrucao
    reconstructed = validar_reconstrucao(directory)
    monthly(reconstructed["taxa_legal"], nonnegative=True)
    for name in files:
        if name.startswith("fontes/") and name.endswith(".json"):
            data = read_json(directory, name)
            if isinstance(data, list):
                bcb_values(data)
    salary = list(csv.DictReader((directory / "salario_minimo.csv").read_text(encoding="utf-8-sig").splitlines()))
    years = [int(row["ano"]) for row in salary]
    if not years or len(years) != len(set(years)) or any(Decimal(row["valor"]) <= 0 for row in salary):
        raise ValueError("Base de salários inválida.")


def _series(directory):
    snapshot = read_json(directory, "indices_simplificados.json")
    values = {key: snapshot[key] for key in ("selic", "ipcae_taxas", "poupanca_total")}
    for name, key in (("ipca_oficial.json", "ipca"), ("taxa_legal_oficial.json", "taxa_legal")):
        values[key] = read_json(directory, name)[key]
    for key in ("inpc", "igpm"):
        values[key] = read_json(directory, key + "_oficial.json")[key]
    values["selic"] = selic_values(directory)
    values["taxa_legal_reconstruida"] = read_json(directory, "taxa_legal_reconstruida.json")["taxa_legal"]
    ec = read_json(directory, "indices_ec136.json")
    for key in ("ipca", "selic"):
        values["ec136_" + key] = bcb_values(ec[key], monthly_series=True)
    values["selic_historica"] = bcb_values(read_json(directory, "selic_historica.json")["selic"], monthly_series=True)
    values["salario_minimo"] = {r["ano"]: r["valor"] for r in csv.DictReader(
        (directory / "salario_minimo.csv").read_text(encoding="utf-8-sig").splitlines())}
    return values


def ensure_no_regression(candidate: Path, previous: Path):
    new, old = _series(candidate), _series(previous)
    for key in old:
        if not set(old[key]).issubset(new[key]):
            raise ValueError("A atualização reduziria a cobertura: " + key)
    consultations = ["indices_simplificados.json", "ipca_oficial.json", "taxa_legal_oficial.json",
                     "fontes/poupanca_depositos_fonte.json", "indices_ec136.json"]
    consultations.extend(["inpc_oficial.json", "igpm_oficial.json", "taxa_legal_reconstruida.json"])
    for name in consultations:
        if read_json(candidate, name)["obtido_em"] < read_json(previous, name)["obtido_em"]:
            raise ValueError("A atualização possui uma consulta anterior: " + name)
    new_ec, old_ec = read_json(candidate, "indices_ec136.json"), read_json(previous, "indices_ec136.json")
    if new_ec.get("selic_obtido_em", new_ec["obtido_em"]) < old_ec.get("selic_obtido_em", old_ec["obtido_em"]):
        raise ValueError("A atualização reduziria a data de consulta da SELIC.")
