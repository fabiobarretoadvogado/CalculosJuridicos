"""Honorários sucumbenciais calculados sobre a redução atualizada de uma dívida."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .criterios_simplificados import (
    CalculoSimplificado,
    CustaDespesaProcessual,
    DadosSimplificados,
    ParcelaSimplificada,
)
from .models import (BaseCalculo, ComponenteCalculo, FaixaHonorariosFazenda, Honorarios,
                     MemoriaMensal, ResultadoCustaDespesaProcessual, faixas_honorarios_fazenda_padrao)
from .acessorios import calcular_honorarios
from .motor_simplificado import calcular_custas_despesas_ipcae, dados_fonte_ipcae, executar_calculo
from .perfis import PERFIS
from .perfis import IPCAE_1AM_SIMPLES


PerfilCalculo = Literal[
    "fazenda_publica_1_v1",
    "fazenda_publica_2_v1",
    "selic_ipcae_poupanca_v1",
    "selic_ipcae_2aa_v1",
    "selic_cjf_v1",
    "ipcae_1am_simples_v1",
    "ipca_taxa_legal_v1",
    "civil_2_v1",
]
CriterioInicioJuros = Literal["vencimento", "citacao", "data_fixa", "por_parcela"]
CATEGORIA = "honorarios_sucumbenciais_proveito_economico"


class DadosHonorarios(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_base: date
    processo: str = ""
    classe: str = ""
    requerente: str = ""
    requerido: str = ""
    comarca: str = ""
    vara: str = ""
    observacoes: str = ""


class ParcelaDivida(BaseModel):
    """Parcela ou item individual que compõe uma das dívidas comparadas."""

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(gt=0)
    historico: str = ""
    data_origem: date
    valor: Decimal = Field(gt=0, max_digits=16, decimal_places=2)


class OperacaoDivida(BaseModel):
    """Uma das duas listas de itens atualizadas antes da comparação."""

    model_config = ConfigDict(extra="forbid")

    perfil: PerfilCalculo = "selic_ipcae_poupanca_v1"
    criterio_inicio_juros: CriterioInicioJuros = "vencimento"
    data_inicial_juros: date | None = None
    multa_moratoria_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    extincao_integral: bool = False
    parcelas: list[ParcelaDivida] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validar_inicio_juros(self):
        if self.extincao_integral:
            # A declaração expressa de extinção prevalece sobre campos antigos
            # que possam ter permanecido preenchidos no formulário.
            self.parcelas = []
            self.data_inicial_juros = None
            self.multa_moratoria_percentual = Decimal("0")
            return self
        if not self.parcelas:
            raise ValueError("Informe ao menos um item da dívida ou marque a extinção integral.")
        if (
            self.perfil != "selic_cjf_v1"
            and self.criterio_inicio_juros in ("citacao", "data_fixa")
            and self.data_inicial_juros is None
        ):
            raise ValueError("Informe a data de início dos juros para o critério escolhido.")
        numeros = [parcela.numero for parcela in self.parcelas]
        if len(set(numeros)) != len(numeros):
            raise ValueError("Os itens da dívida devem ter números distintos.")
        return self


class EscalonamentoFazendaHonorarios(BaseModel):
    """Referência expressa do art. 85, § 4º, IV; sem salário do ano da data-base."""
    model_config = ConfigDict(extra="forbid")

    salario_minimo: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    marco: Literal["sentenca_liquida", "decisao_liquidacao"]
    data_decisao: date
    percentuais_faixas: list[Annotated[Decimal, Field(max_digits=7, decimal_places=4)]] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validar_percentuais(self):
        for faixa, percentual in zip(faixas_honorarios_fazenda_padrao(), self.percentuais_faixas):
            if not faixa.percentual_minimo <= percentual <= faixa.percentual_maximo:
                raise ValueError(f"Faixa {faixa.ordem}: informe percentual entre {faixa.percentual_minimo}% e {faixa.percentual_maximo}% (art. 85, § 3º, CPC).")
        return self


class ResultadoFaixaFazenda(FaixaHonorariosFazenda):
    limite_inferior_salarios_minimos: Decimal
    valor_incidente: Decimal
    valor: Decimal


class ResultadoEscalonamentoFazenda(EscalonamentoFazendaHonorarios):
    base_calculo: Decimal
    percentual_efetivo: Decimal
    valor_total: Decimal
    faixas: list[ResultadoFaixaFazenda]
    fonte: str


class CalculoHonorariosProveito(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: Literal["honorarios_sucumbenciais_proveito_economico"] = CATEGORIA
    dados_gerais: DadosHonorarios
    divida_original: OperacaoDivida
    divida_correta: OperacaoDivida
    custas_despesas: list[CustaDespesaProcessual] = Field(default_factory=list, max_length=2000)
    percentual_sentenca: Decimal | None = Field(default=None, gt=0, le=100, max_digits=7, decimal_places=4)
    escalonamento_fazenda: EscalonamentoFazendaHonorarios | None = None

    @model_validator(mode="after")
    def validar_datas(self):
        if self.divida_original.extincao_integral:
            raise ValueError("A extinção integral só pode ser informada para a dívida correta.")
        if self.escalonamento_fazenda is None and self.percentual_sentenca is None:
            raise ValueError("Informe o percentual da sentença ou o escalonamento da Fazenda Pública.")
        if self.escalonamento_fazenda is not None and self.percentual_sentenca is not None:
            raise ValueError("Escolha percentual único ou escalonamento da Fazenda Pública, sem cumular os dois.")
        for rotulo, operacao in (
            ("Dívida original", self.divida_original),
            ("Dívida correta", self.divida_correta),
        ):
            for parcela in operacao.parcelas:
                if parcela.data_origem > self.dados_gerais.data_base:
                    raise ValueError(
                        f"{rotulo}, item {parcela.numero}: a data de origem não pode ser "
                        "posterior à data-base."
                    )
        for item in self.custas_despesas:
            if item.data < date(2009, 7, 1):
                raise ValueError(
                    f"Custa ou despesa {item.numero}: informe uma data a partir de 01/07/2009, "
                    "início da série IPCA-E disponível neste aplicativo."
                )
            if item.data > self.dados_gerais.data_base:
                raise ValueError(
                    f"Custa ou despesa {item.numero}: a data não pode ser posterior à data-base."
                )
        numeros_custas = [item.numero for item in self.custas_despesas]
        if len(set(numeros_custas)) != len(numeros_custas):
            raise ValueError("As custas e despesas devem ter números distintos.")
        return self


class ResultadoParcelaDivida(BaseModel):
    numero: int
    historico: str
    data_origem: date
    valor_informado: Decimal
    encargos_apurados: Decimal
    valor_atualizado: Decimal
    componentes: dict[str, ComponenteCalculo]


class ResultadoOperacaoDivida(BaseModel):
    rotulo: str
    perfil: PerfilCalculo
    nome_perfil: str
    quantidade_parcelas: int
    valor_informado: Decimal
    encargos_apurados: Decimal
    valor_atualizado: Decimal
    parcelas: list[ResultadoParcelaDivida]
    componentes: dict[str, ComponenteCalculo]
    memoria_mensal: list[MemoriaMensal]
    criterios: list[str]
    metodologia: list[str]
    fontes: dict[str, str]
    premissas: dict[str, Any]


class ResultadoHonorariosProveito(BaseModel):
    categoria: Literal["honorarios_sucumbenciais_proveito_economico"] = CATEGORIA
    dados_gerais: DadosHonorarios
    divida_original: ResultadoOperacaoDivida
    divida_correta: ResultadoOperacaoDivida
    diferenca_atualizada: Decimal
    proveito_economico: Decimal
    percentual_sentenca: Decimal | None
    escalonamento_fazenda: ResultadoEscalonamentoFazenda | None = None
    honorarios_sucumbenciais: Decimal
    custas_despesas: list[ResultadoCustaDespesaProcessual]
    custas_despesas_valor_original: Decimal
    custas_despesas_correcao: Decimal
    custas_despesas_valor_atualizado: Decimal
    total_geral: Decimal
    fontes_custas_despesas: dict[str, str]
    formula: str
    alertas: list[str]
    chave_recuperacao: str | None = None


def moeda(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _moeda_multa(valor: Decimal, perfil: str) -> Decimal:
    if perfil == IPCAE_1AM_SIMPLES:
        return valor.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return moeda(valor)


def _nome_perfil(perfil: str) -> str:
    return next(
        (item["nome"] for item in PERFIS if item["id"] == perfil),
        "IPCA-E + 1% ao mês (legado)" if perfil == IPCAE_1AM_SIMPLES else perfil,
    )


def _agregar_componentes(parcelas) -> dict[str, ComponenteCalculo]:
    """Soma os valores por rubrica sem inventar um fator único para datas diferentes."""

    componentes: dict[str, ComponenteCalculo] = {}
    chaves = {chave for parcela in parcelas for chave in parcela.componentes}
    for chave in chaves:
        itens = [parcela.componentes[chave] for parcela in parcelas if chave in parcela.componentes]
        datas_iniciais = [item.data_inicial for item in itens if item.data_inicial]
        datas_finais = [item.data_final for item in itens if item.data_final]
        componentes[chave] = ComponenteCalculo(
            data_inicial=min(datas_iniciais) if datas_iniciais else None,
            data_final=max(datas_finais) if datas_finais else None,
            base_calculo=sum((item.base_calculo for item in itens), Decimal("0")),
            valor=sum((item.valor for item in itens), Decimal("0")),
        )
    return componentes


def _executar_operacao(
    operacao: OperacaoDivida,
    dados_gerais: DadosHonorarios,
    rotulo: str,
) -> ResultadoOperacaoDivida:
    if operacao.extincao_integral:
        return ResultadoOperacaoDivida(
            rotulo=rotulo,
            perfil=operacao.perfil,
            nome_perfil="Execução integralmente extinta - dívida remanescente zero",
            quantidade_parcelas=0,
            valor_informado=Decimal("0.00"),
            encargos_apurados=Decimal("0.00"),
            valor_atualizado=Decimal("0.00"),
            parcelas=[],
            componentes={},
            memoria_mensal=[],
            criterios=["Extinção integral informada pelo usuário."],
            metodologia=[
                "A dívida correta foi considerada integralmente extinta na data-base; "
                "não há saldo remanescente, atualização monetária, juros ou multa a apurar."
            ],
            fontes={},
            premissas={"extincao_integral": True},
        )
    dados = DadosSimplificados(
        data_base=dados_gerais.data_base,
        processo=dados_gerais.processo,
        classe=dados_gerais.classe,
        requerente=dados_gerais.requerente,
        requerido=dados_gerais.requerido,
        comarca=dados_gerais.comarca,
        vara=dados_gerais.vara,
        observacoes=dados_gerais.observacoes,
        criterio_inicio_juros=(
            "vencimento" if operacao.perfil == "selic_cjf_v1" else operacao.criterio_inicio_juros
        ),
        data_inicial_juros=(
            None if operacao.perfil == "selic_cjf_v1" else operacao.data_inicial_juros
        ),
    )
    parcelas = [
        ParcelaSimplificada(
            numero=parcela.numero,
            historico=parcela.historico or f"{rotulo} - item {parcela.numero}",
            data_vencimento=parcela.data_origem,
            valor_bruto=parcela.valor,
        )
        for parcela in operacao.parcelas
    ]
    calculo = CalculoSimplificado(perfil=operacao.perfil, dados_gerais=dados, parcelas=parcelas)
    resultado = executar_calculo(calculo)
    valor_informado = sum((parcela.valor for parcela in operacao.parcelas), Decimal("0"))
    parcelas_resultado = []
    memoria_multa = []
    for entrada, saida in zip(operacao.parcelas, resultado.parcelas, strict=True):
        multa = _moeda_multa(
            saida.valor_corrigido * operacao.multa_moratoria_percentual / Decimal("100"),
            operacao.perfil,
        )
        componentes = dict(saida.componentes)
        if operacao.multa_moratoria_percentual:
            componentes["multa_moratoria"] = ComponenteCalculo(
                data_inicial=entrada.data_origem,
                data_final=dados_gerais.data_base,
                base_calculo=saida.valor_corrigido,
                taxa_acumulada_percentual=operacao.multa_moratoria_percentual,
                valor=multa,
            )
            memoria_multa.append(MemoriaMensal(
                parcela=entrada.numero,
                competencia=dados_gerais.data_base.strftime("%Y-%m"),
                indice_aplicado="Multa moratória",
                valor_base=saida.valor_corrigido,
                fator_aplicado=1 + operacao.multa_moratoria_percentual / Decimal("100"),
                valor_corrigido=saida.valor_corrigido,
                multa=multa,
                total=saida.total_parcela + multa,
                observacao=(
                    f"Multa de {operacao.multa_moratoria_percentual}% sobre o principal "
                    "corrigido, mantida separada dos juros."
                ),
            ))
        valor_atualizado = moeda(saida.total_parcela + multa)
        parcelas_resultado.append(ResultadoParcelaDivida(
            numero=entrada.numero,
            historico=entrada.historico,
            data_origem=entrada.data_origem,
            valor_informado=entrada.valor,
            encargos_apurados=moeda(valor_atualizado - entrada.valor),
            valor_atualizado=valor_atualizado,
            componentes=componentes,
        ))
    valor_atualizado = sum(
        (parcela.valor_atualizado for parcela in parcelas_resultado), Decimal("0")
    )
    criterios = list(resultado.premissas.get("criterios", []))
    metodologia = list(resultado.premissas.get("metodologia", []))
    if operacao.multa_moratoria_percentual:
        criterios.append(
            f"Multa moratória de {operacao.multa_moratoria_percentual}% preservada nesta dívida."
        )
        metodologia.append(
            "A multa moratória incide sobre o principal corrigido de cada item, sem compor a base dos juros."
        )
    premissas = {
        **resultado.premissas,
        "multa_moratoria_percentual": str(operacao.multa_moratoria_percentual),
    }
    return ResultadoOperacaoDivida(
        rotulo=rotulo,
        perfil=operacao.perfil,
        nome_perfil=_nome_perfil(operacao.perfil),
        quantidade_parcelas=len(operacao.parcelas),
        valor_informado=valor_informado,
        encargos_apurados=moeda(valor_atualizado - valor_informado),
        valor_atualizado=valor_atualizado,
        parcelas=parcelas_resultado,
        componentes=_agregar_componentes(parcelas_resultado),
        memoria_mensal=[*resultado.memoria_mensal, *memoria_multa],
        criterios=criterios,
        metodologia=metodologia,
        fontes=resultado.premissas.get("fontes", {}),
        premissas=premissas,
    )


def apurar_faixas_fazenda(
    base: Decimal, config: EscalonamentoFazendaHonorarios,
) -> ResultadoEscalonamentoFazenda:
    """Adaptador comum das faixas canônicas, sem salário automático ou parcela fictícia."""
    faixas = faixas_honorarios_fazenda_padrao()
    for faixa, percentual in zip(faixas, config.percentuais_faixas):
        faixa.percentual_aplicado = percentual
    with localcontext() as contexto:
        contexto.rounding = ROUND_HALF_UP
        apuracao = calcular_honorarios(Honorarios(
            base_calculo=BaseCalculo.VALOR_MANUAL, valor_manual_base=base,
            escalonar_fazenda_publica=True, salario_minimo=config.salario_minimo,
            faixas_escalonamento=faixas,
        ), [], config.data_decisao)
    anterior, detalhes = Decimal("0"), []
    for item in apuracao["faixas_escalonamento"]:
        detalhes.append(ResultadoFaixaFazenda(**item, limite_inferior_salarios_minimos=anterior))
        if item["limite_salarios_minimos"] is not None:
            anterior = item["limite_salarios_minimos"]
    honorarios = apuracao["valor"]
    return ResultadoEscalonamentoFazenda(
        **config.model_dump(), base_calculo=base, valor_total=honorarios,
        percentual_efetivo=honorarios / base * Decimal("100") if base else Decimal("0"),
        faixas=detalhes,
        fonte="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm#art85",
    )


def executar_honorarios_proveito(
    calculo: CalculoHonorariosProveito,
) -> ResultadoHonorariosProveito:
    original = _executar_operacao(calculo.divida_original, calculo.dados_gerais, "Dívida original")
    correta = _executar_operacao(calculo.divida_correta, calculo.dados_gerais, "Dívida correta")

    diferenca = moeda(original.valor_atualizado - correta.valor_atualizado)
    proveito = max(diferenca, Decimal("0.00"))
    escalonamento = None
    if calculo.escalonamento_fazenda is not None:
        escalonamento = apurar_faixas_fazenda(proveito, calculo.escalonamento_fazenda)
        honorarios = escalonamento.valor_total
    else:
        honorarios = moeda(proveito * calculo.percentual_sentenca / Decimal("100"))
    custas_despesas = calcular_custas_despesas_ipcae(
        calculo.custas_despesas,
        calculo.dados_gerais.data_base,
    )
    custas_original = sum((item.valor_original for item in custas_despesas), Decimal("0"))
    custas_correcao = sum((item.correcao_monetaria for item in custas_despesas), Decimal("0"))
    custas_atualizadas = sum((item.valor_atualizado for item in custas_despesas), Decimal("0"))
    total_geral = moeda(honorarios + custas_atualizadas)
    alertas: list[str] = []
    if diferenca <= 0:
        alertas.append(
            "A dívida correta atualizada não é inferior à dívida original atualizada. "
            "Não há proveito econômico positivo para esta base de honorários."
        )

    return ResultadoHonorariosProveito(
        dados_gerais=calculo.dados_gerais,
        divida_original=original,
        divida_correta=correta,
        diferenca_atualizada=diferenca,
        proveito_economico=proveito,
        percentual_sentenca=calculo.percentual_sentenca,
        escalonamento_fazenda=escalonamento,
        honorarios_sucumbenciais=honorarios,
        custas_despesas=custas_despesas,
        custas_despesas_valor_original=custas_original,
        custas_despesas_correcao=custas_correcao,
        custas_despesas_valor_atualizado=custas_atualizadas,
        total_geral=total_geral,
        fontes_custas_despesas=(
            {"ipcae": dados_fonte_ipcae()} if custas_despesas else {}
        ),
        formula=("Honorários = soma dos honorários de cada faixa do proveito econômico positivo, conforme art. 85, §§ 3º e 5º, CPC. Cada percentual incide somente sobre a parcela da base na respectiva faixa; custas e despesas não integram a base."
        if escalonamento else
            "Honorários = máximo entre zero e (dívida original atualizada - dívida correta atualizada) "
            "× percentual fixado na sentença ÷ 100."
        ),
        alertas=alertas,
    )
