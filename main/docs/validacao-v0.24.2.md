# Validação — versão 0.24.2

Registro: 2026-10-27 (UTC). Controle óptico da difusão das fitas no Pixel Studio, com alcance de 0% a 300%, disponível também em Foco no palco. Não houve conexão a hardware físico.

**50 testes Python passaram** em tests/test_pixel.py, incluindo valores válidos/inválidos e persistência de show.glow. [Resultado](resultado-pytest-diffusion.txt).

**61 testes JavaScript passaram**, incluindo geometria, música, evolução hipnótica, simulação e USB. Os casos novos verificam que o controle não muda nenhum RGB/RGBW exportado, a amostragem física, o movimento ou a grade; conferem também ida/volta do projeto e padrão de 100% em projetos antigos. [Resultado](resultado-pixel-js-diffusion.txt).

O [ensaio nativo](../scripts/validate_pixel_diffusion.py) passou em Qt WebEngine com composição por software e configuração isolada em .runtime/pixel-diffusion-qa. Os valores RGB e o movimento foram congelados. A comparação de pixels reais do Canvas em 0/100/300% confirmou:

- halo externo exatamente preto em 0%, com núcleo luminoso preservado;
- halo mais largo e intenso em 300% que em 100%;
- ausência de faixas separadas no halo;
- mesmos valores de cor no centro e mesmos canais RGB nos três ajustes;
- salvamento de 300% no projeto e preservação do projeto original ao fechar uma montagem virtual temporária.

[Resultado nativo](resultado-pixel-diffusion-v0.24.2.json). As capturas são preview-pixel-diffusion-0.png, preview-pixel-diffusion-100.png e preview-pixel-diffusion-300.png. A inspeção visual acompanhou a leitura de pixels. A suavização gaussiana é separável e usa no máximo 26 desenhos de um halo pequeno por quadro no desktop, evitando um filtro de imagem inteira.

O pacote editável foi atualizado para 0.24.2. A compilação de src/scripts, iniciar.cmd --help e a conferência de bytes/versão do wheel fazem parte da entrega; o relatório fica em resultado-package-v0.24.2.json. O firmware USB 0.22 continua compatível, sem alterações.

A regressão Python ampla anterior, as medições de áudio e os limites de detecção musical permanecem documentados em [validacao-v0.24.md](validacao-v0.24.md). Não foram repetidos os testes de DSP nesta alteração óptica. Operação: [pixel-studio.md](pixel-studio.md).
