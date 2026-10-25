# Arquitetura — versão 0.22

`pixel/usb_protocol.py` define BLP1, CRC32, identificação e configuração de uma saída de 300 WS2812 RGB. `pixel/usb.py` mantém a COM em uma thread, aguarda confirmação e conserva somente o quadro pendente mais recente. A prioridade de blackout pode interromper a espera de confirmação de um frame; falhas encerram a conexão sem reconectar/reativar automaticamente. O emissor é limitado a 30 Hz e descarta amostras com mais de 250 ms.

`ui/pixel_usb.py` amostra `BeatlightPixel.outputFrame(id)` pelo WebChannel do processo local, sem desenhar Canvas. O relógio do motor avança nessa chamada mesmo com a prévia fora da área visível. `computeChannels` é usado tanto pela prévia quanto pela amostragem física, preservando os vinte efeitos e as automações. A identidade selecionada precisa existir como WS2812, 300 LEDs e 300 pixels; não há reamostragem de grupos WS2811. Limites e seleção são salvos em pixel-usb.json, sem ativação/conexão automática.

O firmware em firmware/beatlight_esp32 valida cada pacote completo, aplica limites de brilho/potência e gera WS2812 GRB no GPIO 18. Duplicatas e sequências antigas não atualizam os LEDs; quadros incompletos/corrompidos não renovam o watchdog de 750 ms. Boot, conexão inicial e blackout apagam a fita; o watchdog atua na perda de comunicação enquanto o ESP32 continua energizado. Consulte [esp32-ws2812-usb.md](esp32-ws2812-usb.md), incluindo a limitação ao retirar o USB que alimenta a placa.

`pixel/rendering.py` configura Chromium/Qt Quick para composição por software antes do renderer ser criado. Canvas 2D/WebGL acelerados ficam desativados nessa configuração; a opção não desativa o sandbox. O palco é composto em um Canvas auxiliar e apresentado por uma única cópia, evitando limpar/desenhar parcialmente a superfície visível. A prévia continua limitada a 30 Hz.

O sequenciador do Pixel Studio tem relógio de troca em compassos e relógio de fusão em tempos, independentes dos segundos usados na demonstração. A configuração híbrida é o padrão para projetos antigos sem escolha explícita. Repertórios de breakdown/build-up/groove e a camada de drop acompanham os estados do host. O disparo manual de oito tempos tem prioridade e existe também no cabeçalho Qt, fora da área rolável.

As mensagens musicais incluem `sent_at`; o cliente estima a diferença de base de tempo pela entrega mais rápida observada, compensa a fase e envelhece dados enfileirados. O contador acústico não é alterado. O detector acompanha referências fortes separadas de candidatos fracos acelerados e usa tolerância espectral de até um bin na confirmação; a correção da grade conserva a comparação de timbre completa e estrita.

O foco principal é o **Pixel Studio**, com fitas endereçáveis independentes. A aplicação abre o HTML existente em Qt WebEngine e fornece snapshots musicais via Qt WebChannel. A captura, os detectores, o Link e os painéis anteriores continuam compartilhados; os pixels possuem ativação, blackout e projeto próprios. Uma fita pode ser encaminhada ao ESP32 USB. Consulte [pixel-studio.md](pixel-studio.md).

## Pixel Studio

`pixel/protocol.py` projeta relógio efetivo, kicks confirmados, baixo, densidade e estrutura para mensagens de música; relógio não vira evento de kick. Também valida quadros de pixels com RGB/RGBW de 8 bits. `pixel/project.py` valida geometria e controles de fitas, aplica limites e grava `pixel-studio.json` atomicamente, separado das preferências de áudio v13.

`ui/pixel.py` carrega sob demanda `beatlight/beatlight_pixel_studio.html`, que também integra o pacote como arquivo de dados. O perfil do navegador bloqueia recursos remotos e a ponte expõe operações limitadas a projeto, música e quadros. A porta física é controlada pelo painel nativo e inicia desconectada. A aplicação mantém o nome de dados BEATLIGHT DMX para preservar as preferências existentes.

