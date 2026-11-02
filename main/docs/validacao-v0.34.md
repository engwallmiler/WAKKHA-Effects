# Validação — versão 0.34.0

Registro: **2026-11-01**. Ondas de cor/intensidade sobre uma base contínua, com relógio de movimento integrado. Ensaios sintéticos, sem captura, Traktor, Link nativo ou ESP32 físico.

## Regressão apropriada

**138 testes JavaScript passaram**, incluindo 16 casos novos. Os três padrões apresentam cores distintas em regiões diferentes, contraste de intensidade e deslocamento de frentes. Verificam todos os pixels acesos, continuidade espacial/temporal, fases altas, profundidade zero, variação orgânica, ajuste de velocidade sem salto, relógio avançando sem Canvas, cópias exatas/invertidas e igualdade entre prévia e envio. Os 33 efeitos são exercitados pelo teste de amostragem física. [Log](resultado-pixel-js-v0.34.txt).

**129 testes Python passaram**, incluindo os novos limites de profundidade e velocidade, persistência, projetos, geometria, USB, confiabilidade e UI. [Log](resultado-pytest-v0.34.txt).

A análise musical não mudou e não recebeu nova execução da suíte DSP completa. DSP, música e contratos são conferidos byte a byte contra o wheel 0.33. [Registro anterior](validacao-v0.33.md) · [Verificação do pacote](resultado-package-v0.34.json).

## Canvas e USB emulado

[validate_pixel_flow.py](../scripts/validate_pixel_flow.py) abre a aplicação Qt e uma serial emulada com uma fita de 300 pixels dividida em seis barras e cópias exatas. Pacotes musicais sintéticos alimentam o relógio.

| Padrão | Menor máximo RGB por pixel | Maior máximo RGB por pixel |
|---|---:|---:|
| Ondas orgânicas | 28 | 97 |
| Correntes cruzadas | 23 | 109 |
| Maré cromática | 34 | 79 |

São máximos entre R/G/B de cada pixel no quadro registrado, não medidas elétricas. Em todos os casos o mínimo é positivo; há cores dominantes distintas ao longo da fita e hashes diferentes entre quadros separados no tempo. O brilho mestre estava em 100%, com paleta RGB e resposta musical ativa.

O ensaio também confirmou:

- profundidade zero produz um preenchimento uniforme;
- mudar velocidade não reinicia a fase e o fator evolui gradualmente;
- movimento e transmissão continuam com a janela minimizada;
- buffers e texturas são reutilizados;
- controles são persistidos e a geometria/conexões conservadas;
- blackout e fechamento terminam com pixels zerados.

[Relatório](resultado-pixel-flow-v0.34.0.json) · [Log](resultado-pixel-flow-v0.34.txt) · [Ondas](../preview-organico-liquid-v0.34.png) · [Correntes](../preview-organico-crossflow-v0.34.png) · [Maré](../preview-organico-chromatide-v0.34.png).

Registrou **21,34 fps**, renderização média **6,12 ms** e máxima **10,90 ms**, em uma execução curta. O emulador registra payloads e não simula brilho real, corrente ou precisão elétrica. O resultado não certifica seis horas de operação com hardware. [Confiabilidade](confiabilidade.md).

## Operação e distribuição

O botão **CONTÍNUO** passa a iniciar Ondas orgânicas. O catálogo contínuo inclui as novas famílias e as anteriores recebem camadas dos novos movimentos. Há controles de profundidade (0–100%) e velocidade (25–250%), com padrões de 80% e 100% para projetos anteriores. O relógio das ondas é integrado; uma troca de velocidade não multiplica uma fase antiga pelo novo valor.

Os controles são opcionais nos projetos antigos; não mudam o protocolo USB. Picos, brilho mestre, cor fixa, limites e prioridades de emissão continuam ativos. O firmware 0.22 permanece compatível.

Instalação editável e wheel são **0.34.0**. Fontes e recursos declarados são comparados byte a byte ao pacote. [Verificação](resultado-package-v0.34.json) · [Instruções](ondas-organicas-v0.34.md).
