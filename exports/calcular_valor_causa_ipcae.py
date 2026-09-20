"""Gera o demonstrativo do caso pelo motor mensal e pelo PDF oficial do projeto."""
import calendar
import hashlib
import json
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from pypdf import PdfReader
from liquidacao_custom.core.models import DadosGerais, Parcela
from liquidacao_custom.core.motor_ipcae_mensal import calcular_ipcae_mensal, proximo_mes
from liquidacao_custom.core.motor_simplificado import carregar_base
from liquidacao_custom.core.relatorio_pdf import exportar_pdf


def executar():
    valores = (["833.35"] * 4 + ["1779.31"] * 12 + ["2787.84"] * 5
               + ["3046.30"] * 6 + ["3050.47"] + ["4303.73"] * 5 + ["4519.49"] * 3)
    parcelas = []
    atual = date(2023, 9, 1)
    for numero, valor in enumerate(valores, 1):
        venc = atual.replace(day=calendar.monthrange(atual.year, atual.month)[1])
        parcelas.append(Parcela(numero=numero, historico=f"Parcela mensal - {atual:%m/%Y}",
                                data_vencimento=venc, valor_bruto=Decimal(valor)))
        atual = proximo_mes(atual)
    for historico, valor in (("Repetição em dobro", "99483.58"), ("12 parcelas vincendas", "54233.88")):
        parcelas.append(Parcela(numero=len(parcelas)+1, historico=historico,
                                data_vencimento=date(2026, 8, 31), valor_bruto=Decimal(valor)))
    geral = DadosGerais(data_base=date(2026, 8, 31))
    dados = carregar_base()
    resultado = calcular_ipcae_mensal(geral, parcelas, dados)
    resultado.premissas.update({"omitir_qualificacao": True, "titulo_total": "VALOR DA CAUSA"})
    mensal = sum(p.total_parcela for p in resultado.parcelas[:36])
    geral.observacoes = (
        "Objeto: apuração do valor da causa. Mantidas as 36 parcelas mensais de 09/2023 a 08/2026. "
        "Acrescentadas em 08/2026 as linhas 'Repetição em dobro' (R$ 99.483,58) e '12 parcelas vincendas' "
        "(R$ 54.233,88), pelos valores expressamente informados. A primeira é uma parcela adicional à série mensal."
    )
    resultado.dados_gerais = geral
    resultado.premissas["entrada"]["dados_gerais"] = geral.model_dump(mode="json")
    # Conferência independente: multiplicar as taxas mensais da série oficial IPCA-15/IBGE.
    fonte = ROOT / "backend/data/fontes/bcb_ipca15_2009_2026.json"
    assert hashlib.sha256(fonte.read_bytes()).hexdigest() == dados["sha256_fontes"][fonte.name]
    taxas_ibge = {
        f"{item['data'][6:10]}-{item['data'][3:5]}": Decimal(item["valor"])
        for item in json.loads(fonte.read_text(encoding="utf-8-sig"))
    }
    totais_independentes = []
    for p, r in zip(parcelas, resultado.parcelas):
        competencia = proximo_mes(p.data_vencimento)
        fator_acumulado = Decimal(1)
        while competencia <= geral.data_base:
            taxa = taxas_ibge[competencia.strftime("%Y-%m")]
            fator_acumulado *= Decimal(1) + taxa / Decimal(100)
            competencia = proximo_mes(competencia)
        independente = (p.valor_bruto * fator_acumulado).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert r.total_parcela == independente, (p.numero, r.total_parcela, independente)
        totais_independentes.append(independente)
    assert len(resultado.parcelas) == 38
    assert sum(p.valor_bruto for p in parcelas[:36]) == Decimal("95029.71")
    assert mensal == sum(totais_independentes[:36], Decimal(0))
    assert resultado.resumo.total_atualizado == sum(totais_independentes, Decimal(0))
    assert resultado.resumo.juros_mora == 0
    assert resultado.parcelas[-2].total_parcela == Decimal("99483.58")
    assert resultado.parcelas[-1].total_parcela == Decimal("54233.88")

    out = ROOT / "exports/outputs/valor_causa_ipcae_2026_08"
    out.mkdir(parents=True, exist_ok=True)
    (out / "entrada.json").write_text(json.dumps(resultado.premissas["entrada"], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "memoria_completa.json").write_text(resultado.model_dump_json(indent=2), encoding="utf-8")
    validacao = {"parcelas": 38, "principal_mensal": "95029.71", "correcao_ipcae": str(resultado.resumo.correcao_monetaria),
                 "subtotal_mensal_atualizado": str(mensal), "repeticao_em_dobro_adicional": "99483.58",
                 "vincendas": "54233.88", "valor_da_causa": str(resultado.resumo.total_atualizado),
                 "conferencia_independente": "38 parcelas conferidas pela multiplicação das taxas mensais do IPCA-15/IBGE",
                 "sha256_fonte": dados["sha256_fontes"][fonte.name]}
    (out / "validacao.json").write_text(json.dumps(validacao, ensure_ascii=False, indent=2), encoding="utf-8")
    pdf_path = ROOT / "output/pdf/valor_da_causa_ipcae_2026_08.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(exportar_pdf(resultado))
    reader = PdfReader(pdf_path)
    content = "\n".join(page.extract_text() for page in reader.pages)
    total_formatado = f"{resultado.resumo.total_atualizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    for termo in (total_formatado, "Repetição em dobro", "12 parcelas vincendas", "38 parcelas", "IPCA-E"):
        assert termo in content, termo
    for termo in ("Dados do processo", "Requerente:", "Requerido:", "Poupança", "Início dos juros:"):
        assert termo not in content, termo
    assert len(reader.pages[0].images) == 1
    assert reader.metadata.title == "Demonstrativo de cálculo"
    assert reader.metadata.author == "Barreto Fontes Sociedade de Advogados"
    for n, page in enumerate(reader.pages, 1):
        assert round(float(page.mediabox.width)) == 842
        assert round(float(page.mediabox.height)) == 595
        assert f"Página {n}" in page.extract_text()
    print(json.dumps({"pdf": str(pdf_path), "paginas": len(reader.pages), **validacao}, ensure_ascii=False))


if __name__ == "__main__":
    executar()
