"""Equivalência nominal dos padrões monetários; nunca é índice de inflação."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

INICIO_REAL = date(1994, 7, 1)
INICIO_IPCA = date(1980, 1, 1)
INICIO_IPCAE = date(1992, 1, 1)
FONTE = "https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/arquivos/aeps-2023/secao-xv-indicadores-economicos/apresentacao"
# Data de vigência, nome, símbolo, divisor para o padrão seguinte.
PADROES = (
    (date(1970, 5, 15), "Cruzeiro", "Cr$", Decimal(1000)),
    (date(1986, 2, 28), "Cruzado", "Cz$", Decimal(1000)),
    (date(1989, 1, 16), "Cruzado novo", "NCz$", Decimal(1)),
    (date(1990, 3, 16), "Cruzeiro", "Cr$", Decimal(1000)),
    (date(1993, 8, 1), "Cruzeiro real", "CR$", Decimal(2750)),
    (INICIO_REAL, "Real", "R$", Decimal(1)),
)


def simbolo_moeda(origem):
    if not origem:
        return ""
    if isinstance(origem, str):
        origem = date.fromisoformat(origem)
    return next((item[2] for item in reversed(PADROES) if item[0] <= origem), "")


def inicio_indice(indice):
    if indice == "ipca":
        return INICIO_IPCA
    if indice == "ipcae":
        return INICIO_IPCAE
    return date(2009, 7, 1)


def validar_origem(data, indice, rotulo="Correção"):
    inicio = inicio_indice(indice)
    if data < inicio:
        raise ValueError(f"{rotulo}: a série {indice.upper()} disponível começa em {inicio:%d/%m/%Y}.")


def validar_data_base_real(data):
    if data < INICIO_REAL:
        raise ValueError("A data-base deve ser igual ou posterior a 01/07/1994; os resultados são expressos em reais.")


def conversao_monetaria(valor, origem, rotulo="Valor"):
    """Conserva toda a precisão. O centavo só é apurado no resultado financeiro."""
    if origem < PADROES[0][0]:
        raise ValueError("Padrão monetário anterior à cobertura disponível.")
    posicao = max(i for i, item in enumerate(PADROES) if item[0] <= origem)
    divisor = Decimal(1)
    eventos = []
    for i in range(posicao, len(PADROES) - 1):
        de, para = PADROES[i], PADROES[i + 1]
        divisor *= de[3]
        eventos.append({"data": str(para[0]), "de": de[1], "para": para[1], "divisor": str(de[3])})
    equivalente = valor / divisor
    registro = None if origem >= INICIO_REAL else {
        "operacao": rotulo, "data_origem": str(origem), "moeda_origem": PADROES[posicao][1],
        "simbolo_origem": PADROES[posicao][2], "valor_informado": str(valor),
        "moeda_resultado": "Real", "divisor": str(divisor), "equivalente_nominal_reais": str(equivalente),
        "eventos": eventos, "fonte": FONTE,
    }
    return equivalente, registro


def nota_conversao(registro):
    return (f"{registro['operacao']} de {registro['data_origem']}: "
        f"{registro['simbolo_origem']} {registro['valor_informado']} ({registro['moeda_origem']}) "
        f"÷ {registro['divisor']} = R$ {registro['equivalente_nominal_reais']} em equivalência nominal, "
        "antes da correção. Cortes de moeda separados da inflação; precisão integral no cálculo.")


def registrar_conversoes(resultado, registros):
    registros = [r for r in registros if r]
    if not registros:
        return resultado
    resultado.premissas.setdefault("conversoes_monetarias", []).extend(registros)
    resultado.premissas.setdefault("fontes", {})["moedas_historicas"] = FONTE
    for registro in registros:
        resultado.alertas.append(nota_conversao(registro))
    return resultado


def parcelas_em_reais(funcao):
    """Normaliza somente parcelas deste motor; acessórios mantêm suas entradas próprias."""
    @wraps(funcao)
    def executar(calculo):
        parcelas, registros = [], []
        for parcela in calculo.parcelas:
            bruto, registro = conversao_monetaria(parcela.valor_bruto, parcela.data_vencimento, f"Parcela {parcela.numero}")
            pago, registro_pago = conversao_monetaria(parcela.valor_pago_na_data, parcela.data_vencimento, f"Pagamento no vencimento da parcela {parcela.numero}")
            parcelas.append(parcela.model_copy(update={"valor_bruto": bruto, "valor_pago_na_data": pago}))
            if registro:
                registros.append(registro)
                if parcela.valor_pago_na_data:
                    registros.append(registro_pago)
        convertido = calculo.model_copy(update={"parcelas": parcelas}) if registros else calculo
        resultado = funcao(convertido)
        if registros:
            centavo = lambda v: v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for parcela in resultado.parcelas:
                base_arredondada = centavo(parcela.valor_bruto) - centavo(parcela.valor_pago_na_data)
                diferenca = parcela.valor_apurado - base_arredondada
                parcela.correcao_monetaria += diferenca
                if "ipca" in parcela.componentes:
                    parcela.componentes["ipca"].valor += diferenca
                if "ipcae_pre" in parcela.componentes:
                    parcela.componentes["ipcae_pre"].valor += diferenca
                for campo in ("valor_bruto", "valor_pago_na_data"):
                    setattr(parcela, campo, centavo(getattr(parcela, campo)))
                parcela.valor_apurado = base_arredondada
                for registro in registros:
                    if registro["operacao"] == f"Parcela {parcela.numero}" and parcela.memoria_correcao:
                        parcela.memoria_correcao[0].observacao += " " + nota_conversao(registro)
            for destino, campo in (("principal_original", "valor_bruto"), ("valor_pago_na_data_parcelas", "valor_pago_na_data"),
                    ("principal_apurado", "valor_apurado"), ("correcao_monetaria", "correcao_monetaria")):
                setattr(resultado.resumo, destino, sum((getattr(p, campo) for p in resultado.parcelas), Decimal(0)))
            for key in resultado.resumo.totais_componentes:
                resultado.resumo.totais_componentes[key] = sum((p.componentes[key].valor for p in resultado.parcelas if key in p.componentes), Decimal(0))
            resultado.premissas["entrada"] = calculo.model_dump(mode="json")
        return registrar_conversoes(resultado, registros)
    return executar
