# Detecção de kicks — fase 4, versão 0.3

## Caminho independente

KickDetector recebe AudioBlock original, sem Qt, PortAudio ou iluminação. Os filtros e a FFT escolhidos para o painel espectral não alteram suas decisões. AudioAnalyzer publica KickSnapshot junto dos medidores e do espectro. Uma falha opcional do detector não interrompe os demais; o erro fica no snapshot, nos logs e no painel. Uma troca válida de fonte/formato permite nova tentativa, sem repetição de logs a cada bloco.

A análise mantém os canais separados e combina suas potências, evitando o cancelamento de graves em estéreo com oposição de fase. Há um passa-banda Butterworth causal de ordem 4, com estado entre blocos. Na configuração padrão, a banda é 40–150 Hz.

## Evidências combinadas

1. Energia RMS ponderada pela janela na banda filtrada, com piso absoluto configurável.
2. Ataque: crescimento da energia em relação a aproximadamente 30 ms anteriores.
3. Fluxo: soma das diferenças positivas das magnitudes FFT na banda grave, normalizada pela magnitude atual.
4. Contraste: energia atual relativa à mediana dos últimos aproximadamente 1 s de análise.
5. Participação da banda grave no espectro original, para rejeitar ataques predominantemente agudos.
6. Histórico temporal: intervalo mínimo entre eventos e pequeno apoio de regularidade após três intervalos válidos.

A atividade combina ataque (45%), fluxo (35%) e contraste limitado (20%). A regularidade pode acrescentar até 0,04. O limiar usa mediana e desvio absoluto mediano da atividade recente, com piso e sensibilidade configurável. Energia, ataque, fluxo, contraste, participação grave e intervalo são condições conjuntas; volume sozinho não confirma um evento.

O apoio rítmico considera os últimos oito intervalos aceitos, sua dispersão e a proximidade do próximo intervalo observado. Não é um relógio musical: não prevê kicks na ausência de evidência, não produz BPM, fase ou compasso e não representa coerência com um PLL. O Beat Tracker da fase 5 consome estes eventos para estimar BPM e fase, sem realimentar o detector.

## Janelas, estado e eventos

O detector usa FFT própria de 2048 amostras, janela Hann e passo próximo de 10 ms. A janela dura 42,67 ms em 48 kHz e 46,44 ms em 44,1 kHz. A mediana precisa de 25 quadros de aquecimento: aproximadamente 300 ms de áudio contínuo. Esses tempos não são uma garantia de latência ponta a ponta.

Cada KickEvent contém tempo estimado no relógio de aquisição, instante de detecção, força relativa e confiança heurística. O tempo estimado é o centro da janela; o atraso do filtro causal não foi calibrado nem compensado. A força inicialmente medida no ataque é refinada pelo pico dos 90 ms seguintes, criando novos eventos imutáveis com o mesmo timestamp, sem duplicar a contagem. A confiança é limitada a 0,98 e não é probabilidade estatística.

O snapshot conserva 200 pontos de atividade/limiar e os últimos 16 eventos. A interface mostra oito eventos recentes. Não são armazenadas gravações. Lacunas de sequência, flags de driver, descontinuidade e troca de fonte/formato eliminam janelas incompletas, referências anteriores e intervalos rítmicos. A contagem da sessão é preservada, com novo aquecimento; iniciar outra captura cria um analisador novo.

## Ajustes

| Campo | Padrão | Limites e efeito |
|---|---|---|
| Corte inferior | 40 Hz | 20–375 Hz; menor que o superior. |
| Corte superior | 150 Hz | Até 400 Hz; banda com largura mínima de 25 Hz. |
| Sensibilidade | 1,0 × | 0,5–2,0; valores maiores reduzem o limiar de atividade. |
| Intervalo mínimo | 180 ms | 100–400 ms; bloqueia repiques, mas um intervalo alto também pode rejeitar kicks rápidos legítimos. |
| Piso de energia | −60 dBFS | −90 a −30 dBFS, medido na banda filtrada; independente do indicador de silêncio da entrada. |

Pare a captura, ajuste, salve e reinicie para comparar. Preferências JSON v3 migram automaticamente arquivos v1/v2, preservando os ajustes conhecidos. Valores inválidos mantêm a configuração anterior.

## Uso e limites

Abra Kick Monitor e compare os marcadores com a faixa no Traktor. Observe detecções ausentes e extras em trechos com kick isolado, baixo contínuo, viradas e pausas. Aumente a sensibilidade se faltar detecção e reduza se houver eventos extras; mantenha a faixa grave compatível com o material.

O detector é heurístico, sem modelo treinado de separação de instrumentos. Baixos com ataque, toms graves, mudanças bruscas de ganho e outras fontes percussivas graves podem ser confundidos com kicks. Masterizações muito comprimidas podem esconder o ataque e o contraste necessários. Os testes de volume não demonstram invariância abaixo do piso absoluto. Taxas de 44,1 e 48 kHz foram exercitadas; outros formatos nativos não tiveram a mesma avaliação de detecção.

O usuário aprovou a captura/DSP e relatou detecção de kicks quase perfeita e muito satisfatória no Traktor com a saída do notebook. O acompanhamento BPM/PLL foi acrescentado na fase 5 e também teve resultado aprovado pelo usuário. Veja validacao.md para as evidências e o roteiro.
