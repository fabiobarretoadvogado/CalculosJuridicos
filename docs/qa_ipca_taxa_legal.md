# IPCA e Taxa Legal com datas independentes

Implementação e conferência: 17/09/2026. Perfil público `ipca_taxa_legal_v1`, na categoria Principal e honorários e nos descontos. Os quatro perfis anteriores mantêm sua contagem e regras; a categoria autônoma de redução de dívida não foi ampliada.

## Solicitação e decisão de implementação

Permitir juros desde data anterior à correção monetária, aplicando IPCA e Taxa Legal oficial, em vez de limitar o início dos juros pela data da parcela. Reutilizados o modelo de juros global/individual, o cálculo IPCA do valor da causa e a composição de multa individual, descontos, honorários, cumprimento e custas. Não criados campos, bordas, estilos ou breakpoints novos. Somente neste perfil, o campo interno `data_vencimento` representa o início da correção e recebe essa identificação em tela e nos arquivos.

Os componentes antigos genéricos de Taxa Legal não alimentam este perfil: não usar subtração aritmética de taxas nem substituição por 1% ao mês. O motor e os exportadores usam a série oficial arquivada e memória própria.

## Fontes e metodologia

- IPCA mensal: BCB SGS 433, em `backend/data/ipca_oficial.json`. Consulta direta à API oficial em 17/09/2026 confirmou somente agosto/2026 para a janela agosto/setembro: −0,32%.
- Taxa Legal mensal: BCB SGS 29543, em `backend/data/taxa_legal_oficial.json`, consultada em 17/09/2026, com 26 referências de agosto/2024 a setembro/2026.
- Resolução CMN 5.171/2024: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=5171&tipo=resolu%C3%A7%C3%A3o+cmn
- Metodologia da Calculadora do Cidadão: https://www3.bcb.gov.br/CALCIDADAO/publico/metodologiaCorrigirPelaTaxaLegal.do?method=metodologiaCorrigirPelaTaxaLegal
- Série IPCA: https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=433
- Série Taxa Legal: https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=29543

A Taxa Legal publicada pelo BCB usa a razão dos fatores SELIC e IPCA-15 do mês anterior, com piso zero, e seis casas decimais; não é a subtração direta dos percentuais mensais de SELIC e IPCA. O novo motor aplica essa taxa oficial, juros simples e proporcionalidade diária. Inclui o termo inicial e exclui a data-base, conforme a Calculadora do Cidadão. A mesma janela é utilizada para o IPCA; sua proporcionalidade geométrica diária é premissa expressa do aplicativo, e não afirmação de uma instrução do IBGE.

Os juros incidem sobre o principal corrigido final, conforme art. 7º da resolução, sem juros sobre juros. Somar as taxas mensais proporcionais com precisão integral; aplicar a acumulada arredondada HALF_UP com seis casas e arredondar os valores financeiros ao centavo. Os trechos de juros são diferenças dos juros acumulados arredondados, para conciliar a memória ao total. Não arredondar a base corrigida antes de calcular os juros. Deflações são preservadas.

Não calcular termos anteriores a 30/08/2024 sem outro critério expresso. Índice ausente ou inválido impede conclusão; taxa zero oficialmente publicada é válida. Embora a Taxa Legal de setembro esteja publicada, o IPCA desse mês não está: data-base máxima comum 31/08/2026. Não projetar setembro nem usar SELIC integral adicional.

## Caso fornecido

Fonte preservada: `C:/Users/fabio/Downloads/· Processo Judicial Eletrônico.pdf`, três páginas. SHA-256: `E4E45ACD899522AC568259CDB0E4276494ED8C7A82D996B12C72CC48935B3F35`.

Processo 3005719-41.2026.8.06.0297. Requerente LEONARA LIMA LIBANIO; requerida MOVIDA PARTICIPACOES S.A. Órgão: Núcleo de Justiça 4.0 - Juizados Especiais Adjuntos - CE; comarca não preenchida sem indicação específica. Sentença ID 237259149, assinada em 28/08/2026; a fundamentação identifica a negativação de 02/02/2026 e o dispositivo condena em R$ 5.000,00 por dano moral, com IPCA desde a sentença e juros SELIC deduzido IPCA desde o evento danoso.

As faturas de R$ 3.394,13 e R$ 2.199,00 foram declaradas inexigíveis, não condenações pecuniárias a restituir. Não somadas ao principal. A sentença não impõe custas ou honorários. Não há prova de trânsito, término de prazo para pagamento voluntário, pagamentos, despesas ou contrato de honorários no documento: não incluídos art. 523, astreinte não arbitrada, honorários sucumbenciais ou contratuais, custas ou descontos.

Entrada reproduzível: `backend/examples/processo_3005719-41.2026.8.06.0297.json`. Entrada e resultado integral salvos em `output/calculos/processo_3005719-41.2026.8.06.0297/`. Relatório: `output/pdf/relatorio_3005719-41.2026.8.06.0297_2026-08-31.pdf`.

