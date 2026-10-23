# BEATLIGHT DMX — 0.19

Aplicação desktop local para Windows 11. A versão **0.19** separa a decisão rápida de drop da aprendizagem do timbre: no breakdown/build-up já armado, analisa os primeiros **55 ms do ataque**, desconta o baixo que já estava tocando e compara o impacto com os kicks do groove. O objetivo é reconhecer o **primeiro kick forte**, sem esperar o kick seguinte. A análise completa de 120 ms continua sendo usada para aprender o perfil e corrigir a grade.

Pratos simultâneos, variações de cauda e um baixo contínuo passam por uma análise do transiente acima do fundo sonoro. Um caminho de recuperação procura ataques reais que o detector geral tenha perdido. Com Link selecionado e válido, a fase externa valida a entrada; ela não precisa esperar a realocação da grade acústica. Kicks fracos em ritmo dobrado continuam comparados com a potência do groove, e pausas breves preservam a referência com as luzes apagadas. **[Critérios e limites do detector de drop](docs/drop-detection.md)**.

A leitura inicial de contexto após 1,2 s, a otimização do áudio e o módulo separado de **Ableton Link** continuam disponíveis. Link fornece BPM/fase à grade e ao show de oito tempos; kicks, baixo, densidade e estrutura continuam no áudio. **[Instruções para Traktor e Ableton Link](docs/ableton-link.md)**.

## Abrir e testar

Feche a versão anterior e dê dois cliques em **iniciar.cmd**. O Python **3.12.10** e as dependências, incluindo SciPy, já estão preparados em **.runtime/python312** neste computador. Depois da instalação inicial, a aplicação funciona offline.

1. No **Audio Monitor**, selecione **WASAPI Loopback** e a saída Realtek utilizada pelo Traktor.
2. Reproduza uma faixa no Traktor em **WASAPI compartilhado** e clique em **Iniciar captura**.
3. Abra **Stage Preview**, deixe **Show de 8 · LIGADO** e clique em **Ativar motor**. Isso escolhe **Show cíclico · 8 tempos**. O botão é liga/desliga; desligado seleciona o show contínuo anterior. Após adquirir a grade por áudio ou conectar o Link, clique em **Sincronizar 1/8** no primeiro tempo musical desejado. No groove, os quatro PARs recebem um acento curto (branco em cores automáticas), e o painel confirma **SINCRONIZADO**. A grade de quatro linhas mostra os disparos de cada PAR nas duas colcheias de cada tempo. O sincronismo também ativa esse modo se outro efeito estiver selecionado. O show anterior continua no seletor do Lighting Studio; **Usar automação musical** fica ao final do palco.
4. A leitura inicial de contexto aparece após 1,2 s de áudio contínuo, com confiança provisória. Quatro ataques regulares na faixa de BPM confirmam a grade acústica e permitem aprender a referência para drops. Com Link conectado, a grade dos efeitos já recebe o relógio externo. Acompanhe **breakdown → build-up → drop**. A luz cria tensão na subida e mantém alta energia por oito kicks após o drop.
5. Marque **Cores automáticas** no palco ou escolha **Perfil de cores → Automático · acompanha o áudio** em Lighting Studio. Breakdown usa azul/violeta; a subida clareia até branco; o drop retorna a cores saturadas com acentos brancos. No Show RGBW, a matiz também evolui nos tempos da grade. **Fixo** usa a paleta escolhida. Salve em **Salvar preferências de luz**.
6. Em Lighting Studio, selecione **Show RGBW · cenas em camadas** para sequências com maior contraste. Compare também os efeitos **Linha de baixo · envelope dos graves**, **Densidade sonora · distribuição dos fachos** e **Automação musical · baixo, densidade e kicks**. Ajuste os pesos de kicks (70%), baixo (65%) e densidade (50%), além de intensidade geral, pulso, transição e movimento. No modo musical, Movimento limita a velocidade automática; zero congela a posição. BPM, energia e tensão modulam a velocidade. A luminosidade respeita o master.
7. Teste **Controle manual** e **Blackout**. Blackout permanece ativo ao trocar efeito e zera intensidades até ser liberado.
8. **Rhythm Monitor** mostra a grade contínua, BPM, fase, confiança e próximas batidas, inclusive sem kick. Hipóteses e histórico acústicos permanecem como diagnóstico.
9. **Kick Monitor** distingue candidatos graves, kicks confirmados e tempos previstos sem kick; mostra as rejeições, o grid e a classificação dos eventos. **Pulso por kick** agora recebe somente os kicks confirmados.
10. **Análise espectral** continua mostrando frequências, bandas e transientes genéricos.
11. Use **Parar** antes de mudar a saída ou os ajustes.
12. Em **Configurações → BPM e sincronização**, ajuste a faixa preferida e o tempo de manutenção sem referência. Clique em **Salvar ajustes** e reinicie a captura.
13. Em **Configurações → Detecção de kicks**, ajuste sensibilidade, banda grave, intervalo mínimo e piso de energia. Clique em **Salvar ajustes** e reinicie a captura. Os parâmetros FFT e filtros do espectro continuam disponíveis.

