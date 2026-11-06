# Confiabilidade e operação prolongada — 0.41.0

Esta rodada corrige gargalos identificados no código e acrescenta um ensaio repetível. Ainda não foi realizado um teste de seis ou oito horas reais nesta entrega. O avanço acelerado do relógio musical verifica contadores e evolução de padrões; não substitui tempo real de execução, drivers, temperatura, alimentação ou comunicação com hardware.

## Rodada 0.41: desarmes e registro de falhas

O painel deixa de desarmar definitivamente por uma única resposta com mais de 250 ms: descarta o quadro, apaga temporariamente e aguarda um novo dentro de 750 ms desde o último válido. Falhas persistentes, USB e apagamentos manuais continuam exigindo intervenção. Há somente uma solicitação de quadro em andamento, inclusive após um desarme. Diálogos de arquivos usam Qt para não bloquear os QTimers no Windows.

O registro dedicado tem 1.000 eventos em memória, 60 amostras recentes a 1 Hz, fila de 256 escritas e rotação de quatro arquivos de aproximadamente 2 MB. Disco e exportação trabalham fora da GUI/USB. A janela é não modal e não atualiza quando fechada. Horários seguem o fuso local do PC; causas persistem após reativação. O índice acumulado não é limitado a 32 bits nem aumenta buffers; a exibição separa ciclo de oito tempos e fase percentual. [Investigação e uso](logs-saida-v0.41.md) · [Teste nativo de falhas](resultado-output-diagnostics-v0.41.0.json).

## Rodada 0.40: efeito único e ciclos ancorados

O modo único mantém no máximo dois descritores durante a fusão e evita snapshots de misturas. Repertório e durações têm limites validados; intervalos de até 128 compassos usam somente números de prazo. O contador de entrega entre Python e Qt trata o rollover antes do limite inteiro assinado, e correções de relógio preservam origem e evolução cromática.

Os testes avançam 48 horas musicais com buffers estáveis e sem snapshots no modo único. O ensaio nativo de oito horas musicais aceleradas exercita áudio sintético, serial emulada, gravações lentas, renderer interrompido e reabertura, sem certificar seis horas reais. [Auditoria completa](auditoria-buffers-v0.40.md) · [Resultados](validacao.md).

## Rodada 0.39: palco permanente e desenho sob demanda

A região da prévia e o painel de ajustes têm layouts e rolagem independentes. A tela cheia usa a janela nativa, restaura o estado anterior e mantém saída por teclado e botão. Falha/recarga do renderer e navegação encerram esse modo. Texturas de uma coluna, qualidade exclusiva da prévia e prazos de desenho reduzem trabalho, conservando a composição completa do canvas frontal.

Sem emissão, há um desenho de apagamento, seguido de atualização lenta dos controles sem redesenhar o palco. Ao retomar, existe somente um agendamento de desenho. O estado estático não interrompe o relógio dos efeitos, MIDI ou as solicitações USB. A comparação física manteve 140 quadros RGB exatos contra 0.38.

[Organização e benchmark](interface-pixel-v0.39.md) · [Ensaios e limites](validacao.md).

## Rodada 0.38: prévia e controle MIDI

A prévia reduz cálculos repetidos por pixel, amostra o desenho conforme sua resolução e corrige o prazo de 30 fps. A saída física continua em resolução integral, com 140 quadros de referência idênticos. Lighting Studio e Stage Preview deixam de iniciar o worker por padrão; a reativação é reversível em Configurações.

O MIDI nativo usa uma thread, entrada limitada a 512 eventos, retorno de até dez LEDs somente por mudança e uma chamada de comando WebEngine ativa. O encoder relativo mantém a ordem dos incrementos. Falhas, desconexão e fechamento não impedem o funcionamento independente do Auto Show. O salvamento do perfil é explícito, atômico e fora da interface.

[Detalhes e benchmark](otimizacao-pixel-v0.38.md) · [Operação MIDI](midi-x1-mk1.md) · [Validação da entrega](validacao.md).

## Rodada 0.37: quatro saídas por quadro

As quatro saídas compartilham um avanço do relógio, uma geração de cache, um pacote CRC e um ACK. O emissor conserva uma posição pendente, substituída pelo quadro mais recente, sem criar uma fila ou thread por fita. Dados de fontes duplicadas reaproveitam o mesmo resultado no motor. Apenas os comprimentos ativos percorrem a USB no firmware novo.

