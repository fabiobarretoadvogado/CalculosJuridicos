"""SELIC mensal simples, com taxa computada no mês seguinte à competência."""
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal as D

from .motor_simplificado import carregar_base, carregar_base_ec136, BASE, BASE_EC136, moeda, proximo_mes, consultar
from .models import DadosGerais, ResultadoCalculo, ResultadoParcela, ResumoGeral, ComponenteCalculo, MemoriaMensal
from .perfis import CJF, PERFIS

MANUAL = 'https://www.cjf.jus.br/cjf/corregedoria-da-justica-federal/corregedoria-geral-da-justica-federal/manual_de_calculos_2025_vf.pdf'
NOTA = 'https://www.cjf.jus.br/cjf/corregedoria-da-justica-federal/corregedoria-geral-da-justica-federal/atas_comissao_manual_calculos/250925_sei_0777749_ata.pdf'
BASE_HISTORICA = BASE.with_name('selic_historica.json')


def base_cjf():
    anterior, recente = carregar_base(), carregar_base_ec136()
    historica = json.loads(BASE_HISTORICA.read_text(encoding='utf-8-sig'))
    taxas_historicas = {x['data'][6:]+'-'+x['data'][3:5]: x['valor'] for x in historica['selic']}
    # A consulta mais recente prevalece nos meses sobrepostos.
    return {'selic': {**taxas_historicas, **anterior['selic'], **recente['selic']},
            'obtido_em': recente.get('selic_obtido_em', recente['obtido_em']),
            'fontes': {'selic': anterior['fontes']['selic'], 'selic_limite': recente['fontes']['selic_limite'],
                       'selic_historica': historica['fonte'], 'manual_cjf': MANUAL, 'orientacao_cjf': NOTA}}


def criterios_cjf(dados=None):
    dados = dados or base_cjf()
    consulta = date.fromisoformat(dados['obtido_em'])
    limites = []
    for mes in dados['selic']:
        referencia = date.fromisoformat(mes+'-01')
        # A taxa de julho entra na atualização de agosto (Manual, 4.2.1, nota 4c).
        aplicado = proximo_mes(referencia)
        fim = proximo_mes(aplicado)-timedelta(days=1)
        # A competência da taxa precisa estar fechada, não o mês em que
        # ela é aplicada. No mês corrente, admitir somente a referência dia 01.
        if aplicado <= consulta:
            limites.append(fim if fim < consulta else aplicado)
    if not limites:
        raise ValueError('Não há mês completo disponível para o padrão CJF.')
    limite = max(limites)
    referencia_maxima = limite.replace(day=1)
    return {'perfil': CJF, 'perfis': PERFIS, 'versao_metodologia': 'selic_cjf_mensal_v1',
            'inicio': min(dados['selic'])+'-01', 'inicio_selic': min(dados['selic'])+'-01', 'transicao': '',
            'data_base_maxima': limite.isoformat(),
            'data_referencia_selic_maxima': referencia_maxima.isoformat(),
            'ultima_competencia_selic_disponivel': (referencia_maxima-timedelta(days=1)).strftime('%Y-%m'),
            'atualizado_em': dados['obtido_em'], 'fontes': dados['fontes'],
            'contagem': 'SELIC simples por competência. A taxa de cada mês é computada no mês seguinte, inclusive na data-base. Sem taxa de 1% adicional no mês final.'}


