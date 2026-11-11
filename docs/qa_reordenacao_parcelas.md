# Reordenação das parcelas

Validação da interface: 30/09/2026. Publicação e instalação: 01/10/2026. Escopo: lista de parcelas da tela Principal e honorários.

**Atualização posterior:** desde a edição 1.19, os números acompanham sequencialmente a posição atual após inclusão, exclusão, importação, recuperação ou reordenação. Os demais campos permanecem vinculados à respectiva parcela. As observações da validação de 30/09 abaixo são históricas.

## Comportamento

- Alça junto ao número, com arraste por eventos de ponteiro, indicação da linha de inserção e rolagem nas extremidades da janela durante o arraste.
- Setas para cima/baixo na alça movem a parcela; Esc, cancelamento do ponteiro e perda de captura encerram o arraste sem confirmar uma nova ordem.
- Na validação histórica de 30/09, a sequência mudava sem renumeração automática; essa regra foi substituída pela atualização descrita acima.
- A reordenação passa pela mesma ação de edição do formulário e invalida o resultado anterior. Movimento sem mudança, limites da lista e soltura fora da área não alteram as parcelas.
- Alça desativada com uma única parcela e durante o cálculo. Instrução e anúncio de posição para leitores de tela.
- Controles e campos mantêm a grade, as cores e os pontos de quebra existentes; alças móveis usam o tamanho mínimo compartilhado de 44 pixels.

## Validação automatizada

- Frontend: 59 testes aprovados, incluindo movimentos nos dois sentidos, conservação da lista original e dos campos, limites e posições de inserção, invalidação do resultado, ordem recuperada e instruções acessíveis.
- Backend: 459 testes aprovados no fluxo oficial de publicação, incluindo os 2 testes novos de ordem. As seis permutações de três parcelas conservam os resultados financeiros e a entrada. A sequência 3, 1, 2 permanece na recuperação pela chave, nas linhas do Excel, nas premissas/índices do CSV e no texto das linhas do PDF.
- Compilação TypeScript/Vite e verificação de código do frontend realizadas.
- O motor e os exportadores financeiros não foram alterados. O teste de PDF verifica a sequência textual; esta alteração não modifica seu layout.

## Conferência no navegador

- Lista vazia, uma parcela com alça desativada e três parcelas preenchidas.
- Arraste para o início e para o fim; soltura fora da lista conserva a sequência; limite superior pelo teclado não move a primeira parcela.
- Lista de vinte parcelas: arraste entre posições e movimento da última até a primeira pelo teclado, com foco e identidade preservados.
- Recuperação de cálculo fictício no armazenamento isolado, cálculo pela interface e desaparecimento do resultado/PDF anterior após trocar a ordem.
- Tela ampla de 1600 pixels e tela móvel de 390 pixels, sem rolagem horizontal. Campos e alças mantêm legibilidade.
- Conferida a apresentação com uma custa adicionada e com custas vazias, nos mesmos componentes existentes.
- A automação do navegador usa mouse/teclado. A largura móvel e o tratamento de ponteiro foram conferidos; não houve simulação de dispositivo físico com toque.

Evidências com dados fictícios: [tela ampla](qa-reordenacao/parcelas-ampla.png) e [tela móvel](qa-reordenacao/parcelas-movel.png).

## Entrega

Publicada a edição **1.14**, versão técnica **2026.9.20.14**, pelo fluxo oficial `publicar.ps1`. Release pública e estável, confirmada como a mais recente: [Cálculos Jurídicos 1.14](https://github.com/fabiobarretoadvogado/CalculosJuridicos/releases/tag/v2026.9.20.14).

- Executável empacotado aprovado no autoteste e na verificação MCP/PDF.
- Publicados exatamente o instalador, seu arquivo `.sha256` e `update.json`. Os tamanhos e hashes fornecidos pelo GitHub coincidem com os arquivos locais. O manifesto público foi baixado sem autenticação e sua assinatura foi conferida com a chave pública vigente.
- Instalador: 46.709.195 bytes; SHA-256 `4cb2c8cdd13bc3e6b46231e0ec8321364cf39ae80670276ae7597942dcfaac0b`.
- Instalação local atualizada para 1.14 pelo instalador oficial. Metadados e versão do executável confirmados; arquivos da interface instalada idênticos aos do pacote validado.
- Autoteste e geração de PDF pela integração também aprovados no executável instalado, com dados fictícios em armazenamento isolado.
- Mantidas somente as pastas de instaladores `1.14` e `2026.9.20.14`, conforme a regra de higiene do projeto.

Registros locais: `build/validacao-publicacao-1.14.json`, `build/instalacao-1.14.log` e `build/validacao-instalacao-1.14/`.
