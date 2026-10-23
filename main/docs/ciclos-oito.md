# Ciclos e ritmos dos PARs — versão 0.17

## Ativar e comparar

Reabra iniciar.cmd, inicie a captura e deixe **Show de 8 · LIGADO** no Stage Preview. Ative o motor. O botão agora é liga/desliga: desligado seleciona o Show RGBW contínuo, ligado seleciona Show cíclico · 8 tempos. Isso permite comparar os modos; um botão já ligado não é um novo comando de ativação.

Em **Ritmo dos PARs**, selecione Automático ou um dos 28 motivos. O seletor é compartilhado com Padrão do ciclo de oito em Lighting Studio. A grade logo abaixo mostra quatro linhas (PAR 01–04) e 16 colcheias (duas por tempo). Blocos representam os disparos do desenho; a coluna em destaque acompanha a fase. A grade inclui o acento coletivo inicial. Camadas reativas e envelopes luminosos também afetam a saída.

## Um ciclo de oito tempos

O ciclo continua tendo oito tempos, assumindo 4/4. Cada motivo combina ordem espacial, pausas, duração, acentos e, em 16 dos motivos, disparos de colcheia. A sequência se repete integralmente em oito; não são 64 tempos.

O tempo 1 inclui um acento coletivo curto para tornar a fronteira perceptível, inclusive em pares e contratempos. Os demais tempos executam o motivo selecionado. A escolha automática começa com Perseguição ou Perseguição dupla em áudio denso; não favorece Pares alternados.

| Motivos | Comportamento |
|---|---|
| Todos juntos, Perseguição, Sequência inversa, Vai e volta | Pulsos coletivos ou individuais, com acentos e durações |
| Pares alternados, Espelho, Cruzamento | Conjuntos espaciais diferentes |
| Acumulação, Onda, Perseguição dupla, Pergunta e resposta, Resposta do baixo | Expansões, percursos e respostas |
| Síncope, Chamada no contratempo, Contratempos | Deslocamentos de ataques e pausas |
| Escada com pausas, Saltos, Pêndulo | Percursos com articulações em colcheias |
| Cortes rítmicos, Pulso duplo | Cortes e disparos duplos |
| Cometa, Ondulação com pausa, Trançado, Abertura em leque | Percursos e expansões em colcheias |
| Sequência atrasada, Galope, Órbita, Ecos de pares | Deslocamentos, respostas e ecos |

Os moving heads mantêm pan espelhado, tilt igual, mesma intensidade e RGBW. Seu movimento musical continua separado da ordem espacial dos PARs. Na v0.16, Ritmo dos moves oferece oito famílias, com o automático reagindo às trocas de contexto. Cor percorre quatro posições de matiz por ciclo em modo automático, com acentos W; modo fixo mantém a paleta. Pan/tilt não são recalculados pelo sequenciador de ritmo. Manual, master, blackout e movimento zero mantêm prioridade.

## Mudanças significativas e sorteio controlado

A preferência padrão continua **Mudar somente com novos elementos**. O sistema mede alterações da mixagem; não identifica instrumentos individualmente. A partir da v0.15, compara densidade, ocupação, graves, atividade do baixo, taxa de ataques e brilho, considerando aumentos e reduções.

As amostras são integradas em janelas do período musical (limitado a 0,25–0,8 s), com referência inicial de duas janelas. A comparação usa médias, reduzindo a influência do ataque de cada kick. Pequenas flutuações acompanham lentamente o leito; alterações progressivas maiores permanecem comparadas ao contexto anterior. A troca aceita estabelece uma nova referência.

**Sensibilidade às mudanças do áudio**, em Lighting Studio, varia entre 50% e 200%, com 100% por padrão. Limiares normalizados em 100%: densidade 0,11; ocupação 0,13; graves 0,16; atividade do baixo 0,10; ataques 1,8/s; brilho 0,10. São critérios heurísticos, não probabilidades. Ganho/filtro e retiradas de camadas também podem acioná-los.

Uma mudança detectada agenda o próximo tempo 1/8. O ciclo atual termina antes da troca. Há intervalo entre disparos, e novidade junto com programação produz uma única troca. O palco mostra o descritor que agendou a mudança.

O sorteio acontece somente na troca, nunca por quadro. Evita a família atual e os últimos desenhos; o gerador tem semente fixa para reprodução de ensaios, enquanto a sequência de eventos determina as escolhas. A escolha fica congelada até a próxima mudança. **Variedade do show** abaixo de 35% restringe o banco; acima libera todos os motivos. Modos opcionais continuam disponíveis para mudar a cada ciclo ou após dois ciclos. Padrões fixos não são substituídos.

Build-up, breakdown e drop cobrem o motivo do groove. Uma troca pendente sobrevive à cobertura e pode ser aplicada na fronteira; aparece ao retornar ao groove. Parada, silêncio e correção da grade reiniciam o contexto.

