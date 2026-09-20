"""
Módulo de geração de relatórios textuais em formato Markdown.
"""

from __future__ import annotations

from decimal import Decimal
from liquidacao_custom.core.models import ResultadoCalculo


def gerar_relatorio_texto(resultado: ResultadoCalculo) -> str:
    """
    Gera um relatório textual formatado em Markdown com os detalhes do cálculo.
    """
    dg = resultado.dados_gerais
    res = resultado.resumo
    honorarios_contratuais = Decimal(str(resultado.premissas.get("honorarios_contratuais_destacados", "0")))
    valor_liquido_credito = res.total_atualizado - honorarios_contratuais

    md = []
    md.append(f"# MEMÓRIA DE CÁLCULO JUDICIAL")
    md.append(f"**Processo:** {dg.processo}")
    md.append(f"**Requerente:** {dg.requerente} | **Requerido:** {dg.requerido}")
    md.append(f"**Tipo de Devedor:** {dg.tipo_devedor.value.upper()}")
    md.append(f"**Data-Base do Cálculo:** {dg.data_base.strftime('%d/%m/%Y')}")
    if dg.comarca or dg.vara:
        md.append(f"**Juízo:** Vara {dg.vara} - Comarca {dg.comarca}")
    if dg.contrato:
        md.append(f"**Contrato Ref:** {dg.contrato}")
    if dg.observacoes:
        md.append(f"\n*Observações gerais:* {dg.observacoes}")
    md.append("\n" + "-"*40 + "\n")

    md.append("## 1. RESUMO GERAL DO DÉBITO")
    md.append(f"- **Principal Original:** R$ {res.principal_original:,.2f}")
    md.append(f"- **(-) Pago na Data:** R$ {res.valor_pago_na_data_parcelas:,.2f}")
    md.append(f"- **Principal Apurado:** R$ {res.principal_apurado:,.2f}")
    md.append(f"- **(+) Correção Monetária:** R$ {res.correcao_monetaria:,.2f}")
    md.append(f"- **(+) Juros de Mora:** R$ {res.juros_mora:,.2f}")
    md.append(f"- **(+) Multas/Astreintes:** R$ {res.multas:,.2f}")
    md.append(f"- **(+) Honorários Advocatícios:** R$ {res.honorarios:,.2f}")
    md.append(f"- **(+) Custas Processuais:** R$ {res.custas:,.2f}")
    md.append(f"- **(+) Despesas:** R$ {res.despesas:,.2f}")
    md.append(f"- **(-) Abatimentos Posteriores:** R$ {res.abatimentos:,.2f}")
    md.append(f"### **TOTAL ATUALIZADO DO DÉBITO:** R$ {res.total_atualizado:,.2f}")
    if honorarios_contratuais > Decimal("0"):
        md.append(f"- **(-) Honorários Contratuais Destacados:** R$ {honorarios_contratuais:,.2f}")
        md.append(f"### **VALOR LÍQUIDO DO CRÉDITO:** R$ {valor_liquido_credito:,.2f}")
    md.append("\n" + "-"*40 + "\n")

    md.append("## 2. DETALHAMENTO DAS PARCELAS")
    headers = ["Nº", "Vencimento", "Histórico", "Valor Bruto", "Pago na Data", "Apurado", "Correção", "Juros", "Multa", "Total"]
    md.append("| " + " | ".join(headers) + " |")
    md.append("|" + "|".join(["---" for _ in headers]) + "|")

    for p in resultado.parcelas:
        venc = p.data_vencimento.strftime('%d/%m/%Y') if p.data_vencimento else "-"
        row = [
            str(p.numero),
            venc,
            p.historico,
            f"R$ {p.valor_bruto:,.2f}",
            f"R$ {p.valor_pago_na_data:,.2f}",
            f"R$ {p.valor_apurado:,.2f}",
            f"R$ {p.correcao_monetaria:,.2f}",
            f"R$ {p.juros_mora:,.2f}",
            f"R$ {p.multa:,.2f}",
            f"R$ {p.total_parcela:,.2f}",
        ]
        md.append("| " + " | ".join(row) + " |")

    if resultado.memorias_abatimento:
        md.append("\n" + "-"*40 + "\n")
        md.append("## 3. ABATIMENTOS E PAGAMENTOS PARCIAIS POSTERIORES")
        ab_headers = ["Data Pagto", "Histórico", "Imputação", "Saldo Anterior", "Valor Abatido", "Saldo Devedor"]
        ab_headers.extend(["Mes Quit.", "Saldo Reman."])
        md.append("| " + " | ".join(ab_headers) + " |")
        md.append("|" + "|".join(["---" for _ in ab_headers]) + "|")
        for ab in resultado.memorias_abatimento:
            row = [
                ab.data_pagamento.strftime('%d/%m/%Y'),
                ab.historico,
                ab.forma_imputacao.value,
                f"R$ {ab.saldo_anterior:,.2f}",
                f"R$ {ab.valor_abatido:,.2f}",
                f"R$ {ab.saldo_posterior:,.2f}",
                ab.competencia_quitacao or "-",
                f"R$ {ab.saldo_remanescente:,.2f}",
            ]
            md.append("| " + " | ".join(row) + " |")

    if resultado.alertas:
        md.append("\n" + "="*40 + "\n")
        md.append("## ALERTAS E INCONSISTÊNCIAS IDENTIFICADAS")
        for al in resultado.alertas:
            md.append(f"- ⚠️ {al}")

    return "\n".join(md)
