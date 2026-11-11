# Civil 6 - juros simples anteriores ao Código Civil de 2002

O padrão `civil_6_v1`, exibido como Civil 6, reutiliza o motor do Civil 4 com uma fase própria anterior a 11/01/2003. Está disponível nas parcelas principais, nos descontos e nas operações de comparação de dívidas. Civil 4 e cálculos anteriores preservam suas regras.

- Até 10/01/2003: IPCA SGS 433 desde o termo da correção e juros simples de 0,5% ao mês desde o termo dos juros. A correção pode coexistir com esses juros, que incidem sobre o capital corrigido da fase anterior à SELIC. Os termos permanecem independentes.
- De 11/01/2003 a 29/08/2024: mesmas fases do Civil 4. IPCA quando somente correção; SELIC deduzida do IPCA quando somente juros; SELIC integral quando ambos. Dedução mensal com piso zero e deflação preservada.
- Desde 30/08/2024: mesma consolidação única do saldo total, seguida de IPCA e Taxa Legal oficial simples sobre a base consolidada corrigida, com termos próprios.

Os juros anteriores não são capitalizados mensalmente nem incorporados à base da SELIC em 11/01/2003. Tanto os juros antigos quanto a SELIC incidem sobre o mesmo capital da fase, com os juros antigos segregados até a consolidação de 30/08/2024.

Todos os intervalos incluem o início e excluem a data-base. O corte de janeiro divide o mês pelos dias efetivos: juros de 0,5% até o dia 10 e SELIC desde o dia 11, sem sobreposição. A fração mensal é dias abrangidos divididos pelos dias corridos do respectivo mês, como no Civil 4. Preservar Decimal e arredondamento HALF_UP ao centavo.

A correção começa na primeira competência IPCA disponível; os juros anteriores podem começar em 01/01/1980. Resultados em reais exigem data-base desde 01/07/1994. A janela posterior depende das séries oficiais efetivamente disponíveis; não estimar índices ausentes, usar SELIC parcial nem modificar as bases oficiais.

O novo componente `juros_05am` registra base, taxa acumulada, valor e período. A memória mensal e `memoria_juros_05am` registram taxa, fração, dias, base, juros do trecho e acumulados. A memória de transição inclui os juros antigos e a base da SELIC sem sua capitalização. PDF, Excel e CSV apresentam o novo componente pelos estilos e exportadores comuns, sem nomes internos no PDF. Multas e descontos reutilizam o mesmo perfil em operações autônomas; custas mantêm seu IPCA-E próprio.

O marco de 11/01/2003 corresponde à vigência do Código Civil de 2002. Referências: [Código Civil de 1916, art. 1.062](https://www.planalto.gov.br/ccivil_03/leis/l3071.htm), [Código Civil de 2002, art. 2.044](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm) e [STJ - REsp 1.361.800/SP](https://processo.stj.jus.br/SCON/GetInteiroTeorDoAcordao?dt_publicacao=14%2F10%2F2014&num_registro=201300117194). As convenções posteriores continuam documentadas em [Civil 4](civil_4_temporario.md).

A cobertura automatizada está em `backend/tests/test_civil_6.py` e nos testes de interface: juros anuais simples, proporcionalidade e corte 10/11, termos globais e individuais, correção concomitante, ausência de capitalização na passagem à SELIC, consolidação de 2024, igualdade dos regimes posteriores com Civil 4, índices ausentes, multas, descontos, comparação, recuperação e exportações. São operações e índices fictícios isolados dos cálculos reais.

Em 28/10/2026, passaram os 54 testes dirigidos de Civil 6, Civil 4 e catálogo de perfis, os dois testes novos de interface e a compilação TypeScript/Vite. O ambiente virtual foi reutilizado pelo Python do runtime atual, pois seu executável ainda apontava para um caminho antigo. Os testes com TestClient e Vite exigiram execução fora do sandbox para suas conexões locais. Alteração no projeto local, sem gerar ou instalar uma nova edição do aplicativo.
