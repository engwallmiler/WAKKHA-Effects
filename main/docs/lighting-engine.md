# Motor abstrato de iluminação — versão 0.17

## Escopo

A fase 6 transforma eventos de kick e o relógio musical em FixtureState. O Lighting Studio inspeciona esses estados com valores, cores e barras de intensidade. Stage Preview representa esses mesmos estados em um palco 2D. A versão 0.10 acrescenta uma grade contínua compartilhada e mantém os efeitos de baixo/densidade e kicks confirmados. O motor continua gerando estados abstratos, sem adaptador DMX ou Art-Net. O módulo opcional Link usa a rede local quando ativado pelo operador.

O inventário de demonstração contém quatro PARs RGBW e dois moving heads RGBW, divididos em grupos A/B e famílias wash/movers. As definições descrevem capacidades; os estados possuem intensidade e RGB normalizados em 0–1 e pan/tilt normalizados. PARs mantêm posição neutra; somente luminárias com capacidade pan/tilt recebem movimento. Posição normalizada ainda não representa graus físicos ou limites de um aparelho real.

## Separação de responsabilidades

- lighting/config.py: parâmetros validados e comandos operacionais imutáveis.
- lighting/fixtures.py: inventário abstrato inicial.
- lighting/colors.py: paletas automáticas por estrutura, energia e brilho do áudio.
- lighting/musical.py: perfis visuais por estrutura, energia, BPM e tensão.
- lighting/show.py: sequências relativas de oito tempos, viradas e seleção de famílias por textura.
- lighting/engine.py: efeitos determinísticos a partir de LightingInput e tempo monotônico.
- core/lighting_runtime.py: worker independente, adaptação dos snapshots musicais e publicação de LightingSnapshot.
- ui/lighting.py: controles e inspeção, sem geração de efeitos ou processamento musical.

O engine não recebe AudioBlock nem amostras. LightingInput contém apenas disponibilidade da fonte, frescor dos dados, kicks brutos/confirmados, instante da confirmação, BeatSnapshot, StructureSnapshot e TextureSnapshot. O relógio é projetado pela mesma função usada no Rhythm Monitor. Os algoritmos de kicks e BPM aprovados pelo usuário foram preservados.

O worker tem alvo de 60 Hz e agendamento por prazos absolutos, evitando acumular o arredondamento das esperas do Windows. A interface mostra a frequência efetivamente medida. Cada snapshot é imutável e contém todos os estados; a GUI pode consultar menos vezes sem controlar a execução do motor.

## Efeitos iniciais

| Efeito | Comportamento |
|---|---|
| Show rítmico · padrões, baixo e camadas | PARs com padrões de oito tempos e cores por tempo, respostas no contratempo por graves/densidade, viradas de dois tempos por aumentos sustentados da textura e cenas próprias para tensão/drop. Moving heads usam o perfil musical contínuo. Ver show-ritmico.md. |
| Pulso por kick | Usa somente kick confirmado no runtime; o envelope começa na confirmação, preservando o tempo de aquisição nos registros e a força relativa do último kick; envelope quadrático cai a zero na duração configurada. Um refinamento do mesmo kick não reinicia o pulso. |
| Pulso pelo relógio | Envelope a cada tempo da grade local, inclusive sem kick; usa o PLL como apoio antes da aquisição. |
| Alternância A/B por batida | Alterna os grupos pelos tempos da mesma grade contínua, com cruzamento suave nos primeiros 20% de cada período. Não afirma alternância por compasso. |
| Movimento ambiente | Intensidade base constante e movimento lento dos moving heads, independente de captura de áudio. |
| Automação musical · baixo, densidade e kicks | Base contínua de baixo/densidade e acentos confirmados em groove/aprendizagem. Velocidade acompanha BPM, energia, densidade, atividade grave, tensão e repetição; respiração mais luminosa e branco progressivo na subida; intensidade alta, retorno às cores saturadas e movimento amplo por oito kicks após retorno dos graves. Ver estrutura-musical.md. |
| Linha de baixo · envelope dos graves | Luz acompanha envelope e atividade de 30–250 Hz; movimento contínuo acompanha atividade/densidade, sem exigir BPM ou kick. |
| Densidade sonora · distribuição dos fachos | Ocupação espectral e ataques distribuem os fachos e modulam brilho/velocidade, sem exigir BPM ou kick. |

Os efeitos de relógio produzem movimento dos moving heads a partir de batidas e fase. Em ambiente, a referência de movimento é o tempo contínuo do próprio motor. Nos quatro efeitos iniciais, velocidade zero mantém posições neutras; pan varia aproximadamente entre 0,15–0,85 e tilt entre 0,30–0,70. No modo musical, Movimento limita a frequência automática. A frequência é suavizada e integrada em fase contínua, evitando saltos ao alterar tensão ou estado. Os movimentos convergem na tensão e ficam mais amplos no drop, sempre dentro de 0–1; velocidade zero congela a pose atual.

