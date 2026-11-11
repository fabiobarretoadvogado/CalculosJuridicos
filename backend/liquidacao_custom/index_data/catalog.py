from __future__ import annotations

import sys
from calendar import monthrange
from datetime import date, datetime

from liquidacao_custom.core.motor_simplificado import criterios_publicos
from liquidacao_custom.core.perfis import PERFIS
from liquidacao_custom.updates import settings
from .store import current_dataset, index_context
from .validation import bcb_values, read_json


def catalog():
    with index_context() as dataset:
        directory = dataset.directory
        snapshot = read_json(directory, "indices_simplificados.json")
        ipca = read_json(directory, "ipca_oficial.json")
        legal = read_json(directory, "taxa_legal_oficial.json")
        history = read_json(directory, "selic_historica.json")
        ec = read_json(directory, "indices_ec136.json")
        meta = read_json(directory, "fontes/poupanca_depositos_fonte.json")
        rows = []

        def add(identifier, name, values, obtained, source, note, *, legacy=False, unit="competencia"):
            keys = sorted(values)
            rows.append({"id": identifier, "nome": name, "inicio": keys[0], "fim": keys[-1],
                         "consulta_em": obtained, "quantidade": len(keys), "fonte": source,
                         "observacao": note, "legado": legacy, "unidade": unit})

        selic = {**bcb_values(history["selic"], monthly_series=True), **snapshot["selic"],
                 **bcb_values(ec["selic"], monthly_series=True)}
        obtained = ec.get("selic_obtido_em", ec["obtido_em"])
        closed = [k for k in selic if date.fromisoformat(k + "-01").replace(
            day=monthrange(int(k[:4]), int(k[5:]))[1]) < date.fromisoformat(obtained)]
        note = "Última competência encerrada: " + max(closed) + "."
        if max(selic) > max(closed):
            note += " A taxa de " + max(selic) + " é parcial e não entra como mês encerrado."
        add("selic", "SELIC — BCB SGS 4390", selic, obtained, snapshot["fontes"]["selic"], note)
        add("ipcae", "IPCA-E / IPCA-15 — IBGE", snapshot["ipcae_taxas"], snapshot["obtido_em"],
            snapshot["fontes"].get("ipcae_historico", snapshot["fontes"]["ipcae"]), "Histórico mensal SGS 10764 desde janeiro/1992, conciliado com IPCA-15 SGS 7478. O limite dos juros depende do perfil.")
        add("ipca", "IPCA — IBGE / BCB SGS 433", ipca["ipca"], ipca["obtido_em"],
            ipca["fontes"]["ipca"], "Índice oficial utilizado nos perfis Civil 1 e Civil 2.")
        inpc = read_json(directory, "inpc_oficial.json")
        add("inpc", "INPC — IBGE / BCB SGS 188", inpc["inpc"], inpc["obtido_em"],
            inpc["fontes"]["inpc"], "Índice oficial utilizado no Civil 3; cobertura limitada às competências publicadas, com deflações preservadas.")
        add("taxa_legal", "Taxa Legal — BCB SGS 29543", legal["taxa_legal"], legal["obtido_em"],
            legal["fonte_publica"], "Série oficial. Aplicação a partir de 30/08/2024; depende também da cobertura do IPCA.")
        reconstructed = read_json(directory, "taxa_legal_reconstruida.json")
        add("taxa_legal_reconstruida", "Taxa Legal reconstruída — Civil 5", reconstructed["taxa_legal"],
            reconstructed["obtido_em"], reconstructed["fontes"]["selic_diaria_anualizada"],
            "Metodologia CMN 5.171/2024 aplicada aos dados históricos SELIC e IPCA-15. Até 29/08/2024; não é série de Taxa Legal publicada pelo BCB.")
        add("poupanca_mora", "Poupança — juros de mora", snapshot["poupanca_total"], snapshot["obtido_em"],
            snapshot["fontes"]["poupanca_total"], "Taxas por data de referência, com TR incluída; aplicação conforme o perfil da Fazenda Pública.", unit="data")
        deposits = [r for name in meta["arquivos"] for r in read_json(directory, "fontes/" + name)]
        add("poupanca_deposito", "Poupança — remuneração de depósitos (SGS 195)", bcb_values(deposits),
            meta["obtido_em"], meta["fonte"], "As datas são de início dos períodos publicados. Somente aniversários completos geram rendimento; não se antecipam créditos.", unit="data")
        igpm = read_json(directory, "igpm_oficial.json")
        add("igpm", "IGP-M — FGV / BCB SGS 189", igpm["igpm"], igpm["obtido_em"],
            igpm["fontes"]["igpm"], "Série canônica utilizada pela API de correção configurável; não altera os perfis civis ou da Fazenda Pública.")
        profiles = []
        for profile in [*PERFIS, {"id": "ipcae_1am_simples_v1", "nome": "IPCA-E e juros simples de 1%"},
                        {"id": "poupanca_deposito_v1", "nome": "Depósitos pela poupança"}]:
            try:
                criteria = criterios_publicos(perfil=profile["id"])
                profiles.append({**profile, "data_base_maxima": criteria["data_base_maxima"],
                                 "ultima_competencia_selic": criteria.get("ultima_competencia_selic_disponivel"),
                                 "observacao": ""})
            except ValueError as exc:
                profiles.append({**profile, "data_base_maxima": None, "observacao": str(exc)})
        return {"base": dataset.metadata(), "aviso": dataset.warning, "series": rows, "perfis": profiles,
                "empacotado": bool(getattr(sys, "frozen", False)),
                "atualizacoes_configuradas": bool(settings.REPOSITORY and settings.PUBLIC_KEY)}
