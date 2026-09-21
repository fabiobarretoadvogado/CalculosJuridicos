"""Valida o protocolo MCP do executável empacotado e a geração de PDF."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ENTRADA = {
    "perfil": "selic_cjf_v1",
    "dados_gerais": {"data_base": "2026-08-31", "processo": "AUTOTESTE-MCP"},
    "parcelas": [
        {
            "numero": 1,
            "historico": "Parcela de autoteste",
            "data_vencimento": "2026-08-01",
            "valor_bruto": "1000.00",
        }
    ],
}


async def validar(executavel: Path, pasta_temporaria: Path) -> dict:
    parametros = StdioServerParameters(
        command=str(executavel),
        args=["--mcp"],
        cwd=executavel.parent,
    )
    async with stdio_client(parametros) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            inicializacao = await sessao.initialize()
            ferramentas = await sessao.list_tools()
            nomes = {item.name for item in ferramentas.tools}
            esperadas = {
                "informacoes_aplicativo",
                "calcular_debito_judicial",
                "gerar_pdf_debito_judicial",
                "calcular_honorarios_proveito_economico",
                "gerar_pdf_honorarios_proveito_economico",
                "calcular_honorarios_isolados",
                "gerar_pdf_honorarios_isolados",
            }
            ausentes = esperadas - nomes
            if ausentes:
                raise RuntimeError(f"Ferramentas MCP ausentes: {', '.join(sorted(ausentes))}")
            calculo = await sessao.call_tool(
                "calcular_debito_judicial",
                {"calculo": ENTRADA},
            )
            if calculo.isError or calculo.structuredContent.get("quantidade_parcelas") != 1:
                raise RuntimeError("O cálculo de autoteste MCP falhou.")
            pdf = await sessao.call_tool(
                "gerar_pdf_debito_judicial",
                {
                    "calculo": ENTRADA,
                    "nome_arquivo": "autoteste-mcp.pdf",
                    "pasta_destino": str(pasta_temporaria),
                },
            )
            caminho = Path(pdf.structuredContent.get("arquivo", ""))
            if pdf.isError or not caminho.is_file() or not caminho.read_bytes().startswith(b"%PDF-"):
                raise RuntimeError("O relatório PDF de autoteste MCP falhou.")
            return {
                "sucesso": True,
                "servidor": inicializacao.serverInfo.name,
                "ferramentas": len(nomes),
                "pdf_bytes": caminho.stat().st_size,
            }


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Uso: smoke_mcp.py EXECUTAVEL [PASTA_TEMPORARIA]")
    executavel = Path(sys.argv[1]).resolve(strict=True)
    raiz_temporaria = Path(sys.argv[2]).resolve(strict=True) if len(sys.argv) == 3 else executavel.parent
    with tempfile.TemporaryDirectory(prefix="mcp-smoke-", dir=raiz_temporaria) as pasta:
        resultado = anyio.run(validar, executavel, Path(pasta))
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
