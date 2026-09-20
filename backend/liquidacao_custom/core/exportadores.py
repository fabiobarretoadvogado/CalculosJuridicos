"""
Módulo de exportação de resultados para Excel e CSV.
"""

from __future__ import annotations

import csv
import json
import os
import re
from decimal import Decimal
import openpyxl

from liquidacao_custom.core.models import ResultadoCalculo
from .componentes import colunas_componentes, colunas_perfil


def memoria_exibida(texto):
    return re.sub(r"-?\d+\.\d{5,}", lambda m: f"{Decimal(m.group()):.4f}", texto)


def linhas_indices(resultado):
    yield ["Parcela", "Critério", "Faixa", "Início efetivo", "Fim efetivo", "Base de cálculo", "Fator acumulado", "Taxa acumulada (%)", "Acréscimo (R$)"]
    for parcela in resultado.parcelas:
        for chave, nome, faixa in colunas_componentes(resultado):
            c = parcela.componentes.get(chave)
            if c is not None:
                yield [parcela.numero, nome, faixa, str(c.data_inicial or ""), str(c.data_final or ""),
                       f"{c.base_calculo:.4f}", f"{c.fator_acumulado:.4f}" if c.fator_acumulado is not None else "",
                       (f"{c.taxa_acumulada_percentual:.6f}" if chave == "taxa_legal" else f"{c.taxa_acumulada_percentual:.4f}") if c.taxa_acumulada_percentual is not None else "", str(c.valor)]
        if parcela.multa_detalhes:
            for chave, nome, faixa in colunas_perfil(resultado):
                c = parcela.multa_detalhes.componentes.get(chave)
                if c is not None:
                    yield [parcela.numero, f"Multa - {nome}", faixa, str(c.data_inicial or ""), str(c.data_final or ""),
                           f"{c.base_calculo:.4f}", f"{c.fator_acumulado:.4f}" if c.fator_acumulado is not None else "",
                           (f"{c.taxa_acumulada_percentual:.6f}" if chave == "taxa_legal" else f"{c.taxa_acumulada_percentual:.4f}") if c.taxa_acumulada_percentual is not None else "", str(c.valor)]


def linhas_honorarios_principais(resultado):
    yield ["Rubrica", "Data origem", "Valor original", "Índice", "Fator acumulado", "Base atualizada", "Percentual", "Valor", "Acresce ao total"]
    h, c, d = resultado.honorarios_sucumbenciais, resultado.cumprimento_sentenca, resultado.destaque_contratuais
    if h:
        yield ["Honorários sucumbenciais - " + h.descricao_base, str(h.data_protocolo or ""), str(h.valor_original), h.indice or "", str(h.fator_acumulado), str(h.base_atualizada), str(h.percentual or ""), str(h.valor), "SIM"]
    if c:
        if c.aplicar_multa:
            yield ["Multa - art. 523, § 1º, CPC", "", "", "", "", str(c.base_calculo), "10", str(c.multa), "SIM"]
        if c.aplicar_honorarios:
            yield ["Honorários - art. 523, § 1º, CPC", "", "", "", "", str(c.base_calculo), "10", str(c.honorarios), "SIM"]
    if d:
        yield ["Destaque contratual - " + d.descricao_base, "", "", "", "", str(d.base_calculo), str(d.percentual), str(d.valor), "NÃO"]
        yield ["Saldo da base após destaque contratual (não altera a dívida)", "", "", "", "", "", "", str(d.saldo_apos_destaque), "NÃO"]


def linhas_memoria_valor_causa(resultado):
    yield ["Competência", "Base", "Índice", "Fator", "Valor corrigido", "Período e critério"]
    if resultado.honorarios_sucumbenciais:
        for m in resultado.honorarios_sucumbenciais.memoria:
            yield [m.competencia, str(m.valor_base), m.indice_aplicado, str(m.fator_aplicado), str(m.valor_corrigido), m.observacao]


