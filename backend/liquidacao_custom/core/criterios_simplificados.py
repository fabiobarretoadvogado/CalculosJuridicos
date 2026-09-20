"""Entrada restrita ao escopo inicial. Critérios jurídicos pertencem ao perfil."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

INICIO = date(2021, 12, 9)
INICIO_TEMA_905 = date(2009, 7, 1)
TRANSICAO = date(2025, 9, 10)


class DadosSimplificados(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_base: date
    processo: str = ""
    classe: str = ""
    requerente: str = ""
    requerido: str = ""
    comarca: str = ""
    vara: str = ""
    observacoes: str = ""
    criterio_inicio_juros: Literal["vencimento", "citacao", "data_fixa", "por_parcela"] = "por_parcela"
    data_inicial_juros: date | None = None

    @model_validator(mode="after")
    def validar_inicio_juros(self):
        if self.criterio_inicio_juros in ("citacao", "data_fixa") and self.data_inicial_juros is None:
            raise ValueError("Informe a data de início dos juros para o critério escolhido.")
        return self


class ParcelaSimplificada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero: int = Field(default=1, gt=0)
    historico: str = ""
    data_vencimento: date
    valor_bruto: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    valor_pago_na_data: Decimal = Field(default=Decimal("0"), ge=0, max_digits=16, decimal_places=2)
    multa_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    data_inicial_juros: date | None = None

    @model_validator(mode="after")
    def validar(self):
        if self.valor_pago_na_data > self.valor_bruto:
            raise ValueError("O pagamento no vencimento não pode superar o valor da parcela.")
        return self


class CustaDespesaProcessual(BaseModel):
    """Lançamento autônomo, atualizado exclusivamente pelo IPCA-E."""

    model_config = ConfigDict(extra="forbid")
    numero: int = Field(default=1, gt=0)
    nome: str = Field(min_length=1, max_length=240)
    data: date
    valor: Decimal = Field(gt=0, max_digits=16, decimal_places=2)


class Desconto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero: int = Field(default=1, gt=0)
    aplicar: bool = True
    descricao: str = Field(default="", max_length=240)
    data: date | None = None
    valor: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    encargos_sem_atualizacao: Decimal = Field(default=Decimal("0"), ge=0, max_digits=16, decimal_places=2)

    @model_validator(mode="after")
    def validar(self):
        if self.aplicar and (self.data is None or self.valor is None):
            raise ValueError("Pagamento a abater: informe data e valor.")
        if self.valor is not None and self.encargos_sem_atualizacao > self.valor:
            raise ValueError("Os encargos já pagos não podem superar o valor do pagamento.")
        return self


class OperacaoDescontos(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # None acompanha o perfil das parcelas, mas não o seu marco de juros.
    perfil: Literal[
        "fazenda_publica_1_v1", "fazenda_publica_2_v1",
        "selic_ipcae_poupanca_v1", "selic_ipcae_2aa_v1",
        "selic_cjf_v1", "ipcae_1am_simples_v1",
        "ipca_taxa_legal_v1", "civil_2_v1", "poupanca_deposito_v1",
    ] | None = None
    criterio_inicio_juros: Literal["vencimento", "citacao", "data_fixa"] = "vencimento"
    data_inicial_juros: date | None = None
    itens: list[Desconto] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validar(self):
        if len({item.numero for item in self.itens}) != len(self.itens):
            raise ValueError("Os descontos devem ter números distintos.")
        return self


class HonorariosPrincipais(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aplicar: bool = False
    base: Literal["valor_causa", "proveito_economico", "valor_certo"] = "proveito_economico"
    percentual: Decimal | None = Field(default=None, gt=0, le=100, max_digits=7, decimal_places=4)
    valor_causa: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    data_protocolo: date | None = None
    indice: Literal["ipcae", "ipca"] = "ipcae"
    valor_certo: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)

    @model_validator(mode="after")
    def validar(self):
        if not self.aplicar:
            return self
        if self.base != "valor_certo" and self.percentual is None:
            raise ValueError("Honorários sucumbenciais: informe o percentual fixado.")
        if self.base == "valor_certo" and self.valor_certo is None:
            raise ValueError("Honorários sucumbenciais: informe o valor certo na data-base.")
        if self.base == "valor_causa" and (self.valor_causa is None or self.data_protocolo is None):
            raise ValueError("Honorários sucumbenciais: informe o valor da causa no protocolo e a data do protocolo.")
        return self


class CumprimentoSentenca(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aplicar_multa: bool = False
    aplicar_honorarios: bool = False
    incluir_sucumbenciais_base: bool = Field(
        default=False, deprecated=True,
        description="Campo legado: sempre desconsiderado. Honorários da sentença nunca integram a base do art. 523.",
    )
    destacar_contratuais: bool = False
    percentual_contratuais: Decimal | None = Field(default=None, gt=0, le=100, max_digits=7, decimal_places=4)
    base_contratuais: Literal["credito_parte", "total_sem_custas"] = "credito_parte"

    @model_validator(mode="after")
    def validar(self):
        # Aceitar entradas antigas sem permitir que reativem a regra removida.
        self.incluir_sucumbenciais_base = False
        if self.destacar_contratuais and self.percentual_contratuais is None:
            raise ValueError("Honorários contratuais: informe o percentual de destaque.")
        return self


class CalculoSimplificado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    perfil: Literal[
        "fazenda_publica_1_v1",
        "fazenda_publica_2_v1",
        "selic_ipcae_poupanca_v1",
        "selic_ipcae_2aa_v1",
        "selic_cjf_v1",
        "ipcae_1am_simples_v1",
        "ipca_taxa_legal_v1",
        "civil_2_v1",
    ] = "selic_ipcae_poupanca_v1"
    dados_gerais: DadosSimplificados
    parcelas: list[ParcelaSimplificada] = Field(min_length=1, max_length=2000)
    descontos: OperacaoDescontos = Field(default_factory=OperacaoDescontos)
    custas_despesas: list[CustaDespesaProcessual] = Field(default_factory=list, max_length=2000)
    honorarios_sucumbenciais: HonorariosPrincipais = Field(default_factory=HonorariosPrincipais)
    cumprimento_sentenca: CumprimentoSentenca = Field(default_factory=CumprimentoSentenca)

    def inicio_juros_parcela(self, parcela):
        criterio = self.dados_gerais.criterio_inicio_juros
        if self.perfil in ("ipca_taxa_legal_v1", "civil_2_v1"):
            if criterio in ("citacao", "data_fixa"):
                return self.dados_gerais.data_inicial_juros
            if criterio == "por_parcela":
                return parcela.data_inicial_juros or parcela.data_vencimento
            return parcela.data_vencimento
        if criterio == "vencimento":
            return parcela.data_vencimento
        if criterio in ("citacao", "data_fixa"):
            return max(self.dados_gerais.data_inicial_juros, parcela.data_vencimento)
        return max(parcela.data_inicial_juros or parcela.data_vencimento, parcela.data_vencimento)

    @model_validator(mode="after")
    def validar(self):
        honorarios = self.honorarios_sucumbenciais
        if honorarios.aplicar and honorarios.base == "valor_causa":
            if honorarios.data_protocolo < INICIO_TEMA_905:
                raise ValueError("Valor da causa: a série oficial disponível começa em 01/07/2009.")
            if honorarios.data_protocolo > self.dados_gerais.data_base:
                raise ValueError("Valor da causa: data do protocolo posterior à data-base.")
        if self.perfil != "selic_cjf_v1" and self.dados_gerais.data_base < INICIO_TEMA_905:
            raise ValueError("A data-base deve ser igual ou posterior a 01/07/2009.")
        numeros = [p.numero for p in self.parcelas]
        if len(set(numeros)) != len(numeros):
            raise ValueError("As parcelas devem ter números distintos.")
        numeros_custas = [item.numero for item in self.custas_despesas]
        if len(set(numeros_custas)) != len(numeros_custas):
            raise ValueError("As custas e despesas devem ter números distintos.")
        for p in self.parcelas:
            if self.perfil != "selic_cjf_v1" and p.data_vencimento < INICIO_TEMA_905:
                raise ValueError("Informe um vencimento a partir de 01/07/2009. As faixas anteriores do Tema 905 não estão incluídas neste perfil.")
            if p.data_vencimento > self.dados_gerais.data_base:
                raise ValueError(f"Parcela {p.numero}: vencimento posterior à data-base.")
        for item in self.custas_despesas:
            if item.data < INICIO_TEMA_905:
                raise ValueError(
                    f"Custa ou despesa {item.numero}: informe uma data a partir de 01/07/2009, "
                    "início da série IPCA-E disponível neste aplicativo."
                )
            if item.data > self.dados_gerais.data_base:
                raise ValueError(
                    f"Custa ou despesa {item.numero}: data posterior à data-base."
                )
        if any(item.aplicar for item in self.descontos.itens) and (self.descontos.perfil or self.perfil) not in ("selic_cjf_v1", "poupanca_deposito_v1") and self.descontos.criterio_inicio_juros != "vencimento" and self.descontos.data_inicial_juros is None:
            raise ValueError("Descontos: informe a data de início dos juros.")
        for item in self.descontos.itens:
            if not item.aplicar:
                continue
            if (self.descontos.perfil or self.perfil) != "selic_cjf_v1" and item.data < INICIO_TEMA_905:
                raise ValueError(f"Desconto {item.numero}: informe uma data a partir de 01/07/2009.")
            if item.data > self.dados_gerais.data_base:
                raise ValueError(f"Desconto {item.numero}: data posterior à data-base.")
        return self
