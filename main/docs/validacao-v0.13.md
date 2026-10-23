# Validação — versão 0.13

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10 e dependências existentes. Código/pacote instalado: **0.13.0 / 0.13.0**; preferências **v9**, exportação **v2 / RGBW**. Sem saída física DMX, transmissão de rede ou Link.

## Regressão e instalação

**393 testes passaram em 80,19 s**, incluindo os 355 anteriores. Os 38 novos casos cobrem os oito motivos e sua repetição, troca por novidade no ciclo seguinte, manutenção da troca durante build-up, rejeição de ataques isolados, fade/apagão/retorno, prioridades, sincronização pelo instante do clique, preservação do motivo/alinhamento, comando que chega após o timestamp do worker, parada/correção sem replay do clique, persistência/migração, validação de parâmetros, integração da GUI e os cenários de interrupção prematura do drop.

Os testes de RGBW, captura, DSP, rejeição de bassline, aquisição/continuidade/correção do grid e prioridades continuam passando. O algoritmo acústico de kick não foi afrouxado. A mudança estrutural restringe a saída precoce do drop: ausência de confirmação sozinha não basta; precisa também de retirada dos graves. O antigo prazo absoluto foi retirado. O sequenciador usa um tempo completo nos pulsos do drop, independente da subdivisão anterior.

Evidências: resultado-pytest-v0.13.txt e resultado-pytest.txt. compileall de src/scripts passou. O pacote foi instalado no runtime local sem dependências novas e conferido como 0.13.0; a instalação é editável e inclui as correções finais. Preferências 1–8 migram para v9 preservando os campos conhecidos. Comandos de sincronização não são persistidos.

## Conferência do lançador

Foi encontrada uma pasta .venv312 com Python 3.11.1 e sem NumPy/SciPy/PySide6/PyAudioWPatch. Ela foi preservada. iniciar.cmd agora valida Python 3.12 e essas dependências antes de escolher o ambiente; caso o venv esteja incompleto, tenta o runtime portátil preparado. O smoke test de iniciar.cmd --help, chamado pelo PowerShell, terminou com código zero usando o fallback. Nenhuma dependência foi instalada nesse venv e nenhum ambiente foi removido.

## Ensaios em tempo real com palco aberto

scripts/validate_phrases.py executou structure_demo por 26 s e texture_demo por 23 s. Os dois usaram Show cíclico, sincronização manual no início do groove e fontes sintéticas sem som reproduzido. Capturas são mantidas em memória e codificadas após encerrar os workers.

| Medida | Estrutura | Baixo e camadas |
|---|---|---|
| Blocos recebidos | 2436 | 2154 |
| Descartes / falhas de continuidade / erros | 0 / 0 / nenhum | 0 / 0 / nenhum |
| Primeiro tempo observado após clicar em sincronizar | 1/8 | 1/8 |
| Origem do grid acústico preservada pelo clique | Sim | Sim |
| Preparação por fade observada | 8 quadros | 8 quadros |
| Preparação por apagão observada | Não selecionada | 12 quadros, RGBW/intensidade zero |
| Retorno após preparação | 1 | 2 |
| Tempos vistos sem kicks | 1–8 | 1–8 |
| Kicks confirmados na janela sem kick | Constante em 15 | Constante em 11 |
| Motor, última janela | 60,000 Hz | 59,113 Hz |
| Último quadro de iluminação | 0,357 ms | 0,412 ms |
| Retângulos de palco observados | 1 | 1 |
| Encerramento | Workers encerrados; RGBW e intensidade zero | Workers encerrados; RGBW e intensidade zero |

O palco permaneceu em x=0, y=230, largura=1157 e altura=300 em ambos os ensaios. O fade reduziu o ganho global a cerca de 11% nos quadros finais observados, antes de retornar a 100% no primeiro tempo seguinte. O apagão breve zerou todos os pontos sem ativar o blackout manual. Não houve reinício de captura ao sincronizar.

## Oito kicks do drop medidos

No ensaio estrutural, a cena alcançou cada contagem de 1 a 8. A tabela registra o intervalo observado em que áudio e iluminação estavam em drop naquela contagem; o tempo entre primeiro/último quadro não inclui os intervalos de polling nas bordas.

