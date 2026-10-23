# Estrutura musical e palco — versão 0.18

## Comportamento

A primeira leitura estrutural foi antecipada junto do simulador por solicitação do usuário: o breakdown deve criar tensão na luz; após o drop, a alta energia deve durar oito kicks.

A máquina é causal e heurística. Aprende com um groove já observado, compara a energia dos graves com essa referência, acompanha ataques em médios/agudos e o crescimento do brilho espectral. Não reconhece um instrumento chamado snare nem identifica literalmente um efeito de upfilter. Esses sons podem fornecer os sinais usados pela heurística.

| Estado | Evidências | Luz no modo musical |
|---|---|---|
| Analisando | Janela inicial de 1,2 s de áudio contínuo e pelo menos 12 descritores. Reinicia após silêncio ou descontinuidade. | Base de baixo/densidade; não cria confirmação de kick. |
| Contexto provisório | Groove, breakdown/intro ou build-up provável sem esperar a grade. Histerese de 650 ms; subida inicial exige ataques rápidos e crescimento espectral. Confiança heurística 55%. | Aplica a cena correspondente; ainda não autoriza drop. |
| Groove | Kicks recentes e referência de graves aprendida. | Base de baixo/densidade, pulsos confirmados e movimento conforme atividade. |
| Breakdown | Sem kick por mais de 2,2 períodos (mínimo 1,1 s), graves reduzidos em pelo menos 5 dB e áudio ainda audível. | Respiração de intensidade baixa, preservando espaço para a subida. |
| Build-up | Ataques regulares com crescimento dos agudos/centroide ou aceleração; também roll rápido sustentado acima da referência do groove, mesmo com kicks presentes. | Respiração mais intensa, movimento acelerado com amplitude convergente e cor progressivamente branca conforme a tensão. |
| Drop | Após ausência de kick suficiente, kick confirmado por perfil grave/decaimento e alinhamento na grade junto com recuperação dos graves e aumento de pelo menos 7 dB sobre o breakdown. | Intensidade alta, alternância A/B, acento branco no kick, retorno às cores da paleta e movimento mais amplo/rápido. |
| Silêncio | Energia muito baixa sustentada por mais de 350 ms. | Intensidades zero; pausa breve de build/break preserva o perfil por tempo limitado, e silêncio longo o descarta. |

A grade preditiva e a confirmação estrutural são independentes dos candidatos brutos; veja grid-kicks.md. Previsões não criam eventos. A confirmação observa normalmente cerca de 120 ms de decaimento; no retorno preparado por ausência de cerca de oito tempos ou pausa, pode usar cerca de 90 ms. O timestamp do ataque é preservado.

O primeiro kick do drop conta como 1/8. Refinamentos da intensidade com o mesmo timestamp não contam novamente. A janela mantém alta energia até o nono kick, quando volta ao groove. Não há geração de kicks fictícios pelo relógio. Ausência prolongada de kicks ou dados novos encerra essa energia; uma perda de captura nunca deve deixar o drop preso.

## Rolls rápidos

Os dois envelopes de ataque usam fluxo espectral positivo e crescimento de potência, limiar adaptativo e intervalo mínimo de 40 ms. A detecção exige nova subida após um mínimo local; um único ataque crescente não gera vários eventos. A contribuição energética da banda de médios ajuda a rejeitar vazamento de hats agudos.

O tracker mede repetição em uma janela de 2,5 s, exige regularidade e compara taxa/energia com o groove aprendido. Um roll de médios precisa de pelo menos 4,5 ataques/s e 2,25 ataques por período de kick, superar a referência e persistir por 350 ms após reunir evidência. A regularidade tolera falhas pontuais entre ataques. O contexto precisa mostrar ausência de kick, redução de graves ou aumento do corpo percussivo. Uma virada curta ou percussão que já fazia parte do groove não basta.

Isso permite entrar diretamente de groove em build-up quando o roll aumenta sobre kicks contínuos. Nesse caso, o drop só fica habilitado após uma lacuna suficiente de kicks: um kick comum durante o roll não deve criar um falso drop. Se uma transição real mantiver kicks e graves sem interrupção, ela pode não ser reconhecida como drop. Rolls já rápidos ao entrar no breakdown também podem confirmar build-up sem exigir novo aumento de volume.

## Frases e compassos

O painel mostra oito tempos contínuos da grade e os agrupa em dois compassos relativos de quatro. É uma hipótese de **4/4**, adequada para testar esse padrão de efeitos. A primeira referência adquirida e o drop alinham a contagem relativa. **Não existe detecção automática do downbeat real, da assinatura de tempo nem da posição estrutural absoluta da faixa nesta versão.**

