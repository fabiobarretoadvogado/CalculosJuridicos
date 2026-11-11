"""Memória dos encargos civis com os estilos compartilhados."""
from collections import defaultdict

from .relatorio_layout import moeda, separar_operacoes, tabela_operacional, distribuir_larguras, indice_memoria


def blocos_memoria_civil_4(memoria, rotulo, largura, p, altura):
    grupos = defaultdict(list)
    for item in memoria:
        grupos[item.parcela].append(item)
    blocos = []
    for numero, registros in grupos.items():
        linhas = [[p(t, "cabecalho") for t in ("Mês", "Encargo", "Base", "Fator do trecho", "Saldo do trecho", "Juros do trecho", "Período e critério")]]
        larguras = [50, 88, 78, 83, 86, 80, largura - 465]
        for m in registros:
            nome = ("SELIC deduzida do IPCA" if "deduzida" in m.indice_aplicado else
                    "SELIC" if "SELIC" in m.indice_aplicado else indice_memoria(m.indice_aplicado))
            linha = [p(m.competencia, "celula"), p(nome, "celula"),
                p(f"R$ {m.valor_base:.4f}".replace(".", ","), "numero"),
                p(f"{m.fator_aplicado:.6f}".replace(".", ","), "numero"),
                p(f"R$ {moeda(m.valor_corrigido)}", "numero"),
                p(f"R$ {moeda(m.juros_periodo)}", "numero"), p(m.observacao.split(";", 1)[0], "celula")]
            linhas.append(linha)
        larguras = distribuir_larguras(linhas, larguras)
        alturas = [max(c.wrap(max(w - 12, 1), altura)[1] for c, w in zip(linha, larguras)) + 8 for linha in linhas]
        introducao = [p(f"Memória dos encargos - {rotulo} - parcela {numero}", "secao_tabela"),
            p("Valores em reais. Termos iniciais incluídos e data-base excluída; base consolidada na transição de 30/08/2024.", "nota")]
        tabela = tabela_operacional(linhas, larguras, alturas=alturas)
        blocos.extend([*separar_operacoes(introducao, tabela, largura, altura), *introducao, tabela])
    return blocos
