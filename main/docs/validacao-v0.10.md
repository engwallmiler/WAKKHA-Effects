# Validação — versão 0.10

Registro: 2026-10-13 (UTC). Windows x64 e Python 3.12.10, com as mesmas dependências da versão anterior. Código e metadata instalados: **0.10.0**. Preferências continuam em **v7**. Nenhuma saída física ou transmissão de rede ativada.

## Regressão automatizada

**294 testes passaram em 69,17 s**, incluindo os 276 anteriores. Evidências: resultado-pytest.txt e resultado-pytest-v0.10.txt. compileall de src/scripts passou; código, pacote e Settings.version foram conferidos como 0.10.0 / 0.10.0 / 7.

Os 18 casos novos cobrem:

- Aquisição em quatro ataques a 90, 120 e 150 BPM sem esperar PLL locked; irregularidade e limites configurados de BPM.
- Projeção contínua por dois minutos sem criar eventos, frase/origem, igualdade de fase entre consumidores e projeção sem prazo de expiração.
- Rejeição de ataque isolado/roll, correção de quatro kicks deslocados, mudança consistente de BPM e preservação do andamento quando kicks são omitidos.
- Ataques de identidade mais fraca não podem corrigir a grade; kicks sintetizados deslocados em 200 ms corrigem o pipeline completo.
- Aquisição de quatro kicks detectados no pipeline antes de 2,5 s; saída de Aprendendo sem esperar o PLL; frases avançam sem novos kicks.
- Pulso pelo relógio e alternância continuam depois da expiração do PLL, mas param com a captura.
- Palco e Rhythm Monitor projetam a mesma fase e percorrem oito tempos mesmo com o campo legado de frase congelado; geometria constante.
- Auditoria reinicia janelas pendentes após correção sem recontar kicks.

Dois testes anteriores foram atualizados para a política solicitada: a grade não expira por ausência de kick, e incerteza crescente não pausa o relógio estimado. O teste de refinamentos duplicados compara o mesmo instante temporal; cruzar um tempo agora avança a frase independentemente do evento.

Os três cenários de bassline agressiva/forte continuam passando. Durante o desenvolvimento, permitir correção por quatro candidatos de perfil normal fez a bassline no contratempo deslocar a grade e criar falso drop no teste. Foi acrescentado um perfil mais estrito para autorizar correções (incluindo queda entre 85% e 130% da referência). O cenário negativo e um cenário positivo com kicks deslocados passaram, seguidos pela regressão completa.

## Grade e efeitos sem kick em tempo real

scripts/validate_grid.py abriu a aplicação Qt durante **16 s**, com fonte sintética estrutural e efeito Pulso pelo relógio. A seção sem kick começa em 8 s; o teste observa 9–16 s, incluindo expiração do PLL acústico.

| Medida | Resultado |
|---|---|
| Áudio | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 1.498 |
| Aquisição da grade | 2,140 s |
| Tempos da frase observados sem kick | 1, 2, 3, 4, 5, 6, 7, 8 |
| Kicks confirmados durante a pausa | Contagem constante em 15 |
| Janelas previstas durante a pausa | Contagem avançou de 14 a 28 |
| Fase observada | 0,0013 a 0,9987 |
| Pico de intensidade sem kick | 74,33%, master em 80% |
| PLL acústico expirado durante o ensaio | Sim; a grade continuou |
| Descartes / falhas de continuidade | 0 / 0 |
| Geometria do palco | Um retângulo: x=0, y=230, largura=1157, altura=300 |
| Erros / encerramento | Nenhum; workers encerrados e intensidades finais zero |

Evidência: resultado-grid-v0.10.json. preview-grid.png foi inspecionada, com oito linhas fixas, cursor, BPM de 120 e estado estimado durante a pausa. Esse efeito pulsa em tempos previstos por definição; não cria kicks confirmados.

## Estrutura e palco em tempo real

scripts/validate_stage.py executou o ciclo estrutural com automação musical e palco aberto por **26 s**.

| Medida | Resultado |
|---|---|
| Blocos recebidos | 2.436 |
| Saída de Aprendendo para groove | 2,156 s |
| Breakdown / build-up | 8,625 s / 12,906 s |
| Drop / groove no nono kick | 20,156 s / 24,141 s |
| Kicks pós-drop | 1, 2, 3, 4, 5, 6, 7, 8 |
| Frase durante a pausa | Todos os oito tempos; kicks confirmados constantes em 15 |
| Descartes / falhas de continuidade | 0 / 0 |
| Geometria do palco | Um retângulo: x=0, y=230, largura=1157, altura=300 |
| Branco máximo na subida | 97% |
| Pico de intensidade antes do drop | 63,35%, master em 80% |
| Movimento máximo na subida | 0,325 ciclos/s |
| Motor, última janela / último quadro | 61 Hz / 0,1382 ms |
| Erros / encerramento | Nenhum; workers encerrados e intensidades finais zero |

Evidência: resultado-palco-v0.10.json. preview-buildup.png e preview-drop.png inspecionadas; preview-breakdown.png e preview-palco.png atualizadas. O palco mostra frase de oito tempos e barra de fase, enquanto o contador pós-drop permanece de oito kicks reais. Capturas PNG são codificadas somente após encerrar os workers.

## Limites e avaliação com Traktor

Os ensaios são sintéticos e não reproduzem som, gravam áudio ou transmitem DMX. Não fornecem taxa de acerto em tracks reais nem garantia de precisão depois de longos trechos sem referência. Quatro ataques bastam para uma hipótese temporal rápida, mas um trecho iniciado apenas com baixo pode adquirir uma referência inadequada. Confiança é heurística; seu piso operacional não significa precisão garantida.

A grade segue extrapolando sem kick; incerteza cresce com o tempo. Silêncio, descontinuidade e troca de fonte reiniciam o contexto. Correção grande precisa de quatro ataques regulares de perfil estrito e pode deslocar uma vez a posição visual dentro do tempo. Mudanças simultâneas de timbre/BPM podem exigir reaprendizado. A detecção acústica observa cerca de 120 ms após o ataque; o relógio visual não depende dessa espera em cada tempo.

Frases e compassos continuam relativos à hipótese 4/4; o downbeat real não é detectado. Ableton Link ainda não está integrado; sua função futura como fonte externa de tempo/fase está descrita em grid-kicks.md. Baixo/densidade e seus limites estão em audio-multielementos.md. Histórico anterior preservado em validacao-v0.9.md e resultado-pytest-v0.9.txt.

1. Fechar a versão anterior e reabrir iniciar.cmd. Capturar a saída do Traktor e começar com quatro kicks regulares.
2. Abrir Rhythm Monitor e observar BPM, cursor e oito tempos. Durante breakdown sem kick, conferir continuidade e estado estimado.
3. Em Stage Preview, acompanhar a frase e a fase durante a pausa; verificar que o contador de kicks confirmados não aumenta só por previsão.
4. Comparar Pulso pelo relógio/Alternância A/B com Pulso por kick. Os dois primeiros seguem o grid; o último exige ataque confirmado.
5. Testar retorno real, oito kicks pós-drop, basslines agressivas e mudanças de andamento. Conferir contagem de correções/último desvio no palco.
6. Testar master, manual, blackout, pausa/parada e reabertura; acompanhar descartes e continuidade em Diagnósticos.