Oito kicks não são uma regra para todos os gêneros, músicas ou trechos. A janela de oito foi adotada para a sequência de efeitos solicitada. Acentos e padrões de 16/32 batidas poderão servir à próxima evolução do módulo, sem alterar o detector de kicks.

## Arquitetura e parâmetros

- dsp/structure_features.py recebe o AudioBlock original, remove DC e usa FFT fixa de 2048/75%, independente do filtro de inspeção e do tamanho de FFT escolhido na GUI. Mede 30–180 Hz, 2–16 kHz, centroide e ataques em 300 Hz–16 kHz, com detector independente em 300–3000 Hz para corpo percussivo. Potências por canal preservam estéreo em oposição de fase.
- music/structure.py recebe StructureFeatures, KickEvent e BeatSnapshot. Não conhece amostras, Qt, luminárias ou DMX. Mantém referências adaptativas e históricos limitados; publica StructureSnapshot e até 24 MusicalEvent.
- O último período confiável organiza limites e movimentos durante o breakdown. Isso não estende a validade nem a confiança do PLL existente.
- AudioAnalyzer isola structure_error e registra falhas uma vez por fonte/formato. Medidores, kicks, BPM e espectro continuam independentes.
- LightingInput acrescenta StructureSnapshot. O efeito musical transforma tensão/estado em FixtureState; a análise não escolhe luminárias.
- StageView recebe somente LightingSnapshot e FixtureDefinition. Desenha fachos, cor, intensidade e uma projeção ilustrativa de pan/tilt. Não processa áudio nem gera efeitos.

A suavização energética usa cerca de 600 ms. A tensão responde suavemente em aproximadamente 400 ms e fica limitada a 95% na subida; no drop chega a 100%. Confiança é um indicador heurístico, não uma probabilidade calibrada. Os limiares estruturais são internos nesta primeira versão; os controles de kicks/BPM continuam sendo os já disponíveis.

O limiar de ataques é atualizado a aproximadamente 20 Hz, mantendo avaliação de ataques a cada hop. A GUI atualiza os painéis musicais visíveis e evita redesenhar tabelas ocultas. Iluminação mantém seu próprio worker de cerca de 60 Hz.

## Movimento, cores e estabilidade visual

lighting/musical.py define perfis por estado. O BPM limita a frequência; energia modula o groove, tensão e força do roll aceleram a subida, e o drop usa o limite configurado. O controle Movimento funciona como limite no modo musical; zero preserva a pose atual. Frequência e amplitude têm suavização de cerca de 220 ms. A fase integra a frequência ao longo do tempo: mudar estado, tensão ou velocidade não reposiciona abruptamente a senoide.

Com Perfil de cores automático, o breakdown usa azul/violeta; o build-up aumenta luminosidade e mistura branco gradualmente, chegando a aproximadamente 97% de branco na tensão máxima. O drop retorna suavemente a vermelho/magenta, preserva acentos brancos por kick e troca as cores A/B após quatro kicks. O perfil Fixo usa as duas cores selecionadas sem clareamento automático. A escolha pode ser feita no palco ou no Lighting Studio e é salva em preferências v7. O master continua multiplicando a intensidade final. LightingSnapshot informa movement_hz e white_mix; o palco exibe esses indicadores.

Os rótulos variáveis têm altura fixa e largura que não impõe o tamanho do layout; motivos completos aparecem também em tooltip. Cards, botões e a faixa da barra de rolagem mantêm dimensões durante as mudanças de estrutura. O palco continua se ajustando quando o usuário redimensiona a janela. As células de frase só recebem novo estilo quando mudam de atividade, evitando repolimento desnecessário em cada quadro.

## Pausas, falhas e prioridades

Blackout, motor desativado e manual têm prioridade sobre o modo musical; o master limita todos os efeitos. Os botões do palco e do Lighting Studio comandam os mesmos estados. Uma troca de efeito não libera blackout.

O modo musical exige fonte em execução, blocos recentes e descritores com menos de 600 ms. Silêncio zera a luz. Um intervalo de aquisição maior que 500 ms é tratado como descontinuidade ao retomar blocos, mesmo que o número sequencial continue: janelas, kicks, PLL e estrutura reaprendem. Isso cobre fontes WASAPI que deixam de fornecer callbacks durante ausência de reprodução.

