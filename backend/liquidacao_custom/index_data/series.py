"""Visão mensal única dos JSON oficiais, compartilhada pelos leitores."""
import json
from datetime import datetime
from decimal import Decimal


def read_json(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8-sig"))


def selic_values(directory):
    history = read_json(directory, "selic_historica.json")
    snapshot = read_json(directory, "indices_simplificados.json")
    ec = read_json(directory, "indices_ec136.json")
    values = {}
    for records in (history["selic"],):
        for row in records:
            key = datetime.strptime(row["data"], "%d/%m/%Y").strftime("%Y-%m")
            if key in values:
                raise ValueError("Competência SELIC duplicada.")
            values[key] = row["valor"]
    for rates in (snapshot["selic"], {
        datetime.strptime(row["data"], "%d/%m/%Y").strftime("%Y-%m"): row["valor"]
        for row in ec["selic"]
    }):
        for key, rate in rates.items():
            if key in values and Decimal(str(values[key])) != Decimal(str(rate)):
                raise ValueError("Fontes oficiais SELIC divergentes: " + key)
            values[key] = rate
    return dict(sorted(values.items()))
