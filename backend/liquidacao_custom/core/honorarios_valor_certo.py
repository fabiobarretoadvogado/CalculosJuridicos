"""Valor fixado: correção desde a fixação e juros com marco próprio expresso."""
import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .honorarios_principais import corrigir_valor_causa
from .juros import calcular_juros, contar_meses
from .models import ComponenteCalculo, ConfigJuros, ResultadoParcela, TipoJuros
from .motor_ipca_taxa_legal import BASE_TAXA_LEGAL, apurar_juros_taxa_legal, criterios_ipca_taxa_legal
from .motor_simplificado import moeda


class EncargosValorCerto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_fixacao: date
    indice: Literal["ipcae", "ipca"]
    juros: Literal["simples", "taxa_legal", "sem_juros"]
    data_inicio_juros: date | None = None
    percentual_mensal: Decimal | None = Field(default=None, gt=0, le=100, max_digits=9, decimal_places=6)
    contagem_mes_cheio: bool = False

    @model_validator(mode="after")
    def validar(self):
        if self.data_fixacao < date(2009, 7, 1):
            raise ValueError("Valor certo: a correção disponível começa em 01/07/2009.")
        if self.juros != "sem_juros" and self.data_inicio_juros is None:
            raise ValueError("Informe o trânsito em julgado / termo inicial dos juros. Não se presume o trânsito.")
        if self.data_inicio_juros is not None and self.data_inicio_juros < self.data_fixacao:
            raise ValueError("Valor certo: início dos juros anterior à fixação.")
        if self.juros == "simples" and self.percentual_mensal is None:
            raise ValueError("Informe o percentual mensal simples conforme a decisão.")
        if self.juros != "simples" and self.percentual_mensal is not None:
            raise ValueError("Percentual mensal manual somente no regime simples.")
        if self.juros == "sem_juros" and self.data_inicio_juros is not None:
            raise ValueError("Sem juros: não enviar termo inicial dos juros.")
        if self.juros == "taxa_legal" and self.data_inicio_juros < date(2024, 8, 30):
            raise ValueError("Taxa Legal oficial: início dos juros a partir de 30/08/2024; não substituir períodos anteriores.")
        return self


def atualizar_valor_certo(original, config: EncargosValorCerto, data_base):
    if config.data_fixacao > data_base or (config.data_inicio_juros and config.data_inicio_juros > data_base):
        raise ValueError("Valor certo: fixação e início dos juros não podem ser posteriores à data-base.")
    fator, memoria, fonte, sha = Decimal(1), [], "", None
    if config.data_fixacao < data_base:
        _, fator, registros, fonte, sha = corrigir_valor_causa(SimpleNamespace(
            indice=config.indice, valor_causa=original, data_protocolo=config.data_fixacao), data_base)
        memoria = [m.model_copy(update={"indice_aplicado": m.indice_aplicado.replace("Valor da causa", "Honorários fixados")}) for m in registros]
    saldo_exato = original * fator
    saldo = moeda(saldo_exato)
    juros, mem_juros, auditoria = Decimal(0), [], []
    componente_juros = ComponenteCalculo(base_calculo=saldo_exato, valor=Decimal(0))
    metodologia = ["Correção reutiliza a operação do valor da causa, com o valor e data de fixação dos honorários; meses parciais proporcionais aos dias corridos, extremos incluídos, deflações preservadas. Fixação na data-base não gera nova correção."]
    fontes = {"correcao_honorarios_fixados": fonte} if fonte else {}
    hashes = {"sha256_ipca": sha} if sha else {}
    if config.juros == "taxa_legal":
        juros, componente_juros, mem_juros, auditoria = apurar_juros_taxa_legal(
            saldo_exato, config.data_inicio_juros, data_base, indice_correcao="IPCA-E" if config.indice == "ipcae" else "IPCA")
        fontes.update({k: v for k, v in criterios_ipca_taxa_legal()["fontes"].items() if k != "ipca"})
        hashes["sha256_taxa_legal"] = hashlib.sha256(BASE_TAXA_LEGAL.read_bytes()).hexdigest()
        metodologia.append("Taxa Legal mensal oficial SGS 29543: soma simples das taxas, seis casas decimais, dias proporcionais por mês; inclui início e exclui data-base. Base: honorários corrigidos finais com precisão integral. Sem SELIC adicional, taxa substituta ou juros sobre juros.")
    elif config.juros == "simples":
        with localcontext() as contexto:
            contexto.rounding = ROUND_HALF_UP
            detalhe = calcular_juros(original, saldo_exato, [ConfigJuros(
                tipo=TipoJuros.PERCENTUAL_MENSAL_SIMPLES, percentual=config.percentual_mensal,
                data_inicial=config.data_inicio_juros, data_final=data_base,
                contagem_mes_cheio=config.contagem_mes_cheio, incide_sobre_corrigido=True,
            )], data_base)
            meses = contar_meses(config.data_inicio_juros, data_base, config.contagem_mes_cheio)
            taxa_acumulada = config.percentual_mensal * meses
        juros = detalhe["valor_juros"]
        mem_juros = detalhe["memoria_mensal"] if config.data_inicio_juros < data_base else []
        componente_juros = ComponenteCalculo(
            data_inicial=config.data_inicio_juros if config.data_inicio_juros < data_base else None,
            data_final=data_base if config.data_inicio_juros < data_base else None,
            base_calculo=saldo_exato, taxa_acumulada_percentual=taxa_acumulada, valor=juros)
        metodologia.append(f"Juros simples de {config.percentual_mensal}% a.m. sobre o valor corrigido final; rotina calcular_juros/contar_meses existente. Contagem: {'meses inteiros conforme rotina existente' if config.contagem_mes_cheio else 'dias corridos / 30,4368, meses com seis casas decimais'}. Sem capitalização. Valores financeiros HALF_UP ao centavo.")
    resultado = ResultadoParcela(numero=1, natureza="honorarios_sucumbenciais", historico="Honorários fixados em valor certo",
        data_vencimento=config.data_fixacao, valor_bruto=original, valor_apurado=original,
        correcao_monetaria=saldo-original, valor_corrigido=saldo, juros_mora=juros,
        total_parcela=moeda(saldo+juros), memoria_correcao=memoria, memoria_juros=mem_juros,
        componentes={config.indice: ComponenteCalculo(
            data_inicial=config.data_fixacao if config.data_fixacao < data_base else None,
            data_final=data_base if config.data_fixacao < data_base else None,
            base_calculo=original, fator_acumulado=fator, valor=saldo-original), "juros": componente_juros})
    return resultado, fator, fonte, {"metodologia": metodologia, "fontes": fontes, **hashes, "memoria_taxa_legal": auditoria}