O motor Canvas conserva os vinte padrões e o editor fornecidos. Controles por fita não dependem do motor anterior de PARs/moves. A análise musical é processada no recebimento; o desenho da prévia fica limitado a 30 Hz, com resolução visual reduzida sem mudar o número de pixels do quadro. A entrada do drop acompanha o estado musical e sua saída acompanha as oito confirmações reais. O sequenciador oferece agenda por N compassos, antecipação por novos elementos, combinação das duas regras e manutenção explícita do padrão.

O aplicativo inicia com fitas desativadas e modo ao vivo. Silêncio, captura parada, dados ausentes por 500 ms e blackout zeram pixels/flashes. Projetos não persistem ativação, pausa, blackout nem seleção de modo ao vivo/demonstração. O fechamento aguarda por até um segundo a confirmação da última edição, sem interromper a limpeza dos runtimes.

## Fluxo implementado

~~~mermaid
flowchart LR
    A[WASAPI Loopback ou fonte sintética] -->|AudioBlock float32| B[Fila limitada]
    B --> C[AudioAnalyzer: medidores, DSP, kicks, Beat Tracker e estrutura]
    C -->|MonitorSnapshot imutável| D[Estado mais recente]
    D -->|QTimer 15 a 60 Hz| E[Interface Qt]
    E -->|Worker de controle| F[CaptureRuntime]
    F --> A
    G[SettingsStore JSON v13] --> F
    A --> H[Logs e diagnóstico]
    C --> H
    L[Traktor / sessão Ableton Link] --> M[LinkRuntime: worker e SDK nativo]
    M --> N[Projeção / seleção de relógio]
    D --> N
    N --> E
    N --> I[LightingRuntime em worker próprio]
    E -->|Comandos imutáveis| I
    I --> J[LightingEngine]
    J -->|LightingSnapshot| E
    E -->|Estados abstratos| K[StageView: palco 2D]
~~~

## Organização e dependências

| Componente | Responsabilidade e contrato |
|---|---|
| contracts.py | Modelos imutáveis e protocolos públicos AudioSource e BlockAnalyzer. Sem Qt/PortAudio. |
| audio/wasapi.py | Encapsula completamente PyAudioWPatch. Descobre saídas, abre float32, cria AudioBlock, verifica dispositivo e fecha recursos. |
| audio/synthetic.py | Gera blocos estéreo determinísticos, inclusive silêncio, com ritmo de entrega real. Não reproduz som. |
| streams/buffer.py | Fila protegida por Condition. Capacidade fixa e descarte explícito do item mais antigo. |
| dsp/meter.py | RMS/pico por canal, silêncio, clipping, continuidade e redução visual min/max. Não recebe widgets. |
| dsp/config.py, filters.py, preprocess.py, spectrum.py, transients.py, pipeline.py | Análise DSP causal, separada da GUI. Veja dsp.md. |
| dsp/kick_config.py, kicks.py | Detector independente da análise visual, com eventos, atividade/limiar e histórico limitado. Veja kicks.md. |
| ui/kicks.py, kick_settings.py | Painel e formulário de kicks, sem processamento de áudio. |
| music/config.py, tracker.py, clock.py | Hipóteses de tempo, PLL, estados e projeção pura do relógio musical. Veja beat-tracker.md. |
| ui/rhythm.py, beat_settings.py | Rhythm Monitor e parâmetros de BPM/manutenção. |
| lighting/config.py, fixtures.py, musical.py, colors.py, engine.py | Configuração, inventário abstrato, efeitos e prioridade de comandos. Sem DSP, Qt ou DMX. |
| core/lighting_runtime.py | Worker independente com adaptação de descritores musicais, cadência, snapshots e estado escuro em falhas. |
| dsp/structure_features.py, music/structure.py | Descritores fixos do áudio original e máquina estrutural causal; publica StructureSnapshot e MusicalEvent. |
| music/grid.py, kick_identity.py | Grade preditiva e confirmação espectral/decaimento dos candidatos estruturais; sem realimentar o detector bruto ou o PLL. |
| sync/link.py | Runtime opcional, snapshots imutáveis, worker asyncio e adaptador nativo aalink; não recebe Qt ou áudio. |
| sync/timeline.py | Projeção do Link no relógio monotonic de aquisição, compensação e seleção pura do snapshot efetivo; não cria kicks. |
| ui/link.py | Painel independente, ativação local, estado e seleção do relógio dos efeitos. |
| ui/stage.py | Palco virtual recebe LightingSnapshot; apresenta estrutura sem calcular música ou efeitos. |
| ui/lighting.py | Lighting Studio: comandos e inspeção, sem geração de efeitos. |
| core/runtime.py | Inicialização, encerramento, análise em worker, captura de falhas, métricas e publicação do último snapshot. Aceita fábrica de analisadores. |
| configuration/store.py | Settings v13, validação, fallback e JSON atômico. Não depende de Qt. |
| diagnostics/logging.py | Logs JSON UTC com contexto e rotação. |
| ui/window.py | Comandos do operador, worker de controle e apresentação do estado. |
| ui/panels.py | Construção dos painéis e formulários. |
| ui/plots.py | Desenho com QPainter; recebe somente dados reduzidos. |
| __main__.py | Composição das dependências, caminhos de dados e ciclo de vida da QApplication. |