No novo modo, selecione **Padrão do ciclo de oito → Automático** e ajuste **Variação automática**: somente com novos elementos (padrão), repetir dois ciclos de oito e mudar ou mudar a cada ciclo. A troca ocorre no tempo 1; uma nova camada pode antecipá-la para o próximo ciclo. O seletor **Ritmo dos PARs** no palco compartilha os 28 motivos com Lighting Studio. Compare também Cometa, Galope, Trançado, Órbita, Abertura em leque e Ecos de pares. Compare **Síncope**, **Contratempos**, **Pulso duplo**, **Cortes rítmicos**, **Saltos** e **Escada com pausas**, além dos desenhos anteriores. Os padrões fixos respeitam a escolha; Automático sorteia na troca, evitando a mesma família e os motivos recentes. **Antes de cada ciclo** oferece Fade-out rápido, Apagão breve e Sem preparação; a duração padrão é 140 ms.

Em Lighting Studio, **Ritmo dos moves · sempre juntos** oferece automático, pulso com acentos, pulso duplo, contratempo, sustentação de quatro tempos, ondas de oito tempos, síncope, respiração do baixo e cortes/sustentação. **Cores automáticas** permite a rotação de matiz e acentos W; paleta fixa preserva as cores escolhidas. Pan/tilt e espelhamento continuam como antes.

**Breakdown calmo** oferece quatro estilos suaves, usados automaticamente quando energia/tensão/roll estão baixos. A grade continua contando, enquanto os PARs sustentam luz e fazem fades de cerca de 6–14 s, sem disparos rápidos por tempo. Uma subida real retorna gradualmente à cena de tensão; build e drop mantêm prioridade.

Em Lighting Studio, **Sensibilidade às mudanças do áudio** vai de 50% a 200% (padrão 100%). Aumentar facilita a troca; reduzir exige alterações maiores. O detector compara médias de um tempo com o contexto anterior, em ambas as direções, e descarta ataques isolados. **Variedade do show** controla o banco usado no sorteio.

Em Lighting Studio, ajuste **Uso do canal W** (redistribuição do branco entre RGB e W) e **Variedade do show**. Para criar uma cor manual, marque **Assumir controle manual → Escolher canais R/G/B/W manualmente** e ajuste os quatro canais. A tabela mostra a cor aparente, W e o RGBW exato no tooltip; JSON de estados usa **version 2 / color_model RGBW**.

Os parâmetros de luz são salvos em **Lighting Studio → Salvar preferências de luz**. O motor começa desativado ao abrir, preservando apenas os parâmetros; ativação, manual e blackout pertencem à sessão. Os moving heads acendem juntos, usam a mesma cor e fazem pan espelhado com tilt coordenado nos efeitos automáticos; a alternância espacial continua nos PARs. O inventário tem **4 PARs RGBW + 2 moving heads RGBW** e os estados são abstratos. O palco é uma projeção 2D ilustrativa. **Ainda não há saída física DMX.**

