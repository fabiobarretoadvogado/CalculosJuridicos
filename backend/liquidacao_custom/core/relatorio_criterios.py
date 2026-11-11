"""Critérios em texto e regras compartilhados por todas as modalidades de PDF."""
from collections import OrderedDict

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph

from .perfis import PERFIS
from .relatorio_layout import data_br, notas_tecnicas, texto, separar_operacoes


def operacao(rotulo, premissas, data_final, *, nome=None, inicio=None,
             criterios=None, metodologia=None):
    entrada = premissas.get("entrada", {})
    geral = entrada.get("dados_gerais", {})
    perfil = premissas.get("perfil")
    nome = nome or next((p["nome"] for p in PERFIS if p["id"] == perfil), "Conforme critérios abaixo")
    if inicio is None:
        criterio = geral.get("criterio_inicio_juros", "vencimento")
        if perfil == "poupanca_deposito_v1":
            nome = "Depósito judicial / poupança"
            inicio = "Remuneração desde a data de cada depósito; valores fora da conta permanecem nominais."
        elif perfil == "selic_cjf_v1":
            inicio = "Competência de cada parcela; SELIC única."
        else:
            juros = ("Vencimento de cada parcela" if criterio == "vencimento" else
                     f"{data_br(geral.get('data_inicial_juros'))} ({'citação' if criterio == 'citacao' else 'data específica'})"
                     if criterio in ("citacao", "data_fixa") else "Termo individual indicado em cada parcela")
            inicio = "Correção: data própria de cada lançamento. " + (
                "Sem juros." if perfil == "correcao_mensal_v1" else f"Início dos juros: {juros}.")
    referencia = premissas.get("data_referencia_selic")
    final = data_br(referencia or data_final)
    if perfil in ("ipca_taxa_legal_v1", "civil_2_v1", "civil_3_v1", "civil_4_temporario_v1", "civil_5_taxa_legal_reconstruida_v1", "civil_6_v1"):
        final = f"Data-base: {final} (excluída dos encargos)."
    if referencia:
        competencia = premissas.get("ultima_competencia_selic")
        final = f"Referência mensal: {final}. Último índice aplicado: {competencia[5:7] + '/' + competencia[:4] if competencia else 'nenhum'}."
    notas = notas_tecnicas(criterios if criterios is not None else premissas.get("criterios", []),
                           metodologia if metodologia is not None else premissas.get("metodologia", []))
    # Datas mensais são identificadas no bloco da operação, sem repetir o parágrafo.
    notas = [n.replace("rotina calcular_juros/contar_meses existente. ", "")
             for n in notas if not n.startswith("Data-base SELIC:")]
    # Apenas a redação do PDF muda; a memória original da comparação é preservada.
    notas = [n.replace(
        "A coluna Ajuste ao limite SELIC desconta eventual excesso; a taxa exibida nessa coluna é a SELIC de comparação, e zero significa que não houve redução.",
        "Os valores pós EC 136/2025 são líquidos do limite. Eventual redução já está incorporada à correção monetária; fatores e taxas identificam os índices aplicados antes dessa redução.")
        .replace("O total soma o principal e todas as colunas, inclusive o ajuste negativo ao limite, quando houver.",
                 "O total soma o principal e as colunas líquidas exibidas.") for n in notas]
    return {"rotulo": rotulo, "nome": nome, "inicio": inicio, "final": final, "notas": notas}


def custas(itens, data_final):
    if not itens:
        return []
    return [{"rotulo": "Custas e despesas", "nome": "IPCA-E, sem juros",
             "inicio": "Data própria de cada custa ou despesa.", "final": data_br(data_final),
             "notas": ["IPCA-E: fatores mensais multiplicados, com proporção dos dias corridos nos meses parciais e extremos incluídos; deflações preservadas. Precisão integral até o arredondamento HALF_UP ao centavo por lançamento. Custas são apuradas separadamente, sem juros, fora da base dos honorários e acrescidas somente ao total final."]}]


def criterios_metodologia(operacoes, largura, p, estilos, altura):
    estilos = {nome: ParagraphStyle("criterios_" + nome, parent=estilo,
                                    fontSize=8, leading=11)
               for nome, estilo in estilos.items()}

    def p(conteudo, estilo="tecnico"):
        return Paragraph(texto(conteudo), estilos[estilo])

    regras = OrderedDict()
    for o in operacoes:
        for nota in o["notas"]:
            regras.setdefault(nota, [])
            if o["rotulo"] not in regras[nota]:
                regras[nota].append(o["rotulo"])
    blocos = [p("CRITÉRIOS E METODOLOGIA", "secao")]
    primeira_introducao = []
    for o in operacoes:
        introducao = [p(o["rotulo"], "tecnico_titulo")]
        for rotulo, chave in (("Início dos encargos", "inicio"),
                              ("Referência final", "final")):
            introducao.append(Paragraph(
                f"<b>{rotulo}:</b> {texto(o[chave])}", estilos["tecnico_dados"]))
        # O título acompanha todos os dados básicos da operação, sem grade ou colunas.
        if not primeira_introducao:
            primeira_introducao = introducao
        blocos.append(KeepTogether(introducao))
        blocos.extend(p(nota, "tecnico") for nota, escopos in regras.items()
                      if escopos == [o["rotulo"]])
    # Só as regras de mais de uma operação ficam no bloco comum.
    grupos = OrderedDict()
    for nota, escopos in regras.items():
        if len(escopos) > 1:
            grupos.setdefault(tuple(escopos), []).append(nota)
    for escopos, notas in grupos.items():
        blocos.append(p("Regras comuns - " + " / ".join(escopos), "tecnico_titulo"))
        blocos.extend(p(nota, "tecnico") for nota in notas)
    return separar_operacoes([blocos[0], *primeira_introducao], None, largura, altura) + blocos
