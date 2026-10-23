# Validação — versão 0.14

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10. Código/pacote instalado: **0.14.0 / 0.14.0**; preferências **v10**, exportação **v2 / RGBW**. Sem saída física DMX, transmissão de rede ou Link.

## Regressão e instalação

**443 testes passaram em 73,41 s**, incluindo os 393 anteriores. Os 50 novos casos cobrem os moving heads nos dez efeitos e quatro estados estruturais, transição a partir do manual, congelamento de movimento, master/blackout, três políticas de repetição, aquisição parcial, sincronização e contagem de repetições, coincidência de novidade com troca programada, entrada sincronizada sem fade entre modos, migração v9/v10 e resposta a novas camadas depois de realinhar o ciclo.

A integração da GUI verifica o botão principal, sincronização a partir do show antigo, controles acima do palco, persistência da política e alinhamento sem substituir o runtime de áudio. As verificações de geometria passaram em 1440×960, 1280×800 e 1100×760.

Evidências: resultado-pytest-v0.14.txt e resultado-pytest.txt. compileall de src/scripts passou. O pacote editável foi atualizado no runtime portátil sem novas dependências; o smoke test confirmou 0.14.0 / 0.14.0 / Settings 10. iniciar.cmd --help terminou com código zero. O venv incompleto anterior foi preservado; o lançador mantém o fallback para Python 3.12 preparado.

## Ensaios com palco aberto

scripts/validate_phrases.py executou os sinais sintéticos contínuo (21 s), estrutura (26 s) e textura (23 s). O ensaio parte de configurações do show antigo, usa o botão principal para selecionar o Show cíclico e, ao sincronizar, volta propositalmente ao antigo antes do clique para verificar a ativação automática do novo modo.

| Fonte | Blocos | Quadros com moves coordenados verificados | Motor, última janela | Último quadro |
|---|---|---|---|---|
| synthetic | 1966 | 1252 | 60.00 Hz | 0.272 ms |
| structure_demo | 2436 | 1554 | 60.00 Hz | 0.346 ms |
| texture_demo | 2155 | 1375 | 60.00 Hz | 0.362 ms |

Nos três ensaios houve zero descartes, zero falhas de continuidade e nenhum erro de análise/iluminação. Cada quadro verificado tinha os dois moving heads com mesma intensidade e canais RGBW, pan espelhado e tilt igual. A geometria do palco permaneceu única em cada execução: x=0, y=338, largura=1157, altura=300. O primeiro tempo observado após sincronizar foi 1/8 e a origem do grid acústico permaneceu intacta. Todos os workers encerraram e o estado final ficou com intensidade/RGBW zero.

O novo painel mostra oito células, motivo, tempo, ciclo, repetição e estado do clique acima do palco. preview-cycles-texture_demo-variation.png foi inspecionada na versão 0.14: Perseguição no tempo 1/8, repetição 1/2, dois moving heads e o PAR correspondente acesos a 79%, demais PARs em 1%. Os botões Show de 8 e Sincronizar 1/8 estão visíveis no topo.

## Repetição em contexto estável

No sinal contínuo, após o clique em cerca de 3,06 s, os ciclos 1 e 2 mantiveram Todos juntos, os ciclos 3 e 4 usaram Perseguição e o ciclo 5 passou a Sequência inversa. As mudanças apareceram em cerca de 11,06 s e 19,08 s, ambas no tempo 1. Não houve novidade de textura pendente nesse ensaio: a variação programada funcionou por conta própria.

Cada ciclo continua com oito tempos. A política padrão repete duas vezes antes da troca; as opções a cada ciclo e somente com novos elementos passaram em testes determinísticos. Padrões fixos repetem sem rotação. Um aumento sustentado pode antecipar a troca para o próximo tempo 1, e a coincidência com a programação gera uma só troca.

O ensaio de textura mudou para Perseguição no ciclo 3, detectou novidade e mudou o motivo para Sequência inversa no ciclo 4. O build-up cobriu o motivo; Sequência inversa apareceu ao voltar ao groove em cerca de 20,56 s. A fila de novidade continua preservada durante a cobertura estrutural.

## Preparação, continuidade e drop

O fade foi observado nos três sinais. O ensaio de textura também registrou 11 quadros de apagão breve com intensidade e todos os canais RGBW zero, seguidos de retorno automático. O blackout manual permaneceu liberado. O contador percorreu os oito tempos durante as janelas sem kick, enquanto as confirmações permaneceram constantes em 15 (estrutura) e 11 (textura).

No ensaio estrutural, cada posição do drop atingiu o master de 80%. O oitavo permaneceu até a chegada do nono kick.

| Kick confirmado | Intervalo observado | Duração observada | Pico nos PARs |
|---|---|---|---|
| 1 | 20.172–20.640 s | 0.468 s | 80% |
| 2 | 20.672–21.140 s | 0.468 s | 80% |
| 3 | 21.156–21.656 s | 0.500 s | 80% |
| 4 | 21.656–22.125 s | 0.469 s | 80% |
| 5 | 22.140–22.625 s | 0.485 s | 80% |
| 6 | 22.656–23.125 s | 0.469 s | 80% |
| 7 | 23.156–23.640 s | 0.484 s | 80% |
| 8 | 23.672–24.140 s | 0.468 s | 80% |

Evidências: resultado-ciclos-synthetic-v0.14.json, resultado-ciclos-structure_demo-v0.14.json e resultado-ciclos-texture_demo-v0.14.json. Capturas preview-cycles-*.png são geradas após encerrar os workers.

## Avaliar com Traktor

1. Reabrir iniciar.cmd, iniciar captura da saída usada pelo Traktor e adquirir a grade com quatro kicks regulares.
2. No topo do Stage Preview, clicar Usar show de 8 e Ativar motor. Clicar Sincronizar 1/8 no primeiro tempo desejado; conferir a célula 1 e alinhado pelo clique.
3. Em Lighting Studio, manter Padrão do ciclo de oito em Automático e escolher Variação automática. Observar o nome do motivo e a repetição acima do palco.
4. Conferir os moves juntos nos grooves e nas cenas de tensão/drop, além das sequências nos PARs. Testar fade/apagão breve, manual, blackout e parada.

Os ensaios são sintéticos e não reproduzem as tracks do último teste do usuário. O ciclo é relativo ao grid de BPM, não reconhece downbeat ou instrumentos. A detecção de kicks/basslines não foi afrouxada. O drop conta confirmações reais; perdas de detecção ainda podem prolongá-lo. Histórico da versão anterior: validacao-v0.13.md. Detalhes: ciclos-oito.md.