O ESP32 usa quatro controladores RMT4 com buffers fixos, CRC por tabela de 16 entradas e recepção de 8 KB. O orçamento estimado de corrente é global. Todos os comprimentos e o pacote inteiro são validados antes de alterar os LEDs; um único show atualiza as saídas e o watchdog apaga o conjunto. A compilação WROOM-32 usa 29.920 bytes de RAM estática, sem representar o pico de heap do driver em execução. [Compilação](resultado-esp32-v0.37.json).

O teste do sketch real em periféricos simulados cobre 1.200 pixels, ordens, CRC, quadro incompleto, tamanhos variáveis, saídas desativadas, watchdog e wraparound. O ensaio Qt/USB emulado confirmou mapeamentos, cópias físicas exatas, reutilização de buffers, persistência, minimização e blackout conjunto. Essa execução curta não certifica estabilidade elétrica, fps real ou seis horas com quatro fitas. [Resultados](resultado-pixel-four-outputs-v0.37.0.json) · [Guia](esp32-quatro-saidas.md).

## Rodada 0.36: quantidade física e preparação consistente

A amostragem aceita de 1 a 300 LEDs individuais. A conversão Python valida a quantidade, o formato e cada canal, e completa os endereços não usados com zero, mantendo o protocolo/firmware anteriores. O custo adicional é limitado a completar um quadro de 900 bytes; não há novas threads ou filas. A preparação valida geometria e perfis juntos antes de alterar o projeto, conservando grupos incompatíveis em vez de removê-los.

A seleção e o total da fita são retornados pela mesma operação de preparação. Uma revisão invalida consultas anteriores de fontes; um prazo de dois segundos libera uma preparação que não respondeu, mantendo a saída apagada. O ensaio Qt/USB emulado confirmou uma fita de 120 LEDs, troca 300 → 120 sem resíduos nos últimos endereços, saída minimizada, persistência e blackout no fechamento. Não representa teste elétrico nem duração prolongada. [Resultados](resultado-pixel-strip-size-v0.36.0.json) · [Operação](fitas-variaveis-v0.36.md).

## Rodada 0.35: seleção esporádica na troca de combinação

A participação de contínuos no AUTO é decidida somente quando uma nova combinação é criada. Usa um contador limitado a quatro e um booleano; não há sorteio, fila ou timer por quadro. Os catálogos regulares e contínuos conservam seleções separadas para não reiniciar sua variedade ao intercalar os estilos. Histórico permanece limitado a 12 combinações; os catálogos e contextos limitam os demais mapas.

O ensaio nativo com 300 pixels e USB emulado manteve buffers, saída minimizada e desligamento com zero. Registrou aproximadamente 21,3 fps em execução curta com trocas e capturas de tela. Não certifica seis horas reais ou comportamento elétrico do ESP32. [Resultados](resultado-auto-continuous-v0.35.0.json) · [Operação](auto-continuo-v0.35.md).

## Rodada 0.34: ondas contínuas e velocidade integrada

Os três movimentos novos combinam funções periódicas de espaço e tempo, com uma base positiva de emissão. O cálculo de brilho e cor de cada pixel compartilha os mesmos campos; não há sorteio por quadro ou histórico de posições. Um acumulador de fase e um fator de velocidade suavizado avançam nos timers existentes, inclusive pela amostragem USB quando a janela está minimizada. Não cria timers, threads, buffers ou FFTs.

O ensaio nativo emulado de 300 pixels manteve buffers, mostrou movimento minimizado e concluiu blackout/fechamento com zero. Registrou 21,34 fps e média de renderização de 6,12 ms, com máximo de 10,90 ms, nessa execução curta. Não certifica seis horas reais ou temporização elétrica. Os testes incluem fases avançadas, continuidade de espaço/tempo e troca de velocidade sem salto em fases altas. [Resultados](resultado-pixel-flow-v0.34.0.json) · [Operação](ondas-organicas-v0.34.md).

## Rodada 0.33: picos e preenchimento contínuo

O pico é uma composição RGB no mesmo amostrador da prévia e do envio, depois da resposta musical e antes dos limites de brilho. O status do pico é consultado uma vez por pixel, substituindo três consultas anteriores. Não há novos buffers, timers ou threads. Os quatro efeitos contínuos usam funções periódicas e as quatro famílias novas reutilizam os limites de histórico e os envelopes existentes.

