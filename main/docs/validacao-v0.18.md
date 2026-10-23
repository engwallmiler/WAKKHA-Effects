# Validação — versão 0.18

Registro: 2026-10-22 (UTC). Windows x64, Python 3.12.10; preferências v13; pacote 0.18.0. Sem saída física DMX.

## Regressão

**604 testes passaram em 105,83 s**, incluindo os 586 anteriores e 18 novos. Evidências: docs/resultado-pytest-v0.18.txt e docs/resultado-pytest.txt.

Dezoito novos casos verificam média em potência linear, resistência a acentos isolados, ganhos de entrada diferentes, independência da intensidade normalizada, kicks fracos em ritmo dobrado, retorno no primeiro kick forte, ausência sem eventos fictícios, pausa curta com perfil preservado, silêncio longo com descarte do perfil e prioridade de luz apagada. A compensação do fundo melódico após pausa é exercitada junto da rejeição de harmônicos adicionais.

O caminho completo de áudio foi testado em quatro combinações de ganho (1,0 e 0,25) e relógio (áudio e provedor Link), com kicks fracos em frequência dupla durante o build e meio segundo de silêncio antes do retorno real. Os testes exigem primeiro drop no kick de 20 s, início em menos de 180 ms de descritores, ausência de drop antecipado, oito confirmações reais e nenhuma falha de continuidade. Os testes anteriores de bassline percussiva/harmônica e correção de fase continuam aprovados.

## Confirmação e correção de fase

No rastreio do sinal com pausa, o primeiro ataque ocorreu perto de 20 s e o estado de drop apareceu em aproximadamente 20,085 s de descritores. Esse valor não inclui todos os atrasos entre saída do Traktor, WASAPI, análise e apresentação. O retorno preparado usa cerca de 90 ms de dados apenas para candidatos já alinhados; candidatos fora da grade conservam 120 ms, mantendo a evidência completa exigida pela correção de fase/BPM.

A avaliação inicial encontrou que a volta conjunta da melodia após silêncio excedia o limite harmônico do kick, atrasando a entrada para o kick seguinte. A compensação considera somente o fundo harmônico aprendido, com teto de 6% da potência do ataque; identidade, energia, decaimento e grade continuam obrigatórios. Uma regressão específica verifica que um baixo com excesso harmônico continua bloqueado.

## Palco e integração

Ensaio de 26 s com scripts/validate_phrases.py structure_demo: **2.436 blocos, zero descartes e zero falhas de continuidade**. Os oito kicks do drop tiveram pico 0,8 e duração maior que 350 ms por posição. O ciclo seguiu os oito passos durante ausência de kicks; os moves permaneceram coordenados, o palco manteve uma geometria e o encerramento zerou os canais. A iluminação fechou em 60 Hz. Evidência: docs/resultado-ciclos-structure_demo-v0.18.0-texture.json; prévia: preview-cycles-structure_demo-drop-eight.png.

O palco mostra a razão de potência do último retorno, a quantidade de ataques fracos bloqueados e a pausa recente em suas linhas já existentes. O tamanho dessas linhas permanece fixo. O JSON de diagnóstico contém DropEvidenceSnapshot junto da estrutura.

A sincronização Traktor/Link da versão anterior foi avaliada positivamente pelo usuário. Nesta rodada, o relógio Link é exercitado por snapshots/provedor, sem abrir uma nova sessão de rede ou controlar decks. Não foram fornecidos arquivos das tracks citadas; a calibração com esse repertório continua sendo avaliação operacional.

## Operação

Reabra iniciar.cmd para carregar a nova versão. As preferências v13 e os ajustes Link são preservados. Nenhuma preferência real em AppData foi editada diretamente. Os limiares são internos e a detecção segue heurística: a ausência de cerca de oito tempos reforça a prontidão, mas não força uma previsão de drop nem cria kicks.

Critérios, potências, tempos e limites: [drop-detection.md](drop-detection.md). A validação anterior está em validacao-v0.17.md.
