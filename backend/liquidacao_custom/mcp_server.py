"""Servidor MCP local para usar o motor sem abrir a interface gráfica."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ResourceLink, TextContent, ToolAnnotations

from .core.criterios_simplificados import CalculoSimplificado
from .core.honorarios_isolados import (
    CalculoHonorariosIsolados,
    executar_honorarios_isolados,
)
from .core.honorarios_principais import criterios_correcao_honorarios
from .core.honorarios_proveito import (
    CalculoHonorariosProveito,
    executar_honorarios_proveito,
)
from .core.motor_simplificado import criterios_publicos, executar_calculo
from .core.perfis import PERFIS
from .core.relatorio_honorarios_pdf import exportar_pdf_honorarios
from .core.relatorio_pdf import exportar_pdf
from .metadata import APP_DISPLAY_VERSION, APP_NAME, APP_VERSION


INSTRUCOES = """
Use este servidor como a fonte de verdade para os cálculos do aplicativo Cálculos
Jurídicos. Consulte os critérios antes de montar uma entrada. Não invente datas,
valores, percentuais ou marcos jurídicos ausentes: peça esses dados ao usuário.
As ferramentas de cálculo não alteram arquivos. As ferramentas de relatório executam
o mesmo motor e o mesmo gerador de PDF da interface e salvam um novo arquivo local.
""".strip()

mcp = FastMCP(
    APP_NAME,
    instructions=INSTRUCOES,
    website_url="https://github.com/fabiobarretoadvogado/CalculosJuridicos",
    log_level="ERROR",
)

LEITURA = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
ARQUIVO = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


def _json(modelo: Any) -> dict[str, Any]:
    """Converte modelos e tipos jurídicos para valores JSON nativos."""
    if hasattr(modelo, "model_dump"):
        return modelo.model_dump(mode="json")
    return json.loads(json.dumps(modelo, ensure_ascii=False, default=str))


def _nome_seguro(nome: str, padrao: str) -> str:
    nome = (nome or padrao).strip()
    if nome.lower().endswith(".pdf"):
        nome = nome[:-4]
    nome = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", nome)
    nome = re.sub(r"\s+", " ", nome).strip(" .") or padrao
    return f"{nome[:160]}.pdf"


def _pasta_documentos() -> Path:
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as chave:
                valor, _ = winreg.QueryValueEx(chave, "Personal")
            return Path(os.path.expandvars(valor)).expanduser()
        except (OSError, ValueError):
            pass
    return Path.home() / "Documents"


def _caminho_relatorio(nome_arquivo: str, pasta_destino: str, padrao: str) -> Path:
    pasta = (
        Path(pasta_destino).expanduser()
        if pasta_destino.strip()
        else _pasta_documentos() / APP_NAME / "Relatórios"
    )
    pasta.mkdir(parents=True, exist_ok=True)
    candidato = pasta / _nome_seguro(nome_arquivo, padrao)
    contador = 2
    while candidato.exists():
        candidato = pasta / f"{candidato.stem} ({contador}).pdf"
        contador += 1
    return candidato.resolve()


def _salvar_pdf(
    conteudo: bytes,
    *,
    nome_arquivo: str,
    pasta_destino: str,
    padrao: str,
    resumo: dict[str, Any],
) -> CallToolResult:
    caminho = _caminho_relatorio(nome_arquivo, pasta_destino, padrao)
    caminho.write_bytes(conteudo)
    metadados = {
        "sucesso": True,
        "arquivo": str(caminho),
        "uri": caminho.as_uri(),
        "mime_type": "application/pdf",
        "tamanho_bytes": len(conteudo),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
        "resumo": resumo,
    }
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=(
                    f"Relatório PDF criado em {caminho}. "
                    f"Tamanho: {len(conteudo)} bytes."
                ),
            ),
            ResourceLink(
                type="resource_link",
                name=caminho.name,
                title="Relatório do Cálculos Jurídicos",
                uri=caminho.as_uri(),
                description="PDF gerado pelo mesmo motor usado na interface do aplicativo.",
                mimeType="application/pdf",
                size=len(conteudo),
            ),
        ],
        structuredContent=metadados,
    )


def _resumo_principal(resultado: Any) -> dict[str, Any]:
    resumo = resultado.resumo
    return {
        "data_base": resultado.dados_gerais.data_base.isoformat(),
        "principal_original": str(resumo.principal_original),
        "correcao_monetaria": str(resumo.correcao_monetaria),
        "juros_mora": str(resumo.juros_mora),
        "abatimentos": str(resumo.abatimentos),
        "custas": str(resumo.custas),
        "total_atualizado": str(resumo.total_atualizado),
        "quantidade_parcelas": len(resultado.parcelas),
        "alertas": list(resultado.alertas),
    }


def _resumo_proveito(resultado: Any) -> dict[str, Any]:
    return {
        "data_base": resultado.dados_gerais.data_base.isoformat(),
        "divida_original_atualizada": str(resultado.divida_original.valor_atualizado),
        "divida_correta_atualizada": str(resultado.divida_correta.valor_atualizado),
        "proveito_economico": str(resultado.proveito_economico),
        "honorarios_sucumbenciais": str(resultado.honorarios_sucumbenciais),
        "custas_despesas": str(resultado.custas_despesas_valor_atualizado),
        "total_geral": str(resultado.total_geral),
        "alertas": list(resultado.alertas),
    }


def _resumo_isolados(resultado: Any) -> dict[str, Any]:
    return {
        "data_base": resultado.dados_gerais.data_base.isoformat(),
        "base": resultado.base,
        "base_atualizada": str(resultado.apuracao.base_atualizada),
        "honorarios_sucumbenciais": str(resultado.honorarios_sucumbenciais),
        "custas_despesas": str(resultado.custas_despesas_valor_atualizado),
        "total_geral": str(resultado.total_geral),
        "alertas": list(resultado.alertas),
    }


@mcp.tool(
    title="Informações do Cálculos Jurídicos",
    description="Mostra a versão instalada, os tipos de cálculo e os perfis disponíveis.",
    annotations=LEITURA,
)
def informacoes_aplicativo() -> dict[str, Any]:
    return {
        "aplicativo": APP_NAME,
        "versao_tecnica": APP_VERSION,
        "edicao": APP_DISPLAY_VERSION,
        "tipos_calculo": [
            "principal",
            "honorarios_sucumbenciais_proveito_economico",
            "honorarios_sucumbenciais_isolados",
        ],
        "perfis": PERFIS,
        "pdf": True,
        "interface_grafica_necessaria": False,
    }


@mcp.tool(
    title="Consultar critérios do cálculo principal",
    description="Retorna regras, cobertura e fontes oficiais de um perfil antes do cálculo.",
    annotations=LEITURA,
)
def consultar_criterios(perfil: str) -> dict[str, Any]:
    ids = {item["id"] for item in PERFIS}
    if perfil not in ids:
        raise ValueError(f"Perfil inválido. Use um destes identificadores: {', '.join(sorted(ids))}.")
    return _json(criterios_publicos(perfil=perfil))


@mcp.tool(
    title="Consultar cobertura dos honorários",
    description="Retorna os limites das séries oficiais usadas na correção de honorários.",
    annotations=LEITURA,
)
def consultar_cobertura_honorarios() -> dict[str, Any]:
    return _json(criterios_correcao_honorarios())


@mcp.tool(
    title="Calcular débito judicial",
    description="Executa o cálculo principal. Use resultado resumido para conversa e completo para auditoria.",
    annotations=LEITURA,
)
def calcular_debito_judicial(
    calculo: CalculoSimplificado,
    modo_resultado: Literal["resumo", "completo"] = "resumo",
) -> dict[str, Any]:
    resultado = executar_calculo(calculo)
    return _json(resultado) if modo_resultado == "completo" else _resumo_principal(resultado)


@mcp.tool(
    title="Gerar PDF do débito judicial",
    description="Executa o cálculo principal e salva seu demonstrativo oficial em PDF.",
    annotations=ARQUIVO,
)
def gerar_pdf_debito_judicial(
    calculo: CalculoSimplificado,
    nome_arquivo: str = "relatorio_calculo.pdf",
    pasta_destino: str = "",
) -> CallToolResult:
    resultado = executar_calculo(calculo)
    return _salvar_pdf(
        exportar_pdf(resultado),
        nome_arquivo=nome_arquivo,
        pasta_destino=pasta_destino,
        padrao="relatorio_calculo",
        resumo=_resumo_principal(resultado),
    )


@mcp.tool(
    title="Calcular honorários sobre proveito econômico",
    description="Atualiza as duas dívidas e calcula honorários sobre a redução reconhecida.",
    annotations=LEITURA,
)
def calcular_honorarios_proveito_economico(
    calculo: CalculoHonorariosProveito,
    modo_resultado: Literal["resumo", "completo"] = "resumo",
) -> dict[str, Any]:
    resultado = executar_honorarios_proveito(calculo)
    return _json(resultado) if modo_resultado == "completo" else _resumo_proveito(resultado)


@mcp.tool(
    title="Gerar PDF dos honorários sobre proveito econômico",
    description="Calcula os honorários pela redução da dívida e salva o demonstrativo em PDF.",
    annotations=ARQUIVO,
)
def gerar_pdf_honorarios_proveito_economico(
    calculo: CalculoHonorariosProveito,
    nome_arquivo: str = "relatorio_honorarios_sucumbenciais.pdf",
    pasta_destino: str = "",
) -> CallToolResult:
    resultado = executar_honorarios_proveito(calculo)
    return _salvar_pdf(
        exportar_pdf_honorarios(resultado),
        nome_arquivo=nome_arquivo,
        pasta_destino=pasta_destino,
        padrao="relatorio_honorarios_sucumbenciais",
        resumo=_resumo_proveito(resultado),
    )


@mcp.tool(
    title="Calcular honorários isolados",
    description="Calcula honorários autônomos por valor da causa ou por valor certo.",
    annotations=LEITURA,
)
def calcular_honorarios_isolados(
    calculo: CalculoHonorariosIsolados,
    modo_resultado: Literal["resumo", "completo"] = "resumo",
) -> dict[str, Any]:
    resultado = executar_honorarios_isolados(calculo)
    return _json(resultado) if modo_resultado == "completo" else _resumo_isolados(resultado)


@mcp.tool(
    title="Gerar PDF dos honorários isolados",
    description="Calcula honorários por valor da causa ou valor certo e salva o demonstrativo em PDF.",
    annotations=ARQUIVO,
)
def gerar_pdf_honorarios_isolados(
    calculo: CalculoHonorariosIsolados,
    nome_arquivo: str = "relatorio_honorarios_sucumbenciais.pdf",
    pasta_destino: str = "",
) -> CallToolResult:
    resultado = executar_honorarios_isolados(calculo)
    return _salvar_pdf(
        exportar_pdf_honorarios(resultado),
        nome_arquivo=nome_arquivo,
        pasta_destino=pasta_destino,
        padrao="relatorio_honorarios_sucumbenciais",
        resumo=_resumo_isolados(resultado),
    )


def nomes_ferramentas() -> list[str]:
    """Lista síncrona usada pelo autoteste do executável."""
    return sorted(ferramenta.name for ferramenta in mcp._tool_manager.list_tools())


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