A paleta fornece cores A/B: menta/azul, âmbar/violeta, vermelho/azul ou branco. O perfil Automático usa azul/violeta no breakdown, clareamento na subida e vermelho/magenta no drop. Funciona também nos quatro efeitos anteriores, preservando suas regras de intensidade; uma cena por kick pode ficar escura quando não há kicks. O perfil Fixo usa a paleta selecionada. Manual usa sempre essa paleta. No modo musical, o drop troca A/B após quatro kicks. LightingSnapshot publica movement_hz e white_mix para inspeção. RGB é independente do dimmer; a intensidade geral multiplica a intensidade final de cada luminária. Nenhum mapeamento de canais é realizado.

## Controles e prioridades

Prioridade fixa inicial: **blackout → motor desativado → manual → automação**. O editor completo de regras, cenas e sequências pertence à fase 9.

Blackout zera intensidades no próximo processamento, sem aplicar fade. Permanece ativo enquanto o botão estiver ativo, inclusive ao trocar efeito, paleta ou intensidade. Desativar o motor também zera intensidades. Esses comandos preservam a última posição abstrata, sem continuar a movimentação automática.

O controle manual substitui os efeitos, incluindo intensidade e posição dos moving heads. Ele pode funcionar sem captura quando o motor estiver ativado. O master continua limitando a intensidade e blackout continua tendo prioridade. Master zero atua sobre a saída final, inclusive durante uma transição.

Mudanças de modo, cor, ativação ou posição manual podem interpolar o estado anterior pelo tempo de transição configurado. A intensidade dos pulsos não é continuamente filtrada depois dessa transição. Blackout, desativação e ausência de referência necessária interrompem a transição.

## Fonte e falhas

Efeitos musicais exigem captura em execução. Parar a captura retira imediatamente suas intensidades no próximo quadro. O pulso por kick exige dados recentes. Efeitos por relógio usam a grade local quando há estrutura/fonte/áudio recentes; ela continua mesmo sem kick. Antes de adquiri-la, exigem PLL sincronizado/estimado com período válido e confiança mínima de 0,35. Durante ausência de callbacks, o relógio pode ser projetado até perder confiança ou expirar, conforme o Beat Tracker.

Ambiente e manual são escolhas explícitas que continuam sem áudio. Falha do motor ou do provedor publica estados com intensidades zero, mantém o worker disponível e registra o erro uma vez. Uma alteração de controle permite nova tentativa; não há repetição automática excessiva de logs. Isso não interrompe o analisador de áudio.

Ao fechar a aplicação, o worker de iluminação encerra antes da captura. O fechamento só conclui após os workers encerrarem. O estado final tem todas as intensidades zero.

## Preferências e operação

| Parâmetro | Padrão | Limites |
|---|---|---|
| Efeito | Pulso por kick | Sete efeitos, incluindo baixo, densidade e automação musical. |
| Master | 80% | 0–100%. |
| Pulso | 240 ms | 80–1000 ms. |
| Transição | 300 ms | 0–3000 ms. |
| Movimento | 40% | 0–100%, velocidade relativa ao efeito; limite automático no modo musical. |
| Perfil de cores | Automático | Automático pelo áudio ou Fixo. |
| Paleta fixa / manual | Menta/Azul | Quatro paletas; usada também como apoio sem descritores. |
| Peso dos kicks confirmados | 70% | 0–100%; acentos da automação musical. |
| Peso da linha de baixo | 65% | 0–100%; base musical e efeito de baixo. |
| Peso da densidade sonora | 50% | 0–100%; base musical e efeito de densidade. |

Preferências JSON v12 migram v1–v11 preservando captura, DSP, kicks e BPM conhecidos. Os parâmetros de luz podem ser salvos durante a captura sem substituir o runtime de áudio. Ativação, manual e blackout são estados da sessão; ao abrir novamente, o motor começa desativado.

1. Reinicie iniciar.cmd e capture a saída usada pelo Traktor.
2. Abra Lighting Studio e marque Ativar motor.
3. Observe intensidades e cores na tabela; use rolagem para ver todas as luminárias.
4. Compare Pulso por kick e Pulso pelo relógio. O segundo aguarda sincronização do Beat Tracker.
5. Teste Alternância A/B e as posições dos moving heads. Ajuste master, paleta, duração e velocidade em tempo real.
6. Ative o controle manual e depois Blackout. Troque o efeito e confirme que o blackout permanece; libere para retomar.
7. Salve preferências ou exporte estados JSON para inspeção.

Stage Preview mostra fachos e movimentos produzidos por esses estados abstratos, com controles de ativação e blackout compartilhados. A validação musical/visual atual é sintética; equipamentos físicos continuam sem saída e não foram validados.

## Camadas de áudio

Em aprendizagem/groove, cores automáticas podem acompanhar densidade e graves: âmbar/violeta para textura densa, vermelho/azul para graves fortes com pouco brilho e menta/azul para textura leve. Breakdown/build-up/drop têm prioridade. Os efeitos de textura exigem descritores recentes (menos de 600 ms), escurecem no silêncio e continuam disponíveis mesmo se a análise estrutural ou o BPM falharem. A fonte precisa estar ativa. Pesos não desligam os perfis estruturais de tensão/drop. Ver audio-multielementos.md para fórmulas, suavização e limites.

