"""Remuneração de depósitos pela poupança, independente dos encargos da dívida.

Estimativa por aniversários mensais completos. Não substitui o saldo do extrato
judicial nem presume liberação, pagamento ou aplicabilidade de tese jurídica.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

from .criterios_simplificados import DadosSimplificados
from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import moeda, proximo_mes
from .perfis import PERFIS

PERFIL = "poupanca_deposito_v1"
PASTA = Path(__file__).resolve().parents[2] / "data" / "fontes"
METADADOS = PASTA / "poupanca_depositos_fonte.json"


def carregar_poupanca():
    metadados = json.loads(METADADOS.read_text(encoding="utf-8-sig"))
    taxas, hashes = {}, {}
    for nome in metadados["arquivos"]:
        arquivo = PASTA / nome
        hashes[nome] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        for item in json.loads(arquivo.read_text(encoding="utf-8-sig")):
            inicio = datetime.strptime(item["data"], "%d/%m/%Y").date()
            fim = datetime.strptime(item["dataFim"], "%d/%m/%Y").date()
            valor = D(item["valor"])
            if fim <= inicio or valor < 0:
                raise ValueError("Registro inválido na série oficial da poupança.")
            taxas[inicio] = (fim, valor)
    if not taxas:
        raise ValueError("A base oficial da poupança está vazia.")
    return metadados, taxas, hashes


def criterios_poupanca(dados=None):
    metadados, taxas, _ = dados or carregar_poupanca()
    consulta = date.fromisoformat(metadados["obtido_em"])
    # Uma taxa publicada antecipa seu período, mas não antecipa o crédito bancário.
    limite = min(consulta, max(fim for fim, _ in taxas.values()))
    return {
        "perfil": PERFIL, "perfis": PERFIS,
        "versao_metodologia": "poupanca_aniversarios_sgs195_v1",
        "inicio": min(taxas).isoformat(), "data_base_maxima": limite.isoformat(),
        "atualizado_em": metadados["obtido_em"],
        "fontes": {
            "poupanca_sgs195": metadados["fonte"],
            "aniversario_poupanca": "https://www.bcb.gov.br/meubc/faqs/p/posso-abrir-caderneta-de-poupanca-nos-dias-29-30-e-31-qual-a-diferenca",
        },
        "contagem": "Aniversários mensais completos, com reinvestimento da remuneração. Depósitos dos dias 29, 30 e 31 começam no dia 1 do mês seguinte; não há pro rata de período incompleto.",
    }


def calcular_depositos(dados_gerais, selecionados):
    dados = carregar_poupanca()
    criterios = criterios_poupanca(dados)
    _, taxas, hashes = dados
    fim = date.fromisoformat(str(dados_gerais["data_base"]))
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError("Poupança: atualize a base oficial antes de calcular após " + criterios["data_base_maxima"] + ".")
    parcelas, memoria = [], []
    for item in selecionados:
        if item.data < date.fromisoformat(criterios["inicio"]):
            raise ValueError("Poupança: a série de depósitos novos começa em " + criterios["inicio"] + ".")
        referencia = proximo_mes(item.data) if item.data.day > 28 else item.data
        base = item.valor - item.encargos_sem_atualizacao
        saldo, fator, registros = base, D(1), []
        inicio_efetivo, ultimo_credito = None, None
        while True:
            credito_previsto = proximo_mes(referencia).replace(day=referencia.day)
            if credito_previsto > fim:
                break
            if referencia not in taxas:
                raise ValueError(f"Índice ausente: poupança, aniversário {referencia:%d/%m/%Y}. Atualize a base oficial.")
            credito, taxa = taxas[referencia]
            if credito != credito_previsto:
                raise ValueError("Período oficial da poupança incompatível com o aniversário informado.")
            fator_mes = D(1) + taxa / 100
            anterior = saldo
            fator *= fator_mes
            saldo = base * fator
            inicio_efetivo = inicio_efetivo or referencia
            ultimo_credito = credito
            registros.append(MemoriaMensal(
                parcela=item.numero, competencia=credito.strftime("%Y-%m"),
                valor_base=anterior, indice_aplicado="Poupança - remuneração da conta (SGS 195)",
                fator_aplicado=fator_mes, valor_corrigido=moeda(saldo), total=moeda(saldo),
                observacao=f"Período {referencia:%d/%m/%Y} a {credito:%d/%m/%Y}; taxa oficial {taxa}%; crédito no aniversário. Remuneração reinvestida; saldo conserva precisão integral."
            ))
            referencia = credito
        remuneracao = moeda(saldo) - base
        componente = ComponenteCalculo(
            data_inicial=inicio_efetivo, data_final=ultimo_credito, base_calculo=base,
            fator_acumulado=fator, valor=remuneracao,
        )
        parcelas.append(ResultadoParcela(
            numero=item.numero, historico=item.descricao, data_vencimento=item.data,
            valor_bruto=item.valor, valor_pago_na_data=item.encargos_sem_atualizacao, valor_apurado=base,
            correcao_monetaria=remuneracao, valor_corrigido=base + remuneracao,
            total_parcela=base + remuneracao, componentes={"poupanca_deposito": componente}, memoria_correcao=registros,
        ))
        memoria.extend(registros)
    total = lambda campo: sum((getattr(p, campo) for p in parcelas), D(0))
    return ResultadoCalculo(
        dados_gerais=DadosGerais(**dados_gerais, tipo_devedor="fazenda_publica"),
        parcelas=parcelas, memoria_mensal=memoria,
        resumo=ResumoGeral(principal_original=total("valor_bruto"), valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"), correcao_monetaria=total("correcao_monetaria"),
            total_atualizado=total("total_parcela"), totais_componentes={"poupanca_deposito": total("correcao_monetaria")}),
        premissas={**criterios,
            "entrada": {"perfil": PERFIL, "dados_gerais": DadosSimplificados(**dados_gerais).model_dump(mode="json"), "parcelas": [
                {"numero": p.numero, "historico": p.descricao, "data_vencimento": p.data.isoformat(),
                 "valor_bruto": str(p.valor), "valor_pago_na_data": str(p.encargos_sem_atualizacao)} for p in selecionados]},
            "sha256_base": hashlib.sha256(METADADOS.read_bytes()).hexdigest(), "sha256_fontes": hashes,
            "criterios": ["Remuneração exclusiva da poupança, série oficial SGS 195, por aniversários mensais completos; sem IPCA, SELIC ou juros moratórios adicionais."],
            "metodologia": [
                criterios["contagem"],
                "Multiplicam-se os fatores oficiais dos períodos completos sobre o valor efetivamente destinado à conta; eventual parte expressamente excluída retorna nominalmente ao abatimento.",
                "O desconto é uma estimativa na data-base, não quitação na data do depósito. Na efetiva entrega ao credor, conferir o saldo real da conta judicial e recalcular a diferença.",
            ],
        },
        alertas=["Remuneração da conta estimada pela poupança; conferir o saldo efetivo no extrato bancário antes da liberação."],
    )