## Sincronizar com resultado visível

Após adquirir a grade, pressione **Sincronizar 1/8** no primeiro tempo desejado. O comando usa o timestamp do clique, ativa o Show cíclico e alinha a fase sem modificar BPM, grid acústico ou contador do drop.

No groove, o clique acende os quatro PARs por 220 ms com intensidade mínima normalizada de 95%, antes do master. Em cores automáticas usa branco; em paleta fixa preserva as cores escolhidas. O palco confirma SINCRONIZADO por aproximadamente 1,2 s. O acento não fica retido, não troca o motivo e não cria um kick.

Nas cenas estruturais, a sincronização também alinha a fase real dos PARs; a contagem de kicks do drop é preservada. O acento branco extra não cobre tensão/drop. Manual, blackout, silêncio, dados antigos e motor desativado bloqueiam o acento.

O botão exige captura recente, grade utilizável e motor ativo. Repetir o clique preserva o motivo e reinicia a contagem de repetições. O alinhamento pertence à sessão; parada/troca de fonte, correção grande e a origem de um novo drop retiram a referência anterior.

## Breakdowns calmos

BreakdownWash integra uma fase lenta pelo tempo decorrido, independente do período da grade. Com tensão <0,45, energia <0,65 e roll <0,25 na entrada, começa em luz sustentada. A manutenção tem histerese (entrada abaixo de tensão 0,38/energia 0,60/roll 0,20; saída acima de 0,52/0,75/0,35) e mistura com constante de 0,65 s.

Respiração lenta, Aurora de cores, Passagem suave e Brilho sustentado usam ciclos de 6–14 s e mantêm um piso luminoso. A prévia exibe faixas contínuas, sem blocos de ataques. Build/drop retiram essa camada. Manual, blackout, silêncio e dados antigos mantêm prioridade.

## Builds, drops e preparação

O build tem quatro desenhos: escada crescente, cruzamentos, ondas e chamadas coletivas. Um desenho fica estável no ciclo; a próxima fronteira de oito pode escolher outro. Tensão/roll continuam acelerando os pulsos e clareando as cores.

O drop tem quatro desenhos de impacto, com respostas adicionais em contratempos em duas variantes. O sorteio ocorre ao entrar na cena; os impactos principais conservam fase de tempo inteiro, pico e piso luminoso. A saída normal permanece no nono kick confirmado, após os oito primeiros. Falhas de detecção com graves presentes não encurtam a cena; ausência real dos graves, silêncio e dados antigos mantêm prioridade.

Antes de cada ciclo de groove, Fade-out rápido, Apagão breve ou Sem preparação continuam disponíveis. Duração padrão 140 ms, ajustável 40–300 ms e limitada a 40% do período. O fade usa uma curva quadrática para escurecer também os moves sustentados. O ganho global retorna no tempo 1; não altera o BLACKOUT manual.

## Proteção de retorno do kick

Entrar no drop deixa de usar apenas a triagem normal. Antes de reconciliar a grade ou aceitar um retorno durante breakdown/build, KickIdentity exige confiança >=0,55, pelo menos quatro referências compatíveis, cosseno espectral >=0,90, decaimento próximo do aprendido, ataque grave com contraste mínimo e limite harmônico mais estrito. Descritores legados sem espectro mantêm compatibilidade nos testes; o extrator real fornece perfil.

A referência também só aprende novos descritores depois das quatro sementes quando estes passam a identidade estrita. Isso impede que basslines admitidas pela triagem ampla substituam gradualmente o kick aprendido. StructureSnapshot.rejected_returns e o detalhe do palco registram bloqueios. O contador do drop e os oito kicks não foram alterados. Perfis novos ou kicks muito diferentes podem ser recusados: a heurística é mais conservadora, sem prometer separação de instrumentos.

## Contratos e preferências

Settings v12 acrescenta light_mover_pattern e light_breakdown_style com auto; v1–v11 migram preservando as escolhas conhecidas. A sensibilidade light_change_sensitivity continua com 1,0 e preservando efeito, padrão, política de variação, áudio e RGBW. O padrão de política segue texture. LightingControls mantém os comandos de sincronismo da sessão.

LightingSnapshot inclui phrase_sync_flash, phrase_change_reason, show_rhythm, show_masks e show_phase, além de mover_rhythm, breakdown_calm e breakdown_blend. As máscaras de 16 colcheias descrevem o programa; estados RGBW descrevem a saída aplicada. Ao falhar ou encerrar, estados e diagnósticos de execução são limpos. Exportação permanece v2/RGBW.

Evidências em validacao.md. Os ensaios são sintéticos; a avaliação com tracks reais continua necessária. Não há saída física DMX. A versão 0.17 integra o relógio Link à grade dos efeitos; kicks e estrutura permanecem acústicos. Veja [ableton-link.md](ableton-link.md).
