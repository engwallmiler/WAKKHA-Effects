# Validação — versão 0.20

Registro: 2026-10-24 (UTC). Windows x64, Python 3.12.10; preferências de áudio v13; pacote 0.20.0. Integração local do Pixel Studio, sem saída física.

## Regressão e contrato musical

**655 testes Python passaram em 108,62 s**, incluindo os 626 anteriores e 29 novos testes de projeto, protocolo musical e quadros de pixels. Evidências: docs/resultado-pytest-v0.20.txt e docs/resultado-pytest.txt.

Os novos casos verificam persistência atômica e preservação do projeto válido, limites de geometria/resolução, configurações inválidas, ausência de ativação operacional no projeto, identificadores únicos, projeção de Link sem criação de kick, eventos acústicos confirmados e canais RGB lógicos por pixel. Silêncio, dados antigos e captura parada são separados de áudio audível. Quadros WS2811 com W fictício, contagem de canais incorreta, valores não finitos ou indicação de saída física são rejeitados. Os testes existentes de captura, detecção de drop, Link, PARs/moves, interface e encerramento continuam aprovados.

**19 testes JavaScript passaram**: os sete testes originais de geometria e doze de integração. Evidência: docs/resultado-pixel-js-v0.20.txt. São exercitados efeitos/cores/brilho independentes, perfil WS2811 RGB mesmo com RGBW global, kick real separado da grade, respostas de baixo/densidade sem kick, entrada imediata no drop, oito confirmações, sincronização 1/8, reversão/velocidade/fase, estabilidade do padrão com áudio constante, mudança sustentada na fronteira de oito tempos e importação inválida sem substituição do projeto.

## HTML embutido e áudio

O ensaio desktop scripts/validate_pixel_studio.py passou com o Canvas real hospedado em Qt WebEngine e mensagens musicais via Qt WebChannel. Uma fita foi configurada em vermelho/Atmosfera, outra em azul/Onda e uma terceira apagada. Os dados de cada fita respeitaram seu efeito e sua paleta, com três canais por pixel WS2811; a configuração RGBW global não introduziu W nessas fitas.

Blackout, captura parada e falta de áudio deixaram os quadros em zero. A ativação das fitas permaneceu independente do motor anterior. A configuração foi salva no diretório isolado de QA; uma edição feita imediatamente antes do fechamento também foi recuperada no arquivo, verificando a confirmação final de salvamento. O encerramento foi limpo.

O ciclo musical sintético percorreu **os oito kicks de drop**, com o primeiro quadro comunicado pelo renderizador em aproximadamente **20,203 s**, após o impacto programado em 20 s. Houve **zero blocos de áudio descartados**. Um ensaio anterior registrou aproximadamente 20,140 s. São medições locais de análise/mensagens/renderização do simulador; não representam latência física entre Traktor, controlador e LEDs reais.

O ajuste de desempenho limita o desenho embutido a 30 Hz e reduz a resolução visual do Canvas. A lógica musical é atualizada no recebimento dos dados; a contagem de pixels e os canais exportados conservam a resolução de cada fita. Esse ajuste eliminou o atraso observado no primeiro ensaio, em que renderização atrasada pulava uma das posições visuais do drop.

Evidência final: docs/resultado-pixel-studio-v0.20.json. Verificação curta, com salvamento ao fechar: docs/resultado-pixel-studio-v0.20-smoke.json. Prévia: preview-pixel-studio.png.

O ambiente automatizado exige renderização por software e desativação do sandbox aninhado do Chromium no script de QA. As mensagens de fallback gráfico registradas no stderr não foram erros de análise musical ou do projeto; os testes de canais, blackout, sincronismo e encerramento passaram. Esses parâmetros de QA não são aplicados pelo aplicativo normal.

## Pacote e operação

O pacote editável foi instalado como 0.20.0. Também foi construído o wheel beatlight_dmx-0.20.0-py3-none-any.whl em .runtime/dist-v0.20; a inspeção confirmou os módulos de pixel/UI e o HTML em share/beatlight, com conteúdo idêntico ao arquivo fonte. A compilação dos módulos passou e iniciar.cmd --help foi executado com sucesso.

O aplicativo passa a abrir no Pixel Studio. A página anterior de áudio, o Link e os painéis de PARs/moves permanecem disponíveis. O nome de dados BEATLIGHT DMX foi conservado para manter as preferências existentes. Projetos de fitas ficam em pixel-studio.json, separados das preferências v13. Nenhum arquivo real de preferências em AppData foi editado diretamente durante a implementação.

A validação usou fontes sintéticas, configuração temporária e snapshots/provedor Link. A conexão Traktor/Link já havia sido validada pelo usuário; não foi aberta uma nova sessão Link nativa nem usada captura de hardware nos ensaios desta rodada. A saída atual continua no simulador: controlador, protocolo e transporte de fitas reais serão uma etapa própria.

Guia de uso e limites: [pixel-studio.md](pixel-studio.md). A validação anterior está em [validacao-v0.19.md](validacao-v0.19.md).