Rhythm Monitor, Kick Monitor e Análise espectral têm botões **Iniciar**, **Parar** e **Selecionar entrada**. O painel continua mostrando o último resultado, identificado, depois de parar a captura.

Loopback monitora a mixagem da saída, incluindo outros aplicativos. ASIO nativo da Kontrol S4 MK2 não é capturado. A captura não altera a reprodução e não salva áudio bruto.

Para testar baixo e densidade, selecione **Teste • baixo e densidade**: o ciclo de 24 s tem kicks em 0–6 s, bassline sem kick em 6–18 s, entrada de camadas em 12 s e retorno dos kicks em 18 s. No Show RGBW, observe as trocas após entrada do baixo e camadas; no Show cíclico elas ocorrem no próximo 1/8.

Para testar a sequência estrutural sem Traktor, selecione **Teste • breakdown e drop** no Audio Monitor: o ciclo de 28 s aprende o groove, entra no breakdown, acelera a subida e retorna com kick em 20 s; a alta energia termina em torno de 24 s. Para o teste rítmico simples, selecione **Teste • sinal sintético** ou execute:

~~~bat
iniciar.cmd --synthetic
~~~

O sinal contém componentes graves, médios e agudos e não é reproduzido pelos alto-falantes. É identificado como teste e não comprova desempenho com música real.

## Ableton Link

Abra a página **Ableton Link**. No Traktor, ative LINK, use **BeatSync** e **SYNC** no deck. No BEATLIGHT, clique **Ativar Ableton Link**, aguarde pelo menos um participante e marque **Usar Link como relógio**. Inicie também a captura de áudio. Para marcar o começo desejado do ciclo visual de oito tempos, use **Sincronizar 1/8**. O módulo opcional já está preparado no Python portátil; em outro ambiente, execute **instalar-link.cmd**. Consulte o [guia completo](docs/ableton-link.md), incluindo rede, compensação, limites e diagnóstico independente.

## Implementado

- Interface nativa PySide6 com Ableton Link, Audio Monitor, Análise espectral, Kick Monitor, Rhythm Monitor, Lighting Studio, Stage Preview, Diagnósticos e Configurações.
- Descoberta WASAPI, saída padrão, seleção, captura float32, início/parada e recuperação manual de falhas.
- Forma de onda estéreo, RMS, pico, silêncio, clipping, perdas e continuidade.
- FFT incremental por canal, janela Hann, sobreposição e 96 colunas logarítmicas.
- Energia RMS e participação percentual de graves, médios e agudos; frequência dominante na resolução da FFT.
- Remoção opcional de DC e filtros causais passa-baixa, passa-alta e passa-banda, com estado entre blocos.
- Banco de filtros reutilizável e operações explícitas de mono/normalização controlada.
- Transientes genéricos por fluxo espectral e ataque energético, limiar adaptativo e confiança heurística.
- Detector de kicks com banda independente, ataque, fluxo grave, contraste adaptativo, intervalo mínimo e apoio de regularidade observado.
- Histórico visual de atividade/limiar, eventos recentes e força relativa refinada pelo pico.
- Beat Tracker por hipóteses temporais e PLL, com aquisição, sincronismo, manutenção estimada e expiração.
- BPM/fase/próxima batida, hipóteses de metade/dobro e histórico de andamento.
- Motor de iluminação independente, com dez efeitos e estados normalizados para seis luminárias abstratas.
- Show cíclico de oito tempos: motivos que se repetem, variação programada ou por textura na fronteira, sincronização pelo clique e preparação global de todos os pontos.
- Drop mantém oito kicks confirmados; uma falha de confirmação sem retirada dos graves não encerra a cena. Pulsos do drop usam um passo por tempo.
- Show RGBW: dez famílias, incluindo cruzamento, onda, pergunta/resposta e perseguição dupla; variações a cada 16 tempos, subdivisões e acentos W. O Show rítmico anterior permanece no seletor.
- Canal W independente em todos os pontos; mistura preserva a cor aparente das paletas. Controles manuais R/G/B/W, novas paletas e ajuste de complexidade.
- Grupos A/B, cores, pan/tilt, transições, controle manual, master e blackout prioritário.
- Lighting Studio com inspeção, parâmetros em tempo real e exportação de estados JSON.
- Análise estrutural com referência de groove, breakdown, build-up, tensão, drop, silêncio e histórico de eventos.
- Rolls rápidos em médios com comparação ao groove aprendido, inclusive durante a continuidade dos kicks.
- Movimento automático com fase contínua, cor progressivamente branca no build-up e alternância da paleta após quatro kicks no drop.
- Grade temporal independente para a estrutura, com previsão limitada, confiança e incerteza; contratempos não realinham a grade aprendida.
- Confirmação de kicks por perfil grave, decaimento, ataque harmônico e coerência com o grid; usada na estrutura e nos pulsos, sem prolongar o PLL.
- Envelope dos graves e atividade de baixo independentes do BPM; densidade por ocupação espectral e taxa de ataques.
- Dois novos efeitos, três pesos musicais persistidos e medidores de graves/densidade no palco.
- Perfil de cores automático ou fixo, compartilhado entre palco e Lighting Studio e salvo nas preferências.
- Frase relativa de oito tempos do grid, agrupada em dois compassos assumindo 4/4; avança sem kick e reinicia no drop.
- Aquisição em quatro ataques regulares e correção de fase/BPM após evidência consistente com perfil estrito.
- Grade contínua compartilhada pela análise, visualização e efeitos pelo relógio, independente da expiração do PLL acústico.
- Stage Preview com fachos, cores, intensidade, pan/tilt, confiança e controles compartilhados; layout estável nas mudanças de estado.
- Captura, análise, controle de dispositivos e GUI desacoplados, com fila limitada e descarte de blocos antigos.
- Preferências JSON **v13**, com migração automática de **v1 a v12**, validação, escrita atômica e importação/exportação.
- Logs estruturados com rotação e exportação de diagnóstico.