def executar_cjf(calculo):
    dados = base_cjf()
    criterios = criterios_cjf(dados)
    fim = calculo.dados_gerais.data_base
    inicio_disponivel = date.fromisoformat(criterios['inicio'])
    if fim < inicio_disponivel or any(p.data_vencimento < inicio_disponivel for p in calculo.parcelas):
        raise ValueError(f"Há índices SELIC disponíveis a partir de {inicio_disponivel.strftime('%d/%m/%Y')}. O período anterior não tem cobertura na base oficial.")
    if fim > date.fromisoformat(criterios['data_base_maxima']):
        raise ValueError(f"A data-base máxima permitida é {date.fromisoformat(criterios['data_base_maxima']).strftime('%d/%m/%Y')}, último mês completo disponível.")
    resultados, memoria = [], []
    for p in calculo.parcelas:
        principal = p.valor_bruto-p.valor_pago_na_data
        referencia = p.data_vencimento.replace(day=1)
        taxa_acumulada = D(0)
        registros = []
        while proximo_mes(referencia) <= fim:
            aplicada = proximo_mes(referencia)
            comp = referencia.strftime('%Y-%m')
            taxa = consultar(dados, 'selic', comp)
            taxa_acumulada += taxa/100
            registros.append(MemoriaMensal(
                parcela=p.numero, competencia=aplicada.strftime('%Y-%m'), indice_aplicado='SELIC única - CJF',
                valor_base=principal, fator_aplicado=1+taxa/100,
                valor_corrigido=moeda(principal*(1+taxa_acumulada)), total=moeda(principal*(1+taxa_acumulada)),
                observacao=f'Taxa de {comp}: {taxa}%, computada em {aplicada:%Y-%m}. Soma acumulada: {taxa_acumulada*100}%. Base constante; não capitaliza juros.'
            ))
            referencia = aplicada
        acrescimo = moeda(principal*taxa_acumulada)
        c = ComponenteCalculo(data_inicial=p.data_vencimento, data_final=fim, base_calculo=principal,
                              taxa_acumulada_percentual=taxa_acumulada*100, valor=acrescimo)
        resultados.append(ResultadoParcela(numero=p.numero, historico=p.historico, data_vencimento=p.data_vencimento,
            valor_bruto=p.valor_bruto, valor_pago_na_data=p.valor_pago_na_data, valor_apurado=principal,
            correcao_monetaria=acrescimo, valor_corrigido=principal+acrescimo, total_parcela=principal+acrescimo,
            componentes={'selic': c}, memoria_correcao=registros))
        memoria.extend(registros)
    # Referência mensal da SELIC, sem mudar a data exata usada pelos outros encargos.
    referencia_final = fim.replace(day=1)
    ultima_competencia = (referencia_final-timedelta(days=1)).strftime('%Y-%m') if memoria else None
    ultimo_indice = (referencia_final-timedelta(days=1)).strftime('%m/%Y') if memoria else 'nenhum'
    soma = lambda campo: sum((getattr(p, campo) for p in resultados),D(0))
    return ResultadoCalculo(dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor='fazenda_publica'),
        parcelas=resultados, memoria_mensal=memoria,
        resumo=ResumoGeral(principal_original=soma('valor_bruto'), valor_pago_na_data_parcelas=soma('valor_pago_na_data'),
            principal_apurado=soma('valor_apurado'), correcao_monetaria=soma('correcao_monetaria'),
            total_atualizado=soma('total_parcela'), totais_componentes={'selic': soma('correcao_monetaria')}),
        premissas={**criterios, 'entrada': calculo.model_dump(mode='json'),
            'data_referencia_selic': referencia_final.isoformat(),
            'ultima_competencia_selic': ultima_competencia,
            'sha256_base': hashlib.sha256(BASE.read_bytes()).hexdigest(),
            'sha256_base_ec136': hashlib.sha256(BASE_EC136.read_bytes()).hexdigest(),
            'sha256_selic_historica': hashlib.sha256(BASE_HISTORICA.read_bytes()).hexdigest(),
            'criterios': [
                'SELIC como índice único de atualização monetária e juros de mora.',
                'Aplicação mensal conforme o Manual de Cálculos da Justiça Federal, item 4.2.1, nota 4, alínea c.',
                f'Data-base SELIC: {referencia_final:%d/%m/%Y}. Último índice aplicado: {ultimo_indice}. A referência é mensal, não diária.'
            ], 'metodologia': [
                'Somam-se as taxas mensais SELIC, sem capitalização. O acréscimo de cada parcela é o principal multiplicado pelo percentual acumulado.',
                'A taxa do mês da competência é computada no mês seguinte. A última taxa utilizada é a do mês anterior à data-base. Uma parcela do próprio mês da data-base não recebe acréscimo.',
                'SELIC reúne correção e mora. A data de citação não gera outro encargo nem uma segunda incidência da SELIC.',
                'Arredondamento por parcela ao centavo, com precisão integral nos cálculos. Índices e bases exibidos com quatro casas decimais. Total = principal + SELIC.'
            ]})