O ensaio nativo com 300 pixels e cópias exatas reutilizou os buffers, manteve transmissão minimizada e concluiu blackout/encerramento com zero. A medição ficou próxima de 20 fps no transporte emulado durante interação/capturas; não representa precisão elétrica do ESP32. Os testes do motor incluem avanço acelerado de oito horas e os novos casos verificam continuidade de todas as respostas de fita. Não foi repetido um ensaio de seis horas reais. [Resultados](resultado-pixel-peaks-v0.33.0.json) · [Operação](picos-continuos-v0.33.md).

## Rodada 0.32: reaprendizado independente do perfil antigo

A comparação ocorre nas janelas de candidatos já analisadas. Acrescenta quatro descritores de ataques alinhados e até oito observações de contratempo, com seis amostras de envoltória cada. Filas são limitadas e expiram quando a sequência se interrompe. O reaprendizado troca as referências em uma operação; não acumula bancos antigos. Não adiciona FFT, thread, timer ou gravação de candidatos durante a apresentação. [Operação e limites](perfil-recorrente-v0.32.md).

O ensaio curto, sem GUI/trace/pytest simultâneo, mediu medianas de 16,60% → 17,19% de um núcleo no groove e 17,38% → 18,75% com clique: cerca de +0,6 e +1,4 pontos percentuais de um núcleo, respectivamente. Há variação relevante entre execuções. São três repetições de oito segundos por cenário; não certificam seis horas com Traktor/USB. [Referência 0.31](resultado-dsp-cost-reference-v0.31.json) · [Versão 0.32](resultado-dsp-cost-current-v0.32.json).

## Rodada 0.31: recorrência de picos sem novo FFT

A grade de picos usa os descritores estruturais existentes, com 64 frames, 32 espectros de fundo, até oito propostas, 16 sementes, oito referências, 16 eventos e 200 pontos para o monitor. Cada posição guarda no máximo quatro candidatos e é descartada depois da janela de decisão. A fila adicional da identidade conserva até oito propostas. Não há crescimento de histórico com as horas de festa, nova thread ou timer. O rastreio por candidato continua desativado na operação normal.

O relógio fornece o período; comparar ataques não alimenta o estimador de BPM. A recuperação espera a confirmação normal e não adiciona espera ao primeiro impacto do drop. A fase pode ser corrigida após quatro ataques coerentes, conservando o período informado. [Operação e resultados](grade-picos-v0.31.md).

Três execuções de oito segundos por cenário, sem GUI, trace ou pytest simultâneo, mediram medianas de 16,99% → 16,60% de um núcleo no groove e 17,77% → 17,58% com clique. A diferença está dentro da variação do ensaio; não demonstra ganho de desempenho ou custo universal. [Referência 0.30](resultado-dsp-cost-reference-v0.30.json) · [Versão 0.31](resultado-dsp-cost-current-v0.31.json). O ensaio não certifica seis horas reais com Traktor/USB.

## Rodada 0.30: direção visual com memória limitada

O catálogo de 12 drops e as 14 famílias usam seleção embaralhada com memória por contexto. As listas são limitadas pelo próprio catálogo; o histórico de combinações conserva 12 entradas. Paletas interpoladas são calculadas por descritor/instante e reutilizadas pelos pixels. Não há sorteio por pixel, nova thread, timer ou persistência a cada quadro.

O teste nativo de uma fita de 300 pixels dividida em seis barras, com cópias exatas, manteve buffers e texturas durante os 12 drops. O envio USB foi emulado, ficou próximo de 21 fps e continuou minimizado. Blackout e encerramento enviaram zero. Essa medição curta não representa temporização elétrica real nem certifica seis horas contínuas. [Resultados e limites](validacao.md) · [Operação](direcao-visual-v0.30.md).

## Rodada 0.29: clique auxiliar e diagnóstico separado

O clique de 2–6 kHz reutiliza o FFT estrutural existente. Acrescenta um envelope com até 120 observações e quatro valores de forma por descritor; os 64 descritores e 16 referências continuam limitados. Não há IFFT, novo filtro em áudio, rede ou runtime de inferência. O callback de rastreio é `None` na aplicação normal, sem escrita de candidatos no disco.

O replay é um processo offline, com leitura PCM em blocos e arquivos separados. Suas listas de eventos crescem com a duração analisada para permitir métricas completas; não fazem parte do processo da apresentação. Percentis usam os últimos 8.192 blocos e a prévia limita o desenho a 4.000 marcas por linha. Não execute análise acelerada concorrente com uma festa se quiser reservar CPU ao Traktor.

