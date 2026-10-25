# Validação — versão 0.19

Registro: 2026-10-23 (UTC). Windows x64, Python 3.12.10; preferências v13; pacote 0.19.0. Sem saída física DMX.

## Regressão

**626 testes passaram em 116,57 s**, incluindo os 604 anteriores e 22 novos cenários do primeiro impacto. Evidências: docs/resultado-pytest-v0.19.txt e docs/resultado-pytest.txt.

Os novos testes percorrem o pipeline completo de áudio, com variações de cauda, frequência e amplitude do kick, pausas de 125/500 ms, prato simultâneo, baixo contínuo e baixo forte desde o começo do breakdown. Os casos positivos exigem entrada no primeiro kick e entrega do bloco com estado de drop em menos de 100 ms após o impacto; não basta retroagir o timestamp do drop depois de esperar outro kick.

Também são exercitados 96/128/150 BPM, captura de 44,1/48 kHz, mono/estéreo e ganho global de 0,25. A fase Link deslocada em relação à grade local permite a entrada no primeiro kick sem corrigir essa grade com uma única amostra. O desvio acústico limitado e o baixo denso preservam os oito kicks e a saída para groove.

A omissão intencional da primeira publicação do detector geral verifica a recuperação acústica do impacto. Outra variante libera essa publicação com atraso: o primeiro kick não é contado duas vezes. Nos dois casos, o drop percorre 1–8 uma única vez.

Pratos sem kick, baixo contínuo sem kick e bassline harmônica com prato simultâneo não criam drop. As regressões anteriores de kicks fracos em ritmo dobrado, basslines percussivas/harmônicas, pausas, interrupções, correção consistente de fase, silêncio e isolamento de falhas continuam aprovadas. Uma bateria dirigida de 71 casos também passou antes da regressão final.

## Confirmação do impacto

A análise rápida usa a assinatura e o decaimento do transiente em uma janela de 55 ms, comparada com a mesma janela do groove. O som anterior é descontado em potência. Uma tentativa incerta permanece pendente até a análise completa de 120 ms do mesmo ataque. Descritores rápidos não reescrevem o perfil nem autorizam correções da grade.

Quando o baixo já sustenta o build-up, a entrada deixa de exigir uma subida adicional de 7 dB de toda a mixagem. O transiente ainda precisa passar por potência relativa ao groove, forma espectral, decaimento, ataque e fase. Essa análise continua nos oito kicks do drop para o fundo grave não travar o contador. A potência mínima para kicks fracos/acelerados não foi reduzida.

## Palco em tempo real

O ensaio de 26 s com scripts/validate_phrases.py structure_demo passou com **2.437 blocos, zero descartes e zero falhas de continuidade**. O primeiro estado visual de drop apareceu em **20,093 s**, após o primeiro impacto programado em 20 s, e retornou ao groove em aproximadamente 24,093 s. A janela de confirmação registrada foi de 62 ms; esse indicador não mede o atraso total entre Traktor e a luz apresentada.

As oito posições do drop tiveram pico 0,8 e duração superior a 350 ms cada. O palco manteve uma única geometria (0, 477, 1157, 300), os moves ficaram coordenados em 1.524 quadros observados e o ciclo percorreu oito passos durante a ausência de kicks. A iluminação mediu 61 Hz no encerramento do ensaio. Não houve erros; o encerramento foi limpo e zerou RGBW/intensidades.

Evidência: docs/resultado-ciclos-structure_demo-v0.19.0-texture.json. Prévia: preview-cycles-structure_demo-drop-eight.png. O relatório agora inclui os dados da primeira confirmação e o ensaio exige entrada antes de 20,25 s, impedindo que o segundo kick de 20,5 s satisfaça a verificação.

## Operação e limites

O pacote editável foi atualizado para 0.19.0, a compilação dos módulos passou e iniciar.cmd --help foi executado com sucesso. Reabra iniciar.cmd para carregar a versão nova. Preferências v13 e ajustes Link continuam disponíveis; nenhuma preferência real em AppData foi editada diretamente. As sessões de teste usam configuração temporária e não abrem uma sessão Link nativa.

O usuário já validou a conexão Traktor/Link. Nesta rodada, as verificações usam áudio sintético e snapshots/provedor Link; não foram fornecidos os arquivos das tracks citadas. A detecção continua heurística e precisa do perfil de groove aprendido. Mudanças grandes de timbre, volume ou fase e baixos muito semelhantes a kicks ainda podem produzir erros. Os tempos medidos aqui não representam a latência física de WASAPI/Traktor.

Critérios e diagnóstico: [drop-detection.md](drop-detection.md). A validação anterior está em [validacao-v0.18.md](validacao-v0.18.md).
