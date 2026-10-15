# Dependências

O código desta árvore foi escrito para a base independente. Não foram importados fontes
nem patches do motor anterior. O histórico da branch conserva os commits anteriores.
Esta afirmação não é uma auditoria jurídica nem uma declaração de processo clean-room.

- Python e Tk/Tcl: runtime e interface. Preservar licenças correspondentes ao redistribuir.
- Pillow: composição e leitura de imagens, licença MIT-CMU. https://pillow.readthedocs.io/en/stable/about.html
- FFmpeg: executável externo instalado pelo utilizador. Não é incluído nesta árvore.
  As condições dependem das opções de compilação e codecs: https://www.ffmpeg.org/legal.html
  RTMP usa libx264 por padrão se disponível no executável escolhido. Gravação usa mpeg4.

Uma distribuição futura deve inventariar e incluir os avisos de cada dependência efetivamente
empacotada. Uma nova implementação não elimina os créditos das dependências que utilizar.
Os avisos e licenças da versão anterior não foram alterados nem apagados da branch main.
