# Confiabilidade e operação prolongada — 0.26.0

Esta rodada corrige gargalos identificados no código e acrescenta um ensaio repetível. Ainda não foi realizado um teste de seis ou oito horas reais nesta entrega. O avanço acelerado do relógio musical verifica contadores e evolução de padrões; não substitui tempo real de execução, drivers, temperatura, alimentação ou comunicação com hardware.

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
| Renderizador travado | Último frame continuar sendo apresentado ou quadros antigos voltarem depois | Pedido de frame vence em 250 ms, saída é desarmada, blackout tem prioridade e callbacks antigos são rejeitados. Firmware conserva watchdog de 750 ms. |
| Recuperação da prévia | Reiniciar toda a aplicação e perder captura | **Reabrir prévia** tenta salvar a edição, recarrega o simulador e preserva a captura. Saída física permanece apagada até nova ativação. Se o renderer não responder, usa o último projeto salvo. |
| Históricos de música/USB | Acúmulo de dados ao longo de horas | Históricos DSP e de estrutura são limitados; a composição guarda até 12 combinações, eventos do bridge até 64 e tempos de confirmação USB até 31. |
| Captura de áudio | Atraso crescer sem limite se DSP ficar mais lento | A fila existente conserva oito blocos e descarta o mais antigo quando cheia; o contador de descarte permite identificar sobrecarga. Não foi ampliada para esconder atrasos. |
| Logs | Crescimento ilimitado em disco | Rotação já existente: 2.000.000 bytes por arquivo, mais três cópias, aproximadamente 8 MB no total. |

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