A FFT padrão usa **2048 amostras e 75% de sobreposição**. Em 48 kHz, isso representa janela de 42,67 ms, passo de 10,67 ms e resolução de 23,44 Hz. Aumentar a FFT melhora a resolução em frequência e aumenta o tempo para preencher a janela.

Os filtros escolhidos para o espectro não alteram os medidores nem o detector de kicks. Este usa seus próprios parâmetros. Transientes genéricos e kicks aparecem em painéis separados. A confiança do kick é heurística; baixos com ataque e outras fontes graves percussivas podem causar confusão. O Beat Tracker consome kicks sem alterar o detector. A nova análise estrutural também usa descritores independentes do sinal original. A frase de oito tempos assume 4/4; o downbeat real ainda não é detectado.

O detector usa 40–150 Hz, sensibilidade 1,0 ×, intervalo mínimo de 180 ms e piso de −60 dBFS por padrão. Aguarde cerca de 300 ms para o aquecimento. A força é relativa ao histórico e pode ser refinada nos 90 ms após a detecção, sem criar outro evento. Captura/DSP, kicks e BPM/PLL foram aprovados pelo usuário no cenário com Traktor e a saída do notebook. O motor inicial também foi aprovado. O usuário avaliou a primeira análise estrutural como relativamente satisfatória e relatou instabilidade visual e um roll não detectado. As mudanças de grade da versão 0.10 foram avaliadas como satisfatórias pelo usuário. O RGBW foi avaliado positivamente pelo usuário. Os moves, fades calmos e proteção de drop da versão 0.16 têm validação sintética e precisam de avaliação com faixas reais. A detecção é heurística e não identifica snares/upfilters individualmente.

Baixo é medido como energia de 30–250 Hz, incluindo a contribuição do kick; não há separação de instrumentos. Densidade é preenchimento espectral e atividade, não contagem literal de elementos. Os efeitos dessas camadas funcionam sem kick confirmado ou BPM sincronizado.

