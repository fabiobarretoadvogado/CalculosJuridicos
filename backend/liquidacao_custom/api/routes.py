"""
Roteadores contendo os endpoints da API.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from datetime import date
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from liquidacao_custom.core.models import ResultadoCalculo
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado as CalculoJudicial
from liquidacao_custom.core.motor_simplificado import criterios_publicos
from liquidacao_custom.core.importacao_simplificada import importar_parcelas, gerar_template
from liquidacao_custom.core.exportadores import exportar_excel, exportar_csv
from liquidacao_custom.core.relatorio_pdf import exportar_pdf
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
from liquidacao_custom.core.honorarios_isolados import CalculoHonorariosIsolados, ResultadoHonorariosIsolados
from liquidacao_custom.core.honorarios_proveito import (
    CalculoHonorariosProveito,
    ResultadoHonorariosProveito,
)
from liquidacao_custom.calculos_salvos import CalculoRecuperado, recuperar_calculo
from liquidacao_custom.calculos_registrados import (
    executar_calculo_registrado,
    executar_honorarios_isolados_registrado,
    executar_honorarios_proveito_registrado,
)

router = APIRouter(prefix="/api/v1")


@router.post("/honorarios/isolados", summary="Honorários isolados por valor da causa ou equidade")
def api_honorarios_isolados(calculo: CalculoHonorariosIsolados) -> ResultadoHonorariosIsolados:
    try:
        return executar_honorarios_isolados_registrado(calculo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/honorarios/isolados/exportar/pdf", summary="Relatório dos honorários isolados")
def api_pdf_honorarios_isolados(calculo: CalculoHonorariosIsolados):
    try:
        resultado = executar_honorarios_isolados_registrado(calculo)
        return StreamingResponse(
            io.BytesIO(exportar_pdf_honorarios(resultado)), media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=relatorio_honorarios_sucumbenciais.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/honorarios/criterios-correcao", summary="Cobertura oficial da correção do valor da causa")
def api_criterios_correcao_honorarios():
    from liquidacao_custom.core.honorarios_principais import criterios_correcao_honorarios
    return criterios_correcao_honorarios()


@router.get("/", summary="Verifica se a API está online")
def api_health_check():
    """Endpoint de status usado pelo frontend."""
    return {
        "sistema": "liquidacao-custom",
        "status": "online",
    }


@router.get("/calculos/{chave}", response_model=CalculoRecuperado, summary="Recupera um cálculo salvo pela chave")
def api_recuperar_calculo(chave: str):
    try:
        return recuperar_calculo(chave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=e.args[0]) from e


@router.post("/calculo", response_model=ResultadoCalculo, summary="Executa cálculo judicial completo")
def api_executar_calculo(calculo: CalculoJudicial):
    """
    Recebe a especificação completa de um cálculo judicial e retorna o resultado detalhado
    com resumo geral, dados por parcela, memória de cálculo mensal e alertas.
    """
    try:
        resultado = executar_calculo_registrado(calculo)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao executar cálculo: {str(e)}")


@router.post(
    "/honorarios/proveito-economico",
    response_model=ResultadoHonorariosProveito,
    summary="Calcula honorários sucumbenciais sobre a redução de uma dívida",
)
def api_honorarios_proveito(calculo: CalculoHonorariosProveito):
    """Atualiza dívidas independentes e aplica percentual único ou faixas do art. 85 à redução positiva."""
    try:
        return executar_honorarios_proveito_registrado(calculo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao calcular honorários: {str(e)}") from e


@router.post(
    "/honorarios/proveito-economico/exportar/pdf",
    summary="Executa o cálculo de honorários e exporta relatório PDF",
)
def api_exportar_pdf_honorarios(calculo: CalculoHonorariosProveito):
    try:
        resultado = executar_honorarios_proveito_registrado(calculo)
        return StreamingResponse(
            io.BytesIO(exportar_pdf_honorarios(resultado)),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    "attachment; filename=relatorio_honorarios_sucumbenciais.pdf"
                )
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao exportar relatório de honorários: {str(e)}",
        ) from e


@router.post("/calculo/exportar/pdf", summary="Executa cálculo e exporta relatório PDF")
def api_exportar_pdf(calculo: CalculoJudicial):
    try:
        resultado = executar_calculo_registrado(calculo)
        return StreamingResponse(
            io.BytesIO(exportar_pdf(resultado)), media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=relatorio_calculo.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao exportar PDF: {str(e)}") from e


@router.post("/calculo/exportar/excel", summary="Executa cálculo e exporta arquivo Excel (.xlsx)")
def api_exportar_excel(calculo: CalculoJudicial):
    """
    Recebe a especificação do cálculo judicial, executa e retorna o download do
    arquivo Excel memoria_calculo.xlsx com as 9 abas completas de auditoria.
    """
    try:
        resultado = executar_calculo_registrado(calculo)
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp_path = tmp.name
        
        exportar_excel(resultado, tmp_path)
        
        # Lê o arquivo para retornar na resposta
        with open(tmp_path, "rb") as f:
            data = f.read()
            
        os.unlink(tmp_path)
        
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=memoria_calculo.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao exportar Excel: {str(e)}")


@router.post("/calculo/exportar/csv", summary="Executa cálculo e exporta arquivos CSV (ZIP)")
def api_exportar_csv(calculo: CalculoJudicial):
    """
    Recebe o cálculo, executa-o e retorna um arquivo ZIP contendo resumo_geral.csv,
    memoria_mensal.csv e alertas.csv.
    """
    try:
        resultado = executar_calculo_registrado(calculo)
        
        # Cria diretório temporário para gerar os CSVs
        tmp_dir = tempfile.mkdtemp()
        exportar_csv(resultado, tmp_dir)
        
        # Zipa o conteúdo
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, arcname=file)
                    
        shutil.rmtree(tmp_dir)
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=memorias_calculo_csv.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao exportar CSVs: {str(e)}")


@router.post("/parcelas/importar", summary="Importa e valida parcelas a partir de uma planilha Excel")
async def api_importar_parcelas(file: UploadFile = File(...)):
    """
    Recebe um arquivo Excel (.xlsx) com as parcelas e executa a importação
    e validações. Retorna as parcelas lidas ou relatórios de erros estruturais.
    """
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato inválido. Envie um arquivo Excel .xlsx")

    # Salva o arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parcelas, erros = importar_parcelas(tmp_path)
        os.unlink(tmp_path)

        # Se houver erros estruturais críticos na importação
        if erros:
            return JSONResponse(
                status_code=422,
                content={
                    "mensagem": "Inconsistências encontradas nas linhas da planilha.",
                    "erros": erros
                }
            )

        # Converte para dict para retornar
        return {"parcelas": [p.model_dump(mode="json") for p in parcelas]}
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail=f"Erro ao importar planilha: {str(e)}")


@router.get("/indices", summary="Retorna os índices cadastrados no sistema")
def api_listar_indices():
    return {"indices": ["SELIC", "IPCA-E IBGE", "POUPANCA"]}


@router.get("/criterios", summary="Critérios fixos e cobertura dos índices oficiais")
def api_criterios(perfil: str = "selic_ipcae_poupanca_v1"):
    try:
        return criterios_publicos(perfil=perfil)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/parcelas/modelo", summary="Retorna download do modelo padrão Excel (.xlsx)")
def api_obter_modelo():
    """
    Gera dinamicamente e retorna o download do arquivo templates/modelo_importacao_parcelas.xlsx
    com a estrutura e cabeçalhos corretos para importação do sistema.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp_path = tmp.name
        
        gerar_template(tmp_path)
        
        with open(tmp_path, "rb") as f:
            data = f.read()
            
        os.unlink(tmp_path)
        
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=modelo_importacao_parcelas.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar modelo: {str(e)}")
