# Efeitos por estrutura e cores musicais — 0.30

O AUTO SHOW e o ORGÂNICO agora conservam memória separada para groove, breakdown, build-up e drops. Uma volta ao mesmo tipo de trecho escolhe outra combinação e outra paleta principal. A memória é da apresentação em execução; não é identificação da track nem promessa de combinações inéditas para sempre.

## Doze desenhos de drop

Os desenhos passam por uma seleção embaralhada: os doze são percorridos antes de reutilizar o catálogo, sem repetir imediatamente o último desenho, inclusive na virada do ciclo. Há:

- Impacto total e Explosão de anéis;
- Asas espelhadas e Varredura dupla;
- Túnel pulsante e Cascata cruzada;
- Xadrez rítmico e Acordes de barras;
- Pêndulos opostos e Constelação elétrica;
- Leques em expansão e Rajadas de segmentos.

Cada desenho tem distribuição espacial e ritmo próprios. As camadas complementares entram progressivamente a cada dois tempos; o plano fica estável durante o drop. Os padrões foram desenhados também para uma única fita, usando as posições dos pixels, e não somente alternância entre barras.

O drop automático continua acompanhando os oito kicks confirmados da estrutura. **DROP AGORA** conserva a duração de oito tempos; o agendamento em Demonstração respeita a duração escolhida. Esta mudança não modifica a detecção musical, não cria kicks e não encerra a cena pela duração estimada quando ela está seguindo kicks reais.

Em **Automação → Desenhos de drop**, a opção padrão é **12 desenhos · variar sem repetir**. Para trabalhar com os estilos antigos Impacto/Turbo/Prisma, escolha **Usar o estilo de drop escolhido**. O nome do desenho ativo aparece na leitura do show.

## Groove, breakdown e build-up

O catálogo tem 14 famílias compatíveis. As famílias de groove incluem anéis, corrente, espiral, trama, órbitas, túnel, cascata e prisma. Breakdown pode usar corrente, maré, véu, névoa e constelação suave. Build-up usa espiral, trama, túnel, radar e convergência.

Ao mudar a estrutura, uma família diferente da entrada anterior é escolhida; a combinação também evita repetir a anterior daquele contexto. No modo Variado, a combinação e o elemento principal seguem a mesma proteção. Há uma estabilização de 250 ms para evitar que oscilações breves da análise troquem o show continuamente.

Durante um trecho estável, a direção Hipnótica mantém o mínimo de 32 tempos e troca uma camada por evolução. A direção Variada mantém 16. Assim, as entradas são variadas sem trocar o desenho em cada kick. Mudanças de estrutura têm prioridade e a fusão entre groove/breakdown/build-up usa até quatro tempos. A saída do drop mantém sua fusão progressiva.

Foram retiradas, dos modos automáticos, as camadas fixas que impunham atmosfera azul a 70% no breakdown e scanner no build-up. Elas escondiam as diferenças entre combinações. As famílias adequadas ao contexto e a velocidade modulada pela energia cuidam desses trechos agora.

## Cores que acompanham a música

**Automação → Cores no automático → Paletas musicais · energia e estrutura** vem ativado. Cada entrada escolhe uma paleta principal e um acento coordenado, com memória por estrutura para evitar a paleta principal da visita anterior. O status mostra os nomes e a energia recebida.

Grooves e drops podem alternar neon, RGB, fogo, ácido, pôr do sol, oceano e magenta. Breakdowns incluem perfis mais calmos e variações suaves. No build-up, a tensão acrescenta branco progressivamente; no drop, as cores voltam à saturação. A energia suavizada modifica o equilíbrio entre as paletas e sua distribuição ao longo das fitas. A evolução de cor acompanha o ritmo, sem sorteio por pixel ou por quadro.

**Manter a paleta escolhida** desativa essa automação. Paletas individuais das fitas, cor personalizada fixa e o comportamento Espectro RGB conservam a escolha explícita do operador. Para uma fita acompanhar as paletas musicais, sua paleta individual deve estar em **Seguir paleta global**. Master, brilho por fita, canal W, limite de corrente e blackout mantêm a prioridade.

Projetos anteriores recebem os dois novos controles ativados, mantendo geometria, continuidades e simetrias. As escolhas explícitas de desligá-los são salvas no projeto. Não é necessário regravar o ESP32.

## Validação

Os testes usam sequências longas, sorteio constante, 12 desenhos em uma fita de 300 pixels, retornos à mesma estrutura, respeito a cores fixas, cópias exatas, igualdade entre prévia/USB e memória limitada. A integração Qt testa USB emulado, desenho real, minimização e blackout. [Resultados da entrega](validacao.md).