A grade estrutural prevê **janelas onde um kick caberia**, incluindo uma janela matemática cerca de 30 s à frente. Confiança decai e incerteza cresce durante a ausência de referências, mas a grade continua extrapolando enquanto houver contexto. Ela não sabe quais tempos o arranjo preencherá nem conhece a posição da faixa no Traktor. O drop exige um ataque acústico, potência comparável ao groove, perfil transitório e alinhamento musical. A decisão rápida usa 55 ms; uma tentativa ambígua continua até a análise completa de 120 ms do mesmo ataque. Esses valores são janelas de análise, e a latência total também inclui captura, FFT e apresentação. O pulso visual começa na confirmação para preservar sua intensidade. Baixos muito semelhantes a kicks ainda podem confundir.

O tracker acústico prioriza **90–160 BPM** e mantém previsão por até **4 segundos** sem kick alinhado. A grade contínua usa a mesma faixa de BPM, adquire após quatro ataques regulares e continua independentemente dessa expiração. No PLL, a confiança cai durante a manutenção e sua referência expira. Metade/dobro aparecem como hipóteses explícitas. A contagem de batidas é relativa e não identifica início de compasso.

Uma saída sem reprodução pode não entregar blocos WASAPI. O aplicativo mantém a captura aberta e informa que está aguardando dados. A presença do dispositivo é verificada separadamente. Ao retomar após uma lacuna de aquisição superior a 500 ms, as janelas e referências musicais são reiniciadas. Em fontes multicanal, os medidores visuais apresentam os dois primeiros canais; a análise espectral considera todos.

## Instalação em outro computador

Instale Python **3.12 x64** e execute **instalar.cmd**. O ambiente padrão é **.venv312**; iniciar.cmd o utiliza quando contém Python 3.12 e as dependências necessárias. Caso contrário, usa o runtime portátil preparado.

~~~powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv312\Scripts\python.exe run.py
~~~

Se já tiver instalado uma versão anterior em .venv312, execute instalar.cmd novamente para adicionar SciPy e atualizar o pacote. Para reproduzir as versões validadas no Windows/Python 3.12, use requirements-windows-py312.lock.txt e instale o pacote com --no-deps.

O runtime portátil e ambientes locais são ignorados pelo Git. O VS Code está configurado para o runtime preparado neste checkout; em outra instalação, selecione .venv312/Scripts/python.exe.

## Testes e diagnóstico

~~~powershell
.\.runtime\python312\python.exe -m pytest -q
.\.runtime\python312\python.exe scripts\render_preview.py
.\.runtime\python312\python.exe scripts\validate_synthetic.py --seconds 12
.\.runtime\python312\python.exe -X utf8 scripts\validate_lighting.py --seconds 12
.\.runtime\python312\python.exe -X utf8 scripts\validate_structure.py
.\.runtime\python312\python.exe -X utf8 scripts\validate_stage.py
.\.runtime\python312\python.exe -X utf8 scripts\validate_grid.py
.\.runtime\python312\python.exe -X utf8 scripts\validate_texture.py
.\.runtime\python312\python.exe -X utf8 scripts\validate_phrases.py structure_demo
.\.runtime\python312\python.exe -X utf8 scripts\validate_phrases.py texture_demo
.\.runtime\python312\python.exe -X utf8 scripts\validate_phrases.py synthetic
.\.runtime\python312\python.exe -X utf8 scripts\validate_show.py structure_demo
.\.runtime\python312\python.exe -X utf8 scripts\validate_show.py texture_demo
.\.runtime\python312\python.exe scripts\validate_loopback.py --device Realtek --seconds 30 --cycles 3
~~~

Os testes automatizados não exigem Traktor nem hardware. A ferramenta Loopback não reproduz som e retorna **0** quando recebeu blocos sem falha, **1** em falha de captura/análise e **2** quando não recebeu blocos e o resultado é inconclusivo. Um resultado com silêncio não comprova a captura de uma faixa do Traktor.