NumPy é parte da representação numérica dos blocos. PortAudio e Qt ficam nas bordas. SciPy fornece os filtros SOS causais; sua utilização fica encapsulada no módulo dsp/filters.py.

## Concorrência e propriedade

1. **Callback PortAudio:** interpreta o buffer imutável float32 e entrega à fila. Não executa DSP, I/O de arquivos ou chamadas Qt. Não há espera por capacidade; apenas seções críticas curtas para a fila e contadores.
2. **Worker de análise:** abre a fonte, consome a fila, gera snapshots e fecha a fonte em finally. A mesma thread é dona do ciclo de vida nativo do stream.
3. **Worker de controle:** serializa descoberta, iniciar e parar fora da GUI. Resultados chegam por um Signal Qt, sem alterar widgets no worker.
4. **Verificador WASAPI:** a cada três segundos, redescobre dispositivos usando uma instância PortAudio independente. Reporta remoção e mudança do padrão, sem trocar a fonte automaticamente. Falhas transitórias de descoberta são registradas.
5. **Worker de iluminação:** consulta os descritores publicados, projeta o relógio musical e gera estados de luminárias com alvo de 60 Hz. Comandos são trocados sob lock e snapshots são imutáveis. Não executa processamento de áudio.
6. **Thread Qt:** consulta o último snapshot em frequência configurável. Não recebe amostras individuais nem eventos por bloco. Painéis musicais e tabelas visuais são atualizados quando visíveis, reduzindo a disputa com o DSP.

A fila tem oito blocos por padrão. Ao atingir a capacidade, descarta o mais antigo e incrementa dropped_blocks. Lacunas de sequência, flags de driver e intervalos de aquisição acima de 500 ms incrementam continuity_errors e reiniciam as referências. Um snapshot publicado não é alterado. As amostras usam arrays somente leitura; o buffer de bytes original permanece referenciado pelo array.

Falhas de abertura, callback ou presença do dispositivo encerram a captura e preservam a mensagem de erro. O operador pode atualizar a lista e reiniciar. A fonte sintética é sempre uma escolha explícita; nunca substitui silenciosamente um dispositivo com falha.

Sem blocos, uma saída ainda ativa permanece aberta: WASAPI pode não fornecer dados durante ausência de reprodução. Inatividade, silêncio de blocos e remoção da saída são situações distintas. Não há reabertura automática que possa escolher outra saída sem o operador.