| Kick confirmado | Intervalo observado | Duração observada | Pico nos PARs |
|---|---|---|---|
| 1 | 20,156–20,640 s | 0,484 s | 80% |
| 2 | 20,656–21,156 s | 0,500 s | 80% |
| 3 | 21,172–21,656 s | 0,484 s | 80% |
| 4 | 21,672–22,156 s | 0,484 s | 80% |
| 5 | 22,172–22,640 s | 0,468 s | 80% |
| 6 | 22,672–23,140 s | 0,468 s | 80% |
| 7 | 23,156–23,640 s | 0,484 s | 80% |
| 8 | 23,656–24,140 s | 0,484 s | 80% |

O oitavo permaneceu ativo até 24,140 s, com retorno ao groove na chegada do nono kick. Cada posição atingiu o master configurado de 80%. Os testes estruturais adicionais cobrem quatro segundos sem confirmação com graves presentes e kicks esparsos que atravessam o antigo prazo de oito segundos. Retirada real dos graves e silêncio ainda retiram a cena, como requerido pelo contexto musical.

Evidência: resultado-ciclos-structure_demo-v0.13.json. preview-cycles-structure_demo-drop-eight.png foi inspecionada: o painel mostra 8/8 kicks com fachos ativos e ciclo visual no oitavo tempo.

## Troca de motivo após novos elementos

No ensaio de textura, o motivo Todos juntos se repetiu enquanto o contexto permaneceu estável. As camadas adicionadas em 12 s agendaram uma troca; o build-up existente apareceu por volta de 13,4 s e cobriu o motivo. A troca foi preservada na fronteira do ciclo e Perseguição apareceu ao voltar ao groove em 20,562 s.

A primeira execução desse QA detectou que o início do build-up descartava a troca pendente. A fila agora é preservada durante a cobertura estrutural, com regressão específica e nova execução completa do ensaio aprovada. A entrada de bassline em 6 s, por si só, não cruzou de forma sustentada o limiar deste modo nesse sinal; o sistema não promete reconhecer todo novo instrumento.

Evidência: resultado-ciclos-texture_demo-v0.13.json. preview-cycles-texture_demo-preparation-blackout.png foi inspecionada: os seis pontos estão em zero, o botão BLACKOUT permanece liberado e o painel mostra preparando destaque e alinhado pelo clique. Capturas de sincronia, fade e impacto também são geradas pelo script.

## Avaliação com faixas reais e limites

Os ensaios são sintéticos e não reproduzem a faixa do último teste do usuário. Foram corrigidas e reproduzidas em regressões duas condições do código que podiam encurtar o drop, sem atribuir uma causa única à track não disponível. O contador usa kicks confirmados: perdas de detecção podem prolongar a contagem; o grid previsto não fabrica eventos. Dados antigos, retirada real de graves, silêncio, parada e falha mantêm prioridade.

O ciclo usa oito tempos da grade, assumindo 4/4, e segue mesmo sem kick. O clique alinha o primeiro tempo visual, não detecta downbeat ou synths. Novidade é aumento sustentado de descritores da mixagem; ganho/filtro também podem acioná-la. RGBW permanece um modelo visual de branco neutro, sem calibração para aparelhos físicos.

1. Reabrir iniciar.cmd, iniciar captura da saída do Traktor e adquirir a grade com quatro kicks regulares.
2. No palco, Usar ciclos de 8 → Ativar motor. Clicar Sincronizar 1/8 no primeiro tempo desejado e conferir as oito células.
3. Comparar Todos juntos, Perseguição e os demais motivos. Em Automático, observar repetição em trechos estáveis e troca na fronteira após nova textura.
4. Comparar fade, apagão breve e sem preparação. Ajustar a duração e conferir que a luz retorna automaticamente.
5. Testar build-up e drop, inclusive basslines agressivas e trechos com kicks menos evidentes; observar as oito confirmações e a permanência do oitavo.
6. Conferir manual, blackout e parada; salvar preferências de luz. O clique de sincronização é da sessão.

Detalhes em ciclos-oito.md. Histórico RGBW preservado em validacao-v0.12.md e resultado-pytest-v0.12.txt.