Breakdowns longos mantêm o contexto; não voltam a aprender apenas porque passaram 60 s. Sem referência de kick/grade, a leitura inicial é provisória e nunca autoriza um drop. Os primeiros kicks válidos continuam alimentando o perfil e a aquisição da grade mesmo que o estado provisório já seja breakdown ou build-up. Ao adquirir quatro ataques regulares na faixa de BPM, o sistema passa ao groove de referência, sem criar um drop de introdução.

## Operação

1. Reabrir iniciar.cmd e capturar a saída usada pelo Traktor.
2. Em Stage Preview, clicar em Usar automação musical e Ativar motor. Também é possível escolher Automação musical · baixo, densidade e kicks no Lighting Studio.
3. Começar em um trecho de groove para aprender a referência; acompanhar estado, tensão, confiança e frase.
4. Observar o breakdown e a subida de tensão antes do retorno do kick. No drop, acompanhar o contador 1/8 a 8/8.
5. Testar blackout e sua liberação; ajustar master/paleta em Lighting Studio.

Sem Traktor, escolher Teste • breakdown e drop no Audio Monitor. O ciclo sintético de 28 s tem groove em 0–8 s, breakdown em 8–12 s, subida em 12–20 s e retorno do kick em 20 s. A alta energia termina em torno de 24 s. **Esse sinal não é reproduzido nos alto-falantes.**

Validação com música real deverá comparar decisões e transições com a audição. Nenhum resultado sintético constitui uma taxa de acerto em faixas reais. O palco é 2D ilustrativo; ainda não há endereçamento, geometria física nem transmissão DMX.

## Camadas da versão 0.9

A confirmação acrescenta a comparação do ataque harmônico e passa a alimentar também Pulso por kick. Kick Monitor apresenta previsão e confirmação separadas. A automação musical conserva uma base contínua de graves/densidade, com controles de peso, mesmo sem kicks confirmados em aprendizagem/groove. Os efeitos dedicados de baixo e densidade não precisam de estrutura aprendida nem BPM. O palco exibe seus medidores em uma linha fixa. Detalhes em audio-multielementos.md e grid-kicks.md.

## Grade contínua — 0.10

A aquisição agora usa quatro ataques regulares, com perfil acústico e faixa de BPM, sem exigir o PLL locked. project_grid projeta índice/fase para estrutura, GUI e efeitos pelo relógio. As frases continuam durante breakdowns sem kicks e reiniciam no drop; os oito kicks pós-drop continuam sendo eventos reais deduplicados. Ausência de kicks aumenta a incerteza sem pausar a grade. Silêncio, fonte/formato e descontinuidade reiniciam o contexto.

Quatro ataques de perfil mais estrito podem corrigir um desvio grande de fase/BPM. Uma bassline que apenas passa pela confirmação normal não recebe automaticamente poder de mover a grade. Contagem de correções e desvio ficam visíveis. Detalhes e limites em grid-kicks.md.

## Relógio Link e classificação na versão 0.17

A classificação de contexto foi separada da confirmação da referência de kick. reference_ready indica que existe perfil/grade acústica aprendido, e timing_source distingue áudio de Link no snapshot efetivo. A confiança provisória é um indicador heurístico; não confirma kick nem posição estrutural absoluta. Sem onsets regulares ou com pouca energia grave, a introdução é tratada como breakdown provável; atividade rítmica com graves favorece groove. Um hi-hat rápido estável, sozinho, não vira build-up: é necessário crescimento espectral inicial.

O Link pode fornecer BPM ao analisador e BPM/fase à grade dos efeitos. A máquina de estrutura e a auditoria de kicks continuam usando eventos acústicos e sua grade interna. O adaptador substitui somente o relógio efetivo exibido/consumido pelos efeitos; não altera estado, tensão, contagem de drop ou os eventos do snapshot original. Os oito kicks pós-drop continuam reais. Instruções: [ableton-link.md](ableton-link.md).

A versão 0.17 também reduz o custo da geração da forma de onda: duas reduções vetoriais preservam os extremos das mesmas partições visuais e substituem centenas de chamadas pequenas por bloco. Isso amplia a margem de tempo do DSP e evita perdas de continuidade que reiniciavam a aquisição estrutural nos ensaios. A redução visual não modifica o sinal, RMS/picos ou os descritores musicais.

## Potência e pausa — v0.18

O retorno exige potência comparável à média de até 16 kicks do groove, congelada no build/break. Kicks fracos em repetição dobrada não disparam o drop nem mudam sua grade. O pico do ataque participa da recuperação dos graves; pausas curtas mantêm a referência com luzes apagadas. O retorno conjunto da melodia tem compensação limitada pelo fundo harmônico aprendido. Critérios, tempos e limites: [drop-detection.md](drop-detection.md).