Ao fechar a janela, o worker de iluminação é encerrado e publica intensidades zero; em seguida, a captura é encerrada no worker de controle. A GUI continua processando eventos até o stream e o worker encerrarem. Timeouts impedem abrir uma segunda captura quando o driver ainda está fechando. Chamadas nativas que travem completamente continuam sendo uma limitação: Python não pode cancelar com segurança uma chamada C arbitrária.

## Tempo e métricas

AudioBlock distingue acquired_at e received_at. O adaptador mapeia input_buffer_adc_time do relógio PortAudio para monotonic; se o timestamp não for utilizável, estima o início pelo tamanho/duração do bloco. Essa estimativa é documentada e não equivale a uma calibração de hardware.

MonitorSnapshot possui processed_at, processing_ms e delivery_ms. No pipeline atual, delivery_ms mede a espera desde o recebimento até o início do processamento, separada do tempo DSP. A interface calcula a idade entre aquisição e apresentação e informa a latência reportada pelo driver separadamente. Essa idade não mede o atraso acústico dos alto-falantes nem a resposta de futuras luminárias.

O painel Diagnósticos mostra frequência de atualização efetiva da UI, blocos, descartes, ocupação da fila, falhas de continuidade e tempos do analisador. Não apresenta uma porcentagem fictícia de CPU por subsistema.

## Persistência

Preferências globais, de captura, DSP, kicks, tracker e luz estão em Settings v13. Arquivos v1/v2/v3/v4/v5/v6/v7/v8/v9/v10/v11/v12 são migrados preservando os campos conhecidos de cada versão; novos ajustes recebem padrões. Campos desconhecidos da mesma versão são ignorados; versões futuras são rejeitadas com fallback. Valores, tipos e limites são validados. A escrita usa arquivo temporário no mesmo diretório, flush/fsync e os.replace.

A identidade WASAPI usa nome e ocorrência. Índices são resolvidos novamente antes de abrir o stream. Nomes modificados pelo driver ou duas saídas com nomes iguais podem exigir nova seleção. Uma integração futura com MMDevice poderá usar IDs de endpoint persistentes.

Importação/exportação atual é de preferências do protótipo. Um projeto de iluminação completo terá documento e migrações próprios nas fases correspondentes; não há esquema fictício de cenas nesta versão.

## Evolução dos subsistemas previstos

| Subsistema | Estado e próximo contrato útil |
|---|---|
| Application Core | Implementado para ciclo de captura e GUI. |
| Audio Input Engine | WASAPI e sinal sintético implementados; arquivos/roteamento virtual poderão implementar AudioSource. |
| DSP Engine | Medidores, pré-processamento, filtros, FFT sobreposta, bandas e transientes genéricos implementados. BlockAnalyzer pode ser substituído por fábrica. |
| Music Intelligence | KickEvent/KickSnapshot e BeatTracker implementados. BeatSnapshot publica BPM, fase, previsão, confiança, hipóteses e estados. StructureSnapshot e MusicalEvent implementam groove, breakdown, build-up, drop e silêncio. Frases relativas assumem 4/4; downbeat real continua planejado. |
| Lighting Automation | Motor implementado: dez efeitos, grupos A/B, transições e prioridade blackout/desativado/manual/automação. Editor completo de regras/cenas está planejado. |
| Fixture Management | FixtureDefinition e FixtureState implementados com capacidades, grupos e parâmetros normalizados. Inventário de demonstração fixo; editor e personalidades físicas estão planejados. |
| Visual Simulation | StageView implementado: recebe FixtureState via LightingSnapshot e desenha seis luminárias, fachos e piso 2D. |
| Lighting Output | LightingOutput permanece a borda conceitual para DMX; PixelUsbOutput implementa separadamente a saída física de uma fita WS2812. |
| User Interface | Monitor, análise espectral, kicks, ritmo, Lighting Studio, Stage Preview, diagnóstico e configurações implementados. Demais áreas estão identificadas como próximas fases. |
| Configuration/Projects | Preferências v13 com migração de v1 a v12 implementadas; projetos de iluminação entram com cenas e fixtures reais. |
| Diagnostics/Testing | Logs, métricas, testes isolados e integração sem hardware implementados. |

