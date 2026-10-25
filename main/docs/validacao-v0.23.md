# Validação — versão 0.23

Registro: 2026-10-25. Windows x64, Python 3.12.10, Qt WebEngine com composição por software. Esta rodada valida evolução de efeitos, organização da interface e detecção de drops. **Nenhuma COM real foi aberta e nenhum ESP32 foi regravado.** A saída permanece em uma fita WS2812 RGB de 300 pixels, com firmware 0.22.

## Regressão automatizada

**704 testes Python passaram em 123,98 s**, sem testes pulados. [Resultado](resultado-pytest-v0.23.txt). Incluem captura, DSP, kick/grade, estrutura/drop, Link, projetos, interface e transporte USB/firmware emulado.

As regressões novas cobrem novidade espectral, invariância a ganho, retorno de kick sobre bassline sustentada, rejeição de roll fraco, impacto provisório, retirada real e confirmação da continuidade em três kicks únicos. A primeira luz não espera três kicks; as oito posições acústicas continuam protegidas contra falhas de confirmação. Foi conferida a equivalência do processamento em lote do histórico de candidatos, evitando recalcular a cadência para cada entrada repetida.

**47 testes JavaScript passaram.** [Resultado](resultado-pixel-js-v0.23.txt). Além de geometria, persistência e integração musical, verificam:

- mínimo de 16 tempos antes de trocar por novos elementos ou pelo prazo automático;
- entrada e saída graduais de camadas, preservando a base;
- combinações novas nas voltas de breakdown para groove;
- participação dos picos estável por composição e sincronização independente em quatro/oito tempos;
- blackout e ausência de relógio prevalecendo sobre picos;
- planos de drop variados, progressivos e limitados a oito tempos;
- velocidade suavizada por energia, sem alterar BPM/grade;
- migração de projetos antigos, controle Variação e reinício do relógio;
- novidade sustentada versus um onset isolado;
- amostragem RGB comum à prévia e à saída física para os 26 padrões.

## Interface e evolução no renderer nativo

[validate_pixel_evolution.py](../scripts/validate_pixel_evolution.py) passou em Qt WebEngine, com relógio controlado e cópia isolada do projeto disponível. As fitas da cópia foram configuradas para seguir o show global; o projeto real não foi alterado. O cenário atual tem uma linha e 300 pixels. [Resultado](resultado-pixel-evolution-v0.23.0.json).

O ensaio confirmou quatro camadas, pesos entrando progressivamente e saindo no fim do ciclo, mesma composição antes do mínimo e troca na fronteira de compasso agendada. A comparação usa o prazo informado pelo motor, pois a recepção nativa pode ocorrer alguns milissegundos após o início do compasso. Foram conferidos breakdown lento, build rápido, dois planos diferentes de drop com oito posições, botão de sincronizar pico, painéis recolhíveis e fechamento limpo.

O palco manteve posição e altura nas mudanças musicais, cabendo na área de visualização. O painel USB inicia recolhido e APAGAR SAÍDA permanece visível. Captura: preview-pixel-evolution.png.

## Ensaio de áudio sintético e drop

[validate_pixel_studio.py](../scripts/validate_pixel_studio.py) passou com áudio sintético, ponte Qt WebChannel e motor real do HTML. [Resultado](resultado-pixel-studio-v0.23.0.json).

O primeiro quadro de drop apareceu em **20,172 s**, para um impacto sintético em **20,000 s**: aproximadamente **172 ms** nesse cenário completo. As oito posições apareceram. Foram medidos **zero blocos de áudio descartados**, DSP médio de **1,61 ms**, máximo de **4,60 ms**, e desenho médio de **24,24 ms**, máximo de **35,10 ms**. Uma execução inicial descartava sete blocos; a leitura em lote do histórico de candidatos eliminou esse descarte no ensaio final.

Passaram as amostras de pintura após rolagem, drop manual nativo, valores RGB independentes, blackout, áudio parado, persistência e fechamento limpo. As amostras aguardam a conclusão da pintura antes da leitura. Esses números descrevem o ambiente e o áudio sintético usados; não são garantia de FPS ou latência para qualquer máquina ou track.

## USB emulado e compatibilidade do ESP32

[validate_pixel_usb.py](../scripts/validate_pixel_usb.py) passou com porta e firmware serial emulados, sem dispositivo real. [Resultado](resultado-pixel-usb-v0.23.0.json). Os **26 padrões** produziram quadros de **900 bytes RGB**, com **82 quadros** no cenário e indicador de aproximadamente **20,66 fps**. Rolagem e troca de painel mantiveram a transmissão. Blackout, APAGAR SAÍDA e apagamento/liberação da porta ao fechar passaram.

O protocolo BLP1 e a configuração física continuam iguais: uma fita, 300 LEDs individuais, ESP32 DevKit/WROOM-32, GPIO 18 e USB serial a 921.600 baud. **Não é necessário regravar o firmware 0.22 para usar as novas combinações.** Não foram implementadas saídas paralelas nesta rodada.

Sketch, protocolo e imagem permanecem os da compilação 0.22 registrada em [resultado-esp32-v0.22.json](resultado-esp32-v0.22.json). A imagem unificada tem 357.360 bytes e SHA256 `9b46db6cc3661fd19cc909819c064c2d8e68041c663088c98fd792a88cec4cff`. A validação anterior documenta o toolchain e os testes do sketch real no computador: [validacao-v0.22.md](validacao-v0.22.md).

## Pacote e limites

O aplicativo e o pacote passam a **0.23.0**, mantendo pySerial 3.5 e os demais requisitos. O wheel inclui HTML, módulos Python, guias, avaliação do anexo, projeto de 300 pixels e firmware 0.22. A conferência de empacotamento fica em resultado-package-v0.23.json. Os comandos de reprodução estão no README.

A avaliação das recomendações está em [avaliacao-recomendacoes-drop-v0.23.md](avaliacao-recomendacoes-drop-v0.23.md). RMS, graves relativos, onsets, contexto, assinatura do kick e grade já existiam. Foram acrescentados novidade espectral e distinção explícita entre impacto imediato e continuidade. O score é diagnóstico; identidade, potência e alinhamento continuam obrigatórios. Aprendizado de máquina não foi adicionado sem áudio anotado para treinamento e avaliação.

Não foram fornecidos arquivos das tracks com atraso. Os testes sintéticos não medem a precisão em toda a biblioteca musical, a latência física do áudio ou o resultado elétrico na fita. Não foi aberta nova sessão nativa Link/Traktor. Não há DMX físico. Instruções de operação: [pixel-studio.md](pixel-studio.md); montagem existente: [esp32-ws2812-usb.md](esp32-ws2812-usb.md).