O ensaio curto de produção fez três execuções por cenário, sem GUI e com rastreio desligado. A mediana passou de 13,28% para 12,30% de um núcleo no groove e de 14,06% para 13,67% no groove com clique. A diferença é pequena e compatível com variação de medição; não demonstra ganho universal nem certifica seis horas reais. [Medição completa](resultado-dsp-cost-v0.29.json) · [Validação](validacao.md).

## Rodada 0.28: estabilidade da grade acústica

A prioridade da grade reutiliza o FFT e os descritores existentes. O detector conserva até 16 candidatos brutos e 16 elegíveis; a grade conserva 32 observações e usa até oito referências (28 inclinações entre pares) para decidir o inteiro. As filas e históricos continuam limitados. Nenhum histórico cresce com a duração da festa, e a nova análise não depende de desenho da interface.

Há regressões para candidatos antecipados, manutenção do período sob jitter, silêncio/baixo sustentado/vibrato com grade ativa, troca persistente de andamento, perda de áudio e critérios de drop nos modos contínuo e inteiro. Os ensaios são sintéticos e curtos; não certificam seis horas reais. [Resultados desta rodada](validacao.md) · [Funcionamento](grade-audio-estavel.md).

## Rodada 0.27: recuperação de kicks sob bassline

O novo sensor reutiliza o FFT existente e mantém vetores de frequência limitados ao necessário, dois espectros anteriores, fundo/proposta, 100 escores e 200 pontos. A aquisição usa até 16 candidatos e o perfil conserva até 16 referências. Não há modelo externo, rede ou dependência adicional. A confirmação espectral observa mais um hop, de aproximadamente 10 ms, sem atrasar o caminho principal.

O ensaio nativo sintético de oito segundos processou 749 blocos sem descarte. A comparação de 56 s de áudio registrou aproximadamente +0,6 ponto percentual de um núcleo de CPU sobre a 0.26. São medidas locais curtas; não certificam seis horas reais ou custo idêntico com o Traktor. [Matriz, metodologia e limitações](kicks-baixo.md).

## Rodada 0.26: operação em segundo plano

A aplicação agora pausa requestAnimationFrame e timers de informação do Pixel Studio quando a janela está minimizada ou a página de pixels está oculta. Nas abas de controle e em Apresentação leve, atualiza os indicadores a 4 Hz sem desenhar Canvas. O recebimento musical e as chamadas de saída mantêm um único relógio de avanço, sem depender de pintura.

O espectro já tinha atualização por página; agora também exige janela restaurada e modo leve desligado. Medidores, diagnósticos e interfaces anteriores não recebem atualizações ocultas. O worker PAR/moves dorme num evento fora de suas páginas, sem consultar o provider a 60 Hz. Captura, DSP, Link e transporte dos pixels continuam ativos.

O modo padrão Simular projeto atual bloqueia conexão/ativação USB. Há uma solicitação explícita para voltar à prévia; snapshots antigos do operador não podem desfazer uma escolha física recente. A regressão nativa cobre a conexão pelos próprios botões, os 26 efeitos e apagamento/reabertura. [Operação e abas](apresentacao-leve.md).

### Medição curta da 0.26

O ensaio em Qt por software usa áudio sintético, projeto de 300 pixels em seis barras e USB emulado. São sete fases de aproximadamente oito segundos. Não houve execução simultânea da suíte pytest nesta medição final.

| Fase | CPU principal | CPU renderer | Desenhos Canvas | Quadros USB emulados |
|---|---|---|---|---|
| palco | 78.32% | 49.61% | 166 | 170 |
| controles | 66.02% | 16.99% | 0 | 170 |
| leve | 50.98% | 11.33% | 0 | 171 |
| minimizado | 41.80% | 9.77% | 0 | 170 |
| espectro_visivel | 55.36% | 6.04% | 0 | 170 |
| palco_PAR | 62.38% | 7.99% | 0 | 170 |
| retorno_pixel | 87.89% | 45.51% | 160 | 169 |

**100% de CPU na tabela equivale a um núcleo lógico**, não à utilização total do computador. Os padrões e a análise evoluem entre fases; os números não isolam o custo da FFT nem são uma comparação controlada antes/depois. O resultado varia com carga e máquina. Todos os modos mantiveram pixels em movimento, grade avançando e zero descartes de áudio. Espectro oculto e worker PAR/moves fora de sua página tiveram zero atualizações verificadas; voltar ao palco retomou o desenho. [JSON completo](resultado-pixel-presentation-v0.26.0.json).

