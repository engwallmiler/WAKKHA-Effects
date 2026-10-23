# Grade contínua e confirmação de kicks — versão 0.10

## Aquisição e relógio

A grade local adquire referência com **quatro candidatos aprovados pela análise acústica**, formando três intervalos regulares. O maior desvio de intervalo deve ficar em até 6% da mediana, e o BPM deve pertencer à faixa configurada (90–160 por padrão). Não espera que o PLL fique locked nem exige oito kicks/três segundos de histórico. Sem referência anterior, esses primeiros ataques ainda são uma hipótese acústica, não uma classificação infalível de instrumento.

StructureTracker usa essa aquisição para sair de Aprendendo e formar a referência de groove. No teste sintético a 120 BPM, a aquisição ocorreu em aproximadamente 2,14 s, incluindo o aquecimento do detector e a confirmação de cerca de 120 ms. Isso não garante o mesmo prazo em uma track real.

KickGridSnapshot publica âncora, período, índice, fase, origem da frase, referências e correções. project_grid é a função pura usada pela análise, interface e iluminação. A frase tem **oito tempos do relógio**, agrupados em dois compassos relativos em 4/4. Avança sem kick; o drop redefine a origem da frase. O contador de oito kicks reais do pós-drop é independente.

A grade aprendida continua extrapolando enquanto houver contexto de áudio, sem expirar só pela ausência de kicks. O estado muda para predicting, a confiança heurística decai até um piso operacional de 40% e a incerteza temporal aumenta. Esse piso mantém o relógio utilizável, não representa precisão ou probabilidade garantida. O horizonte publicado é uma janela móvel de 60 s; a previsão +30 s é uma posição matemática possível. Não anuncia a existência futura de kick/drop.

Silêncio sustentado, troca de fonte/formato e descontinuidade reiniciam a referência. Parar a captura congela a visualização e retira a intensidade dos efeitos musicais; dados antigos também retiram luz. O PLL acústico mantém sua expiração configurada (4 s por padrão), seu próprio diagnóstico e suas hipóteses de metade/dobro. A continuidade da grade não altera esse diagnóstico.

## Correção por evidência

Kicks alinhados atualizam um ajuste linear de até 32 referências. Período e fase recebem correção gradual, preservando a posição temporal atual ao mudar o período, inclusive em sessões longas. A janela de aceitação depende do jitter observado, limitada a 18% do período; incerteza acumulada durante uma pausa não alarga a janela até o contratempo.

Desvios grandes não são descartados indefinidamente. Quatro ataques de perfil estrito e intervalos regulares podem confirmar uma nova referência. Correção de fase exige ausência de referências alinhadas por pelo menos três períodos. Uma mudança consistente de BPM superior a 4% pode ser reconhecida mesmo se alguns ataques ainda coincidirem com a grade antiga. Omissões em múltiplos do período não reduzem automaticamente o BPM pela metade.

A correção grande é aplicada uma vez ao ser confirmada e pode deslocar a posição visual dentro do tempo. Não há ajuste por cada candidato isolado. Revision/corrections/last_correction_ms permitem inspeção e reiniciam as janelas pendentes da auditoria sem recontar eventos antigos. Perfil novo ou mudança simultânea de timbre/andamento podem exigir reaprendizado.

## Confirmação acústica e proteção contra basslines

O detector bruto continua independente. KickIdentity compara a distribuição normalizada de 30–250 Hz, o decaimento de 80–130 ms e o ataque harmônico em 250–1500 Hz, subtraindo a potência anterior ao ataque. Após quatro referências, a confirmação normal exige similaridade ≥0,72 e, para referências com queda ≥3 dB, queda mínima de 30% da referência e ao menos 1,2 dB. A proporção harmônica deve ficar abaixo de max(0,04; mediana × 4 + 0,025).

**Alterar a grade exige uma identidade mais próxima**: similaridade ≥0,90, queda entre 85% e 130% da referência quando esta tem queda ≥3 dB (senão diferença ≤2 dB), proporção harmônica abaixo de max(0,02; mediana × 3 + 0,015). Isso impede que a correção temporal, por si só, promova um baixo parecido ao papel de kick. Referências são aprendidas apenas em aquecimento/groove; candidatos rejeitados não mudam o perfil.

A decisão espera aproximadamente 120 ms após o ataque. O timestamp original é preservado; o envelope visual do Pulso por kick começa na confirmação. Kicks fora da grade sem correção aprovada não disparam esse efeito, não avançam o contador pós-drop e não confirmam retorno de kick. A frase temporal continua avançando independentemente deles.

## Visualização e efeitos

Rhythm Monitor mostra uma grade de oito linhas fixas, cursor contínuo e marcas de kicks observados, além de BPM/fase do relógio local. Hipóteses/histórico são identificados como diagnóstico acústico. Stage Preview mostra oito tempos e uma barra de fase contínua, mais contagem de correções e último desvio.

Pulso pelo relógio e Alternância A/B usam a mesma grade quando disponível e recente, incluindo períodos sem kick. Antes da aquisição podem usar o PLL. Pulso por kick continua exigindo evento confirmado. Automação musical conserva baixo/densidade, tensão e oito kicks reais pós-drop. Blackout, manual, master e frescor dos dados continuam prioritários.

KickAudit classifica janelas 200 ms após cada tempo como confirmado, grave rejeitado ou sem kick; não cria eventos. Kick Monitor mantém os candidatos e as contagens separadas. A auditoria acompanha a revisão da grade após correções.

## Traktor e Ableton Link

O Quantize do Traktor mantém saltos entre cues/loops sincronizados; sua referência é o beatgrid da faixa. Aqui a referência é estimada a partir do áudio ao vivo. [Manual do Traktor](https://docs.native-instruments.com/ni-tech-manuals/traktor-pro-manual/en/traktor-overview)

A partir da versão 0.17, Link fornece uma fonte externa de tempo, batida e fase para aplicações participantes. Essa informação alimenta o relógio efetivo da grade e dos efeitos; análise de kicks, densidade e estrutura permanece no áudio. A sessão não equivale à posição absoluta da track ou à identificação do drop. [Conceitos do Ableton Link](https://ableton.github.io/link/)

O Traktor pode exigir alinhamento manual do primeiro tempo; BeatSync ajuda a manter seus decks na linha de tempo Link. [Orientação da Native Instruments](https://support.native-instruments.com/support/solutions/articles/69000879473-how-to-sync-traktor-to-other-applications-via-ableton-link)

**Link está integrado na versão 0.17**, em módulo opcional separado. A página Ableton Link ativa a conexão, mostra participantes/BPM/fase e permite selecionar a fonte efetiva e compensação visual. A perda de participantes ou de amostras recentes retorna ao áudio. O worker nativo usa o SDK via aalink, sem comandos de tempo/transporte. A ativação usa a rede local para sincronismo, sem saída física DMX. Veja [instruções e limites](ableton-link.md).

Na v0.18, a confirmação do retorno alinhado pode usar cerca de 90 ms após ausência longa de kick ou pausa. Candidatos que propõem correção de fase/BPM conservam o perfil de 120 ms. A energia do retorno é comparada com a média do groove e o pico do próprio ataque; veja [drop-detection.md](drop-detection.md).