Art-Net, sACN, USB-DMX, strobe físico e editor completo de cenas permanecem para as fases posteriores. A versão 0.11 inclui um banco de sequências para os PARs no simulador. Antes de qualquer saída física, deverão existir mapeamento de canais, validação de endereços, blackout, política de falhas e limites explícitos para flashes. Captura/DSP, kicks e Beat Tracker foram aprovados pelo usuário no cenário com Traktor e a saída do notebook. O motor inicial também foi aprovado. O usuário avaliou o simulador e a estrutura como relativamente satisfatórios. A versão 0.7 estabiliza o layout, acrescenta evidência de rolls em médios e refina movimento/cor/luminosidade; esses refinamentos têm validação sintética e precisam de nova avaliação com músicas reais. Detalhes do detector estão em kicks.md; FFT, calibração, filtros e transientes estão em dsp.md.

## Referências de implementação

- [Exemplo oficial de WASAPI Loopback do PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch/blob/master/examples/pawp_record_wasapi_loopback.py): descoberta, callback e ciclo de vida PortAudio.
- [QPainter — documentação Qt](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html): renderização nativa dos widgets.
- [QTimer — documentação Qt](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html): atualização periódica na thread gráfica.

## Caminhos DSP independentes

AudioAnalyzer entrega o bloco original ao medidor e a KickDetector. O espectro recebe o resultado de AudioPreprocessor. KickSnapshot e SpectralSnapshot são publicados em MonitorSnapshot, com erros opcionais separados. Nenhum deles faz o medidor depender do sucesso do outro.

O detector mantém filtros/janelas/histórico próprios e elimina referências em descontinuidades. Contagem é da sessão; 16 eventos e 200 pontos são os limites dos snapshots. Eventos refinados são novos objetos imutáveis com o mesmo timestamp. A GUI pode atualizar mais lentamente sem perder a contagem. O Beat Tracker consome os eventos de kick e acrescenta um relógio explícito em BeatSnapshot. O motor inicial consome esses descritores sem alterar os algoritmos musicais. Regras/cenas completas e saídas físicas continuam nas próximas fases.

## Relógio musical

O worker atualiza BeatTracker com eventos deduplicados e o fim temporal de cada AudioBlock. Falha do tracker tem campo beat_error independente. Lacunas e troca de fonte/formato invalidam a referência anterior. O relógio é projetado por project_clock, função pura compartilhada entre análise e GUI; a apresentação pode avançar e expirar mesmo sem callbacks. Ao parar, a UI congela o último resultado.

Nenhum evento prevê downbeat/compasso nesta fase. O contador é relativo à referência adquirida. Históricos e candidatos são limitados; geração de hipóteses roda somente quando chega um kick novo. Configuração, importaçao/exportação e criação do runtime passam os mesmos parâmetros validados de BPM.

## Iluminação abstrata

LightingInput carrega frescor/disponibilidade da fonte, kicks brutos e confirmados, instante da confirmação, BeatSnapshot, StructureSnapshot e TextureSnapshot. LightingEngine gera seis FixtureState normalizados a partir desse contrato, LightingControls e tempo monotônico. Prioridade: blackout, desarmado, manual e efeito automático. Master limita a intensidade final. Transições não atrasam blackout nem a remoção de referência necessária.

