import io
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pypdf import PdfReader

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.mcp_server import (
    calcular_debito_judicial,
    gerar_pdf_debito_judicial,
    informacoes_aplicativo,
    nomes_ferramentas,
)


def entrada_principal():
    return {
        "perfil": "selic_cjf_v1",
        "dados_gerais": {
            "data_base": "2026-08-31",
            "processo": "MCP-TESTE",
        },
        "parcelas": [
            {
                "numero": 1,
                "historico": "Parcela de teste",
                "data_vencimento": "2026-08-01",
                "valor_bruto": "1000.00",
            }
        ],
    }


def test_mcp_expoe_motor_e_pdf_sem_interface(tmp_path):
    calculo = CalculoSimplificado.model_validate(entrada_principal())
    resumo = calcular_debito_judicial(calculo)
    assert resumo["total_atualizado"]
    assert resumo["quantidade_parcelas"] == 1

    resposta = gerar_pdf_debito_judicial(
        calculo,
        nome_arquivo='Relatório: "MCP".pdf',
        pasta_destino=str(tmp_path),
    )
    dados = resposta.structuredContent
    arquivo = Path(dados["arquivo"])
    assert arquivo.is_file()
    assert arquivo.suffix == ".pdf"
    assert ":" not in arquivo.name
    assert arquivo.read_bytes().startswith(b"%PDF-")
    texto = "\n".join(
        pagina.extract_text() for pagina in PdfReader(io.BytesIO(arquivo.read_bytes())).pages
    )
    assert "MCP-TESTE" in texto
    assert any(item.type == "resource_link" for item in resposta.content)


def test_mcp_lista_todas_as_operacoes_e_informa_versao():
    ferramentas = nomes_ferramentas()
    assert len(ferramentas) == 9
    assert "gerar_pdf_honorarios_proveito_economico" in ferramentas
    assert informacoes_aplicativo()["pdf"] is True


def test_protocolo_stdio_inicializa_calcula_e_gera_pdf(tmp_path):
    raiz = Path(__file__).resolve().parents[2]

    async def executar():
        parametros = StdioServerParameters(
            command=sys.executable,
            args=[str(raiz / "desktop_main.py"), "--mcp"],
            cwd=raiz,
        )
        async with stdio_client(parametros) as (leitura, escrita):
            async with ClientSession(leitura, escrita) as sessao:
                await sessao.initialize()
                ferramentas = await sessao.list_tools()
                nomes = {item.name for item in ferramentas.tools}
                assert "calcular_debito_judicial" in nomes
                resposta = await sessao.call_tool("informacoes_aplicativo", {})
                assert resposta.isError is False
                assert resposta.structuredContent["pdf"] is True
                calculo = await sessao.call_tool(
                    "calcular_debito_judicial",
                    {"calculo": entrada_principal()},
                )
                assert calculo.isError is False
                assert calculo.structuredContent["quantidade_parcelas"] == 1
                pdf = await sessao.call_tool(
                    "gerar_pdf_debito_judicial",
                    {
                        "calculo": entrada_principal(),
                        "nome_arquivo": "protocolo-mcp.pdf",
                        "pasta_destino": str(tmp_path),
                    },
                )
                assert pdf.isError is False
                assert Path(pdf.structuredContent["arquivo"]).is_file()
                assert any(item.type == "resource_link" for item in pdf.content)

    anyio.run(executar)
