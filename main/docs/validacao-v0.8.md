# Validação — versão 0.8

Registro: 2026-10-13 (UTC). Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Nenhuma dependência nova. Pacote e metadata locais: 0.8.0; preferências v6 com migração de v1–v5.

## Regressão automatizada

**248 testes passaram em 53,75 s**, incluindo os 229 casos anteriores. Evidência: resultado-pytest.txt. Histórico preservado em validacao-v0.7.md e resultado-pytest-v0.7.txt.

Os 19 casos novos cobrem:

- Previsão temporal 30 s à frente em 90, 120 e 150 BPM, sem inventar eventos ou prolongar o PLL; rejeição de contratempos, expiração, incerteza e mudança gradual de andamento.
- Perfil grave: rejeição de espectro diferente e de baixo sustentado com mesmo espectro; confirmação única de kick semelhante após observar seu decaimento.
- Pipeline completo com baixo forte sem kick, sobre a grade ou no contratempo, misturado a hats/melodia/roll. Os dois cenários provocam ao menos quatro candidatos ambíguos no detector bruto, não criam drop na seção sem kick e reconhecem oito kicks após o retorno real.
- Perfil automático nos efeitos existentes, perfil fixo durante mudanças estruturais, branco no build-up e cores saturadas no drop, manual preservando sua paleta, migração e persistência.
- Escolha de cor compartilhada entre palco e Lighting Studio, sem substituir a captura em execução.

Continuam passando os testes de geometria constante nas três dimensões de janela, rolls rápidos, independência de DSP, ganho reduzido, estéreo em oposição de fase, reset/descontinuidades, falhas isoladas, blackout/manual/master e encerramento.

## Sessão em tempo real, palco aberto

validate_stage.py executou a aplicação Qt com fonte sintética e modo musical durante 26 s. Imagens foram capturadas em memória e codificadas após parar os workers, evitando disputa da compressão PNG com o DSP.

| Medida | Resultado |
|---|---|
| Áudio | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 2.436 |
| Descartes / falhas de continuidade | 0 / 0 |
| Groove aprendido | 4,156 s |
| Breakdown | 8,640 s |
| Build-up | 12,922 s |
| Drop confirmado | 20,156 s |
| Retorno ao groove no nono kick confirmado | 24,156 s |
| Contagem no drop | 1, 2, 3, 4, 5, 6, 7, 8 |
| Geometria do palco | Um único retângulo: x=0, y=194, largura=1157, altura=300 |
| Grade prevista com janela +30 s | Observada durante a pausa de kicks |
| Perfis observados | Groove menta/azul e alta energia; breakdown azul/violeta; build-up para branco; drop vermelho/magenta |
| Pico de branco do perfil na subida | 97% |
| Pico de intensidade antes do drop | 63,35%, master em 80% |
| Pico de frequência de movimento na subida | 0,325 ciclos/s |
| Motor de iluminação | Última janela: 60 Hz |
| Processamento do último quadro de luz | 0,3674 ms |
| Erros de subsistemas | Nenhum |
| Encerramento | Workers encerrados; intensidades finais zero |

Evidência: resultado-palco-v0.8.json. Imagens inspecionadas: preview-buildup.png e preview-drop.png, mostrando respectivamente clareamento e retorno às cores saturadas, além da nova linha de previsão e controle compartilhado. preview-breakdown.png e preview-palco.png também foram atualizadas. O script exige sequência completa, oito kicks, ausência de descartes, geometria constante, branco acima de 85%, grade prevista, mudança de perfil e encerramento limpo.

## Composição offline

validate_structure.py analisou 28 s de sinal em aproximadamente **7,04 s**. Média: **2,42 ms/bloco**; percentil 99: **4,32 ms**. Drop confirmado em 20,117 s e retorno ao groove em 24,117 s. Pico de intensidade na confirmação do drop: 0,710, limitado pelo master em 0,8. Nenhuma falha de análise/continuidade. Evidência: resultado-estrutura-v0.8.json.

Esses números são de uma execução sintética local, sem reprodução sonora, gravação de áudio ou transmissão DMX. Não garantem desempenho prolongado nem taxa de acerto em tracks reais.

## Limites e nova avaliação com Traktor

O usuário obteve certo sucesso com os snares e relatou falsos drops em baixos sem kick, especialmente no contratempo. As faixas reais não foram fornecidas nesta sessão; a validação 0.8 usa as composições descritas acima.

A confirmação de perfil observa cerca de 120 ms de decaimento, adicionando esse tempo à decisão estrutural. O detector bruto aprovado continua independente. No cenário com baixo sustentado forte sobre a grade, os primeiros ataques reais ficaram mascarados e o primeiro kick confirmado foi o de aproximadamente 21 s, embora a seção com kick começasse em 20 s. No cenário com baixo no contratempo e na composição base, o primeiro kick de retorno foi confirmado. A rejeição conservadora pode atrasar a identificação de alguns drops.

1. Fechar a versão anterior e reabrir iniciar.cmd. Iniciar a captura em um groove com kicks regulares.
2. Em Stage Preview, clicar em Usar automação musical e Ativar motor. Observar próxima janela, previsão +30 s quando disponível, confiança e incerteza.
3. Repetir os trechos com baixo/hats/melodias sem kick. Conferir as rejeições de grade/perfil e verificar que o pós-drop não é ativado indevidamente.
4. Comparar o retorno real dos kicks com a confirmação do drop e seus oito kicks. Kick Monitor mostra candidatos brutos e pode exibir um que a estrutura rejeitou.
5. Marcar Cores automáticas no palco ou escolher Perfil de cores → Automático no Lighting Studio. Observar azul/violeta no breakdown, branco crescente no build-up e vermelho/magenta no drop. Comparar com Fixo e salvar a preferência.
6. Testar movimento, master, manual, blackout e parada; o palco deve manter dimensões estáveis durante as transições.

O grid prevê janelas temporais possíveis; não garante a presença futura de kick, não conhece o arranjo ou a posição da faixa no Traktor e não detecta downbeat real. Baixos curtos semelhantes a kicks podem continuar confundindo a confirmação. Ver grid-kicks.md para os critérios e limites. Nenhuma saída física DMX foi implementada.