## Relógio da grade — 0.10

LightingEngine usa grid_clock/project_grid para obter a mesma fase e índice da interface e da estrutura. Ausência de kick não pausa efeitos explicitamente pelo relógio; isso não cria KickEvent, não dispara Pulso por kick e não avança o contador real do drop. Dados antigos, silêncio e captura parada retiram as intensidades musicais. O PLL acústico permanece separado. A correção grande é aplicada apenas após quatro ataques regulares com perfil estrito. Na versão 0.17, Link também pode fornecer o relógio efetivo de BPM/fase. A escolha vale para a grade da GUI e dos efeitos; a grade acústica interna e as confirmações de kick continuam independentes. Veja ableton-link.md.

## RGBW e cenas em camadas — 0.12

FixtureState acrescenta white como canal independente e mantém color como RGB. lighting/rgbw.py transfere o branco comum das paletas ao W, preserva o manual independente e recompõe a cor para o palco. O inventário contém seis pontos RGBW; fixtures legadas RGB seguem aceitas. Blackout, falha e encerramento zeram os quatro canais. Show RGBW acrescenta quatro famílias, variação de 16 tempos, subdivisão por densidade, matiz e acentos W. Settings v8 migra v1–v7 com dois ajustes novos; a exportação usa versão 2 e color_model RGBW. Ver rgbw-show.md para operação, contratos e limites.

## Ciclos de oito e alinhamento visual — 0.13

lighting/phrase_clock.py alinha o ciclo pelo timestamp do clique sem alterar o grid acústico. lighting/phrase.py mantém motivos de oito, troca por novidade na fronteira e preparação global. O engine aplica esse ganho após as transições. Build/drop cobrem os motivos sem descartar uma troca pendente; o drop mantém oito confirmações e usa uma fase inteira por tempo, com saída antecipada apenas em retirada real/silêncio/interrupção. Settings v9 migra v1–v8; comandos de sincronização são da sessão. Ver ciclos-oito.md.

## Coordenação e acesso aos ciclos — v0.14

Após a interpolação das cenas automáticas, o motor coordena os moving heads: intensidade conjunta, RGBW da referência, pan espelhado e tilt igual. A passagem comum cobre todos os efeitos, sem alterar os padrões espaciais dos PARs. Manual conserva seus valores; velocidade zero conserva as posições.

O botão principal do palco seleciona phrase_show. Sincronizar 1/8 valida a captura e a grade recentes, ativa o modo e envia o timestamp em um único comando; a entrada sincronizada não herda o fade entre modos. Contador, motivo e estado do alinhamento aparecem acima do palco.

LightConfig/Settings v10 acrescentam light_phrase_variation (two_cycles/cycle/texture). A contagem avança em fronteiras futuras e não conta uma aquisição parcial. Novidade e prazo coincidentes causam uma única troca. Repetir a sincronização preserva o motivo e reinicia a contagem e o cooldown de novidade na nova origem. LightingSnapshot inclui phrase_pattern e phrase_repetition, inclusive quando uma cena estrutural cobre o motivo. Exportação permanece v2/RGBW.

## Ritmos dos PARs e mudanças de contexto — v0.15

lighting/patterns.py define 20 motivos, incluindo oito articulações em colcheias, e um sorteio que evita repetição recente/família. lighting/novelty.py integra seis descritores em janelas musicais e compara mudanças nos dois sentidos ao contexto anterior. O sequenciador mantém o motivo estável e troca no próximo início de oito. Settings v11 acrescenta sensibilidade de mudança; versões anteriores recebem 1,0.

ShowSequencer escolhe variantes de build nas fronteiras e de drop na entrada, conservando a contagem e os envelopes principais. A projeção de fase do Show cíclico também chega às cenas estruturais. Um clique de sincronização gera acento coletivo curto somente no groove, preservando paleta fixa e prioridades.

Stage Preview apresenta um botão liga/desliga real, seletor compartilhado e ParPatternView que lê máscaras/fase do snapshot. Mostra a confirmação do clique e o motivo da troca sem analisar áudio na GUI. Os moving heads continuam coordenados na passagem comum do engine. Ver ciclos-oito.md.

## Moves, fades calmos e retorno estrito — v0.16

MoverSequencer produz intensidade, RGB e W conjuntos, preservando as posições do motor musical; a coordenação final mantém o espelhamento. BreakdownWash produz luz sustentada e fades lentos independentes do grid, com histerese e mistura por tensão/energia/roll. A prévia usa faixas contínuas no modo calmo. O banco de PARs tem 28 motivos.

Settings v12 acrescenta os seletores de ritmo dos moves e estilo calmo. LightingSnapshot expõe mover_rhythm, breakdown_calm e breakdown_blend; StructureSnapshot expõe rejected_returns.

KickIdentity.return_matches é consultado antes de reconciliar a grade nos estados de retorno. Aceitar um candidato pela triagem normal não basta para criar drop ou reescrever a referência treinada. O perfil inclui contraste de ataque, além de forma espectral, decaimento e relação harmônica. A aquisição em quatro referências e a contagem de oito kicks do drop permanecem. Ver ciclos-oito.md e validacao.md.
