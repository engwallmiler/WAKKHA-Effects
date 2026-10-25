# Validação — versão 0.21

Registro: 2026-10-25 (UTC). Windows x64, Python 3.12.10; preferências de áudio v13; pacote 0.21.0. Ensaios locais do simulador Pixel Studio.

## Regressão

**664 testes Python passaram em 235,37 s.** Evidências: [resultado completo](resultado-pytest-v0.21.txt) e resultado-pytest.txt. A suíte inclui captura, DSP, estrutura, rejeição de basslines, grade contínua, Link, motores anteriores, interface, projetos e protocolo de pixels.

Os sete novos casos acústicos reproduzem referências de groove contaminadas por rolls fracos acelerados, mudança de altura do kick no retorno e um candidato fora da grade ocupando o refratário imediatamente antes do impacto. Os retornos sintéticos são confirmados no primeiro ataque, com decisão em menos de 110–130 ms nos casos novos. Reduções normais de volume continuam como groove; baixo lento com agudos permanece rejeitado. Dois novos testes verificam a configuração gráfica por software, sua idempotência e a preservação do sandbox normal.

**30 testes JavaScript passaram:** sete de geometria e 23 de integração. [Resultado](resultado-pixel-js-v0.21.txt). Exercitam variação por compassos com áudio estável, migração de projetos antigos, modos somente elementos/manter padrão, fusão em tempos, repertórios estruturais, drop manual imediato por oito tempos, cancelamento, sincronização durante o drop, retomada da captura, compensação de mensagens atrasadas e apresentação de quadros completos. Também permanecem cobertos geometria, cores/respostas por fita, WS2811 RGB, blackout, silêncio e separação entre grade prevista e kick confirmado.

## Janela nativa e desempenho

[validate_pixel_studio.py](../scripts/validate_pixel_studio.py) passou com Qt WebEngine, Canvas real, Qt WebChannel e áudio sintético. O botão DROP AGORA do cabeçalho disparou e cancelou a cena manual. Cores/efeitos independentes e uma fita desabilitada produziram os canais esperados. Blackout e captura parada zeraram a emissão. Salvamento automático, última edição imediatamente antes de fechar e encerramento limpo passaram.

As quatro verificações de controles após rolagem retornaram RGB [23, 37, 58], sem blocos pretos nas capturas estabilizadas. O ensaio aguarda um segundo após cada rolagem: a captura nativa automatizada pode ainda mostrar a posição anterior em 200 ms, mesmo com o DOM já reposicionado. Essa verificação não garante ausência de todo artefato transitório em outros drivers.

O caminho inicial por software consumiu aproximadamente 180 ms por quadro. Os halos passaram a usar uma camada de 150 × 70, difusão sem filtros de tela inteira e cópia final do quadro em memória. Uma sondagem isolada caiu para cerca de 21 ms; o ensaio completo final registrou **31,16 ms em média**, máximo de 49,4 ms. O desenho embutido é limitado a 30 Hz e suspenso quando o palco sai da área visível; o relógio e as cenas continuam avançando. Os pixels e canais exportados mantêm toda a resolução configurada.

O impacto sintético foi programado em 20 s. O primeiro quadro de drop foi comunicado em **20,188 s**, preservando **as oito posições** e com **zero blocos de áudio descartados**. Essa é uma medida local de análise, mensagens e comunicação do renderizador; não mede LEDs físicos nem demonstra o mesmo desempenho em toda track real.

Evidências: [ensaio completo](resultado-pixel-studio-v0.21.0.json), [ensaio curto](resultado-pixel-studio-v0.21.0-smoke.json), resultado-pixel-native-v0.21.txt e preview-pixel-studio.png.

## Projeto existente e estrutura musical

[validate_pixel_cues.py](../scripts/validate_pixel_cues.py) clonou o projeto disponível do usuário, com **cinco fitas e 1.500 pixels**, para um diretório de QA. No modo Orgânico, as combinações mudaram nos tempos 32, 48 e 64, respeitando quatro compassos entre trocas. O contexto controlado também selecionou repertórios de breakdown/build-up, entrou no drop automático e aceitou o disparo manual. Blackout e fechamento passaram. [Resultado](resultado-pixel-cues-v0.21.0.json).

Esse ensaio usa relógio e mensagens musicais controlados; não representa análise acústica da track do usuário. Os arquivos reais de AppData foram somente lidos, sem edição direta. Projetos antigos recebem a regra padrão Compassos + novos elementos, preservando geometria e configurações individuais.

## Pacote e limites

O pacote editável está instalado como 0.21.0. O wheel em .runtime/dist-v0.21 inclui o novo módulo pixel/rendering.py e o HTML em share/beatlight; a inspeção confirmou a identidade do HTML com a fonte e a versão dos metadados. A compilação de src/scripts e iniciar.cmd --help passaram.

O aplicativo usa composição por software por padrão e preserva seu sandbox. Somente os scripts de QA desativam o sandbox aninhado do Chromium, necessário neste ambiente automatizado. O stderr ainda contém avisos do backend gráfico do ambiente, inclusive no encerramento; os contratos de pixels, contagem musical e encerramento passam. Não se considera que esses avisos comprovem compatibilidade com todos os drivers.

Não foram fornecidos arquivos de áudio dos drops problemáticos; as melhorias do detector foram verificadas com regressões sintéticas e casos negativos. A decisão continua causal e heurística. Não foi aberta uma nova sessão Link nativa nem usada captura de hardware nesta rodada. Não há saída física de pixels ou DMX.

Guia de uso: [pixel-studio.md](pixel-studio.md). Validação anterior: [validacao-v0.20.md](validacao-v0.20.md).