LightingRuntime mantém um worker separado do DSP e da Qt. Sem callbacks, efeitos por relógio usam projeção até perder confiança; ao parar captura, automações musicais zeram. Manual/ambiente são escolhas explícitas independentes. Falhas publicam intensidades zero e permitem nova tentativa mediante alteração de comando. LightingSnapshot contém estados, motivo, cadência medida, tempo de processamento, movimento em ciclos/s, mistura branca e nome do perfil de cores. O modo musical suaviza a frequência e integra sua fase; não multiplica o tempo absoluto por velocidades variáveis.

O Lighting Studio é um inspetor. StageView renderiza os mesmos estados, sem calcular efeitos nem música. O modo musical exige descritores recentes; perda de dados e silêncio retiram as intensidades. LightingOutput continua sendo somente a borda de protocolo para futuros adaptadores; nenhum adaptador físico é instanciado. Detalhes em lighting-engine.md.

## Estrutura musical

O extrator estrutural recebe o sinal original, com FFT/bandas fixas independentes da inspeção. StructureTracker recebe descritores, kicks e período confiável; aprende o groove, calcula tensão e confirma retorno dos graves com kick. Os oito kicks do pós-drop são eventos detectados e deduplicados, não batidas sintetizadas pelo PLL. Contagem relativa em 4/4 não equivale à detecção de downbeat. Detalhes, limites e critérios em estrutura-musical.md.

A estrutura publica KickGridSnapshot com janelas previstas, confiança, incerteza, horizonte e previsão +30 s quando utilizável. Kicks confirmados são publicados separadamente dos candidatos brutos. A aprendizagem e a correção da grade usam assinaturas graves e 120 ms de observação; o retorno e os oito kicks do drop também podem usar o perfil transitório de 55 ms. A grade preserva a fase durante o breakdown e rejeita contratempos. A previsão não estende o PLL nem garante kick/drop. Detalhes em grid-kicks.md e drop-detection.md.

## Textura e verificação de kicks — 0.9

O extrator fixo do sinal original publica também 30–250 Hz, 250–1500 Hz e doze bandas logarítmicas. TextureTracker calcula envelope grave, atividade e densidade sem depender de kick/BPM. KickIdentity compara ataque harmônico, perfil e decaimento; StructureTracker aplica a coerência com a grade. KickAudit mantém contagens e classifica tempos previstos após 200 ms sem criar eventos. MonitorSnapshot separa texture_error e kick_verification_error de structure_error. Falhas são isoladas e registradas uma vez; falha do extrator compartilhado invalida seus dependentes.

LightingRuntime envia os kicks confirmados explicitamente; indisponibilidade da verificação envia uma tupla vazia, impedindo substituição por candidatos brutos. Os efeitos dedicados de baixo/densidade continuam com textura recente mesmo se BPM/estrutura falharem. GUI apenas apresenta medidores, classificações e controles. As preferências v7 acrescentam três pesos e a fonte texture_demo, migrando v1–v6. Detalhes em audio-multielementos.md.

## Relógio contínuo — 0.10

KickGrid adquire após quatro ataques regulares aprovados, respeitando BeatConfig. StructureTracker não espera oito kicks nem PLL locked. KickGridSnapshot acrescenta índice, fase, origem de frase, revisão, correções e parâmetros de incerteza. project_grid é uma projeção pura compartilhada; grid_clock oferece um BeatSnapshot de leitura aos consumidores sem realimentar o PLL. Rhythm Monitor, Stage Preview, estrutura e efeitos pelo relógio usam a mesma referência. A frase avança por tempo; o contador pós-drop avança por KickEvent.

O relógio local não expira apenas por ausência de kicks; fica estimado, com confiança decrescente e incerteza crescente. Frescor, silêncio, parada, troca de fonte e descontinuidade continuam tratados pelo ciclo de captura. KickIdentity.correction_matches exige perfil mais estrito para permitir correção da grade; quatro ataques coerentes confirmam mudança grande de fase/BPM. KickAudit reinicia janelas pendentes quando revision muda, preservando contagens deduplicadas. Na versão 0.17, o adaptador Link fornece tempo/fase aos mesmos consumidores, mantendo a auditoria acústica independente.

