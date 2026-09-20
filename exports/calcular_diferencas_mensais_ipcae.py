"""Calcula diferenças mensais com correção exclusiva pelo IPCA-E."""
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


FAIXAS = (
    (date(2023, 9, 1), date(2023, 11, 1), Decimal("159.98")),
    (date(2023, 12, 1), date(2024, 11, 1), Decimal("212.46")),
    (date(2024, 12, 1), date(2025, 11, 1), Decimal("356.65")),
    (date(2025, 12, 1), date(2026, 8, 1), Decimal("572.76")),
)
DATA_BASE = date(2026, 8, 31)
NOME_CASO = "diferencas_mensais_ipcae_2026_08"


def meses_entre(inicio: date, fim: date):
    atual = inicio
    while atual <= fim:
        yield atual
        atual = proximo_mes(atual)


def carregar_taxas_da_fonte(dados):
    fonte = ROOT / "backend/data/fontes/bcb_ipca15_2009_2026.json"
    digest = hashlib.sha256(fonte.read_bytes()).hexdigest()
    assert digest == dados["sha256_fontes"][fonte.name]
    itens = json.loads(fonte.read_text(encoding="utf-8-sig"))
    taxas = {
        f"{item['data'][6:10]}-{item['data'][3:5]}": Decimal(item["valor"])
        for item in itens
    }
    return fonte, digest, taxas


def executar():
    parcelas = []
    resumo_faixas = []
    for inicio, fim, valor in FAIXAS:
        meses = list(meses_entre(inicio, fim))
        resumo_faixas.append(
            {
                "periodo": f"{inicio:%m/%Y} a {fim:%m/%Y}",
                "quantidade": len(meses),
                "diferenca_mensal": str(valor),
                "principal": str(valor * len(meses)),
            }
        )
        for competencia in meses:
            vencimento = competencia.replace(
                day=calendar.monthrange(competencia.year, competencia.month)[1]
            )
            parcelas.append(
                Parcela(
                    numero=len(parcelas) + 1,
                    historico=f"Diferença mensal - {competencia:%m/%Y}",
                    data_vencimento=vencimento,
                    valor_bruto=valor,
                )
            )

    geral = DadosGerais(
        data_base=DATA_BASE,
        observacoes=(
            "Objeto: atualização de 36 diferenças mensais pelo IPCA-E, sem juros. "
            "Faixas informadas: 09/2023 a 11/2023, R$ 159,98 por mês; "
            "12/2023 a 11/2024, R$ 212,46 por mês; "
            "12/2024 a 11/2025, R$ 356,65 por mês; e "
            "12/2025 a 08/2026, R$ 572,76 por mês."
        ),
    )
    dados = carregar_base()
    resultado = calcular_ipcae_mensal(geral, parcelas, dados)
    resultado.premissas.update(
        {
            "omitir_qualificacao": True,
            "titulo_total": "TOTAL ATUALIZADO",
            "faixas_informadas": resumo_faixas,
        }
    )

    fonte, digest, taxas_ibge = carregar_taxas_da_fonte(dados)
    totais_independentes = []
    for parcela, calculada in zip(parcelas, resultado.parcelas):
        competencia = proximo_mes(parcela.data_vencimento)
        fator_acumulado = Decimal(1)
        while competencia <= DATA_BASE:
            taxa = taxas_ibge[competencia.strftime("%Y-%m")]
            fator_acumulado *= Decimal(1) + taxa / Decimal(100)
            competencia = proximo_mes(competencia)
        esperado = (parcela.valor_bruto * fator_acumulado).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert calculada.total_parcela == esperado, (
            parcela.numero,
            calculada.total_parcela,
            esperado,
        )
        totais_independentes.append(esperado)

    assert len(parcelas) == 36
    assert [faixa["quantidade"] for faixa in resumo_faixas] == [3, 12, 12, 9]
    principal = sum((p.valor_bruto for p in parcelas), Decimal(0))
    total_independente = sum(totais_independentes, Decimal(0))
    assert resultado.resumo.principal_original == principal
    assert resultado.resumo.total_atualizado == total_independente
    assert resultado.resumo.juros_mora == 0

    pasta = ROOT / "exports/outputs" / NOME_CASO
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "entrada.json").write_text(
        json.dumps(resultado.premissas["entrada"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (pasta / "memoria_completa.json").write_text(
        resultado.model_dump_json(indent=2), encoding="utf-8"
    )

    validacao = {
        "data_base": DATA_BASE.isoformat(),
        "criterio": "IPCA-E exclusivo, sem juros",
        "parcelas": len(parcelas),
        "faixas": resumo_faixas,
        "principal": str(principal),
        "correcao_ipcae": str(resultado.resumo.correcao_monetaria),
        "juros": str(resultado.resumo.juros_mora),
        "total_atualizado": str(resultado.resumo.total_atualizado),
        "conferencia_independente": (
            "36 parcelas conferidas pela multiplicação das taxas mensais "
            "do IPCA-15 produzidas pelo IBGE"
        ),
        "fonte_arquivada": str(fonte.relative_to(ROOT)),
        "sha256_fonte": digest,
    }
    (pasta / "validacao.json").write_text(
        json.dumps(validacao, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pdf_path = ROOT / "output/pdf" / f"relatorio_final_{NOME_CASO}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(exportar_pdf(resultado))

    reader = PdfReader(pdf_path)
    conteudo = "\n".join(page.extract_text() for page in reader.pages)
    total_formatado = f"{resultado.resumo.total_atualizado:,.2f}".replace(
        ",", "X"
    ).replace(".", ",").replace("X", ".")
    for termo in (
        total_formatado,
        "36 parcelas",
        "IPCA-E",
        "159,98",
        "212,46",
        "356,65",
        "572,76",
    ):
        assert termo in conteudo, termo
    for termo in ("Dados do processo", "Requerente:", "Requerido:", "Poupança"):
        assert termo not in conteudo, termo
    assert len(reader.pages[0].images) == 1
    assert reader.metadata.title == "Demonstrativo de cálculo"
    assert reader.metadata.author == "Barreto Fontes Sociedade de Advogados"
    for numero, pagina in enumerate(reader.pages, 1):
        assert round(float(pagina.mediabox.width)) == 842
        assert round(float(pagina.mediabox.height)) == 595
        assert f"Página {numero}" in pagina.extract_text()

    print(
        json.dumps(
            {
                "pdf": str(pdf_path),
                "paginas": len(reader.pages),
                "validacao": str(pasta / "validacao.json"),
                **validacao,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    executar()
