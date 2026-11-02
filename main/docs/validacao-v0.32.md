# Validação — versão 0.32.0

Registro: **2026-10-31**. Recuperação de ataques alinhados quando o perfil antigo bloqueia as confirmações. Ensaios sintéticos, sem captura, Traktor, Link nativo, COM ou LEDs físicos.

## Regressão

**842 testes Python passaram**, em 340,90 segundos. [Log](resultado-pytest-v0.32.txt) · [JUnit](resultado-pytest-v0.32.xml). Cobrem análise, mascaramento, relógios, kicks, drops, oito kicks, captura, projetos, UI, Link e transporte USB emulado.

**11 testes específicos passaram** com a banda **40–110 Hz** nos cenários positivos, incluindo retomada depois de pausa e 44,1 kHz/blocos de 113 amostras. O grupo também verifica negativos e prioridade a 40% sem criar kicks em silêncio/baixo sustentado/vibrato. [Log](resultado-recurrent-tests-v0.32.txt).

**91 testes JavaScript passaram**. [Log](resultado-pixel-js-v0.32.txt). O HTML/motor de efeitos permanece byte a byte igual à versão anterior. [Validação anterior](validacao-v0.31.md).

## Reproduzir o bloqueio

[validate_recurrent_profile.py](../scripts/validate_recurrent_profile.py) compara o wheel 0.31 com a versão atual usando o mesmo sinal. O BPM é estimado pelo áudio, sem usar rótulos para decidir. Tolerância de associação: 75 ms.

| Cenário | Confirmados 0.31 → 0.32 | Falsos 0.31 → 0.32 | Reaprendizados | Drops falsos |
|---|---:|---:|---:|---:|
| Novo timbre de kick, 28 kicks reais | 9 → 24 | 0 → 0 | 1 | 0 |
| Kicks retirados; baixo sustentado | 9 → 9 | 0 → 0 | 0 | 0 |
| Kicks retirados; baixo no contratempo | 9 → 9 | 0 → 0 | 0 | 0 |
| Kicks retirados; baixo harmônico | 9 → 9 | 0 → 0 | 0 | 0 |
| Kicks retirados; roll acelerado fraco | 9 → 9 | 2 → 2 | 0 | 0 |

O caso positivo mantém **127 BPM**: nove kicks estabelecem referência, depois o corpo passa a ser mais largo e centrado em 45 Hz, com baixo contínuo em 105 Hz. A 0.31 perde os 19 kicks depois da mudança e acumula rejeições. A 0.32 perde quatro ataques na transição, reaprende e confirma os 15 seguintes. Isso não demonstra a mesma taxa em músicas reais.

Os dois falsos do roll já existiam na 0.31: a recuperação não aprendeu esse padrão, mas essa limitação continua presente. A imagem do usuário não contém áudio para identificar o veto exato de cada evento; monitor e trace agora exibem o motivo.

[Referência](resultado-recurrent-reference-v0.31.json) · [Atual](resultado-recurrent-v0.32.json) · [Funcionamento e limites](perfil-recorrente-v0.32.md).

O ensaio anterior de picos sob baixo contínuo foi repetido: preserva 22/24 em 65 Hz, 22/24 em 105 Hz a 48 kHz e 21/24 a 44,1 kHz, sem falsos ou drops indevidos nesses sinais. [Resultado](resultado-peak-grid-v0.32.json).

## Monitor e custo

[validate_recurrent_ui.py](../scripts/validate_recurrent_ui.py) processa áudio sintético e exibe o snapshot na aplicação Qt. Verifica o sensor **Perfil + grade**, perfil ativo, um reaprendizado, 127 BPM e USB desarmado. [Resultado](resultado-recurrent-ui-v0.32.json) · [Imagem](../preview-recurrent-v0.32.png).

O comparador mantém quatro candidatos e até oito observações de contratempo, reaproveitando a janela de descritores. Não há novo FFT, modelo, thread ou timer. Não grava candidatos na apresentação. [Confiabilidade](confiabilidade.md).

Três execuções de oito segundos por cenário, sem GUI/trace/pytest simultâneo, mediram medianas de 16,60% → 17,19% de um núcleo no groove e 17,38% → 18,75% com clique. A variação entre execuções é relevante; não certifica custo universal ou seis horas com Traktor/hardware. [Referência](resultado-dsp-cost-reference-v0.31.json) · [Atual](resultado-dsp-cost-current-v0.32.json).

## Distribuição

Instalação editável e wheel são versão **0.32.0**. Fontes e recursos declarados são comparados byte a byte ao pacote; estimador de BPM, extrator estrutural, módulo próprio de drop, HTML do Pixel Studio e firmware 0.22 são conferidos contra o wheel anterior. [Verificação](resultado-package-v0.32.json).

Reinicie o programa e a captura. Não é necessário regravar o ESP32. [Operação](perfil-recorrente-v0.32.md).
