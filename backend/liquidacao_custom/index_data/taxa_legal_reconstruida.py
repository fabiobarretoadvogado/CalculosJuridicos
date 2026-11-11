"""Reconstituição histórica explícita da metodologia CMN 5.171/2024."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal as D, ROUND_HALF_EVEN, localcontext
from functools import lru_cache

METODOLOGIA = "cmn_5171_selic1178_ipca15_7478_mes_anterior_nbr5891_v1"
ARQUIVO = "taxa_legal_reconstruida.json"
FONTES = (
    "fontes/bcb_selic_anual_civil5_2000_2009.json",
    "fontes/bcb_selic_anual_civil5_2010_2019.json",
    "fontes/bcb_selic_anual_civil5_2020_2024.json",
    "fontes/bcb_ipca15_civil5_2000_2024.json",
)


def mes_seguinte(competencia):
    year, month = map(int, competencia.split("-"))
    return f"{year + (month == 12):04d}-{month % 12 + 1:02d}"


@lru_cache(maxsize=2048)
def fator_diario(taxa_anual):
    """Art. 4: SELIC anual com duas casas e fator diário com oito casas."""
    rate = D(taxa_anual)
    if not rate.is_finite() or rate < 0 or rate.as_tuple().exponent < -2:
        raise ValueError("SELIC anualizada inválida para reconstrução da Taxa Legal.")
    with localcontext() as ctx:
        ctx.prec = 48
        return ctx.power(1 + rate / 100, 1 / D(252)).quantize(D("0.00000001"), rounding=ROUND_HALF_EVEN)


def reconstruir_mes(taxas_selic, ipca15, competencia_anterior):
    """Sem substituir dado ausente, taxa mensal arredondada ou inflação distinta."""
    if not taxas_selic or ipca15 is None:
        raise ValueError("Fonte ausente para reconstrução da Taxa Legal: " + competencia_anterior)
    inflation = D(ipca15)
    if not inflation.is_finite() or inflation <= -100 or inflation.as_tuple().exponent < -2:
        raise ValueError("IPCA-15 inválido para reconstrução da Taxa Legal.")
    with localcontext() as ctx:
        ctx.prec = 48
        factor = D(1)
        for rate in taxas_selic:
            factor *= fator_diario(str(rate))
        factor = factor.quantize(D("0.00000001"), rounding=ROUND_HALF_EVEN)
        inflation_factor = (1 + inflation / 100).quantize(D("0.0001"), rounding=ROUND_HALF_EVEN)
        quotient = (factor / inflation_factor - 1) * 100
        legal = max(quotient, D(0)).quantize(D("0.000001"), rounding=ROUND_HALF_EVEN)
    return {"competencia_insumos": competencia_anterior, "dias_uteis": len(taxas_selic),
            "fator_selic": str(factor), "ipca15_percentual": str(inflation),
            "fator_ipca15": str(inflation_factor), "piso_zero_aplicado": quotient < 0,
            "taxa_mensal": str(legal)}


def reconstruir_fontes(directory):
    selic, inflation, seen = defaultdict(list), {}, set()
    for name in FONTES:
        records = json.loads((directory / name).read_text(encoding="utf-8-sig"))
        if not isinstance(records, list) or not records:
            raise ValueError("Fonte histórica vazia: " + name)
        for row in records:
            day = datetime.strptime(row["data"], "%d/%m/%Y").date()
            month = day.strftime("%Y-%m")
            if name == FONTES[-1]:
                if month in inflation:
                    raise ValueError("IPCA-15 histórico duplicado: " + month)
                inflation[month] = row["valor"]
            else:
                if day in seen or day.weekday() > 4:
                    raise ValueError("SELIC anualizada duplicada ou fora de dia útil.")
                seen.add(day)
                selic[month].append(row["valor"])
    if set(selic) != set(inflation):
        raise ValueError("Fontes históricas SELIC e IPCA-15 com competências ausentes.")
    return {mes_seguinte(month): reconstruir_mes(selic[month], inflation[month], month)
            for month in sorted(inflation)}


def validar_reconstrucao(directory):
    snapshot = json.loads((directory / ARQUIVO).read_text(encoding="utf-8-sig"))
    if snapshot.get("metodologia") != METODOLOGIA or snapshot.get("series") != {"selic": 1178, "ipca15": 7478}:
        raise ValueError("Metodologia ou séries históricas da Taxa Legal inválidas.")
    if date.fromisoformat(snapshot["obtido_em"]) > date.today():
        raise ValueError("Consulta histórica da Taxa Legal futura.")
    if set(snapshot["sha256_fontes"]) != set(FONTES) or set(snapshot["urls_consultadas"]) != set(FONTES):
        raise ValueError("Lista incompleta das fontes históricas da Taxa Legal.")
    for name in FONTES:
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != snapshot["sha256_fontes"][name]:
            raise ValueError("Hash da fonte histórica da Taxa Legal divergente: " + name)
        series = 7478 if name == FONTES[-1] else 1178
        if not snapshot["urls_consultadas"][name].startswith(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados?"):
            raise ValueError("URL da fonte histórica da Taxa Legal inválida.")
    reconstructed = reconstruir_fontes(directory)
    expected = {month: details for month, details in reconstructed.items() if month <= "2024-08"}
    if snapshot["memoria_formacao"] != expected or snapshot["taxa_legal"] != {k: v["taxa_mensal"] for k, v in expected.items()}:
        raise ValueError("Taxa Legal histórica diverge da reconstituição de suas fontes.")
    comparisons = {k: reconstructed[k] for k in ("2024-08", "2024-09", "2024-10", "2024-11", "2024-12")}
    if snapshot.get("verificacao_publicada") != comparisons:
        raise ValueError("Memória da comparação com a Taxa Legal publicada divergente.")
    official = json.loads((directory / "taxa_legal_oficial.json").read_text(encoding="utf-8-sig"))["taxa_legal"]
    if any(month not in official or D(details["taxa_mensal"]) != D(official[month]) for month, details in comparisons.items()):
        raise ValueError("Reconstituição não reproduz a Taxa Legal oficial publicada.")
    return snapshot
