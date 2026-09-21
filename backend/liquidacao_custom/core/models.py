"""
Modelos de dados centrais para o motor de cálculo judicial.

Todos os modelos usam Pydantic v2 para validação.
O design segue o princípio de que cada parcela pode ter critérios próprios
de correção monetária, juros, multa, datas e observações.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TipoDevedor(str, Enum):
    """Tipo de devedor do cálculo."""
    FAZENDA_PUBLICA = "fazenda_publica"
    PRIVADO = "privado"
    OUTRO = "outro"


class IndiceCorrecao(str, Enum):
    """Índices de correção monetária disponíveis."""
    SEM_CORRECAO = "sem_correcao"
    IPCA = "ipca"
    INPC = "inpc"
    IPCAE = "ipcae"
    IGPM = "igpm"
    SELIC = "selic"
    TAXA_LEGAL = "taxa_legal"
    INDICE_MANUAL = "indice_manual"


class TipoJuros(str, Enum):
    """Tipos de juros disponíveis."""
    SEM_JUROS = "sem_juros"
    PERCENTUAL_MENSAL_SIMPLES = "percentual_mensal_simples"
    PERCENTUAL_MENSAL_COMPOSTO = "percentual_mensal_composto"
    SELIC = "selic"
    TAXA_LEGAL = "taxa_legal"
    POUPANCA = "poupanca"
    TAXA_MANUAL = "taxa_manual"


class FormaImputacao(str, Enum):
    """Formas de imputação de abatimentos."""
    ABATER_DO_TOTAL_NA_DATA_BASE = "abater_do_total_na_data_base"
    ABATER_NA_DATA_DO_PAGAMENTO = "abater_na_data_do_pagamento"
    PRIMEIRO_JUROS_DEPOIS_PRINCIPAL = "primeiro_juros_depois_principal"
    PRIMEIRO_PRINCIPAL_DEPOIS_JUROS = "primeiro_principal_depois_juros"
    PROPORCIONAL = "proporcional"
    PARCELA_ESPECIFICA = "parcela_especifica"


class Periodicidade(str, Enum):
    """Periodicidade para preenchimento em série."""
    MENSAL = "mensal"
    BIMESTRAL = "bimestral"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"


class BaseCalculo(str, Enum):
    """Bases de cálculo para honorários e acessórios."""
    SUBTOTAL_PARCELAS = "subtotal_parcelas"
    SUBTOTAL_ATUALIZADO = "subtotal_atualizado"
    PRINCIPAL_CORRIGIDO = "principal_corrigido"
    JUROS = "juros"
    PARCELA_ESPECIFICA = "parcela_especifica"
    VALOR_MANUAL = "valor_manual"


class TipoHonorarios(str, Enum):
    """Tipos de honorarios advocaticios."""
    CONTRATUAIS = "contratuais"
    SUCUMBENCIAIS = "sucumbenciais"
    EXECUCAO = "execucao"


class FaixaHonorariosFazenda(BaseModel):
    """Faixa progressiva do art. 85, par. 3 do CPC."""
    ordem: int
    limite_salarios_minimos: Optional[Decimal] = None
    percentual_minimo: Decimal
    percentual_maximo: Decimal
    percentual_aplicado: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Dados gerais do cálculo
# ---------------------------------------------------------------------------

class DadosGerais(BaseModel):
    """Dados gerais do cálculo judicial."""
    data_base: date
    processo: str = ""
    classe: str = ""
    requerente: str = ""
    requerido: str = ""
    tipo_devedor: TipoDevedor = TipoDevedor.PRIVADO
    comarca: str = ""
    vara: str = ""
    contrato: str = ""
    observacoes: str = ""
    criterio_inicio_juros: str = "por_parcela"
    data_inicial_juros: date | None = None


class CriteriosDisponiveis(BaseModel):
    """
    Catálogo de critérios disponíveis para o cálculo.
    Funcionam como opções — não obrigam todas as parcelas a usar o mesmo critério.
    """
    indices_correcao: list[IndiceCorrecao] = Field(
        default_factory=lambda: list(IndiceCorrecao)
    )
    tipos_juros: list[TipoJuros] = Field(
        default_factory=lambda: list(TipoJuros)
    )


# ---------------------------------------------------------------------------
# Períodos de correção e juros (suporte a múltiplos períodos por parcela)
# ---------------------------------------------------------------------------

class PeriodoCorrecao(BaseModel):
    """Define um período de correção monetária para uma parcela."""
    indice: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    data_inicial: Optional[date] = None
    data_final: Optional[date] = None
    fator_manual: Optional[Decimal] = None
    observacao: str = ""


class ConfigJuros(BaseModel):
    """Configuração de juros para um período específico."""
    tipo: TipoJuros = TipoJuros.SEM_JUROS
    data_inicial: Optional[date] = None
    data_final: Optional[date] = None
    percentual: Decimal = Decimal("0")
    composto: bool = False
    pro_rata_die: bool = False
    contagem_mes_cheio: bool = True
    incide_sobre_corrigido: bool = True
    taxa_manual_mensal: Optional[Decimal] = None
    observacao: str = ""


# ---------------------------------------------------------------------------
# Parcela — modelo principal
# ---------------------------------------------------------------------------

class Parcela(BaseModel):
    """
    Modelo principal de parcela do crédito.

    Cada parcela pode ter seus próprios critérios de correção,
    juros, multa, datas e observações.
    """
    numero: int = 1
    natureza: str = ""
    data_vencimento: Optional[date] = None
    historico: str = ""
    valor_bruto: Decimal = Decimal("0")
    valor_pago_na_data: Decimal = Decimal("0")
    valor_apurado: Decimal = Decimal("0")

    # Correção monetária — suporte a múltiplos períodos
    periodos_correcao: list[PeriodoCorrecao] = Field(default_factory=list)

    # Compatibilidade: campos simples para parcelas com período único
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    data_inicial_correcao: Optional[date] = None
    data_final_correcao: Optional[date] = None

    # Juros moratórios — suporte a múltiplos períodos
    periodos_juros: list[ConfigJuros] = Field(default_factory=list)

    # Compatibilidade: campos simples para parcelas com período único
    juros_moratorios: TipoJuros = TipoJuros.SEM_JUROS
    data_inicial_juros: Optional[date] = None
    data_final_juros: Optional[date] = None
    percentual_juros: Decimal = Decimal("0")

    multa_moratoria: Decimal = Decimal("0")
    observacao: str = ""

    def recalcular_apurado(self) -> None:
        """Recalcula valor_apurado como valor_bruto - valor_pago_na_data."""
        self.valor_apurado = self.valor_bruto - self.valor_pago_na_data

    @model_validator(mode="after")
    def _auto_calc_apurado(self) -> "Parcela":
        """Calcula valor_apurado automaticamente se não foi informado ou é zero."""
        if self.valor_apurado == Decimal("0") and self.valor_bruto > Decimal("0"):
            self.valor_apurado = self.valor_bruto - self.valor_pago_na_data
        return self

    def get_periodos_correcao_efetivos(self, data_base: date) -> list[PeriodoCorrecao]:
        """
        Retorna os períodos de correção efetivos.
        Se periodos_correcao estiver vazio, monta a partir dos campos simples.
        """
        if self.periodos_correcao:
            return self.periodos_correcao
        if self.correcao_monetaria != IndiceCorrecao.SEM_CORRECAO:
            return [PeriodoCorrecao(
                indice=self.correcao_monetaria,
                data_inicial=self.data_inicial_correcao,
                data_final=self.data_final_correcao or data_base,
            )]
        return []

    def get_periodos_juros_efetivos(self, data_base: date) -> list[ConfigJuros]:
        """
        Retorna os períodos de juros efetivos.
        Se periodos_juros estiver vazio, monta a partir dos campos simples.
        """
        if self.periodos_juros:
            return self.periodos_juros
        if self.juros_moratorios != TipoJuros.SEM_JUROS:
            return [ConfigJuros(
                tipo=self.juros_moratorios,
                data_inicial=self.data_inicial_juros,
                data_final=self.data_final_juros or data_base,
                percentual=self.percentual_juros,
            )]
        return []


# ---------------------------------------------------------------------------
# Preenchimento em série
# ---------------------------------------------------------------------------

class ConfigPreenchimentoSerie(BaseModel):
    """Configuração para geração de parcelas em série."""
    data_inicial: date
    data_final: date
    periodicidade: Periodicidade = Periodicidade.MENSAL
    dia_vencimento: int = 1
    historico_padrao: str = ""
    valor_fixo: Decimal = Decimal("0")
    natureza: str = ""
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    data_inicial_correcao: Optional[date] = None
    juros_moratorios: TipoJuros = TipoJuros.SEM_JUROS
    data_inicial_juros: Optional[date] = None
    percentual_juros: Decimal = Decimal("0")
    multa_moratoria: Decimal = Decimal("0")


class ConfigSalarioMinimo(BaseModel):
    """Configuração para geração de parcelas baseadas em salário mínimo."""
    percentual: Decimal
    data_inicial: date
    data_final: date
    periodicidade: Periodicidade = Periodicidade.MENSAL
    dia_vencimento: int = 1
    historico: str = ""
    natureza: str = ""
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    juros_moratorios: TipoJuros = TipoJuros.SEM_JUROS
    percentual_juros: Decimal = Decimal("0")
    multa_moratoria: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Acessórios
# ---------------------------------------------------------------------------

def faixas_honorarios_fazenda_padrao() -> list[FaixaHonorariosFazenda]:
    """Faixas legais do art. 85, par. 3 do CPC."""
    return [
        FaixaHonorariosFazenda(ordem=1, limite_salarios_minimos=Decimal("200"), percentual_minimo=Decimal("10"), percentual_maximo=Decimal("20")),
        FaixaHonorariosFazenda(ordem=2, limite_salarios_minimos=Decimal("2000"), percentual_minimo=Decimal("8"), percentual_maximo=Decimal("10")),
        FaixaHonorariosFazenda(ordem=3, limite_salarios_minimos=Decimal("20000"), percentual_minimo=Decimal("5"), percentual_maximo=Decimal("8")),
        FaixaHonorariosFazenda(ordem=4, limite_salarios_minimos=Decimal("100000"), percentual_minimo=Decimal("3"), percentual_maximo=Decimal("5")),
        FaixaHonorariosFazenda(ordem=5, limite_salarios_minimos=None, percentual_minimo=Decimal("1"), percentual_maximo=Decimal("3")),
    ]


class Honorarios(BaseModel):
    """Configuração de honorários advocatícios."""
    tipo: TipoHonorarios = TipoHonorarios.SUCUMBENCIAIS
    descricao: str = "Honorários sucumbenciais"
    percentual: Optional[Decimal] = None
    valor_fixo: Optional[Decimal] = None
    base_calculo: BaseCalculo = BaseCalculo.SUBTOTAL_ATUALIZADO
    parcela_especifica: Optional[int] = None
    valor_manual_base: Optional[Decimal] = None
    escalonar_fazenda_publica: bool = False
    salario_minimo: Optional[Decimal] = None
    faixas_escalonamento: list[FaixaHonorariosFazenda] = Field(
        default_factory=faixas_honorarios_fazenda_padrao
    )


class MultaCPC523(BaseModel):
    """Configuração da multa do art. 523 do CPC."""
    aplicar: bool = False
    aplicar_multa: bool = False
    aplicar_honorarios: bool = False
    percentual_multa: Decimal = Decimal("10")
    percentual_honorarios: Decimal = Decimal("10")
    base_calculo: BaseCalculo = BaseCalculo.SUBTOTAL_ATUALIZADO

    @model_validator(mode="before")
    @classmethod
    def _compat_aplicar(cls, data):
        """Mantém compatibilidade com cálculos antigos que usavam um único campo aplicar."""
        if isinstance(data, dict) and data.get("aplicar") and "aplicar_multa" not in data and "aplicar_honorarios" not in data:
            data = {**data, "aplicar_multa": True, "aplicar_honorarios": True}
        return data

    @model_validator(mode="after")
    def _sincronizar_aplicar(self) -> "MultaCPC523":
        self.aplicar = self.aplicar_multa or self.aplicar_honorarios
        return self


class MultaAdicional(BaseModel):
    """Multas configuráveis, como litigância de má-fé ou embargos protelatórios."""
    descricao: str = "Multa"
    percentual: Optional[Decimal] = Decimal("10")
    valor_fixo: Optional[Decimal] = None
    base_calculo: BaseCalculo = BaseCalculo.SUBTOTAL_ATUALIZADO
    parcela_especifica: Optional[int] = None
    valor_manual_base: Optional[Decimal] = None
    observacao: str = ""


class CustaDespesa(BaseModel):
    """Custas ou despesas processuais."""
    data: Optional[date] = None
    historico: str = ""
    valor: Decimal = Decimal("0")
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    data_inicial_correcao: Optional[date] = None
    juros_moratorios: TipoJuros = TipoJuros.SEM_JUROS
    data_inicial_juros: Optional[date] = None
    percentual_juros: Decimal = Decimal("0")
    observacao: str = ""


class Astreintes(BaseModel):
    """Astreintes (multa cominatória)."""
    valor: Decimal = Decimal("0")
    data_inicial: Optional[date] = None
    data_final: Optional[date] = None
    valor_diario: Optional[Decimal] = None
    historico: str = ""
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    observacao: str = ""


# ---------------------------------------------------------------------------
# Abatimentos
# ---------------------------------------------------------------------------

class Abatimento(BaseModel):
    """
    Abatimento posterior ao vencimento da parcela.

    Pagamentos realizados na data do vencimento devem ser lançados
    como valor_pago_na_data na parcela.
    Pagamentos posteriores são lançados aqui como abatimentos.
    """
    data_pagamento: date
    valor: Decimal
    historico: str = ""
    parcela_especifica: Optional[int] = None
    forma_imputacao: FormaImputacao = FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE
    correcao_monetaria: IndiceCorrecao = IndiceCorrecao.SEM_CORRECAO
    data_inicial_correcao: Optional[date] = None
    juros_moratorios: TipoJuros = TipoJuros.SEM_JUROS
    data_inicial_juros: Optional[date] = None
    percentual_juros: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Configuração da Taxa Legal
# ---------------------------------------------------------------------------

class ConfigTaxaLegal(BaseModel):
    """Configuração para a Taxa Legal."""
    data_inicio_vigencia: date = date(2022, 12, 1)
    resultado_negativo_como_zero: bool = True
    fonte: str = "Banco Central do Brasil"


# ---------------------------------------------------------------------------
# Configuração da SELIC como taxa única
# ---------------------------------------------------------------------------

class ConfigSelicTaxaUnica(BaseModel):
    """
    Configuração para uso da SELIC como taxa única.
    Usada tipicamente em cálculos contra Fazenda Pública (EC 113/2021).
    """
    aplicar: bool = False
    data_inicio: Optional[date] = None
    consolidar_saldo_ate: Optional[date] = None
    observacao: str = ""


# ---------------------------------------------------------------------------
# Modelo raiz do cálculo
# ---------------------------------------------------------------------------

class CalculoJudicial(BaseModel):
    """
    Modelo raiz que agrega todos os elementos de um cálculo judicial.
    """
    dados_gerais: DadosGerais
    criterios_disponiveis: CriteriosDisponiveis = Field(
        default_factory=CriteriosDisponiveis
    )
    parcelas: list[Parcela] = Field(default_factory=list)
    honorarios: list[Honorarios] = Field(default_factory=list)
    multa_cpc523: MultaCPC523 = Field(default_factory=MultaCPC523)
    multas_adicionais: list[MultaAdicional] = Field(default_factory=list)
    custas: list[CustaDespesa] = Field(default_factory=list)
    despesas: list[CustaDespesa] = Field(default_factory=list)
    astreintes: list[Astreintes] = Field(default_factory=list)
    abatimentos: list[Abatimento] = Field(default_factory=list)
    config_taxa_legal: ConfigTaxaLegal = Field(default_factory=ConfigTaxaLegal)
    config_selic_taxa_unica: ConfigSelicTaxaUnica = Field(
        default_factory=ConfigSelicTaxaUnica
    )


# ---------------------------------------------------------------------------
# Modelos de resultado
# ---------------------------------------------------------------------------

class MemoriaMensal(BaseModel):
    """Registro de memória mensal de cálculo."""
    parcela: int = 0
    competencia: str = ""
    valor_base: Decimal = Decimal("0")
    indice_aplicado: str = ""
    fator_aplicado: Decimal = Decimal("1")
    valor_corrigido: Decimal = Decimal("0")
    juros_periodo: Decimal = Decimal("0")
    juros_acumulados: Decimal = Decimal("0")
    multa: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    observacao: str = ""


class ResultadoCustaDespesaProcessual(BaseModel):
    """Atualização individual de uma custa ou despesa, exclusivamente pelo IPCA-E."""
    numero: int
    nome: str
    data: date
    valor_original: Decimal
    fator_ipcae: Decimal
    correcao_monetaria: Decimal
    valor_atualizado: Decimal
    memoria: list[MemoriaMensal] = Field(default_factory=list)


class ComponenteCalculo(BaseModel):
    """Índice acumulado e acréscimo de um período, sem arredondar sua base."""
    data_inicial: Optional[date] = None
    data_final: Optional[date] = None
    base_calculo: Decimal = Decimal("0")
    fator_acumulado: Optional[Decimal] = None
    taxa_acumulada_percentual: Optional[Decimal] = None
    valor: Decimal = Decimal("0")


class ResultadoMultaParcela(BaseModel):
    percentual: Decimal
    base_calculo: Decimal
    valor_original: Decimal
    correcao_monetaria: Decimal
    juros_mora: Decimal
    total_atualizado: Decimal
    componentes: dict[str, ComponenteCalculo] = Field(default_factory=dict)
    memoria: list[MemoriaMensal] = Field(default_factory=list)


class ResultadoParcela(BaseModel):
    """Resultado do cálculo de uma parcela individual."""
    numero: int = 0
    natureza: str = ""
    historico: str = ""
    data_vencimento: Optional[date] = None
    valor_bruto: Decimal = Decimal("0")
    valor_pago_na_data: Decimal = Decimal("0")
    valor_apurado: Decimal = Decimal("0")
    correcao_monetaria: Decimal = Decimal("0")
    valor_corrigido: Decimal = Decimal("0")
    juros_mora: Decimal = Decimal("0")
    multa: Decimal = Decimal("0")
    multa_detalhes: Optional[ResultadoMultaParcela] = None
    total_parcela: Decimal = Decimal("0")
    memoria_correcao: list[MemoriaMensal] = Field(default_factory=list)
    memoria_juros: list[MemoriaMensal] = Field(default_factory=list)
    componentes: dict[str, ComponenteCalculo] = Field(default_factory=dict)
    alertas: list[str] = Field(default_factory=list)


class MemoriaAbatimento(BaseModel):
    """Registro de memória de abatimento aplicado."""
    data_pagamento: date
    valor_abatido: Decimal = Decimal("0")
    valor_original: Decimal = Decimal("0")
    correcao_monetaria: Decimal = Decimal("0")
    juros_mora: Decimal = Decimal("0")
    forma_imputacao: FormaImputacao = FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE
    parcela_especifica: Optional[int] = None
    historico: str = ""
    saldo_anterior: Decimal = Decimal("0")
    saldo_posterior: Decimal = Decimal("0")
    competencia_quitacao: Optional[str] = None
    saldo_remanescente: Decimal = Decimal("0")


class ResumoGeral(BaseModel):
    """Resumo geral do cálculo."""
    principal_original: Decimal = Decimal("0")
    valor_pago_na_data_parcelas: Decimal = Decimal("0")
    principal_apurado: Decimal = Decimal("0")
    correcao_monetaria: Decimal = Decimal("0")
    juros_mora: Decimal = Decimal("0")
    multas: Decimal = Decimal("0")
    honorarios: Decimal = Decimal("0")
    custas: Decimal = Decimal("0")
    despesas: Decimal = Decimal("0")
    abatimentos: Decimal = Decimal("0")
    total_atualizado: Decimal = Decimal("0")
    totais_componentes: dict[str, Decimal] = Field(default_factory=dict)


class ResultadoHonorariosPrincipais(BaseModel):
    base: str
    descricao_base: str
    percentual: Optional[Decimal] = None
    valor_original: Decimal
    data_protocolo: Optional[date] = None
    indice: Optional[str] = None
    fator_acumulado: Decimal = Decimal("1")
    correcao_monetaria: Decimal = Decimal("0")
    base_atualizada: Decimal
    valor: Decimal
    memoria: list[MemoriaMensal] = Field(default_factory=list)
    fonte: str = ""


class ResultadoCumprimentoSentenca(BaseModel):
    credito_parte: Decimal
    sucumbenciais_na_base: Decimal
    base_calculo: Decimal
    percentual_multa: Decimal = Decimal("10")
    percentual_honorarios: Decimal = Decimal("10")
    multa: Decimal
    honorarios: Decimal
    aplicar_multa: bool
    aplicar_honorarios: bool


class ResultadoDestaqueContratuais(BaseModel):
    base: str
    descricao_base: str
    base_calculo: Decimal
    percentual: Decimal
    valor: Decimal
    saldo_apos_destaque: Decimal
    acresce_total: bool = False


class ResultadoCalculo(BaseModel):
    descontos: Optional["ResultadoCalculo"] = None
    """Resultado completo de um cálculo judicial."""
    dados_gerais: DadosGerais
    resumo: ResumoGeral = Field(default_factory=ResumoGeral)
    parcelas: list[ResultadoParcela] = Field(default_factory=list)
    custas_despesas: list[ResultadoCustaDespesaProcessual] = Field(default_factory=list)
    memoria_mensal: list[MemoriaMensal] = Field(default_factory=list)
    memorias_abatimento: list[MemoriaAbatimento] = Field(default_factory=list)
    honorarios_detalhes: list[dict] = Field(default_factory=list)
    honorarios_sucumbenciais: Optional[ResultadoHonorariosPrincipais] = None
    cumprimento_sentenca: Optional[ResultadoCumprimentoSentenca] = None
    destaque_contratuais: Optional[ResultadoDestaqueContratuais] = None
    alertas: list[str] = Field(default_factory=list)
    premissas: dict = Field(default_factory=dict)
    chave_recuperacao: Optional[str] = None
