# Validação — versão 0.17

Registro: 2026-10-22 (UTC). Windows x64, Python 3.12.10. Preferências v13; pacote 0.17.0; aalink 0.2.3 instalado no Python portátil. Iluminação abstrata; rede local usada somente no módulo Link quando ativado.

## Regressão

**586 testes passaram em 117,43 s**, incluindo os 547 anteriores e 39 novos. Evidências: docs/resultado-pytest-v0.17.txt e docs/resultado-pytest.txt.

Os 547 casos anteriores e 39 novos exercitam a aquisição de contexto sem kick, introdução com pads, groove fora da faixa preferida, subida inicial com rolls/crescimento, breakdown superior a um minuto, retomada após silêncio e confirmação do primeiro groove sem criar drop. A aquisição da grade é testada por reference_ready, pois groove também pode ser uma leitura provisória anterior aos quatro kicks.

A cobertura Link inclui frescor, perda de participantes, erro de dependência, retomada, compensação de fase, ciclo de oito tempos, prioridade do silêncio/áudio indisponível, ausência de eventos artificiais de kick, seleção do relógio, GUI, alinhamento visual e migração de preferências. A interface inicia sem ingressar na rede, inclusive se a seleção de relógio Link foi salva.

## Continuidade e custo do DSP

O perfil inicial de cinco segundos de áudio sintético identificou custo elevado na redução visual min/max da onda. O mesmo perfil caiu de 3,450 s para 1,047 s após vetorização; o custo acumulado em LevelAnalyzer passou de 2,231 s para 0,121 s. Esses números incluem a sobrecarga do perfilador e não constituem garantia de desempenho com hardware real.

Dezenove casos novos verificam extremos por partição, janelas parciais/desiguais, mono/estéreo e retenção dos últimos 200 ms. RMS, picos e sinal musical permanecem iguais. O perfil reproduzível está em scripts/profile_analysis.py e docs/resultado-profile-v0.17.txt.

Os ensaios iniciais de palco detectaram descartes de blocos e reinícios da estrutura, inclusive sem outros testes em paralelo. Depois da otimização, o ensaio isolado de 26 s em scripts/validate_phrases.py structure_demo recebeu **2.437 blocos sem descartes e sem falhas de continuidade**. Manteve uma geometria de palco, oito passos durante a pausa sem aumentar a contagem de kicks, sincronização observada no tempo 1 e retorno completo dos oito kicks no drop, cada um com pico 0,8 e duração superior a 350 ms. Iluminação: 60 Hz no fechamento; motor encerrou com todos os canais zerados.

Evidência: docs/resultado-ciclos-structure_demo-v0.17.0-texture.json. As capturas preview-cycles-structure_demo-*.png usam dados sintéticos. preview-link.png mostra a página Link com conexão desativada, sem captura.

## Ableton Link nativo

scripts/validate_link.py ingressou com dois participantes nativos no mesmo computador e verificou 25 amostras compartilhadas. Cada um encontrou um participante; ambos leram 120 BPM. A maior diferença de fase entre os quinze últimos pares projetados foi cerca de 0,699 ms. O teste não enviou comandos de mudança de tempo, beat ou transporte e encerrou ambos os runtimes. A sessão local começa em 120 BPM quando este módulo é o primeiro participante; o guia orienta ativar o Traktor primeiro.

Evidência: docs/resultado-link-v0.17.json. A medição entre dois leitores locais não mede atraso entre áudio capturado e luz nem garante esse erro com Traktor, rede Wi-Fi ou outro computador. A compensação visual permite ajuste local de −250 a +250 ms.

## Operação e limites

A leitura provisória exige 1,2 s de áudio contínuo; a confirmação de referência de kick continua exigindo quatro ataques acústicos regulares na faixa configurada. O início de oito tempos no Link é uma referência da sessão, não reconhecimento automático de frase da track. Sincronizar 1/8 marca somente o ciclo visual. Perder o Link retorna ao relógio acústico; silêncio, áudio antigo, desativação e blackout mantêm prioridade.

Não foi realizada uma sessão com o Traktor nesta rodada. O teste operacional com faixas reais deve conferir LINK no Master Clock, BeatSync, SYNC no deck, ao menos um participante no BEATLIGHT, relógio dos efeitos em LINK e compensação inicialmente em zero. A análise sonora continua necessária. Instruções completas e fontes oficiais: [ableton-link.md](ableton-link.md).

Compilação de src/scripts e inicialização por iniciar.cmd --help aprovadas. Preferências existentes serão migradas ao abrir a nova versão; nenhum arquivo de preferências real do usuário foi reescrito durante o desenvolvimento.