| Rubrica | Base, período ou índice | Resultado |
| --- | --- | --- |
| Principal | Condenação por dano moral | R$ 5.000,00 |
| IPCA | 28 a 30/08/2026; agosto −0,32%; 3/31 dias | −R$ 1,55 |
| Principal corrigido | Fator 0,9996898741361690016411121676 | R$ 4.998,45 |
| Taxa Legal | 02/02/2026 a 30/08/2026; acumulada aplicada 4,325078% | R$ 216,19 |
| Total em 31/08/2026 | Principal + IPCA + juros, sem outras rubricas | R$ 5.214,64 |

Base integral dos juros: R$ 4.998,449370680845008205560838. Taxas mensais de fevereiro a agosto/2026: 0,962232%; 0,155714%; 0,768672%; 0,198293%; 0,450641%; 0,706607%; 1,154527%. Frações: 27/28 em fevereiro, meses intermediários completos e 30/31 em agosto.

Conferência independente feita na Calculadora do Cidadão, mesmas datas e R$ 5.000,00 sem correção: taxa acumulada 4,325078%, total R$ 5.216,25. Esse resultado verifica somente a Taxa Legal; não é o total do processo, pois a calculadora dessa modalidade não incorpora a correção IPCA independente. Também testado o exemplo oficial de 30 a 31/08/2024: R$ 1.000,00 gera R$ 0,20 em juros, confirmando um dia, e não dois.

## Auditabilidade e apresentação

IPCA e Taxa Legal aparecem em colunas separadas, com datas efetivas, bases, índices e acréscimos. Taxas legais têm seis casas; bases e fatores conservam a escala visual de quatro casas, com precisão integral nas premissas. PDF tem tabela mensal de Taxa Legal por parcela; cada tabela tem um único cabeçalho e continuações com larguras fixas. A tabela principal mantém título, nota, cabeçalho e primeira linha juntos no novo perfil; última parcela e total não são separados.

Excel inclui a aba Taxa Legal e índices por parcela com seis casas nas taxas. CSV inclui `taxa_legal_mensal.csv`; JSON preserva entradas, memória completa e hashes das duas fontes. As memórias ordinárias permanecem disponíveis, sem capitalização ou dupla contagem.

## Validação e pendências

- 18 testes próprios do novo perfil aprovados: datas independentes, critérios global/individual, dia único, janela vazia, juros posteriores, pagamento integral, taxa oficial zero, fonte ausente/inválida, período anterior, IPCA futuro, ordem de multa/desconto/honorários/custas, API, PDF, Excel/CSV, muitas parcelas e cabeçalho não órfão.
- 190 testes dos fluxos relacionados aprovados antes do último teste de paginação; suite completa final: 235 aprovados e quatro falhas preexistentes, listadas abaixo. Nenhuma falha restante pertence ao perfil novo.
- Frontend: 27 testes aprovados; compilação e lint concluídos sem erros. Build em `frontend/dist`, com o novo padrão no catálogo da tela principal.
- Backend final reiniciado e verificado no serviço local: cálculo R$ 5.214,64, período dos juros desde 02/02/2026, data-base máxima 31/08/2026 e exportações PDF, Excel e CSV respondendo. O texto de todas as páginas do PDF devolvido pelo endpoint é igual ao relatório salvo; taxas no Excel com seis casas e CSV mensal próprio confirmados. Preview do build acessível em `http://127.0.0.1:4173/processamento`.
- Conferência visual das 51 páginas renderizadas em PNG, inspecionadas em contatos de páginas: caso real (2), perfil novo com 20 parcelas (9) e 36 parcelas (14); regressão com uma parcela/custas (6), 20 SELIC/CJF (7) e 36/múltiplos componentes (13), incluindo observações e descrições extensas. Logo, formato, cores, margens, cabeçalhos, continuação, totais e rodapés preservados. Encontrado e corrigido cabeçalho órfão no novo perfil, com teste específico.
- Falhas preexistentes mantidas sem alteração de regras fora deste pedido: `test_ipcae_mensal.py::test_deflacao_parcelas_adicionais_sem_nova_correcao_e_pdf` (componentes de perfil interno antigo); `test_perfis_ec136.py::test_selic_ate_ec136_nao_aplica_tema905_ou_poupanca_antes_da_transicao`, `test_inicio_juros_nao_limita_selic_nem_ipcae` e `test_mes_corrente_parcial_nao_e_completo` (expectativas de fixtures EC 136). Não considerar a suite geral integralmente aprovada.
- Automação do navegador indisponível por falha de inicialização/ACL, confirmada após um reset e uma tentativa. Não foi possível inspecionar visualmente a interface nem carregar a entrada do processo na aba aberta. Não alteradas permissões de segurança. Caso calculado e salvo por modelo/API local; conferência visual da tela em largura ampla/móvel permanece pendente.

As regras permanentes foram acrescentadas ao AGENTS.md e a utilização documentada no README.md. O relatório deve ser revisado em conjunto com o título judicial e com dados supervenientes antes de utilização processual; os autos fornecidos não demonstram exigibilidade após trânsito ou intimação.