A prévia em software permanece um custo relevante, especialmente pela cópia de imagem por quadro. Minimização e modo leve evitam esse caminho, mantendo o cálculo dos pixels necessários à saída. Isso reduz trabalho de desenho sem provar, por um ensaio curto, confiabilidade em seis horas reais.

## Gargalos examinados desde a 0.25

| Ponto | Risco identificado | Implementação ou conclusão |
|---|---|---|
| Halo das fitas | Composição e suavização adicionais por quadro | Removidos completamente, junto com o controle. Projetos antigos são aceitos, mas o valor não atua nem é exportado. |
| Barras copiadas | Recalcular o mesmo efeito para cada cópia | Uma topologia compilada mantém referências e um cache por quadro. Só os pontos solicitados são calculados; destinos reutilizam a referência. |
| Texturas | Recriação em edições e dimensionamento por LED físico | Recursos reutilizados por identidade/resolução. Nome e coordenadas não recriam texturas ou buffers do motor. Texturas usam pixels controláveis, evitando repetir o cálculo em grupos WS2811. |
| Salvamento | Validação, escrita e fsync na thread da interface | Thread dedicada, um pedido ativo e apenas a edição mais recente pendente. Escrita atômica, confirmação após sucesso e drenagem no fechamento. |
| Música → renderizador | Mensagens antigas se acumularem durante uma pausa | Uma entrega em voo, confirmação por identificador e somente o snapshot mais recente pendente. Mensagens preservam o instante original de envio. |
| Lista USB | Consultas JavaScript repetidas enquanto outra está bloqueada | Uma consulta em voo, prazo de dois segundos, sem recriar a lista quando nada mudou. |
| Histórico do navegador | Crescimento por recursos bloqueados/erros repetidos | Filas circulares: 128 eventos de navegação e 32 erros JavaScript, com mensagens limitadas. |
| Renderizador travado | Último frame continuar sendo apresentado ou quadros antigos voltarem depois | Quadros acima de 250 ms são descartados com apagamento temporário; 750 ms sem quadro válido desarmam. Um pedido em voo, callbacks de gerações antigas rejeitados. Firmware conserva watchdog independente de 750 ms. |
| Recuperação da prévia | Reiniciar toda a aplicação e perder captura | **Reabrir prévia** tenta salvar a edição, recarrega o simulador e preserva a captura. Saída física permanece apagada até nova ativação. Se o renderer não responder, usa o último projeto salvo. |
| Históricos de música/USB | Acúmulo de dados ao longo de horas | Históricos DSP e de estrutura são limitados; a composição guarda até 12 combinações, eventos do bridge até 64 e tempos de confirmação USB até 31. |
| Captura de áudio | Atraso crescer sem limite se DSP ficar mais lento | A fila existente conserva oito blocos e descarta o mais antigo quando cheia; o contador de descarte permite identificar sobrecarga. Não foi ampliada para esconder atrasos. |
| Logs | Crescimento ilimitado em disco ou escrita bloquear USB | Dois registros com rotação própria: geral e saída, aproximadamente 8 MB cada. O da saída usa worker, fila de 256 e memória limitada; informa saturação/erro de disco. |

O contador de quadros não guarda os quadros anteriores. A topologia tem buffers proporcionais ao número de pixels configurados, não ao tempo de funcionamento. O rollover do identificador interno de quadro limpa as marcas de cache.

## Ensaio automatizado

Execute na pasta `main`, com a aplicação de uso normal fechada para não disputar recursos:

```powershell
# Três minutos reais, percorrendo oito horas no relógio musical.
.\.runtime\python312\python.exe -X utf8 scripts\validate_pixel_endurance.py --seconds 180 --music-hours 8

# Oito horas REAIS, com relógio musical também em oito horas.
.\.runtime\python312\python.exe -X utf8 scripts\validate_pixel_endurance.py --seconds 28800 --music-hours 8
```

O script usa configuração isolada em `.runtime/pixel-endurance-qa`, áudio sintético, Qt WebEngine por software e **ESP32 emulado**. Não abre COM real, não inicia Link nativo e não altera o projeto de uso normal. O ensaio longo deve rodar em primeiro plano pelo terminal; não suspenda o computador.

