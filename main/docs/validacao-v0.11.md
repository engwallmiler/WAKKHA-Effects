# Validação — versão 0.11

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10 e dependências existentes. Código e pacote instalado conferidos: **0.11.0 / 0.11.0**; preferências **v7**. Nenhuma saída física DMX ou transmissão de rede ativada.

## Regressão e instalação

**313 testes passaram em 67,09 s**, incluindo os 294 anteriores. Evidências: resultado-pytest-v0.11.txt e resultado-pytest.txt. compileall de src/scripts passou. O pacote foi reinstalado no runtime portátil sem novas dependências; iniciar.cmd utiliza esse runtime quando não há .venv312.

Os 19 casos novos verificam contraste e alternância espacial dos quatro PARs, repetição da frase e das cores, virada no próximo tempo após aumento sustentado, rejeição de ataque isolado/snapshot repetido, permanência da família e histerese, resposta sem kicks e sem grade, prioridades operacionais nos quatro estados, silêncio recente mesmo antes da transição estrutural, aceleração/branco/impacto, paleta fixa, candidatos brutos sem acento, cancelamento após correção/interrupção, prioridade de tensão/drop sobre virada pendente, persistência e alteração de paleta durante o compasso. O teste existente da GUI também verifica o novo botão e o controle efetivamente recebido pelo worker. Os testes de geometria passam em 1440×960, 1280×800 e 1100×760.

## Show com palco aberto em tempo real

scripts/validate_show.py foi executado separadamente com structure_demo e texture_demo, depois da instalação final. As fontes sintéticas não reproduzem som. As imagens são mantidas em memória durante o ensaio e codificadas após o encerramento dos workers.

| Medida | Breakdown/build/drop | Baixo e novas camadas |
|---|---|---|
| Duração | 26,00 s | 23,00 s |
| Áudio | 48 kHz, estéreo, blocos de 512 | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 2435 | 2156 |
| Viradas por textura | 0 | 2 |
| Passos vistos sem kicks | 1–8 | 1–8 |
| Kicks confirmados na seção observada sem kick | Constante em 15 | Constante em 11 |
| Motor, última janela | 61 Hz | 59 Hz |
| Maior tempo de processamento de iluminação observado | 0,95 ms | 1,20 ms |
| Quadros com contraste entre PARs maior que 30 pontos percentuais | 476 de 1429 | 505 de 1247 |
| Descartes / falhas de continuidade / erros | 0 / 0 / nenhum | 0 / 0 / nenhum |
| Retângulos de palco observados | 1 | 1 |
| Encerramento | Workers encerrados; intensidades finais zero | Workers encerrados; intensidades finais zero |

Em ambos os ensaios o retângulo permaneceu em x=0, y=230, largura=1157 e altura=300. O motor operou próximo de 60 Hz; os valores da tabela são as últimas janelas, não uma garantia de latência máxima. No ensaio estrutural, todos os PARs variaram de 0,80% até 80,00%, com master em 80%. O menor componente RGB no pico branco foi 94,59%, mostrando branco nos PARs da subida.

No ensaio de textura, as viradas começaram em 7,02 s e 12,50 s. A primeira acompanha a entrada da bassline sem kick em 6 s; a segunda acompanha as camadas adicionadas em 12 s. A família passou a vai e volta após a primeira virada e a acumulação após o trecho de tensão. A estrutura classificou o trecho denso como build-up de aproximadamente 13,4 s a 20,6 s; isso é uma leitura heurística dos elementos sintéticos, não comprovação de um build-up real. A contagem de kicks permaneceu estável na janela sem kick.

Evidências: resultado-show-structure_demo-v0.11.json e resultado-show-texture_demo-v0.11.json. Capturas preview-show-structure_demo-groove.png, preview-show-structure_demo-build.png, preview-show-structure_demo-drop.png e preview-show-texture_demo-fill.png permitem comparar acendimento individual, pares brancos e impacto do drop. As lentes agora acompanham o brilho real do estado; o desenho anterior usava cor plena mesmo em intensidades muito baixas.

## Limites e avaliação com Traktor

Os ensaios verificam execução, repetição, resposta e integração com o palco. Não medem precisão com tracks reais. Densidade é ocupação espectral/atividade; graves incluem kicks e bassline. A novidade é aumento sustentado desses descritores, não identificação ou separação de instrumentos. Mudanças de ganho/filtro também podem produzir viradas. Frases e compassos são relativos à grade assumindo 4/4; o downbeat real não é detectado. A confirmação acústica e a análise de estrutura aprovadas não foram modificadas nesta versão. Link permanece sem integração.

1. Reabrir iniciar.cmd e iniciar captura da mesma saída usada pelo Traktor.
2. No Stage Preview, clicar em Usar show rítmico e Ativar motor. Ativar Cores automáticas para o branco da subida e mudanças de perfil.
3. Começar com quatro kicks regulares, comparar padrões e cores durante várias frases e observar a continuidade em uma bassline sem kick.
4. Ouvir entrada de hats/melodias/baixo e comparar as viradas, mantendo uma sequência reconhecível nos compassos seguintes.
5. Comparar breakdown, aceleração/clareamento do build-up e os oito kicks de alta energia após o drop. Comparar também com Usar automação musical, o modo contínuo anterior.
6. Ajustar os pesos e master; verificar manual, blackout e parada. Salvar preferências de luz para preservar a escolha do efeito.

Histórico da grade contínua preservado em validacao-v0.10.md e resultado-pytest-v0.10.txt. Detalhes e limites do Show rítmico estão em show-ritmico.md.