def linhas_pagamentos_registrados(resultado):
    yield ["Nº", "Descrição", "Data", "Valor total pago", "Base da atualização", "Encargos sem nova incidência", "Selecionado para abater"]
    for item in resultado.premissas.get("selecao_descontos", []):
        valor = Decimal(item["valor"]) if item["valor"] is not None else None
        nominal = Decimal(item["encargos_sem_atualizacao"])
        yield [item["numero"], item["descricao"], item["data"] or "", str(valor) if valor is not None else "",
               str(valor - nominal) if valor is not None else "", str(nominal), "SIM" if item["aplicar"] else "NÃO"]


def exportar_csv(resultado: ResultadoCalculo, pasta_destino: str) -> None:
    """Exporta os resumos, memória mensal e alertas em arquivos CSV separados."""
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    with open(os.path.join(pasta_destino, "premissas.json"), "w", encoding="utf-8") as f:
        json.dump(resultado.premissas, f, ensure_ascii=False, indent=2, default=str)

    # 1. Resumo Geral
    caminho_resumo = os.path.join(pasta_destino, "resumo_geral.csv")
    with open(caminho_resumo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Campo", "Valor"])
        res = resultado.resumo
        for k, v in res.model_dump().items():
            if isinstance(v, dict):
                writer.writerows((chave, str(valor)) for chave, valor in v.items())
            else:
                writer.writerow([k, str(v)])

    if resultado.resumo.totais_componentes:
        with open(os.path.join(pasta_destino, "indices_por_parcela.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_indices(resultado))
    if resultado.premissas.get("memoria_taxa_legal"):
        from .relatorio_taxa_legal import linhas_taxa_legal
        with open(os.path.join(pasta_destino, "taxa_legal_mensal.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_taxa_legal(resultado))

    # 2. Memória Mensal
    caminho_memoria = os.path.join(pasta_destino, "memoria_mensal.csv")
    with open(caminho_memoria, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Parcela", "Competencia", "Valor Base", "Indice", "Fator", "Valor Corrigido", "Juros Periodo", "Juros Acumulado", "Multa", "Total", "Observacao"])
        for m in resultado.memoria_mensal:
            writer.writerow([
                m.parcela, m.competencia, f"{m.valor_base:.4f}", m.indice_aplicado,
                f"{m.fator_aplicado:.4f}",
                str(m.valor_corrigido), str(m.juros_periodo), str(m.juros_acumulados),
                str(m.multa), str(m.total), memoria_exibida(m.observacao)
            ])

    if resultado.custas_despesas:
        with open(os.path.join(pasta_destino, "custas_despesas.csv"), "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Nº", "Nome", "Data", "Valor original", "Fator IPCA-E", "Correção monetária", "Valor atualizado"])
            for item in resultado.custas_despesas:
                writer.writerow([
                    item.numero, item.nome, item.data.isoformat(), str(item.valor_original),
                    f"{item.fator_ipcae:.8f}", str(item.correcao_monetaria), str(item.valor_atualizado),
                ])
        with open(os.path.join(pasta_destino, "memoria_custas_despesas.csv"), "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Nº", "Nome", "Competência", "Valor base", "Índice", "Fator", "Valor corrigido", "Observação"])
            for item in resultado.custas_despesas:
                for memoria in item.memoria:
                    writer.writerow([
                        item.numero, item.nome, memoria.competencia, f"{memoria.valor_base:.4f}",
                        memoria.indice_aplicado, f"{memoria.fator_aplicado:.8f}",
                        str(memoria.valor_corrigido), memoria_exibida(memoria.observacao),
                    ])

    if "multa_parcela" in resultado.resumo.totais_componentes:
        with open(os.path.join(pasta_destino, "multas_parcelas.csv"), "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Nº", "Descrição", "Vencimento", "Saldo base", "Multa (%)", "Multa nominal", "Atualização da multa", "Juros da multa", "Total da multa"])
            for parcela in resultado.parcelas:
                m = parcela.multa_detalhes
                if m:
                    writer.writerow([parcela.numero, parcela.historico, str(parcela.data_vencimento), str(m.base_calculo), str(m.percentual), str(m.valor_original), str(m.correcao_monetaria), str(m.juros_mora), str(m.total_atualizado)])

    if resultado.premissas.get("selecao_descontos"):
        with open(os.path.join(pasta_destino, "pagamentos_registrados.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_pagamentos_registrados(resultado))
    if resultado.descontos:
        descontos = resultado.descontos
        with open(os.path.join(pasta_destino, "descontos.csv"), "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Nº", "Descrição", "Data do desconto", "Valor informado", "Correção", "Juros", "Valor atualizado", "Abatido", "Excedente"])
            for p, ab in zip(descontos.parcelas, resultado.memorias_abatimento):
                writer.writerow([p.numero, p.historico, str(p.data_vencimento), str(p.valor_bruto), str(p.correcao_monetaria), str(p.juros_mora), str(p.total_parcela), str(ab.valor_abatido), str(ab.saldo_remanescente)])
        with open(os.path.join(pasta_destino, "indices_descontos.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_indices(descontos))
        with open(os.path.join(pasta_destino, "memoria_descontos.csv"), "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Nº", "Competência", "Base", "Índice", "Fator", "Atualizado", "Juros", "Observação"])
            for m in descontos.memoria_mensal:
                writer.writerow([m.parcela, m.competencia, str(m.valor_base), m.indice_aplicado, str(m.fator_aplicado), str(m.valor_corrigido), str(m.juros_periodo), m.observacao])
        with open(os.path.join(pasta_destino, "premissas_descontos.json"), "w", encoding="utf-8") as f:
            json.dump(descontos.premissas, f, ensure_ascii=False, indent=2, default=str)

    # 3. Alertas
    if resultado.honorarios_sucumbenciais or resultado.cumprimento_sentenca or resultado.destaque_contratuais:
        with open(os.path.join(pasta_destino, "honorarios_cumprimento.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_honorarios_principais(resultado))
    if resultado.honorarios_sucumbenciais and resultado.honorarios_sucumbenciais.memoria:
        with open(os.path.join(pasta_destino, "memoria_valor_causa.csv"), "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(linhas_memoria_valor_causa(resultado))

    caminho_alertas = os.path.join(pasta_destino, "alertas.csv")
    with open(caminho_alertas, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Alerta"])
        for a in resultado.alertas:
            writer.writerow([a])


def exportar_excel(resultado: ResultadoCalculo, caminho_arquivo: str) -> None:
    """
    Exporta a memória de cálculo completa para um arquivo Excel contendo as 9 abas:
    1. Dados Gerais, 2. Parcelas, 3. Memória Mensal, 4. Correção, 5. Juros,
    6. Acessórios, 7. Abatimentos, 8. Alertas, 9. Resumo.
    """
    diretorio = os.path.dirname(caminho_arquivo)
    if diretorio and not os.path.exists(diretorio):
        os.makedirs(diretorio)

    wb = openpyxl.Workbook()

    # 1. Aba Dados Gerais
    ws_dados = wb.active
    ws_dados.title = "Dados Gerais"
    dg = resultado.dados_gerais
    ws_dados.append(["Campo", "Valor"])
    ws_dados.append(["Processo", dg.processo])
    ws_dados.append(["Requerente", dg.requerente])
    ws_dados.append(["Requerido", dg.requerido])
    ws_dados.append(["Tipo de Devedor", dg.tipo_devedor.value])
    ws_dados.append(["Comarca", dg.comarca])
    ws_dados.append(["Classe", dg.classe])
    ws_dados.append(["Vara", dg.vara])
    ws_dados.append(["Contrato", dg.contrato])
    ws_dados.append(["Data-Base", dg.data_base.strftime("%Y-%m-%d")])
    if resultado.premissas.get("data_referencia_selic"):
        ws_dados.append(["Data-base SELIC (referência mensal)", resultado.premissas["data_referencia_selic"]])
        ws_dados.append(["Último índice SELIC aplicado (competência)", resultado.premissas.get("ultima_competencia_selic") or "Nenhum"])
    ws_dados.append(["Observações", dg.observacoes])
    if resultado.premissas.get("perfil") == "selic_ipcae_2aa_v1":
        ws_dados.append(["Padrão do cálculo", "Fazenda Pública 4"])
        ws_dados.append(["Início dos juros", {"vencimento": "Vencimento de cada parcela", "citacao": "Citação", "data_fixa": "Data específica", "por_parcela": "Por parcela"}.get(dg.criterio_inicio_juros, dg.criterio_inicio_juros)])
        ws_dados.append(["Data do início dos juros", dg.data_inicial_juros.strftime("%d/%m/%Y") if dg.data_inicial_juros else ""])

    ws_premissas = wb.create_sheet("Premissas")
    ws_premissas.append(["Premissa", "Valor"])
    for chave, valor in resultado.premissas.items():
        if chave == "entrada":
            valor = {
                **valor,
                "parcelas": "Ver linhas Entrada parcela abaixo",
                "custas_despesas": "Ver linhas Entrada custa ou despesa abaixo",
                "descontos": "Ver linhas Entrada descontos abaixo",
            }
        ws_premissas.append([chave, json.dumps(valor, ensure_ascii=False, default=str)])
    # Entrada completa e fontes em linhas separadas, evitando o limite de célula do Excel.
    if "entrada" in resultado.premissas:
        for p in resultado.premissas["entrada"]["parcelas"]:
            ws_premissas.append([f"Entrada parcela {p['numero']}", json.dumps(p, ensure_ascii=False)])
        for item in resultado.premissas["entrada"].get("custas_despesas", []):
            ws_premissas.append([
                f"Entrada custa ou despesa {item['numero']}",
                json.dumps(item, ensure_ascii=False),
            ])
        descontos_entrada = resultado.premissas["entrada"].get("descontos", {})
        ws_premissas.append(["Entrada descontos - critérios", json.dumps({k: v for k, v in descontos_entrada.items() if k != "itens"}, ensure_ascii=False)])
        for item in descontos_entrada.get("itens", []):
            ws_premissas.append([f"Entrada desconto {item['numero']}", json.dumps(item, ensure_ascii=False)])

    # 2. Aba Parcelas
    ws_parc = wb.create_sheet("Parcelas")
    ws_parc.append(["Nº", "Natureza", "Vencimento", "Histórico", "Valor Bruto", "Pago na Data", "Apurado", "Total Atualizado"])
    for p in resultado.parcelas:
        venc = p.data_vencimento.strftime("%Y-%m-%d") if p.data_vencimento else ""
        ws_parc.append([
            p.numero, p.natureza, venc, p.historico,
            float(p.valor_bruto), float(p.valor_pago_na_data), float(p.valor_apurado), float(p.total_parcela)
        ])

    if "multa_parcela" in resultado.resumo.totais_componentes:
        ws_multas = wb.create_sheet("Multas parcelas")
        ws_multas.append(["Nº", "Descrição", "Vencimento", "Saldo base", "Multa (%)", "Multa nominal", "Atualização da multa", "Juros da multa", "Total da multa"])
        for parcela in resultado.parcelas:
            m = parcela.multa_detalhes
            if m:
                ws_multas.append([parcela.numero, parcela.historico, str(parcela.data_vencimento), *[float(v) for v in (m.base_calculo, m.percentual, m.valor_original, m.correcao_monetaria, m.juros_mora, m.total_atualizado)]])

    # 3. Aba Memória Mensal
    ws_mem = wb.create_sheet("Memória Mensal")
    ws_mem.append(["Parcela", "Competência", "Valor Base", "Índice", "Fator", "Valor Corrigido", "Juros Período", "Juros Acumulados", "Multa", "Total", "Observação"])
    for m in resultado.memoria_mensal:
        ws_mem.append([
            m.parcela, m.competencia, float(m.valor_base), m.indice_aplicado,
            float(m.fator_aplicado), float(m.valor_corrigido), float(m.juros_periodo),
            float(m.juros_acumulados), float(m.multa), float(m.total), memoria_exibida(m.observacao)
        ])

    # 4. Aba Correção
    ws_corr = wb.create_sheet("Correção")
    ws_corr.append(["Parcela", "Competência", "Índice", "Fator", "Valor Corrigido"])
    for m in resultado.memoria_mensal:
        if m.valor_corrigido > Decimal("0") or m.fator_aplicado != Decimal("1"):
            ws_corr.append([m.parcela, m.competencia, m.indice_aplicado, float(m.fator_aplicado), float(m.valor_corrigido)])

    # 5. Juros
    ws_jur = wb.create_sheet("Juros")
    ws_jur.append(["Parcela", "Competência", "Juros Período", "Juros Acumulados"])
    for m in resultado.memoria_mensal:
        if m.juros_periodo > Decimal("0") or m.juros_acumulados > Decimal("0"):
            ws_jur.append([m.parcela, m.competencia, float(m.juros_periodo), float(m.juros_acumulados)])

    # 6. Acessórios
    ws_aces = wb.create_sheet("Acessórios")
    ws_aces.append(["Descrição/Honorários", "Percentual / Base", "Valor"])
    for h in resultado.honorarios_detalhes:
        ws_aces.append([h["descricao"], f"{h.get('percentual') or 0}% sobre {h.get('base_calculo')}", float(h["valor"])])
    ws_aces.append(["Custas Processuais Corrigidas", "", float(resultado.resumo.custas)])
    ws_aces.append(["Despesas Processuais Corrigidas", "", float(resultado.resumo.despesas)])

    if resultado.custas_despesas:
        ws_custas = wb.create_sheet("Custas e despesas")
        ws_custas.append(["Nº", "Nome", "Data", "Valor original", "Fator IPCA-E", "Correção monetária", "Valor atualizado"])
        for item in resultado.custas_despesas:
            ws_custas.append([
                item.numero, item.nome, item.data.isoformat(), float(item.valor_original),
                float(item.fator_ipcae), float(item.correcao_monetaria), float(item.valor_atualizado),
            ])
        ws_mem_custas = wb.create_sheet("Memória custas")
        ws_mem_custas.append(["Nº", "Nome", "Competência", "Valor base", "Índice", "Fator", "Valor corrigido", "Observação"])
        for item in resultado.custas_despesas:
            for memoria in item.memoria:
                ws_mem_custas.append([
                    item.numero, item.nome, memoria.competencia, float(memoria.valor_base),
                    memoria.indice_aplicado, float(memoria.fator_aplicado),
                    float(memoria.valor_corrigido), memoria_exibida(memoria.observacao),
                ])

    # 7. Abatimentos
    ws_abat = wb.create_sheet("Abatimentos")
    headers_abatimentos = [
        "Data Pagamento", "Historico", "Forma Imputacao", "Saldo Anterior",
        "Valor Abatido", "Saldo Posterior", "Mes Quitacao", "Saldo Remanescente"
    ]
    ws_abat.append(["Data Pagamento", "Histórico", "Forma Imputação", "Saldo Anterior", "Valor Abatido", "Saldo Posterior"])
    ws_abat.cell(row=1, column=7, value=headers_abatimentos[6])
    ws_abat.cell(row=1, column=8, value=headers_abatimentos[7])
    for ab in resultado.memorias_abatimento:
        ws_abat.append([
            ab.data_pagamento.strftime("%Y-%m-%d"), ab.historico, ab.forma_imputacao.value,
            float(ab.saldo_anterior), float(ab.valor_abatido), float(ab.saldo_posterior),
            ab.competencia_quitacao or "", float(ab.saldo_remanescente)
        ])

    # 8. Alertas
    ws_al = wb.create_sheet("Alertas")
    ws_al.append(["Mensagem de Alerta"])
    for al in resultado.alertas:
        ws_al.append([al])

    # 9. Resumo
    ws_res = wb.create_sheet("Resumo")
    ws_res.append(["Rubrica", "Valor"])
    res = resultado.resumo
    ws_res.append(["Principal Original", float(res.principal_original)])
    ws_res.append(["(-) Pago na Data", float(res.valor_pago_na_data_parcelas)])
    ws_res.append(["Principal Apurado", float(res.principal_apurado)])
    ws_res.append(["(+) Correção Monetária", float(res.correcao_monetaria)])
    ws_res.append(["(+) Juros de Mora", float(res.juros_mora)])
    ws_res.append(["(+) Multas/Astreintes", float(res.multas)])
    ws_res.append(["(+) Honorários Advocatícios", float(res.honorarios)])
    ws_res.append(["(+) Custas Processuais", float(res.custas)])
    ws_res.append(["(+) Despesas", float(res.despesas)])
    ws_res.append(["(-) Abatimentos Posteriores", float(res.abatimentos)])
    ws_res.append(["TOTAL ATUALIZADO DO DÉBITO", float(res.total_atualizado)])

    if resultado.premissas.get("selecao_descontos"):
        ws_pagamentos = wb.create_sheet("Pagamentos registrados")
        for linha in linhas_pagamentos_registrados(resultado):
            ws_pagamentos.append(linha)
    if resultado.descontos:
        descontos = resultado.descontos
        ws_desc = wb.create_sheet("Descontos")
        ws_desc.append(["Nº", "Data do desconto", "Descrição", "Valor informado", "Atualizado", "Abatido", "Excedente"])
        for p, ab in zip(descontos.parcelas, resultado.memorias_abatimento):
            ws_desc.append([p.numero, str(p.data_vencimento), p.historico, float(p.valor_bruto), float(p.total_parcela), float(ab.valor_abatido), float(ab.saldo_remanescente)])
        ws_desc_indices = wb.create_sheet("Índices descontos")
        for linha in linhas_indices(descontos):
            ws_desc_indices.append(linha)
        ws_desc_mem = wb.create_sheet("Memória descontos")
        ws_desc_mem.append(["Nº", "Competência", "Base", "Índice", "Fator", "Atualizado", "Juros", "Observação"])
        for m in descontos.memoria_mensal:
            ws_desc_mem.append([m.parcela, m.competencia, float(m.valor_base), m.indice_aplicado, float(m.fator_aplicado), float(m.valor_corrigido), float(m.juros_periodo), m.observacao])
        ws_desc_prem = wb.create_sheet("Critérios descontos")
        ws_desc_prem.append(["Premissa", "Valor"])
        for chave, valor in descontos.premissas.items():
            if chave != "entrada":
                ws_desc_prem.append([chave, json.dumps(valor, ensure_ascii=False, default=str)])

    if resultado.premissas.get("perfil") in (
        "fazenda_publica_1_v1", "fazenda_publica_2_v1",
        "selic_ipcae_poupanca_v1", "selic_ipcae_2aa_v1", "selic_cjf_v1",
        "ipcae_1am_simples_v1", "ipca_taxa_legal_v1", "civil_2_v1",
    ):
        ws_indices = wb.create_sheet("Índices por parcela")
        for linha in linhas_indices(resultado):
            ws_indices.append(linha)
        for row in ws_indices.iter_rows(min_row=2):
            for cell in row[5:]:
                if cell.value != "":
                    cell.value = float(cell.value)
                    cell.number_format = '#,##0.00' if cell.column == 9 else '0.000000' if cell.column == 8 and 'Taxa Legal' in str(row[1].value) else '0.0000'
        ws_parc.delete_rows(1, ws_parc.max_row)
        cabecalho = ["Nº", "Correção desde" if resultado.premissas.get("perfil") in ("ipca_taxa_legal_v1", "civil_2_v1") else "Vencimento", "Histórico", "Valor bruto", "Pago no vencimento", "Principal apurado"]
        for _, nome, faixa in colunas_componentes(resultado):
            cabecalho.extend([f"{nome} ({faixa}) - índice acumulado", f"{nome} - acréscimo (R$)"])
        ws_parc.append([*cabecalho, "Total atualizado"])
        for p in resultado.parcelas:
            linha = [p.numero, str(p.data_vencimento), p.historico, float(p.valor_bruto), float(p.valor_pago_na_data), float(p.valor_apurado)]
            for chave, _, _ in colunas_componentes(resultado):
                c = p.componentes[chave]
                indice = "Não incide" if c.data_inicial is None else (
                    f"Fator {c.fator_acumulado:.4f}" if c.fator_acumulado is not None else f"{c.taxa_acumulada_percentual:.6f}%" if chave == "taxa_legal" else f"{c.taxa_acumulada_percentual:.4f}%")
                linha.extend([indice, float(c.valor)])
            ws_parc.append([*linha, float(p.total_parcela)])
        for nome in ("Correção", "Juros", "Acessórios", "Abatimentos", "Alertas"):
            if (nome == "Abatimentos" and resultado.descontos) or (nome == "Alertas" and resultado.alertas):
                continue
            wb.remove(wb[nome])
        ws_res.delete_rows(1, ws_res.max_row)
        ws_res.append(["Rubrica", "Valor"])
        for nome, valor in (
            ("Principal original", res.principal_original),
            ("Pago no vencimento", res.valor_pago_na_data_parcelas),
            ("Principal apurado", res.principal_apurado),
            *[(f"{nome} ({faixa})", res.totais_componentes[chave]) for chave, nome, faixa in colunas_componentes(resultado)],
            *([("(-) Descontos atualizados abatidos", res.abatimentos)] if resultado.descontos else []),
            *([("(+) Honorários sucumbenciais", resultado.honorarios_sucumbenciais.valor)] if resultado.honorarios_sucumbenciais else []),
            *([("(+) Multa art. 523", resultado.cumprimento_sentenca.multa)] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_multa else []),
            *([("(+) Honorários art. 523", resultado.cumprimento_sentenca.honorarios)] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_honorarios else []),
            ("(+) Custas e despesas processuais — IPCA-E", res.custas),
            ("TOTAL ATUALIZADO DO DÉBITO", res.total_atualizado),
        ):
            ws_res.append([nome, float(valor)])
        from openpyxl.styles import Font, PatternFill, Alignment
        if resultado.premissas.get("memoria_taxa_legal"):
            from .relatorio_taxa_legal import linhas_taxa_legal
            ws_legal = wb.create_sheet("Taxa Legal")
            for linha in linhas_taxa_legal(resultado):
                ws_legal.append(linha)
            for row in ws_legal.iter_rows(min_row=2):
                for i in (4, 5, 6, 7, 8, 9):
                    row[i].value = float(row[i].value)
                    row[i].number_format = '0.000000' if i < 7 else '0.0000' if i == 7 else '#,##0.00'
        if resultado.honorarios_sucumbenciais or resultado.cumprimento_sentenca or resultado.destaque_contratuais:
            ws_h = wb.create_sheet("Honorários e cumprimento")
            for linha in linhas_honorarios_principais(resultado):
                ws_h.append(linha)
            for row in ws_h.iter_rows(min_row=2):
                for i in (2, 4, 5, 6, 7):
                    if row[i].value not in ("", None):
                        row[i].value = float(row[i].value)
                        row[i].number_format = '0.0000' if i in (4, 6) else '#,##0.00'
        if resultado.honorarios_sucumbenciais and resultado.honorarios_sucumbenciais.memoria:
            ws_h_mem = wb.create_sheet("Memória valor causa")
            for linha in linhas_memoria_valor_causa(resultado):
                ws_h_mem.append(linha)
            for row in ws_h_mem.iter_rows(min_row=2):
                for i in (1, 3, 4):
                    row[i].value = float(row[i].value)
                    row[i].number_format = '0.0000' if i != 4 else '#,##0.00'
        for row in ws_res.iter_rows(min_row=2, min_col=2, max_col=2):
            row[0].number_format = '#,##0.00'
        for row in ws_parc.iter_rows(min_row=2):
            for cell in row[3:]:
                if isinstance(cell.value, (float, int)):
                    cell.number_format = '#,##0.00'
        for row in ws_mem.iter_rows(min_row=2):
            row[2].number_format = '0.0000'
            row[4].number_format = '0.0000'
        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1E3A8A")
                cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
            ws.row_dimensions[1].height = 45 if ws == ws_parc else 30
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(16, max(len(str(c.value or "")) for c in col) + 2))
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    # Valores textuais do processo nunca são fórmulas da planilha.
                    if isinstance(cell.value, str):
                        cell.data_type = "s"
    wb.save(caminho_arquivo)
