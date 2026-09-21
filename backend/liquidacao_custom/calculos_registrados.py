"""Executa e registra os cálculos produzidos pelo aplicativo."""
from __future__ import annotations

from .calculos_salvos import registrar_calculo
from .core.criterios_simplificados import CalculoSimplificado
from .core.honorarios_isolados import CalculoHonorariosIsolados, ResultadoHonorariosIsolados, executar_honorarios_isolados
from .core.honorarios_proveito import CalculoHonorariosProveito, ResultadoHonorariosProveito, executar_honorarios_proveito
from .core.models import ResultadoCalculo
from .core.motor_simplificado import executar_calculo


def executar_calculo_registrado(calculo: CalculoSimplificado) -> ResultadoCalculo:
    resultado = executar_calculo(calculo)
    resultado.chave_recuperacao = registrar_calculo("calculo_principal", calculo, resultado)
    return resultado


def executar_honorarios_proveito_registrado(calculo: CalculoHonorariosProveito) -> ResultadoHonorariosProveito:
    resultado = executar_honorarios_proveito(calculo)
    resultado.chave_recuperacao = registrar_calculo("honorarios_sucumbenciais_proveito_economico", calculo, resultado)
    return resultado


def executar_honorarios_isolados_registrado(calculo: CalculoHonorariosIsolados) -> ResultadoHonorariosIsolados:
    resultado = executar_honorarios_isolados(calculo)
    resultado.chave_recuperacao = registrar_calculo("honorarios_sucumbenciais_isolados", calculo, resultado)
    return resultado
