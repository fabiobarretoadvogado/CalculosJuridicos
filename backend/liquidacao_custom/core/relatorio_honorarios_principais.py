"""Blocos de honorários reutilizáveis pelo demonstrativo principal."""
from .relatorio_layout import separar_operacoes, tabela_operacional, indice_memoria


def blocos_honorarios_pdf(resultado, largura, p, estilos, *, anexos=None, altura=523):
    from .relatorio_pdf import moeda, data_br
    from .exportadores import memoria_exibida
    partes = []
    memorias = partes if anexos is None else anexos

    tabela = tabela_operacional

    h, c, d = resultado.honorarios_sucumbenciais, resultado.cumprimento_sentenca, resultado.destaque_contratuais
    if h:
        bloco = [p("Honorários sucumbenciais", "secao"), p(h.descricao_base + ". Custas e despesas não integram a base.", "nota")]
        if h.base == "valor_causa":
            nomes = ["Valor no protocolo", "Data do protocolo", "Índice / fator", "Correção", "Base atualizada", "Percentual", "Honorários"]
            valores = [f"R$ {moeda(h.valor_original)}", data_br(h.data_protocolo), f"{'IPCA-E' if h.indice == 'ipcae' else 'IPCA'}\n{h.fator_acumulado:.4f}".replace(".", ","), f"R$ {moeda(h.correcao_monetaria)}", f"R$ {moeda(h.base_atualizada)}", f"{h.percentual:.4f}%".replace(".", ","), f"R$ {moeda(h.valor)}"]
        elif h.base == "valor_certo":
            nomes, valores = ["Base", "Valor certo na data-base"], [h.descricao_base, f"R$ {moeda(h.valor)}"]
        else:
            nomes, valores = ["Base atualizada", "Percentual fixado", "Honorários sucumbenciais"], [f"R$ {moeda(h.base_atualizada)}", f"{h.percentual:.4f}%".replace(".", ","), f"R$ {moeda(h.valor)}"]
        estilos_valores = ["numero"] * len(valores)
        if h.base == "valor_causa":
            estilos_valores[1:3] = ["celula", "componente"]
        elif h.base == "valor_certo":
            estilos_valores[0] = "celula"
        bloco.append(tabela([[p(v, "cabecalho") for v in nomes],
            [p(v, estilo) for v, estilo in zip(valores, estilos_valores, strict=True)]], [largura/len(nomes)]*len(nomes)))
        partes.extend([*separar_operacoes(bloco[:-1], bloco[-1], largura, altura), *bloco])
        if h.memoria:
            titulo_memoria = p("Memória da correção do valor da causa", "secao")
            nota_memoria = p("Correção monetária desde o protocolo até a data-base, sem juros. Bases e fatores exibidos com quatro casas; valores finais em reais com duas.", "nota")
            linhas = [[p(v, "cabecalho") for v in ["Mês", "Base", "Índice", "Fator", "Valor corrigido", "Período e cálculo"]]]
            for m in h.memoria:
                linhas.append([p(m.competencia, "celula"), p(f"{m.valor_base:.4f}".replace(".", ","), "componente"), p(indice_memoria(m.indice_aplicado), "celula"), p(f"{m.fator_aplicado:.4f}".replace(".", ","), "componente"), p(moeda(m.valor_corrigido), "numero"), p(memoria_exibida(m.observacao), "celula")])
            larguras_memoria = [58, 92, 146, 70, 90, largura-456]
            tabela_memoria = tabela(linhas, larguras_memoria)
            memorias.extend([*separar_operacoes([titulo_memoria, nota_memoria], tabela_memoria, largura, altura),
                titulo_memoria, nota_memoria, tabela_memoria])
    if c:
        bloco = [p("Cumprimento de sentença", "secao"), p(f"Base comum: crédito das parcelas atualizado após descontos R$ {moeda(c.base_calculo)}. Honorários da sentença, custas e despesas excluídos. Os honorários do art. 523 não incidem sobre a multa do próprio artigo.", "nota")]
        linhas = [[p(v, "cabecalho") for v in ["Rubrica", "Base de cálculo", "Percentual", "Valor"]]]
        if c.aplicar_multa:
            linhas.append([p("Multa - art. 523, § 1º, CPC/2015 (antigo art. 475-J, CPC/1976)", "celula"), p(moeda(c.base_calculo), "numero"), p("10,0000%", "numero"), p(moeda(c.multa), "numero")])
        if c.aplicar_honorarios:
            linhas.append([p("Honorários advocatícios - art. 523, § 1º, CPC/2015", "celula"), p(moeda(c.base_calculo), "numero"), p("10,0000%", "numero"), p(moeda(c.honorarios), "numero")])
        linhas.append([p("TOTAL", "celula"), "", "", p(moeda(c.multa + c.honorarios), "numero")])
        bloco.append(tabela(linhas, [largura-330, 130, 80, 120], total=True))
        partes.extend([*separar_operacoes(bloco[:-1], bloco[-1], largura, altura), *bloco])
    if d:
        bloco = [p("Destaque de honorários contratuais", "secao"), p(d.descricao_base + ". Sem incidência sobre custas ou despesas. Apenas divisão do crédito: não acresce ao cálculo nem reduz a dívida do executado.", "nota")]
        bloco.append(tabela([[p(v, "cabecalho") for v in ["Base do destaque", "Percentual contratual", "Honorários destacados", "Saldo dessa base após destaque"]], [p(v, "numero") for v in [f"R$ {moeda(d.base_calculo)}", f"{d.percentual:.4f}%".replace(".", ","), f"R$ {moeda(d.valor)}", f"R$ {moeda(d.saldo_apos_destaque)}"]]], [largura/4]*4))
        partes.extend([*separar_operacoes(bloco[:-1], bloco[-1], largura, altura), *bloco])
    return partes