## Show rítmico — 0.11

lighting/show.py consome grid_clock, estrutura e textura, sem analisar amostras. Mantém padrões relativos de oito tempos, família por compasso, paleta e referência suavizada para aumentos de atividade. Viradas são quantizadas e têm intervalo mínimo; correções e interrupções cancelam pendências. LightingEngine aplica os níveis/cores aos PARs por ordem do inventário e preserva os estados musicais dos moving heads. LightingSnapshot acrescenta padrão, passo, viradas e indicador de novidade. A GUI só exibe os estados, com geometria estável. Settings v7 conserva os mesmos campos e aceita o novo valor rhythmic_show; os efeitos e preferências anteriores continuam válidos.

## RGBW e cenas em camadas — 0.12

FixtureState acrescenta white como canal independente e mantém color como RGB. lighting/rgbw.py transfere o branco comum das paletas ao W, preserva o manual independente e recompõe a cor para o palco. O inventário contém seis pontos RGBW; fixtures legadas RGB seguem aceitas. Blackout, falha e encerramento zeram os quatro canais. Show RGBW acrescenta quatro famílias, variação de 16 tempos, subdivisão por densidade, matiz e acentos W. Settings v8 migra v1–v7 com dois ajustes novos; a exportação usa versão 2 e color_model RGBW. Ver rgbw-show.md para operação, contratos e limites.

## Ciclos de oito e alinhamento visual — 0.13

lighting/phrase_clock.py alinha o ciclo pelo timestamp do clique sem alterar o grid acústico. lighting/phrase.py mantém motivos de oito, troca por novidade na fronteira e preparação global. O engine aplica esse ganho após as transições. Build/drop cobrem os motivos sem descartar uma troca pendente; o drop mantém oito confirmações e usa uma fase inteira por tempo, com saída antecipada apenas em retirada real/silêncio/interrupção. Settings v9 migra v1–v8; comandos de sincronização são da sessão. Ver ciclos-oito.md.

## Coordenação e acesso aos ciclos — v0.14

Após a interpolação das cenas automáticas, o motor coordena os moving heads: intensidade conjunta, RGBW da referência, pan espelhado e tilt igual. A passagem comum cobre todos os efeitos, sem alterar os padrões espaciais dos PARs. Manual conserva seus valores; velocidade zero conserva as posições.

O botão principal do palco seleciona phrase_show. Sincronizar 1/8 valida a captura e a grade recentes, ativa o modo e envia o timestamp em um único comando; a entrada sincronizada não herda o fade entre modos. Contador, motivo e estado do alinhamento aparecem acima do palco.

LightConfig/Settings v10 acrescentam light_phrase_variation (two_cycles/cycle/texture). A contagem avança em fronteiras futuras e não conta uma aquisição parcial. Novidade e prazo coincidentes causam uma única troca. Repetir a sincronização preserva o motivo e reinicia a contagem e o cooldown de novidade na nova origem. LightingSnapshot inclui phrase_pattern e phrase_repetition, inclusive quando uma cena estrutural cobre o motivo. Exportação permanece v2/RGBW.

## Ritmos dos PARs e mudanças de contexto — v0.15

lighting/patterns.py define 20 motivos, incluindo oito articulações em colcheias, e um sorteio que evita repetição recente/família. lighting/novelty.py integra seis descritores em janelas musicais e compara mudanças nos dois sentidos ao contexto anterior. O sequenciador mantém o motivo estável e troca no próximo início de oito. Settings v11 acrescenta sensibilidade de mudança; versões anteriores recebem 1,0.

ShowSequencer escolhe variantes de build nas fronteiras e de drop na entrada, conservando a contagem e os envelopes principais. A projeção de fase do Show cíclico também chega às cenas estruturais. Um clique de sincronização gera acento coletivo curto somente no groove, preservando paleta fixa e prioridades.

