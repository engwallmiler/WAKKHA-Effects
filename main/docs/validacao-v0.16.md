# Validação — versão 0.16

Registro: 2026-10-14 (UTC). Windows x64, Python 3.12.10. Preferências v12; exportação v2/RGBW. Sem saída DMX, rede ou Link.

## Regressão

**547 testes passaram em 82,68 s**, incluindo os 493 anteriores. Os 54 casos adicionais cobrem os oito novos motivos de PARs e suas colcheias, os oito ritmos dos moves, repetição/cores/espelhamento, mudança por contexto, paleta fixa, quatro estilos calmos em dois BPMs, fades equivalentes em grades diferentes, histerese, prioridades, persistência/migração, prévia e controles da GUI.

A proteção do drop foi exercitada com ataques que passam a triagem normal mas falham na identidade estrita por decaimento, forma espectral ou harmônicos. Há regressões da referência contaminada por bassline e da atualização legítima por variação de kick. Dois ensaios DSP completos com notas graves no grid, sem kick, passaram em ganhos 1,0 e 0,25, sem criar drop e com retornos bloqueados. Os retornos reais do demo estrutural continuam entrando no drop e mantendo as oito posições.

A primeira regressão completa encontrou que a nova camada dos moves acendia mesmo com todos os pesos zerados em Automação musical. Nesse modo, ela agora é modulada pelo leito de energia já produzido pelos controles existentes. Os 53 testes relacionados passaram, seguidos da regressão completa aprovada. Motivos dos shows continuam tendo seu relógio próprio e contribuições de baixo/densidade.

Evidências: resultado-pytest-v0.16.txt e resultado-pytest.txt. O histórico anterior está em validacao-v0.15.md.

## Ensaios com palco aberto

O script validate_phrases.py executou as fontes sintéticas contínua (21 s), textura (23 s) e estrutura (26 s), com política texture e GUI offscreen. Estrutura e textura foram conferidas novamente após proteger a aprendizagem do perfil de kick.

| Fonte | Blocos | Quadros com moves coordenados | Ritmos MOV observados | Amostras de cor quantizadas | Quadros calmos | Último quadro |
|---|---|---|---|---|---|---|
| synthetic | 1966 | 1253 | 2 | 25 | 0 | 0.287 ms |
| texture_demo | 2155 | 1371 | 4 | 48 | 0 | 0.289 ms |
| structure_demo | 2437 | 1543 | 2 | 25 | 256 | 0.329 ms |

Nos três ensaios houve zero descartes, zero erros de continuidade e nenhum erro de análise/iluminação. A geometria ficou única em cada execução: x=0, y=477, largura=1157, altura=300. Os moving heads tiveram RGBW/intensidade e tilt iguais, com pan espelhado em todos os quadros verificados. O motor ficou em cerca de 60 Hz, encerrou limpo e zerou intensidade/RGBW.

As amostras de cor são RGB aparente arredondado a uma casa decimal, incluindo a contribuição W; não representam bancos de cores discretas. No sinal de textura foram vistos Sustentação de quatro tempos, Pulso duplo, Ondas de oito tempos e Cortes e sustentação. No contínuo, o motivo dos PARs permaneceu em Perseguição por cinco ciclos após sincronizar, sem novidade pendente. A preferência de não girar em trechos estáveis foi preservada.

## Breakdowns calmos

O ensaio estrutural registrou 256 quadros de breakdown calmo. Na janela de 9,5–11,5 s, a maior diferença entre intensidades de PARs em quadros observados consecutivos foi 0,000768 (menos de 0,1 ponto percentual), mostrando fades suaves em lugar de pulsos por tempo. A cena calmo mantém luz sustentada e transita para build-up conforme aumentam tensão/energia.

preview-cycles-structure_demo-calm.png foi inspecionada com tensão de 16%, Aurora de cores/fade livre e PARs sustentados em cerca de 10–19%. A prévia usa faixas contínuas no modo calmo. O seletor em Lighting Studio oferece respiração lenta, aurora, passagem suave e brilho sustentado. Os testes confirmam equivalência dos fades em períodos 0,40 e 0,66 s.

## Retorno estrito e oito kicks

O detector agora verifica identidade de retorno antes de reconciliar a grade em breakdown/build-up. Somente descritores próximos do kick aprendido, com ataque/decaimento adequados e limite harmônico estrito, autorizam esse retorno. Candidatos da triagem ampla não podem reescrever o perfil já treinado. No ensaio de textura, dois retornos foram bloqueados e não houve drop na bassline.

A saída normal do drop continua no nono confirmado. O ensaio estrutural preservou todos os oito, com pico no master de 80%:

| Kick | Intervalo observado | Duração observada | Pico nos PARs |
|---|---|---|---|
| 1 | 20.156–20.641 s | 0.485 s | 80% |
| 2 | 20.656–21.156 s | 0.500 s | 80% |
| 3 | 21.172–21.672 s | 0.500 s | 80% |
| 4 | 21.672–22.141 s | 0.469 s | 80% |
| 5 | 22.156–22.625 s | 0.469 s | 80% |
| 6 | 22.641–23.141 s | 0.500 s | 80% |
| 7 | 23.156–23.609 s | 0.453 s | 80% |
| 8 | 23.656–24.141 s | 0.485 s | 80% |

## Groove, sincronismo e preparação

O banco de PARs tem 28 motivos. No ensaio de textura, Perseguição mudou para Abertura em leque em cerca de 7,06 s; Pergunta e resposta apareceu ao retornar ao groove em cerca de 20,56 s. Foram vistos três programas e 12 conjuntos de PARs na saída.

O clique continuou marcando 1/8 sem alterar a origem acústica, com acento mínimo de 76% nos quatro PARs (95% antes do master de 80%). O fade de preparação agora usa curva quadrática, escurecendo também ritmos de MOV sustentados; o apagão breve foi observado em 13 quadros no ensaio de textura, com retorno automático. A contagem continuou nos oito tempos das janelas sem kick.

Evidências: resultado-ciclos-synthetic-v0.16.0-texture.json, resultado-ciclos-texture_demo-v0.16.0-texture.json e resultado-ciclos-structure_demo-v0.16.0-texture.json.

## Avaliação com faixas reais

1. Fechar a versão anterior, reabrir iniciar.cmd e iniciar a captura usada pelo Traktor.
2. Manter Show de 8 LIGADO, Ritmo dos PARs em Automático e Cores automáticas para a rotação de matiz dos moves.
3. Em Lighting Studio, comparar Ritmo dos moves e Breakdown calmo. Salvar preferências mantém as escolhas; o padrão dos dois seletores é automático.
4. Conferir pads/melodias calmas com luz sustentada, entrada de camadas no groove e retomada do kick. O detalhe estrutural mostra retornos graves bloqueados.

Os sinais são sintéticos e não reproduzem as tracks do último teste do usuário. A proteção é mais conservadora: novos kicks com timbre muito diferente podem ser recusados. O sistema continua heurístico e não separa instrumentos. A grade prevista não cria kicks; perdas de confirmação podem prolongar o drop. Detalhes em ciclos-oito.md.

Instalação confirmada: código/pacote 0.16.0 / 0.16.0. Preferências locais carregaram como v12, ritmo dos moves auto, breakdown auto e cores automáticas, sem alterar o arquivo original. compileall passou; iniciar.cmd --help terminou com código zero. preview-cycles-texture_demo-movers.png foi inspecionada com os dois moves violetas em 70%, pan espelhado e um PAR verde executando o groove.
