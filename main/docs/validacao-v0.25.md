# Validação — versão 0.25.0

Registro: **2026-10-28 (UTC)**. Continuidade/simetria entre barras, remoção da difusão e primeira rodada de confiabilidade. Nenhum ESP32 ou dispositivo de áudio físico foi usado nesta validação.

## Regressão

**740 testes Python passaram** em 120,80 s. Incluem DSP/estrutura, captura, Link, USB emulado, projetos, topologia, persistência e a ponte Qt. [Saída completa](resultado-pytest-v0.25.txt).

**72 testes JavaScript passaram**, sem falhas. Incluem cópia de uma referência para vários destinos, inversão, continuidade 80+220, ordem física, espelhamento de fitas inteiras e de trechos da mesma fita, perfis/resoluções, conflitos de associação, exclusão, edição pelos controles, simulação temporária e compatibilidade com projetos anteriores. A difusão antiga é aceita, descartada na importação e ausente do desenho/exportação. [Saída completa](resultado-pixel-js-v0.25.txt).

Os testes exercitam oito horas no relógio lógico e verificam a estabilidade dos recursos. Salvamento concorrente e mensagens de música com confirmação retida verificam os limites das filas, deduplicação, edição mais recente, falhas de escrita e preservação do último arquivo válido. São verificações funcionais, sem afirmar oito horas reais.

## Ensaio nativo

O [script de endurance](../scripts/validate_pixel_endurance.py) passou com **180 segundos reais / aproximadamente oito horas musicais aceleradas**, Qt WebEngine por software, áudio sintético e ESP32 emulado. Configuração isolada em `.runtime/pixel-endurance-qa`.

- Uma fita de 300 pixels, seis barras, pares 1/6, 2/5 e 3/4: igualdade dos canais em todas as amostras.
- 16.876 blocos de áudio processados e **zero descartados**.
- 3.983 desenhos; média de **6,00 ms**, máximo observado de 32,70 ms. Difusão: zero.
- Buffers do sinal em 6.300 bytes e texturas em 10.800 bytes, sem crescimento nas amostras; histórico de até 12 combinações.
- 90 gravações concluídas com atraso de 50 ms provocado no worker, sem erro de disco.
- Pausa de 450 ms no renderer: saída apagada/desarmada e callbacks antigos rejeitados.
- Reabrir prévia preservou o projeto e manteve a captura ativa, sem reativar a saída física.
- Sem erros JavaScript, canais inválidos ou falha de fechamento.

[Relatório estruturado](resultado-pixel-endurance-v0.25.0.json) · [Log nativo](resultado-pixel-endurance-native-v0.25.txt) · [Captura dos controles](../preview-pixel-connections.png).

A memória residente do renderer variou de 140,01 a 217,14 MiB; terminou em 213,38 MiB. O resultado não exclui crescimento lento de memória. O FPS do ESP32 emulado não certifica o transporte físico. O teste não abriu sessão Link nem verificou precisão de drops com faixas reais. As mensagens gráficas de inicialização do Qt offscreen aparecem no log; o renderer passou nas verificações de desenho/canais e foi inspecionado visualmente.

**Não foi executado um ensaio de seis ou oito horas reais.** O comando para oito horas reais, a auditoria de gargalos e os limites remanescentes estão em [Confiabilidade](confiabilidade.md). Para reproduzir, execute na pasta main:

```powershell
.\.runtime\python312\python.exe -m pytest -q
node --test beatlight/tests/*.test.cjs
.\.runtime\python312\python.exe -X utf8 scripts\validate_pixel_endurance.py --seconds 28800 --music-hours 8
```

## Distribuição e operação

A compilação de src/scripts, `iniciar.cmd --help`, instalação editável e conferência de versão/bytes do wheel integram a entrega. O relatório do pacote fica em [resultado-package-v0.25.json](resultado-package-v0.25.json). Os dois projetos de conexões e os guias são incluídos no wheel. O firmware 0.22 permanece idêntico e compatível; não requer regravação.

Operação: [Conexões entre fitas](conexoes-fitas.md), [Pixel Studio](pixel-studio.md), [ESP32 USB](esp32-ws2812-usb.md). A validação anterior está arquivada em [validacao-v0.24.2.md](validacao-v0.24.2.md).
