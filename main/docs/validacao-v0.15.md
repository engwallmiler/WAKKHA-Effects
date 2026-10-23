# Validação — versão 0.15

Registro: 2026-10-14 (UTC). Windows x64, Python 3.12.10. Preferências v11 e estados v2/RGBW. Sem saída DMX, rede ou Link.

## Regressão

**493 testes passaram em 123,77 s**, incluindo os 443 anteriores. Os 50 casos adicionais cobrem os 12 motivos novos, ritmos em colcheias, mudanças positivas/negativas em seis descritores, ritmo repetitivo sem trocas, mudança gradual, sensibilidade/migração, sorteio sem repetir família/motivos recentes, groove denso sem pares fixos, acento de sincronismo aplicado aos quatro PARs, paleta fixa, prioridades, sincronismo real das cenas estruturais sem alterar a contagem, variação dos builds/drops, grade de breakdown, botão liga/desliga e seletor compartilhado.

As expectativas antigas de uma rotação fixa (Todos juntos → Perseguição → Inversa) foram substituídas por verificações de manutenção dentro do ciclo, mudança na fronteira, famílias diferentes e preservação do motivo ao ressincronizar. A opção por novidade continua sendo o padrão, sem rotação por tempo decorrido.

Evidências: resultado-pytest-v0.15.txt e resultado-pytest.txt. As verificações de geometria em três tamanhos, RGBW, captura/DSP, rejeição de bassline, grid contínuo, oito kicks do drop e coordenação dos moves continuam passando.

## Ensaios em tempo real

scripts/validate_phrases.py executou sinal contínuo por 21 s, textura por 23 s e estrutura por 26 s, com GUI real em modo offscreen e fontes sintéticas sem reprodução de som. Todos usaram a política texture. O script também verifica ativação do Show cíclico pelo sincronismo vindo do modo anterior.

| Fonte | Blocos | Quadros com moves coordenados | Programas de groove observados | Quadros de acento do clique | Último quadro do motor |
|---|---|---|---|---|---|
| synthetic | 1967 | 1255 | 1 | 13 | 0.336 ms |
| texture_demo | 2154 | 1373 | 3 | 13 | 0.310 ms |
| structure_demo | 2435 | 1552 | 1 | 12 | 0.244 ms |

Nos três ensaios: zero descartes de blocos, zero erros de continuidade, nenhum erro de análise/iluminação, uma geometria de palco por execução (0, 477, 1157, 300), encerramento limpo e RGBW/intensidade final zero. Os moves tiveram mesma intensidade, RGBW e tilt, com pan espelhado em todos os quadros verificados. O motor ficou em cerca de 60 Hz.

O clique foi observado no tempo 1/8 preservando a origem acústica. Os quatro PARs atingiram no mínimo 76% durante o acento, correspondente a 95% antes do master de 80%. O acento voltou ao motivo automaticamente.

## Groove: repetição e troca por áudio

No sinal contínuo, Perseguição permaneceu nos cinco ciclos após sincronizar, sem novidade pendente. Foram observados disparos individuais de cada PAR, o acento coletivo e repouso; o motivo não girou por tempo decorrido.

No ensaio de textura, Perseguição mudou para Saltos em 7,063 s, após o início da bassline em 6 s. Saltos repetiu nos ciclos 2 e 3. A entrada de camadas em 12 s agendou outro motivo, mantido durante a cobertura do build-up. Pergunta e resposta apareceu na volta ao groove em 20,563 s. Foram vistos três programas de groove e sete conjuntos de PARs na saída efetiva, incluindo luzes individuais, par final e coletivo.

Os motivos de mudança registrados foram ocupação ↑, densidade ↑ e graves ↓. O sistema mede alterações da mixagem, incluindo retiradas; não identifica instrumentos. Os testes determinísticos também cobrem brilho e atividade/ataques, transientes isolados e mudanças graduais.

O palco mostra um seletor de 20 motivos e uma grade dos disparos dos quatro PARs em 16 colcheias. preview-cycles-texture_demo-variation.png foi inspecionada com Saltos no primeiro tempo, desenho com contratempos/pausas, Show de 8 LIGADO e moves espelhados. preview-cycles-synthetic-sync.png mostra SINCRONIZADO e os quatro PARs brancos.

## Build, preparação e drop

No ensaio de textura, o build passou por Cruzamentos, Escada crescente e Ondas nas fronteiras do ciclo. O ensaio estrutural também usou Abertura e resposta no drop. Os desenhos têm escolhas por fronteira/entrada; não são sorteados por quadro. A preparação registrou fade nos três sinais e 11 quadros de apagão breve no sinal de textura, sem travar o BLACKOUT manual.

Nas janelas sem kick, as oito células continuaram avançando, enquanto os kicks confirmados permaneceram constantes em 11 (textura) e 15 (estrutura).

O drop manteve todas as oito posições; cada uma atingiu o master de 80%. O oitavo ficou até a chegada do nono confirmado:

| Kick | Intervalo observado | Duração observada | Pico nos PARs |
|---|---|---|---|
| 1 | 20.172–20.672 s | 0.500 s | 80% |
| 2 | 20.672–21.157 s | 0.485 s | 80% |
| 3 | 21.188–21.657 s | 0.469 s | 80% |
| 4 | 21.672–22.172 s | 0.500 s | 80% |
| 5 | 22.172–22.657 s | 0.485 s | 80% |
| 6 | 22.657–23.157 s | 0.500 s | 80% |
| 7 | 23.172–23.657 s | 0.485 s | 80% |
| 8 | 23.672–24.157 s | 0.485 s | 80% |

Evidências: resultado-ciclos-synthetic-v0.15.0-texture.json, resultado-ciclos-texture_demo-v0.15.0-texture.json e resultado-ciclos-structure_demo-v0.15.0-texture.json.

## Instalação e avaliação no Traktor

O pacote 0.15.0 usa as dependências já preparadas no runtime Python 3.12. O venv incompleto permanece preservado e iniciar.cmd mantém seu fallback.

1. Fechar a versão anterior, reabrir iniciar.cmd e iniciar a captura da saída usada pelo Traktor.
2. Deixar Show de 8 LIGADO, ativar o motor e manter Ritmo dos PARs em Automático.
3. Após adquirir a grade, clicar Sincronizar 1/8 no início desejado. Conferir confirmação, acento coletivo e coluna inicial.
4. Comparar motivos como Síncope, Pulso duplo, Contratempos e Escada com pausas pelo seletor do palco. Voltar a Automático para reagir às mudanças.
5. Se necessário, ajustar Sensibilidade às mudanças do áudio em Lighting Studio e salvar preferências de luz. A política padrão continua mudando somente por contexto.

Os ensaios são sintéticos e não reproduzem as tracks do último teste do usuário. Densidade, ocupação e brilho não são contagem/separação literal de instrumentos. Ganho/filtro também podem disparar mudanças. Oito tempos são relativos à grade; o downbeat real não é reconhecido. Kicks não confirmados podem prolongar o drop. Histórico anterior: validacao-v0.14.1.md e validacao-v0.14.md. Detalhes: ciclos-oito.md.

Instalação conferida: código/pacote 0.15.0 / 0.15.0. As preferências locais carregaram como v11 / auto / texture / sensibilidade 1,0, sem alterar o arquivo original. compileall passou e iniciar.cmd --help terminou com código zero usando o runtime preparado.
