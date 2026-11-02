# Sair do contínuo e usá-lo ocasionalmente no AUTO — 0.35

Reinicie a aplicação. O botão passou a se chamar **CONTÍNUO FIXO** para distinguir o modo mantido pelo operador dos trechos escolhidos pelo automático.

## Sair do contínuo fixo

Você pode:

- pressionar **AUTO SHOW** para voltar à apresentação automática regular;
- pressionar **ORGÂNICO** para voltar às combinações orgânicas regulares;
- pressionar **CONTÍNUO FIXO** novamente para voltar ao AUTO SHOW.

A saída usa a fusão musical configurada, então a mudança visual acontece gradualmente. O botão de destino fica selecionado imediatamente. A direção regular anterior, Hipnótica ou Variada, é restaurada e guardada no projeto.

Projetos antigos que ficaram salvos como AUTO com direção Contínua passam a abrir como AUTO regular. Se não havia registro da direção anterior, o retorno usa Hipnótica. Um projeto salvo deliberadamente em contínuo fixo continua podendo ser aberto nesse modo e sair pelos botões acima.

## Contínuos esporádicos no AUTO SHOW

Em **Efeitos e cores → Automação → Contínuos no AUTO SHOW**, escolha **Esporádicos entre padrões**. A opção vem ativada por padrão nos projetos antigos.

O AUTO intercala um trecho contínuo depois de duas a quatro combinações regulares, com escolha variável dentro desse intervalo. Cada trecho contínuo dura pelo menos **32 tempos** e depois volta a um padrão regular. Não há dois trechos contínuos automáticos seguidos. As transições usam os fades existentes; não há sorteio a cada kick.

Na tela aparece **AUTO SHOW · CONTÍNUO OCASIONAL**, enquanto o botão AUTO SHOW continua selecionado. CONTÍNUO FIXO fica desligado: isso indica que o trecho vai terminar automaticamente.

Os contínuos ocasionais participam de groove, breakdown e demonstração. Build-up e drop conservam seu repertório próprio; mudanças de estrutura podem antecipar a troca. A direção Variada mantém seu mínimo de 16 tempos nos padrões regulares e usa pelo menos 32 nos contínuos ocasionais.

Para desativar a participação, escolha **Não participar**. Se um trecho contínuo automático estiver em andamento, ele sai com uma fusão. Para antecipar a saída para um padrão regular, também pode pressionar AUTO SHOW novamente.

As regras de troca continuam valendo: **Manter padrão** não troca por tempo, e **Somente novos elementos** depende de mudanças no áudio. Para alternância periódica, use **Compassos + novos elementos** ou **A cada N compassos**. Efeitos individuais definidos nas fitas continuam tendo prioridade sobre o padrão global; escolha **Herdar** nas fitas que devem acompanhar o show completo.

## Validação

O teste nativo exerceu os três caminhos de saída, a seleção exclusiva dos botões, 18 combinações do AUTO com três entradas contínuas, preenchimento dos 300 pixels nos contínuos, persistência, transmissão minimizada e zero no blackout/fechamento. A serial foi emulada; não abriu ESP32 real.

[Relatório](resultado-auto-continuous-v0.35.0.json) · [Volta ao AUTO](../preview-auto-retomado-v0.35.png) · [Contínuo ocasional](../preview-auto-continuo-ocasional-v0.35.png) · [Validação completa](validacao.md).
