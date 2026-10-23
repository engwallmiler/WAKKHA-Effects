# Validação — versão 0.12

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10 e dependências existentes. Código e pacote instalado conferidos: **0.12.0 / 0.12.0**; preferências **v8**; exportação de estados **v2 / RGBW**. Sem saída física ou transmissão de rede.

## Regressão

**355 testes passaram em 78,98 s**, incluindo os 313 anteriores. Os 42 novos casos cobrem transferência RGB→RGBW sem duplicar branco, primárias/pastéis/branco puro, ajuste W sem alterar a cor de paleta, inventário RGBW e compatibilidade RGB, manual independente, master e prioridades, interpolação, falha/parada sem W retido, validação de canais/ajustes, migração v1–v7, persistência v8, evolução de 16 tempos, subdivisão densa, complexidade baixa, paleta fixa, candidatos rejeitados sem acentos W e integração real dos controles/tabela/persistência pela GUI.

Testes anteriores de cor passam a comparar a composição visível RGB+W, pois color agora contém os canais RGB residuais. O teste de perfil automático em efeito anterior usa ambiente com intensidade ativa; estados apagados agora zeram os quatro canais. As verificações anteriores de áudio, grade, baixo agressivo, kicks, estrutura, prioridades e geometria continuam passando. A análise acústica não foi modificada.

Evidências: resultado-pytest-v0.12.txt e resultado-pytest.txt. compileall de src/scripts passou; reinstalação local sem dependências novas concluída. O runtime inicializa com versão 0.12.0 e Settings.version 8.

## Ensaios Qt com Show RGBW e palco aberto

scripts/validate_show.py executou separadamente as fontes sintéticas structure_demo e texture_demo, mantendo o novo modo ativo. Cada estado foi conferido com R/G/B/W normalizados e todos os pontos receberam W durante o ensaio. Nenhum áudio foi reproduzido pelos alto-falantes.

| Medida | Estrutura | Baixo e densidade |
|---|---|---|
| Duração | 26 s | 23 s |
| Blocos recebidos | 2437 | 2154 |
| Descartes / falhas de continuidade / erros | 0 / 0 / nenhum | 0 / 0 / nenhum |
| Motor, última janela | 60 Hz | 60 Hz |
| Maior tempo de iluminação observado | 1,23 ms | 0,95 ms |
| W máximo nos PARs, antes do dimmer | 95,05% | 100,00% |
| W máximo nos moving heads, antes do dimmer | 98,67% | 97,75% |
| Viradas por textura | 0 | 2 |
| Tempos observados sem kick | 1–8 | 1–8 |
| Kicks confirmados na janela sem kick | Constante em 15 | Constante em 11 |
| Retângulos do palco observados | 1 | 1 |
| Encerramento | Workers encerrados; RGB/W/intensidade zero | Workers encerrados; RGB/W/intensidade zero |

Geometria constante nos dois ensaios: x=0, y=230, largura=1157 e altura=300. No ciclo estrutural, os quatro PARs variaram de 0,8% a 80%, respeitando master de 80%. O grid percorreu oito tempos durante a pausa e o drop manteve a janela estrutural de oito kicks reais. A iluminação operou perto de 60 Hz; os tempos observados não constituem garantia de latência máxima.

No ciclo de textura, as viradas entraram em 7,01 s e 12,53 s. A primeira acompanha a entrada de bassline sem kick em 6 s, a segunda as camadas adicionadas em 12 s. Pergunta/resposta apareceu após a evolução/virada, e acumulação após o trecho de tensão. O trecho denso também é classificado como build-up pela heurística estrutural existente, de cerca de 13,4 a 20,5 s; isso não comprova reconhecimento de instrumentos ou de um build-up real.

Evidências: resultado-show-structure_demo-v0.12.json e resultado-show-texture_demo-v0.12.json. Capturas preview-rgbw-structure_demo-build.png e preview-rgbw-texture_demo-fill.png foram inspecionadas, incluindo a identificação 0.12, branco da subida, contraste entre PARs e indicação de W. As capturas de groove/drop também são produzidas pelo script.

## Controles manuais

scripts/render_rgbw.py abriu Lighting Studio sem iniciar áudio, selecionou manual independente com R=G=B=0 e W=100%. Os seis estados tinham RGB zero e W 1, com intensidade de 56% (manual 70% × master 80%). A coluna W mostrava 100% e a cor aparente era branca. Fechamento zerou W. preview-rgbw-controles.png e preview-rgbw-canais.png foram inspecionadas: controles acessíveis por rolagem e tabela com canal W e cor aparente.

## Limites e próximo teste com Traktor

Os resultados são sintéticos e não medem precisão em faixas reais. A mistura visual usa branco neutro e soma saturada de RGB+W; não está calibrada para temperatura, gamut ou potência de LEDs físicos. O canal W e intensity são controles separados: 100% de W não significa 100% de intensidade ou luminosidade física medida.

Densidade e novidade descrevem a mixagem, sem separar instrumentos. Ganho/filtro também podem causar viradas. Compassos/frases continuam relativos à grade assumindo 4/4. O grid segue sem kicks, mas não cria eventos confirmados. Não há Link, patch de canais, DMX, Art-Net ou sACN.

1. Reabrir iniciar.cmd, iniciar captura da saída usada pelo Traktor e adquirir a grade com quatro kicks regulares.
2. Usar Stage Preview → Usar show RGBW → Ativar motor, com Cores automáticas.
3. Ouvir algumas frases estáveis e observar a repetição, a evolução a cada 16 tempos e as cores; comparar bassline sem kick, entrada de elementos, build-up e drop.
4. Em Lighting Studio, comparar complexidade baixa/alta e ajustar os pesos existentes. Conferir Uso do canal W, paletas fixas e canais manuais independentes.
5. Verificar blackout, master zero, parada e reabertura. Salvar preferências de luz preserva o efeito e ajustes, mantendo ativação/manual como estados de sessão.

Detalhes em rgbw-show.md. Histórico preservado em validacao-v0.11.md e resultado-pytest-v0.11.txt.
