"""Honorários autônomos por valor da causa ou equidade; reutiliza o motor vigente."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .acessorios import calcular_honorarios
from .criterios_simplificados import CustaDespesaProcessual, HonorariosPrincipais
from .honorarios_principais import corrigir_valor_causa
from .honorarios_valor_certo import EncargosValorCerto, atualizar_valor_certo
from .honorarios_proveito import (
    DadosHonorarios, EscalonamentoFazendaHonorarios, ResultadoEscalonamentoFazenda,
    apurar_faixas_fazenda, moeda,
)
from .models import BaseCalculo, Honorarios, ResultadoCustaDespesaProcessual, ResultadoHonorariosPrincipais, ResultadoParcela
from .motor_simplificado import calcular_custas_despesas_ipcae, dados_fonte_ipcae


class CalculoHonorariosIsolados(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: Literal["honorarios_sucumbenciais_isolados"] = "honorarios_sucumbenciais_isolados"
    dados_gerais: DadosHonorarios
    base: Literal["valor_causa", "valor_certo"]
    valor_causa: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    data_protocolo: date | None = None
    indice: Literal["ipcae", "ipca"] | None = None
    valor_certo: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    encargos_valor_certo: EncargosValorCerto | None = None
    percentual_sentenca: Decimal | None = Field(default=None, gt=0, le=100, max_digits=7, decimal_places=4)
    escalonamento_fazenda: EscalonamentoFazendaHonorarios | None = None
    custas_despesas: list[CustaDespesaProcessual] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validar(self):
        if self.base == "valor_certo":
            if self.valor_certo is None:
                raise ValueError("Equidade: informe o valor certo dos honorários.")
            if self.encargos_valor_certo and (self.encargos_valor_certo.data_fixacao > self.dados_gerais.data_base or (self.encargos_valor_certo.data_inicio_juros and self.encargos_valor_certo.data_inicio_juros > self.dados_gerais.data_base)):
                raise ValueError("Valor certo: fixação e início dos juros não podem ser posteriores à data-base.")
            if any(v is not None for v in (self.valor_causa, self.data_protocolo, self.indice, self.percentual_sentenca, self.escalonamento_fazenda)):
                raise ValueError("Equidade não se cumula com valor da causa, percentual ou escalonamento.")
        else:
            if self.encargos_valor_certo is not None:
                raise ValueError("Encargos do valor certo somente na base de equidade / valor certo.")
            if self.valor_causa is None or self.data_protocolo is None or self.indice is None:
                raise ValueError("Informe o valor da causa no protocolo, a data do protocolo e o índice.")
            if self.valor_certo is not None:
                raise ValueError("Não cumular valor certo com honorários sobre o valor da causa.")
            if self.data_protocolo < date(2009, 7, 1):
                raise ValueError("Valor da causa: a série disponível começa em 01/07/2009.")
            if self.data_protocolo > self.dados_gerais.data_base:
                raise ValueError("Valor da causa: data do protocolo posterior à data-base.")
            if (self.percentual_sentenca is None) == (self.escalonamento_fazenda is None):
                raise ValueError("Escolha percentual único ou escalonamento da Fazenda Pública, sem cumular.")
        if len({c.numero for c in self.custas_despesas}) != len(self.custas_despesas):
            raise ValueError("As custas e despesas devem ter números distintos.")
        for c in self.custas_despesas:
            if not date(2009, 7, 1) <= c.data <= self.dados_gerais.data_base:
                raise ValueError(f"Custa ou despesa {c.numero}: informe data entre 01/07/2009 e a data-base.")
        return self


class ResultadoHonorariosIsolados(BaseModel):
    categoria: Literal["honorarios_sucumbenciais_isolados"] = "honorarios_sucumbenciais_isolados"
    dados_gerais: DadosHonorarios
    base: Literal["valor_causa", "valor_certo"]
    apuracao: ResultadoHonorariosPrincipais
    atualizacao_valor_certo: ResultadoParcela | None = None
    percentual_sentenca: Decimal | None
    escalonamento_fazenda: ResultadoEscalonamentoFazenda | None = None
    honorarios_sucumbenciais: Decimal
    custas_despesas: list[ResultadoCustaDespesaProcessual]
    custas_despesas_valor_original: Decimal
    custas_despesas_correcao: Decimal
    custas_despesas_valor_atualizado: Decimal
    fontes_custas_despesas: dict[str, str]
    total_geral: Decimal
    formula: str
    alertas: list[str] = Field(default_factory=list)
    premissas: dict[str, Any]


def executar_honorarios_isolados(calculo: CalculoHonorariosIsolados) -> ResultadoHonorariosIsolados:
    certo = calculo.base == "valor_certo"
    original = calculo.valor_certo if certo else calculo.valor_causa
    base, fator, memoria, fonte, sha = original, Decimal(1), [], "", None
    atualizacao, premissas_atualizacao = None, {}
    if certo and calculo.encargos_valor_certo:
        atualizacao, fator, fonte, premissas_atualizacao = atualizar_valor_certo(original, calculo.encargos_valor_certo, calculo.dados_gerais.data_base)
        base, memoria = atualizacao.valor_corrigido, atualizacao.memoria_correcao
    if not certo:
        # O validador de inclusão do fluxo principal exige percentual; a correção
        # isolada reutiliza apenas sua configuração, inclusive no modo por faixas.
        config = HonorariosPrincipais(
            base="valor_causa", valor_causa=original,
            data_protocolo=calculo.data_protocolo, indice=calculo.indice,
        )
        base, fator, memoria, fonte, sha = corrigir_valor_causa(config, calculo.dados_gerais.data_base)
    escalonamento = None
    if calculo.escalonamento_fazenda:
        escalonamento = apurar_faixas_fazenda(base, calculo.escalonamento_fazenda)
        valor = escalonamento.valor_total
    else:
        with localcontext() as contexto:
            contexto.rounding = ROUND_HALF_UP
            detalhe = calcular_honorarios(Honorarios(
                base_calculo=BaseCalculo.VALOR_MANUAL, valor_manual_base=base,
                valor_fixo=(atualizacao.total_parcela if atualizacao else original) if certo else None,
                percentual=calculo.percentual_sentenca if not certo else None,
            ), [], calculo.dados_gerais.data_base)
        valor = detalhe["valor"]
    apuracao = ResultadoHonorariosPrincipais(
        base=calculo.base, descricao_base="Equidade - valor certo atualizado desde a fixação" if atualizacao else "Equidade - valor certo na data-base" if certo else "Valor da causa atualizado",
        percentual=calculo.percentual_sentenca, valor_original=original,
        data_protocolo=calculo.data_protocolo, indice=calculo.indice,
        fator_acumulado=fator, correcao_monetaria=moeda(base - original),
        base_atualizada=base, valor=valor, memoria=memoria, fonte=fonte,
    )
    custas = calcular_custas_despesas_ipcae(calculo.custas_despesas, calculo.dados_gerais.data_base)
    total_custas = sum((c.valor_atualizado for c in custas), Decimal(0))
    criterio = ("Equidade: valor certo dos honorários informado já na data-base, sem nova correção ou juros automáticos. Não arbitra nem revisa o valor judicial."
        if certo else f"Valor da causa no protocolo, corrigido exclusivamente por {'IPCA-E IBGE (IPCA-15)' if calculo.indice == 'ipcae' else 'IPCA SGS 433'} até a data-base, sem juros.")
    if atualizacao:
        config = calculo.encargos_valor_certo
        criterio = f"Valor certo fixado em {config.data_fixacao:%d/%m/%Y}, corrigido por {'IPCA-E IBGE (IPCA-15)' if config.indice == 'ipcae' else 'IPCA SGS 433'}. " + (
            "Juros não incluídos por opção expressa." if config.juros == "sem_juros" else f"Juros desde {config.data_inicio_juros:%d/%m/%Y}, termo informado pelo usuário. Art. 85, § 16, CPC: marco legal dos juros é o trânsito em julgado; não se presume sua ocorrência.")
    formula = ("Honorários = valor certo informado na data-base." if certo else
        "Honorários = soma dos valores das faixas sobre o valor da causa atualizado." if escalonamento else
        "Honorários = valor da causa atualizado × percentual da sentença ÷ 100.")
    if atualizacao:
        formula = "Honorários atualizados = valor fixado + correção monetária + juros de mora."
    premissas = {
        "entrada": calculo.model_dump(mode="json"), "criterios": [criterio, "Custas e despesas não integram a base; são corrigidas separadamente por IPCA-E e somadas somente ao total final."],
        "metodologia": [] if certo else ["Correção idêntica ao fluxo principal: meses parciais proporcionais aos dias corridos, incluindo os extremos; deflações preservadas. Base e honorários arredondados ao centavo com HALF_UP."],
        "fontes": {"correcao_valor_causa": fonte} if fonte else {},
    }
    if sha:
        premissas["sha256_ipca_valor_causa"] = sha
    if atualizacao:
        premissas.update(premissas_atualizacao)
    return ResultadoHonorariosIsolados(
        dados_gerais=calculo.dados_gerais, base=calculo.base, apuracao=apuracao, atualizacao_valor_certo=atualizacao,
        percentual_sentenca=calculo.percentual_sentenca, escalonamento_fazenda=escalonamento,
        honorarios_sucumbenciais=valor, custas_despesas=custas,
        custas_despesas_valor_original=sum((c.valor_original for c in custas), Decimal(0)),
        custas_despesas_correcao=sum((c.correcao_monetaria for c in custas), Decimal(0)),
        custas_despesas_valor_atualizado=total_custas,
        fontes_custas_despesas={"ipcae": dados_fonte_ipcae()} if custas else {},
        total_geral=moeda(valor + total_custas), formula=formula, premissas=premissas,
    )
