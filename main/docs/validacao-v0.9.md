# Validação — versão 0.9

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Sem dependências novas. Código e metadata instalados: **0.9.0**. Preferências **v7**, com migração de v1–v6.

## Regressão automatizada

**276 testes passaram em 144,77 s** na execução final, após corrigir o carregamento percentual dos três pesos. A execução inicial também passou (62,17 s); a duração variou entre execuções. Evidências: resultado-pytest.txt e resultado-pytest-v0.9.txt. Histórico anterior: validacao-v0.8.md e resultado-pytest-v0.8.txt. compileall de src/scripts passou; código, metadata e Settings.version foram conferidos como 0.9.0 / 0.9.0 / 7.

Os 28 casos adicionados cobrem:

- Envelope grave sem kick/BPM, densidade em espectros esparsos/densos, ganho, agudos sem graves, estéreo em oposição de fase, reset e isolamento de falhas.
- Efeitos de baixo/densidade, distribuição gradual dos fachos, master/blackout, dados antigos, silêncio imediato, três pesos inválidos e base musical sem kicks.
- Pulso alimentado exclusivamente por kicks confirmados, preservação do pico após a espera acústica e ligação dos contratos pelo worker real.
- Tempos esperados sem inventar eventos, candidatos acústicos fora da grade e deduplicação das contagens.
- Rejeição de baixo harmônico com perfil grave/decaimento parecido e pipeline com bassline distorcida sobre o tempo, seguido de oito kicks reais.
- Migração v6 preservando cores/kicks e controles compartilhados/salvos durante a captura. O teste de interface verifica valores iniciais e recarga dos pesos, além de alteração/salvamento.

Continuam passando os casos anteriores de DSP, captura, BPM/PLL, grade/expiração, rolls, geometria estável em três tamanhos, prioridades, falhas isoladas e encerramento.

## Baixo e densidade em tempo real

scripts/validate_texture.py abriu a aplicação Qt com fonte sintética durante **23 s**, alternando automação musical → baixo → densidade → automação musical. A composição tem groove em 0–6 s, bassline agressiva no contratempo sem kick em 6–18 s e camadas adicionais a partir de 12 s.

| Medida | Resultado |
|---|---|
| Áudio | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 2.154 |
| Descartes / falhas de continuidade | 0 / 0 |
| Densidade média antes/depois das novas camadas | 49,07% / 85,03% |
| Intensidade média/pico no efeito de baixo | 33,79% / 40,60%, master em 80% |
| Kicks confirmados na janela sem kick avaliada (6,3–17 s) | 0 |
| Geometria do palco | Um retângulo: x=0, y=230, largura=1157, altura=300 |
| Erros de subsistemas | Nenhum |
| Encerramento | Workers encerrados; intensidades finais zero |

Evidência: resultado-textura-v0.9.json. Imagens preview-baixo.png e preview-densidade.png inspecionadas. O ensaio integrado identificou uma conversão incorreta na carga das preferências: pesos fracionários estavam sendo arredondados para 1% nos controles. A escala foi corrigida, os testes de carga/recarga ampliados e o ensaio repetido com sucesso. A validação considera média e pico do envelope; notas curtas podem escurecer entre ataques.

## Estrutura e estabilidade do palco em tempo real

scripts/validate_stage.py executou a fonte estrutural durante **26 s** com o palco aberto. Capturas são guardadas em memória e codificadas após parar os workers.

| Medida | Resultado |
|---|---|
| Blocos recebidos | 2.435 |
| Descartes / falhas de continuidade | 0 / 0 |
| Groove / breakdown / build-up | 4,156 s / 8,625 s / 12,953 s |
| Drop / retorno ao groove no nono kick | 20,187 s / 24,187 s |
| Contagem pós-drop | 1, 2, 3, 4, 5, 6, 7, 8 |
| Geometria do palco | Um retângulo: x=0, y=230, largura=1157, altura=300 |
| Previsão da grade | Observada durante a pausa |
| Branco máximo na subida | 97% |
| Pico de intensidade antes do drop | 63,36%, master em 80% |
| Movimento máximo na subida | 0,325 ciclos/s |
| Iluminação, última janela / último quadro | 59 Hz / 0,3454 ms |
| Erros / encerramento | Nenhum; workers encerrados e intensidades finais zero |

Evidência: resultado-palco-v0.9.json. preview-buildup.png e preview-drop.png foram inspecionadas: clareamento na subida e cores saturadas após o retorno. preview-breakdown.png e preview-palco.png atualizadas. Os novos medidores conservaram a estabilidade geométrica durante todas as mudanças.

## Análise offline

scripts/validate_structure.py analisou 28 s em **15,90 s**, com média de **5,56 ms/bloco** e percentil 99 de **8,83 ms**, nesta execução local. Usa os mesmos contratos de textura e confirmação do runtime. Drop em 20,117 s, groove em 24,117 s, oito kicks e intensidade máxima 0,8 na confirmação (master em 0,8). Sem falhas de subsistemas/continuidade. Evidência: resultado-estrutura-v0.9.json.

## Limites e avaliação com Traktor

Os testes são sintéticos, sem reprodução sonora, gravação ou transmissão DMX. Não medem taxa de acerto em faixas reais nem garantem desempenho prolongado. O usuário aprovou as fases anteriores com Traktor e relatou confusões persistentes com baixos agressivos; essas músicas não foram fornecidas nesta sessão.

Confirmação observa cerca de 120 ms após o ataque. O pulso visual começa na confirmação, mantendo o timestamp original no diagnóstico. Até aprender uma grade confiável, o efeito Pulso por kick espera; baixo/densidade já podem iluminar. Uma fonte que começa só com baixo pode fornecer uma referência inadequada. Baixos com timbre/ataque muito próximos do kick na mesma posição temporal ainda podem passar, e mudanças de timbre ou andamento podem exigir reaprendizado. Baixo forte pode mascarar kicks reais, como observado nos cenários anteriores.

Densidade mede ocupação espectral e ataques, não quantidade literal de instrumentos. Graves incluem a energia do kick; não há separação de stems. A grade prevê onde um kick caberia, sem conhecer o arranjo ou a posição no Traktor. A hipótese 4/4 organiza tempos e frases relativas; downbeat/assinatura de tempo reais não são detectados.

1. Fechar a versão anterior e reabrir iniciar.cmd. Capturar a saída do Traktor e começar com groove regular.
2. Em Stage Preview, usar automação musical e ativar motor. Comparar medidores de graves/densidade com os trechos ouvidos.
3. Em Lighting Studio, comparar Linha de baixo, Densidade sonora e Automação musical; ajustar os três pesos e salvar preferências.
4. Em Kick Monitor, comparar candidatos, confirmados e tempos previstos sem kick nos trechos de baixo agressivo. Um candidato bruto não deve automaticamente disparar Pulso por kick ou iniciar drop.
5. Observar retorno real, oito kicks pós-drop, tensão/clareamento na subida e movimento contínuo. Comparar cores automáticas e fixas.
6. Testar master, movimento zero, manual, blackout, parada e reabertura. Acompanhar descartes/continuidade em Diagnósticos.

Fixture Manager, editor completo de cenas/regras e saídas DMX permanecem nas etapas futuras. Nenhum adaptador físico foi implementado ou ativado.
