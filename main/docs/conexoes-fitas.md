# Conexões entre fitas — Pixel Studio 0.26

Abra **Mostrar controles → Fitas e geometria · controles individuais → Conexões · continuidade e simetria**. A posição das barras no desenho continua livre: as conexões definem o comportamento e a ordem dos pixels, sem mover o desenho.

Na 0.26, **Fitas e grupos** abre diretamente essa área. Os cartões verdes listam todas as conexões aplicadas, com origem, destinos, sentido e tipo de cópia. Cada cartão oferece **Editar grupo** e **Desligar grupo**. Os campos são um rascunho até clicar em Aplicar; o resumo informa quantos grupos estão ativos.

## Fazer a barra 6 acompanhar a barra 1

1. Em **Cópias exatas e espelhamento**, escolha a barra 1 em **Fita de referência**.
2. Em **Adicionar cópia**, escolha a barra 6 e clique **Adicionar destino**.
3. Mantenha **Mesmo sentido**, ou escolha a inversão para que início e fim sejam espelhados.
4. Em **Como copiar**, escolha **Cópia exata · mesmos pixels e formato**, e clique **Aplicar cópias**.

Cópia exata exige a mesma quantidade de pixels e formato RGB/RGBW. WS2811 e WS2812 RGB são compatíveis entre si; o tipo herdado da demonstração precisa corresponder ao mesmo tipo herdado no destino. Em fitas compostas, os formatos devem coincidir ao longo da sequência. **Mesmo sentido** repete a ordem; **Espelhado** a inverte.

Se houver diferenças, **Igualar destinos à referência e aplicar** ajusta resolução e perfil dos destinos antes de ativar. Pode aumentar o número de LEDs declarado para comportar os pixels; confira se corresponde ao equipamento. Não modifica posição nem metragem. Referências com perfis diferentes nos seus trechos devem ser ajustadas manualmente. Alterações que ultrapassem os limites do projeto são rejeitadas inteiras.

Para conservar resoluções diferentes, use **Adaptar à resolução do destino**, também usado nos grupos antigos sem modo explícito. A mesma fase é amostrada pela posição proporcional, com possível diferença de detalhe por causa da resolução.

Os destinos recebem o mesmo instante do efeito, cor, brilho, fase e resposta musical da referência. Adicione outras barras ao mesmo grupo para que todas acompanhem juntas. Crie outros grupos para ter, por exemplo, 1/6, 2/5 e 3/4. Também é possível copiar uma fita lógica inteira.

O perfil RGB/RGBW e o liga/desliga permanecem próprios de cada barra. Para cópias de cor exatas, use o mesmo perfil e a mesma resolução. Resoluções diferentes são ajustadas pela posição proporcional, sem interpolação entre pixels. Desligar a referência também apaga sua imagem nos destinos; desligar um destino não apaga a referência.

Os controles de efeito do destino ficam bloqueados e o painel identifica a referência. Edite o efeito na origem. **Desligar grupo** remove a associação e recupera os controles independentes armazenados nas barras.

## Dividir uma fita contínua entre várias barras

1. Em **Uma fita dividida em barras**, selecione a criação de uma nova fita lógica e dê um nome.
2. Adicione a barra 1 e depois a barra 2 usando **Adicionar trecho → Adicionar barra**.
3. Use **↑/↓** para definir a ordem do fio. O primeiro pixel da segunda barra vem imediatamente depois do último da primeira.
4. Escolha o sentido de ligação de cada trecho: **Início → fim** ou **Fim → início**. Isso permite desenhar uma fita em zigue-zague, por exemplo.
5. Clique **Aplicar continuidade**.

O efeito percorre a soma dos pixels, sem reiniciar em cada barra. Uma fita com trechos de 80 e 220 pixels comporta-se como uma fita contínua de 300 pixels. A metragem e a posição desenhada não mudam essa contagem.

Efeito, paleta, brilho, velocidade, fase, sentido do efeito e resposta musical são compartilhados a partir dos controles armazenados na primeira barra da sequência. Editar outra barra que participa dessa base altera esses mesmos controles. Liga/desliga e perfil de pixel permanecem por trecho. O **sentido de ligação** informa a ordem física; o **sentido do efeito** informa como o padrão se move nessa ordem.

**Desfazer continuidade** separa as barras novamente. Cada barra conserva seus controles individuais armazenados. Se a fita lógica era referência ou destino de uma cópia inteira, essa associação é removida junto com ela.

## Uma fita física de 300 pixels em seis barras simétricas

Importe [uma-fita-300-6-barras.json](../examples/uma-fita-300-6-barras.json) em **Importar projeto de fitas**. Exporte seu projeto atual antes se quiser manter uma cópia.

O exemplo contém:

- uma única fita lógica, com seis trechos de 50 pixels;
- ligação física na ordem 1 → 2 → 3 → 4 → 5 → 6;
- referências 1 → 6, 2 → 5 e 3 → 4;
- perfil WS2812, total de 300 LEDs e 300 pixels individuais.

Os primeiros três trechos mostram a base contínua do efeito. Os três seguintes repetem os trechos correspondentes no mesmo instante. As cópias conservam seus endereços no fio, mas não gastam posições adicionais na base visual: o efeito completo percorre os 150 pixels de origem e aparece também nas três cópias.

No painel **ESP32 USB**, escolha **Uma fita - 300 pixels / 6 barras**. O aplicativo envia um único quadro de 900 bytes RGB, na ordem dos seis trechos. O firmware 0.22 permanece compatível e não precisa ser regravado. A versão atual transmite uma única fita lógica de 300 pixels; várias fitas lógicas no desenho não criam novas saídas físicas no ESP32.

O segundo exemplo, [fitas-simetricas-continuas.json](../examples/fitas-simetricas-continuas.json), mostra duas fitas lógicas de 300 pixels, cada uma com três trechos, com cópia entre as fitas inteiras. A prévia mostra ambas; a saída USB permite selecionar uma delas.

## Resolução, limites e salvamento

**Preparar 300 WS2812** distribui 300 pixels individuais entre os trechos da fita selecionada, proporcionalmente à resolução anterior, com pelo menos um pixel por trecho. Aplica o perfil WS2812 a todos eles. As outras fitas permanecem com suas resoluções anteriores. Confira os comprimentos físicos e a distribuição de pixels da instalação antes de ativar a saída.

Uma barra pertence a apenas uma fita contínua. Cada barra de destino segue uma referência, e uma cópia não pode ser usada como origem de outra cópia. Essa regra também considera a sobreposição entre uma fita inteira e seus trechos; evita ciclos e ordens ambíguas. Reúna vários destinos no mesmo grupo. Permanecem os limites de 32 barras, 8.192 pixels controláveis e 32.768 LEDs no projeto.

Ao excluir uma barra, o sistema remove os trechos e as cópias que deixam de existir, preservando as demais barras por identificador. Alterar somente nome ou coordenadas preserva as conexões e os buffers de renderização.

O salvamento automático e **Exportar projeto de fitas** incluem as conexões. **Exportar geometria** guarda apenas o desenho, sem essas associações. Projetos antigos sem conexões abrem com barras independentes. **Simular meu projeto · sem USB** usa a instalação atual; **Testar outra montagem** cria uma montagem temporária; **Voltar ao meu projeto** recupera também as conexões originais. Exporte o projeto virtual para guardar as alterações feitas nessa montagem temporária.

As fitas são sempre exibidas sem difusão. O antigo ajuste de halo é ignorado na importação e não volta a ser salvo.