A renderização de QA produz preview.png, preview-espectro.png, preview-kicks.png, preview-ritmo.png, preview-iluminacao.png, preview-palco.png e preview-configuracoes.png com dados sintéticos. validate_stage.py acrescenta preview-breakdown.png, preview-buildup.png e preview-drop.png. validate_texture.py acrescenta preview-baixo.png e preview-densidade.png. validate_grid.py acrescenta preview-grid.png. validate_phrases.py acrescenta preview-cycles-*.png e mede as oito posições do drop, sincronização e preparação. validate_show.py acrescenta preview-rgbw-*.png. render_rgbw.py captura os controles manuais e a inspeção de W. A validação atual tem **626 testes aprovados**; veja docs/validacao.md.

Preferências e logs ficam no diretório local de dados WAKKHA/BEATLIGHT DMX, sob %LOCALAPPDATA%; Configurações mostra o caminho completo. Logs: logs/beatlight.jsonl, com rotação em 2 MB e três cópias. Também é possível utilizar outro diretório:

~~~powershell
.\.runtime\python312\python.exe run.py --config-dir .runtime\userdata
~~~

As preferências são salvas ao fechar. **Salvar ajustes** persiste e aplica os parâmetros DSP imediatamente para a próxima sessão. Parâmetros inválidos mantêm os ajustes anteriores e produzem uma mensagem.

## Documentação e próximos passos

- **docs/drop-detection.md**: potência do kick, aceleração do build, pausa e critérios de retorno.
- **docs/ableton-link.md**: instalação, Traktor/BeatSync, fonte de relógio, compensação e diagnóstico independente.
- **docs/ciclos-oito.md**: motivos de oito tempos, sincronização, preparação e correção do drop.
- **docs/validacao-v0.12.md**: histórico do RGBW e das cenas em camadas.
- **docs/rgbw-show.md**: canais RGBW, manual, complexidade e novas cenas.
- **docs/validacao-v0.11.md**: histórico do primeiro Show rítmico.
- **docs/show-ritmico.md**: padrões, viradas, integração das camadas e operação.
- **docs/validacao-v0.10.md**: histórico da grade contínua e frases sem kicks.
- **docs/audio-multielementos.md**: envelope grave, densidade, pesos e novos efeitos.
- **docs/grid-kicks.md**: grade preditiva, confirmação de kick, horizonte, confiança e limites.
- **docs/estrutura-musical.md**: critérios de breakdown/build-up/drop, oito kicks, palco e limites.
- **docs/lighting-engine.md**: efeitos, prioridades, worker e operação.
- **docs/beat-tracker.md**: estimação de BPM, PLL, estados, configuração e limites da fase 5.
- **docs/kicks.md**: algoritmo, ajuste e limites da fase 4.
- **docs/dsp.md**: algoritmos, calibração, configurações e limites da fase 3.
- **docs/arquitetura.md**: componentes, concorrência e contratos.
- **docs/validacao.md**: resultados atuais e roteiro de validação com música real.
- **docs/validacao-v0.9.md**: histórico dos efeitos por baixo/densidade e confirmação dos pulsos.
- **docs/validacao-v0.8.md**: histórico da grade preditiva, confirmação estrutural e cores.
- **docs/validacao-v0.7.md**: histórico da estabilidade visual, rolls e perfis de movimento.
- **docs/validacao-v0.6.md**: histórico da primeira análise estrutural e do palco.
- **docs/validacao-fase6.md**: histórico da validação do motor inicial.
- **docs/validacao-fase5.md**: histórico da validação de BPM/PLL.
- **docs/validacao-fase4.md**: histórico da validação de kicks.
- **docs/validacao-fase3.md**: histórico da validação DSP.
- **docs/validacao-fase1-2.md**: histórico da fundação e captura.
- **docs/especificacao-original.md**: requisitos fornecidos.

Ableton Link está disponível como fonte externa de BPM/fase, com retorno ao áudio quando indisponível. Configuração e limites: [docs/ableton-link.md](docs/ableton-link.md).

Próximas etapas: refinar a estrutura com as músicas reais, analisar acentos/downbeat e ampliar cenas/regras. Endereçamento de fixtures e saídas DMX continuam nas fases posteriores da especificação.

O arquivo vazio originalmente chamado main continua preservado ao lado do projeto como main.original.empty.
