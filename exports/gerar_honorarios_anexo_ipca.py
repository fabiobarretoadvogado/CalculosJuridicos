"""Gera o caso do anexo usando exclusivamente o motor e o PDF oficiais."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "output" / "pdf" / "honorarios_valor_causa_anexo_ipca_2026-08.pdf"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from liquidacao_custom.core.honorarios_isolados import (  # noqa: E402
    CalculoHonorariosIsolados,
    executar_honorarios_isolados,
)
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios  # noqa: E402


def montar_entrada() -> CalculoHonorariosIsolados:
    return CalculoHonorariosIsolados.model_validate({
        "categoria": "honorarios_sucumbenciais_isolados",
        "dados_gerais": {
            "data_base": "2026-08-31",
            "processo": "202601150833",
            "classe": "Recurso Inominado",
            "requerente": "MANOEL MESSIAS DE JESUS MENEZES",
            "requerido": "EDILSON DA PAIXÃO",
            "observacoes": (
                "Origem: cumprimento de sentença nº 202440103644. "
                "Documento-base: demonstrativo de atualização monetária do TJDFT, "
                "emitido em 27/11/2024. O total de R$ 49.498,12 foi adotado como "
                "valor da causa nessa data por indicação expressa do usuário."
            ),
        },
        "base": "valor_causa",
        "valor_causa": "49498.12",
        "data_protocolo": "2024-11-27",
        "indice": "ipca",
        "percentual_sentenca": "10",
    })


def gerar() -> bytes:
    resultado = executar_honorarios_isolados(montar_entrada())
    assert resultado.apuracao.base_atualizada == Decimal("53516.27")
    assert resultado.apuracao.correcao_monetaria == Decimal("4018.15")
    assert resultado.honorarios_sucumbenciais == Decimal("5351.63")
    return exportar_pdf_honorarios(resultado, incluir_memoria_detalhada=False)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(gerar())
    print(OUTPUT)