Stage Preview apresenta um botão liga/desliga real, seletor compartilhado e ParPatternView que lê máscaras/fase do snapshot. Mostra a confirmação do clique e o motivo da troca sem analisar áudio na GUI. Os moving heads continuam coordenados na passagem comum do engine. Ver ciclos-oito.md.

## Moves, fades calmos e retorno estrito — v0.16

MoverSequencer produz intensidade, RGB e W conjuntos, preservando as posições do motor musical; a coordenação final mantém o espelhamento. BreakdownWash produz luz sustentada e fades lentos independentes do grid, com histerese e mistura por tensão/energia/roll. A prévia usa faixas contínuas no modo calmo. O banco de PARs tem 28 motivos.

Settings v12 acrescenta os seletores de ritmo dos moves e estilo calmo. LightingSnapshot expõe mover_rhythm, breakdown_calm e breakdown_blend; StructureSnapshot expõe rejected_returns.

KickIdentity.return_matches é consultado antes de reconciliar a grade nos estados de retorno. Aceitar um candidato pela triagem normal não basta para criar drop ou reescrever a referência treinada. O perfil inclui contraste de ataque, além de forma espectral, decaimento e relação harmônica. A aquisição em quatro referências e a contagem de oito kicks do drop permanecem. Ver ciclos-oito.md e validacao.md.

## Sincronização externa na versão 0.17

LinkRuntime é independente de CaptureRuntime e LightingRuntime. Todas as chamadas ao SDK pertencem a seu worker asyncio. A GUI e o DSP leem somente LinkSnapshot protegido por lock. A conexão inicia desativada e é encerrada em finally junto com os demais runtimes. A interface não oferece comandos para mudar tempo, beat ou transporte. O Link compartilha o tempo inicial do primeiro participante; o Traktor deve entrar primeiro.

MainWindow publica a seleção/compensação como uma tupla; resolve o mesmo snapshot efetivo para GUI e iluminação. AudioAnalyzer recebe opcionalmente um provedor de BPM externo sem acesso nativo. O snapshot acústico original, KickIdentity e KickAudit continuam independentes. apply_link conserva estado estrutural, tensão e eventos, trocando o relógio e a fase de oito tempos.

A projeção exige pelo menos um participante e amostra recente (até 500 ms, ou até 250 ms anterior à amostra para descritores capturados). Referência inválida retorna ao snapshot por áudio. Revisões de conexão, reposicionamento grande e compensação invalidam o alinhamento visual manual. Não há saída DMX. O protocolo Link usa rede local; as demais saídas permanecem abstratas.

## Evidência de drop — v0.19

music/drop.py mantém a média de potência linear de até 16 ataques e acompanha pausa e cadência dos candidatos, sem controlar o relógio externo. KickIdentity aprende também a forma e o decaimento nos primeiros 55 ms do ataque. No retorno armado, subtrai o fundo sonoro em potência e pode confirmar o mesmo ataque sem aguardar a cauda completa. Uma tentativa rápida incerta permanece pendente até 120 ms; descritores rápidos não alteram o perfil aprendido nem autorizam correção da grade. Um candidato contextual pode recuperar um ataque grave real perdido pelo detector geral, com deduplicação das publicações tardias.

StructureTracker usa a fase do Link fornecida pelo pipeline quando ela é válida. Na previsão acústica após ausência longa, a tolerância de retorno é limitada a 18% de um tempo; a correção da grade continua exigindo evidência completa e consistente. Oito kicks reais continuam sendo contados desde o primeiro impacto, com a análise do transiente também ativa durante essa cena. O transiente forte validado dispensa uma subida global de 7 dB quando o baixo já estava presente. DropEvidenceSnapshot acrescenta a janela de confirmação medida e a indicação de ataque recuperado; o palco usa as linhas de tamanho fixo já existentes. Ver drop-detection.md.
