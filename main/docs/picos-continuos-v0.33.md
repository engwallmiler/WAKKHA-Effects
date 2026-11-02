# Picos fortes e apresentação contínua — 0.33

Reinicie o programa. Os novos controles ficam em **Pixel Studio → Efeitos e cores → Automação · evolução, compassos e picos**. O botão **CONTÍNUO** também está disponível no palco.

## Experimentar um pico de destaque

1. Escolha **Picos por frase → Sempre ativos**.
2. Selecione a repetição de **4 ou 8 tempos**.
3. Use **Clarão · fita inteira**, **Branco de destaque** e **Intensidade do pico → 100%**.
4. Pressione **Sincronizar pico** no acento desejado. O botão marca esse instante e os próximos ciclos usam essa referência, sem alterar o BPM.

O Clarão agora possui uma camada própria: no máximo, preenche todos os pixels com branco, mesmo que o padrão de base seja esparso ou a resposta da fita seja kick, baixo ou densidade. Não depende de haver kick exatamente no acento previsto; precisa de áudio/relógio válidos ou da demonstração ativa.

O controle vai de **0%, sem alterar a apresentação nem sua preparação**, até **100%, usando o teto disponível**. Brilho mestre, brilho de cada fita e limites da saída USB continuam valendo. O máximo não aumenta esses limites. O acento tem uma sustentação curta para ser visível na saída próxima de 21 fps, depois retorna ao padrão com fade. Há uma redução breve antes do próximo pico para aumentar o contraste; ela acompanha a intensidade escolhida.

Além do Clarão:

- **Onda de impacto:** duas frentes fortes partem do centro e percorrem a fita.
- **Blocos de impacto:** segmentos acendem com força e alternam a cada ciclo.
- **Cores da apresentação:** conserva a cor escolhida/paleta em vez de usar branco. O pico normaliza a força dessa cor para destacar o acento.

**Branco de destaque** é uma sobreposição explícita durante o pico, inclusive sobre uma cor fixa. Fora dele, a apresentação conserva suas cores. No modo **Participação automática**, o pico continua entrando por combinação, em vez de sortear sua participação a cada tempo. Os drops mantêm sua cena própria.

## Fitas preenchidas e fades

Pressione **CONTÍNUO**, ou escolha **Direção visual → Contínua · fitas preenchidas e fades** para AUTO/ORGÂNICO. A apresentação mantém uma base luminosa em todos os LEDs, com energia e tensão suavizadas. Uma resposta de fita previamente configurada como kick, grid ou baixo não apaga essa base entre ataques.

As combinações duram pelo menos **32 tempos**, com uma base conectando as frases e alterações graduais das camadas. Mudanças da estrutura musical continuam tendo prioridade. A velocidade segue a energia se **Velocidade automática** estiver ativada; os drops conservam o impacto próprio.

Há quatro efeitos novos, disponíveis também individualmente na biblioteca e nos controles de cada fita:

- **Banho de cor:** preenchimento com variações lentas de brilho e mistura de cores.
- **Respiração plena:** fades amplos da fita inteira, conservando uma base acesa.
- **Gradiente contínuo:** gradientes percorrem todos os pixels.
- **Cores em fusão:** ondas largas de cor e brilho se misturam suavemente.

Os picos continuam independentes do estilo contínuo. Para uma apresentação somente com fades, escolha **Picos por frase → Desligados**. Cores fixas e o espectro RGB continuam selecionáveis. Os novos controles são salvos no projeto; projetos anteriores recebem os padrões Clarão/Branco para os picos, sem alterar geometria ou conexões.

## Conferência

Prévia e transmissão usam o mesmo cálculo RGB, inclusive em fitas contínuas e cópias exatas. O teste nativo utilizou uma fita emulada de 300 pixels dividida em seis barras, sem abrir uma porta física: níveis 0/25/50/75/100%, Onda/Blocos, base contínua, persistência, minimização, blackout e encerramento. Não prova brilho ou temporização elétrica da instalação real.

[Resultados](resultado-pixel-peaks-v0.33.0.json) · [Clarão no palco](../preview-pico-maximo-v0.33.png) · [Estilo contínuo](../preview-continuo-v0.33.png) · [Validação](validacao.md).

O firmware 0.22 permanece compatível; não é necessário regravar o ESP32.
