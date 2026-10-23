# RGBW e Show em camadas — versão 0.12

## Operação

Reabra iniciar.cmd. No Stage Preview, use **Usar show RGBW → Ativar motor**; o seletor do Lighting Studio mostra **Show RGBW · cenas em camadas**. Mantenha Cores automáticas para a evolução pelo espectro e branco da subida. O efeito Show rítmico anterior e os outros sete efeitos permanecem no seletor.

Todos os seis pontos do inventário agora têm capacidade rgb + white. O contrato FixtureState mantém color como os três canais R/G/B e acrescenta white como quarto canal W, ambos normalizados. intensity é o dimmer comum, aplicado a RGB e W. Pan/tilt continuam apenas nos moving heads. É um inventário virtual, sem endereçamento ou saída física.

## Mistura e controles

As paletas continuam definindo uma cor aparente RGB. lighting/rgbw.py transfere a parte comum dos três canais ao W e a subtrai de RGB. Por exemplo, a cor desejada (0,25; 1; 0,70) vira RGB (0; 0,75; 0,45) + W 0,25. Branco puro vira RGB zero + W 1. Primárias saturadas usam W zero. A transferência evita contar a mesma parcela branca duas vezes.

**Uso do canal W** controla a fração transferida, de 0 a 100%. Reduzi-lo mantém a cor de base e redistribui o branco entre RGB e W; também reduz os acentos W adicionais do novo show. Não é o dimmer geral. **Intensidade geral** continua limitando toda a luz.

No **Controle manual**, marque Assumir controle manual e Escolher canais R/G/B/W manualmente. Os quatro ajustes são independentes; W não é extraído novamente das cores manuais. Para testar somente o emissor branco, coloque R/G/B em 0% e W em 100%. Intensidade manual, master e blackout continuam valendo. Sem a seleção de canais manuais, o manual usa a paleta escolhida e sua transferência automática para W.

As novas paletas são Ciano/Magenta, Lima/Rosa e Ouro/Gelo. Os ajustes manuais permitem misturas intermediárias. Em cores fixas, os padrões continuam alternando as duas cores escolhidas, incluindo sua componente W, sem rotação de matiz automática.

A tabela do Lighting Studio mostra a cor aparente e uma coluna Canal W; o tooltip da cor apresenta R/G/B/W exatos. O palco soma RGB e W com saturação em 1 e aplica intensity aos fachos/lentes. Esse modelo usa branco neutro e serve de ilustração; não mede reprodução de cor, temperatura ou eficiência luminosa de um aparelho real. Fixtures legadas sem white recebem apenas a composição RGB.

## Show RGBW

O novo modo combina os descritores existentes, sem mudar a análise acústica ou inventar kicks. O relógio é o mesmo grid contínuo, inclusive durante basslines e breakdowns sem kick.

| Família | Comportamento espacial |
|---|---|
| Perseguição | Percorre os quatro PARs |
| Vai e volta | Percorre e retorna |
| Pares alternados | Ímpares respondem aos pares |
| Espelho | Externos e internos |
| Acumulação | Abre conjuntos progressivamente |
| Resposta do baixo | Pares com respostas individuais |
| Cruzamento | Alterna blocos vizinhos, diagonais e espelho |
| Onda | Pares vizinhos percorrem o palco |
| Pergunta e resposta | Dois lados, pausa e resposta coletiva |
| Perseguição dupla | Intercala lados e termina em pares |

Densidade favorece conjuntos, cruzamentos e ondas. Baixo com atividade favorece respostas e perseguições intercaladas. Trechos esparsos usam perseguição, retorno e pergunta/resposta. A seleção continua nos limites de quatro tempos relativos, com histerese na densidade. A variação periódica avança a cada **16 tempos**; os aumentos sustentados da textura também agendam as viradas de dois tempos existentes. Assim a sequência tem repetição antes de evoluir.

**Complexidade do Show RGBW** limita a sobreposição: abaixo de 35% não há evolução periódica a cada 16 tempos; acima de 60%, densidade ponderada maior que 30% permite dois passos por tempo. A subdivisão é escolhida nos limites dos compassos, sem mudar a cada quadro. O grid e a leitura 4/4 continuam relativos, sem detecção de downbeat real.

Com cores automáticas, a matiz varia em passos de dois tempos por uma volta relativa de 16 tempos, com deslocamento entre PARs. Complexidade maior amplia essa variação. Kicks confirmados acrescentam acentos W ao conjunto ativo, mais fortes no drop. Candidatos graves rejeitados não disparam esse acento. O branco não substitui os padrões de intensidade.

Breakdown preserva a cena espaçada; build-up alterna pares, aumenta luminosidade e transfere o branco progressivo para W. Drop preserva o período de alta energia por oito kicks reais. Essas cenas têm prioridade sobre viradas por textura. Moving heads mantêm o movimento musical contínuo por BPM, energia, densidade e tensão, limitado pelo controle Movimento; zero congela sua posição.

## Persistência, exportação e prioridades

Settings v8 acrescenta light_white_strength e light_show_complexity. Versões 1–7 migram automaticamente, preservando os campos conhecidos e usando padrões de 100% e 70%. Salvar preferências de luz persiste os ajustes e o efeito. Valores manuais e ativação pertencem à sessão, como antes.

A exportação de estados agora usa **version: 2, color_model: RGBW**. Cada estado tem color (RGB), white (W) e intensity (dimmer), sem mistura física de canais DMX. Consumidores que liam o formato v1 precisam considerar white para reconstruir a cor aparente. O JSON é apenas uma inspeção; não transmite estados.

Blackout, desativação, master zero, silêncio ou áudio antigo zeram os quatro canais de saída nos estados automáticos pertinentes. Manual tem prioridade sobre automação. Falha e encerramento do worker também zeram RGB/W e intensidade, sem deixar W retido. Interpolação entre cenas considera o quarto canal.

## Validação e limites

355 testes passaram, incluindo 42 novos casos de RGBW, cenas e integração. Dois ensaios com palco aberto cobriram build/drop e bassline sem kick com camadas adicionais, além da inspeção manual de branco puro. Evidências em validacao.md. As capturas preview-rgbw-*.png mostram os controles, W na tabela e os efeitos.

Esses testes são sintéticos. Densidade/novidade são descritores da mixagem, não reconhecimento de instrumentos; mudanças de filtro ou ganho podem causar viradas. O modelo de cor é virtual e não está calibrado para LEDs físicos. Não há DMX, Art-Net, sACN ou conexão Ableton Link nesta etapa.
