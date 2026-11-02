# Replay causal e rotulagem — 0.29

O replay executa o mesmo `AudioAnalyzer` da aplicação, lendo o WAV em blocos. Não inicia captura, Link, preview, ESP32 ou iluminação. O processamento é acelerado, sem esperar a duração real da faixa; execute separadamente de uma apresentação para medir custo sem disputar CPU com o Traktor.

## Preparar o material

Use WAV PCM sem compressão, de 8/16/24/32 bits, mono ou estéreo, de preferência no formato da captura real. PCM de 24 bits é aceito. WAV float, MP3 e outros contêineres devem ser convertidos previamente. A ferramenta não instala codecs, não normaliza volume e não altera o áudio.

Marque no editor de áudio os segundos exatos dos kicks e drops. Use a mixagem que chega ao programa, incluindo basslines, filtros e transições. Uma faixa original isolada não representa necessariamente uma mixagem com dois decks. Comece com os casos problemáticos e trechos negativos semelhantes; depois amplie o conjunto.

Copie [replay-labels.json](../examples/replay-labels.json) e substitua os tempos ilustrativos. O formato é:

```json
{
  "version": 1,
  "bpm": 128,
  "regions": [[16, 64]],
  "kicks": [16.0, 16.46875],
  "drops": [48.0],
  "states": [
    {"start": 32, "end": 40, "state": "breakdown"},
    {"start": 40, "end": 48, "state": "buildup"},
    {"start": 48, "end": 52, "state": "drop"}
  ]
}
```

**Esse trecho é apenas um exemplo de formato:** se `kicks` estiver presente, anote TODOS os kicks nas regiões avaliadas. As demais detecções serão contadas como falsas. Para avaliar somente drops e estrutura, remova `kicks`. Lista ausente significa não avaliado; lista vazia significa região negativa sem eventos. `regions` pode delimitar vários trechos completamente anotados; fora deles não há cálculo de precisão. O áudio anterior ainda é analisado para adquirir a referência, sem cortar o aquecimento.

Tempos são relativos ao início do WAV. Regiões e estados não podem se sobrepor ou ultrapassar o áudio. Estados válidos: `warming`, `groove`, `breakdown`, `buildup`, `drop`, `silence`. Não é necessário rotular todos os estados para medir drops.

## Executar

Na pasta `main`, com captura normal parada:

```powershell
.\replay.cmd "C:\Audio\faixa.wav" "C:\Audio\faixa.labels.json" --out ".runtime\replays\faixa-01"
```

O diretório de saída deve ser novo. A ferramenta não sobrescreve relatórios anteriores. Alternativa equivalente: `.\.runtime\python312\python.exe -m beatlight.replay ...`.

O modo padrão estima o inteiro pelo áudio. Use `--grid-mode continuous` para testar andamento fracionário ou `--fixed-bpm 128` para reproduzir o valor informado pelo operador. O `bpm` dos rótulos **nunca orienta o detector**; só define a tolerância de avaliação de drops. O teste também não usa Link ou posições de deck como conhecimento futuro.

Para reproduzir seus ajustes de sensibilidade, filtros e grade, exporte as preferências em Configurações e acrescente `--settings "C:\Audio\preferences.json"`. Esses parâmetros ficam registrados em `analysis_parameters` no relatório; configurações de captura, Link e luz não são ativadas. As opções explícitas de BPM da linha de comando têm prioridade sobre as preferências.

`--block-size 512` reproduz o bloco padrão. Compare, por exemplo, 113 e 2048 samples para medir o efeito do tamanho do bloco sobre disponibilidade e latência.

## Ler os resultados

- **report.html**: abra localmente no navegador. Mostra linhas de referência/detecção, resumo de métricas, etapas e transições. Clique numa linha para posicionar o áudio; Play é manual. Não controla luzes.
- **report.json**: dados completos, associações entre eventos e rótulos, atrasos, falsos, perdidos e confusão dos estados ponderada por tempo.
- **decisions.jsonl**: uma linha por avaliação de candidato. Distingue rejeição de forma/queda/ataque/harmônicos, potência insuficiente, alinhamento e recuperação/contexto.

Kicks usam associação única a até 75 ms; drops usam até um tempo do BPM anotado. Isso mede acerto temporal, não apenas o estado final. Falsos drops/minuto usam a duração das regiões rotuladas. O JSON também informa quantos impactos chegaram até 150 ms e quantos chegaram antes do rótulo.

Há dois tempos separados: o **erro do timestamp do ataque** e o **atraso até a decisão estar disponível**. A disponibilidade usa o fim do bloco realmente entregue, incluindo a janela FFT. Não retrocede a decisão ao centro da FFT e não usa `monotonic()` de um replay acelerado como se fosse tempo da faixa. A medição não inclui drivers de captura, envio USB ou fita.

O rastreio existe apenas no replay. A aplicação de apresentação não grava candidatos no disco. Históricos de análise são limitados; percentis de custo usam os últimos 8.192 blocos e o máximo acompanha a execução inteira. O relatório completo de eventos cresce com o áudio avaliado e fica no processo offline. A prévia desenha no máximo 4.000 marcas por linha, mantendo o JSON completo.

## Antes de ajustar limiares

Observe o candidato do primeiro kick: ele apareceu no detector bruto? Passou pela identidade curta? Parou em `identity_early_attack`, `identity_early_click_body_power`, `return_power`, `grid_alignment` ou `recovery_or_context`? Compare os mesmos arquivos e rótulos entre versões, incluindo negativos e rolls fracos. Não reduza um limiar só porque uma faixa melhorou.

O conjunto sintético desta entrega é reproduzível por `scripts/validate_drop_replay.py`. Ele testa mecanismos isolados; não substitui um conjunto de faixas reais rotuladas. [Avaliação das sugestões](avaliacao-abordagens-v0.29.md).
