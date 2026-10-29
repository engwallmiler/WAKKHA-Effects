# Validação — versão 0.24

Registro: 2026-10-25. Windows x64, Python 3.12.10, Qt WebEngine por software. Esta rodada acrescenta referência explícita dos picos do groove e direção visual Hipnótica. Nenhum dispositivo físico foi aberto ou regravado.

## Regressões automatizadas

**712 testes Python passaram em 138,83 s**, sem testes pulados. [Resultado](resultado-pytest-v0.24.txt). As regressões novas conferem médias em potência linear com acentos isolados, três níveis de ganho, tolerância conjunta do pico e transiente, rejeição de baixo alto com ataque fraco, roll acelerado e congelamento da referência durante build/primeiro retorno. O contrato de projeto aceita as duas direções visuais e rejeita valores desconhecidos.

Continuam aprovados os testes de primeiro impacto no pipeline completo, timbre/assinatura curta, basslines, agudos sem kick, pausas, BPM/fase Link, deduplicação, oito confirmações acústicas, continuidade e isolamento de falhas.

**53 testes JavaScript passaram.** [Resultado](resultado-pixel-js-v0.24.txt). A direção Variada conserva as regressões de mínimo de 16 tempos. A Hipnótica acrescenta:

- permanência mínima de 32 tempos mesmo com novos elementos;
- base preservada por três composições, com somente uma camada substituída em cada troca dentro da família;
- crescimento das camadas ao longo de oito tempos e sustentação após a antiga fronteira de 16;
- repertórios compatíveis com breakdown/build e prioridade da mudança estrutural;
- continuidade dos elementos retidos e da sincronização;
- repetição visual do conjunto de ondas em um ciclo comum, sem deriva independente;
- migração de projetos antigos para o novo padrão sem alterar geometria/controles das fitas.

Também passaram os testes existentes de todos os 26 efeitos, blackout, silêncio, dados antigos, picos de quatro/oito tempos, drop manual/automático e cálculo RGB compartilhado com USB.

## Evolução e interface nativas

[validate_pixel_evolution.py](../scripts/validate_pixel_evolution.py) passou com relógio controlado, motor HTML real e uma cópia isolada do projeto disponível. A cópia usa uma linha de 300 pixels e quatro camadas seguindo o show global. O projeto real não foi alterado. [Resultado](resultado-pixel-evolution-v0.24.0.json).

O ensaio confirmou crescimento gradual, mesma composição até o prazo de 32 tempos/fronteira de compasso, mesma família e apenas uma substituição na próxima frase. Passaram a desaceleração do breakdown, aceleração do build, dois planos diferentes de drop com oito posições, sincronizar pico, painéis recolhíveis, altura estável do palco e fechamento limpo. A captura aguarda a pintura nativa depois das mudanças de painel: preview-pixel-evolution.png.

## Áudio sintético e latência observada

[validate_pixel_studio.py](../scripts/validate_pixel_studio.py) passou com áudio sintético e Qt WebChannel. [Resultado](resultado-pixel-studio-v0.24.0.json). O primeiro quadro do drop apareceu em **20,140 s**, para impacto em **20,000 s**: cerca de **140 ms** no cenário completo. Foram vistas as oito posições, com **zero blocos de áudio descartados**. DSP: média **1,68 ms**, máximo **4,85 ms**. Desenho: média **24,44 ms**, máximo **32,30 ms**.

Passaram as amostras de pintura após rolagem, drop manual nativo, RGB independente, blackout, áudio parado, persistência e fechamento. Essa latência inclui o cenário desktop; as regressões separadas do pipeline também verificam o primeiro ataque. Os números não demonstram precisão universal nem garantem FPS/latência em outras máquinas ou tracks.

## Saída USB e pacote

[validate_pixel_usb.py](../scripts/validate_pixel_usb.py) passou com serial/firmware emulados e nenhuma COM real aberta. [Resultado](resultado-pixel-usb-v0.24.0.json). Os 26 padrões produziram quadros de 900 bytes RGB; foram confirmados 82 quadros e o indicador desse ensaio offscreen ficou aproximadamente em 15,50 fps. Rolagem, troca de painel, blackout, APAGAR SAÍDA e apagamento/liberação da porta ao fechar passaram. Esse indicador emulado não mede a taxa da montagem do usuário.

A saída permanece uma fita WS2812/WS2812B RGB de 300 LEDs, ESP32 DevKit/WROOM-32, GPIO 18, BLP1 e 921.600 baud. **O firmware 0.22 continua compatível; não é necessário regravar.** A imagem de 357.360 bytes mantém SHA256 `9b46db6cc3661fd19cc909819c064c2d8e68041c663088c98fd792a88cec4cff`. Não foram acrescentadas saídas paralelas ou DMX físico.

O aplicativo e o pacote editável passam a 0.24.0, com as mesmas dependências e pySerial 3.5. O wheel inclui HTML, módulos Python, projeto de 300 pixels, guias e firmware compatível. A conferência de bytes, versão e hash fica em resultado-package-v0.24.json. Compilação de src/scripts e iniciar.cmd --help integram a conferência final.

## Limites

A média dos picos só prova recuperação após um ataque real passar por identidade, potência e alinhamento. A bassline isolada e a previsão de relógio não criam kicks. A referência conjunta usa tolerância de 90% da potência do transiente e 85% do pico; os caminhos anteriores de menor volume permanecem sujeitos aos filtros existentes. São critérios heurísticos, não um modelo treinado.

Não foram fornecidos arquivos das tracks problemáticas. Os resultados sintéticos não medem precisão em toda a biblioteca nem latência elétrica na fita. Nenhuma nova sessão Link/Traktor nativa foi aberta. Operação: [pixel-studio.md](pixel-studio.md). Critérios: [drop-detection.md](drop-detection.md). Histórico: [validacao-v0.23.md](validacao-v0.23.md).