Carrega uma fita de 300 pixels dividida em seis barras com três pares simultâneos. Alterna groove/breakdown/build/drop, edita posições sem realocar recursos e impõe 50 ms a cada gravação para exercitar a thread de disco. Provoca uma pausa de 450 ms no renderer, verifica blackout/desarme e rejeição de quadros antigos, reativa somente dentro do ensaio, e depois testa a reabertura da prévia com áudio ainda ativo. Ao final verifica fechamento e conclusão do salvamento.

As asserções exigem zero blocos de áudio descartados, buffers/texturas estáveis, histórico limitado, progresso do desenho, canais finitos de 0–255, igualdade dos três pares, ausência de erros JavaScript e no máximo uma gravação pendente. Um erro interrompe o script. O JSON só recebe `passed: true` depois de todas as verificações e do fechamento.

O resultado é salvo em [resultado-pixel-endurance-v0.25.0.json](resultado-pixel-endurance-v0.25.0.json), substituindo o resultado anterior. Guarde uma cópia antes de repetir se quiser comparar execuções. [Regressão e evidências desta entrega](validacao.md).

## Medições da execução curta da 0.25 (histórico)

Registro: 2026-10-28 (UTC), neste computador, sem hardware conectado. Resultado aprovado em **180 segundos reais**, com aproximadamente **oito horas musicais aceleradas**. Os estados musicais são fornecidos pelo ensaio; isto não mede acurácia de detecção em músicas reais.

| Medida | Resultado |
|---|---|
| Blocos de áudio processados / descartados | 16.876 / **0** |
| Desenhos da prévia / tempo médio / máximo observado | 3.983 / **6,00 ms** / 32,70 ms |
| Buffers de sinal / texturas dos trechos | **6.300 / 10.800 bytes**, sem crescimento nas amostras |
| Histórico de combinações | Até 12 |
| Quadros USB emulados confirmados | 3.802; aproximadamente 21,3 FPS no final |
| Gravações com atraso de disco provocado | 90 concluídas, sem erro |
| Pausa do renderer / callbacks antigos / reabertura | Desarme, rejeição e recuperação aprovados |
| Memória residente do processo principal | 270,96–280,04 MiB; primeira/última amostra 275,89/280,04 MiB |
| Memória residente do renderer | 140,01–217,14 MiB; primeira/última amostra 140,01/213,38 MiB |

O renderer cresceu durante o aquecimento e oscilou; portanto o resultado **não comprova memória total estável por horas**. Os buffers sob controle do motor ficaram constantes. O heap JavaScript reportado pelo Chromium foi aproximadamente 24,5 MB nas amostras; essa API pode fornecer valores arredondados. As medições de RSS abrangem processo principal e renderer, não a soma de todos os subprocessos Qt/Chromium.

Os testes unitários adicionais bloqueiam a confirmação de música por 10.000 envios e retardam o disco em rajadas, verificando que permanece somente a última edição/mensagem pendente. As medidas curtas acima não têm uma comparação de desempenho antes/depois; demonstram o comportamento da configuração testada.

## Limites que ainda precisam de acompanhamento

A apresentação do Canvas ainda usa uma cópia de pixels em memória por quadro, necessária à solução atual para as piscadas observadas no Qt. Ela cria alocações transitórias e disputa memória/CPU com o renderer. Não foi trocada por outra forma de composição sem validar novamente os artefatos gráficos. A prévia tem resolução reduzida e limite de 30 Hz; o envio físico usa todos os 300 pixels, mesmo com o palco fora da área visível.

O RSS do Chromium inclui heap, coleta de lixo e caches; não deve ser confundido com o tamanho dos buffers controlados pelo motor. Um ensaio curto não permite excluir um vazamento lento. A versão curta mede os processos principal/renderizador e, quando disponível, o heap JavaScript. A comparação em várias horas reais continua necessária.

O motor JavaScript e a amostragem física continuam no processo do Qt WebEngine. Uma falha desse processo interrompe a saída; a captura de áudio e o transporte USB têm ciclos separados. A recuperação deixa a saída apagada. Se o disco ou o sistema operacional pararem de responder, a escrita pode demorar a concluir, embora não bloqueie diretamente a thread da interface.

Depois do ensaio sintético longo, faça um ensaio supervisionado com a montagem real, Traktor/Link e o conjunto de efeitos/resolução que pretende usar. Acompanhe memória do processo principal e subprocessos, blocos descartados, erros de continuidade, FPS confirmado e mensagens USB. Oscilação inicial de memória pode ser cache; crescimento persistente após estabilização exige investigação. O FPS obtido com serial emulada não prevê a taxa da fita física. Não há reconexão ou reativação física automática após uma falha.
