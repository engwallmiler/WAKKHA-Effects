# Validação — versão 0.14.1

Registro: 2026-10-14 (UTC). A preferência do usuário passa a ser o padrão: **mudar somente com novos elementos**, mantendo o motivo em trechos estáveis e trocando na próxima fronteira de oito tempos. As opções de rotação programada continuam disponíveis.

LightConfig e Settings usam light_phrase_variation=texture; preferências v1–v9 recebem esse valor na migração. A configuração local encontrada era v9 com padrão automático e sem política de variação, portanto adotará a escolha ao reabrir, preservando os demais ajustes. Não foi necessário escrever no arquivo de preferências fora do projeto.

**77 testes de ciclos, configuração e GUI passaram em 16,32 s**. Incluem repetição estável, troca após novidade sustentada, quantização, migração, sincronização, prioridades e persistência. A regressão completa de 443 testes da versão 0.14.0 está registrada em validacao-v0.14.md; não foi repetida para esta alteração de preferência.

O ensaio sintético de 21 s manteve Todos juntos nos cinco ciclos observados após sincronizar: nenhuma troca programada e nenhuma novidade pendente. Foram recebidos 1967 blocos, com zero descartes/erros de continuidade. Os moving heads ficaram coordenados em 1253 quadros verificados, a geometria permaneceu estável e o motor terminou a 60 Hz. Sincronização marcou 1/8 preservando a origem do grid, com quatro retornos após fade. Encerramento limpo e intensidade/RGBW final zero.

Evidência: resultado-ciclos-synthetic-v0.14.1-texture.json. O script aceita uma política opcional como segundo argumento (texture, cycle ou two_cycles); sem argumento usa o padrão atual.

Os ensaios são sintéticos. Os motivos e os efeitos estruturais de tensão/drop continuam funcionando sobre descritores heurísticos; não há separação literal de instrumentos. Sem saída física DMX.
