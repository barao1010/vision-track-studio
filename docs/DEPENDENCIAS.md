# Dependências da base independente

A árvore atual foi escrita para o motor independente. Não importa fontes, patches,
bibliotecas ou plugins do motor anterior. O histórico preservado não é uma declaração
de processo clean-room nem uma auditoria jurídica.

| Componente | Uso | Avisos |
|---|---|---|
| Python/Tk/Tcl | Runtime/interface | Preservar avisos de Python e Tcl/Tk distribuídos |
| Pillow | Imagens/composição | MIT-CMU e avisos de componentes incluídos |
| NumPy | PCM/mixer/visão | BSD e componentes incluídos |
| OpenCV headless | HOG/histogramas | Apache-2.0 e licenças de componentes da wheel |
| Playwright / Chromium | Fontes web | Apache-2.0 e avisos Chromium/terceiros |
| pyserial | Portas série PTZ | BSD |
| PyAudioWPatch / PortAudio | Som do sistema WASAPI no Windows | MIT e avisos PortAudio |
| sounddevice / PortAudio | Monitorização | MIT e avisos PortAudio incluídos |
| FFmpeg | Executável externo | Não redistribuído; licença depende da compilação/codecs |
| PyInstaller | Empacotamento | GPL com exceção do bootloader e partes Apache-2.0 |
| ReportLab | Geração do manual | BSD e avisos de componentes |
| Inno Setup | Instalador | Condições do fornecedor; ver documentação |

O script scripts/collect_notices.py recolhe avisos dos pacotes instalados sem os alterar.
A completude dos avisos e obrigações de cada binário deve ser auditada antes de uma Release
final. A wheel OpenCV e o Chromium podem incluir componentes nativos com licenças próprias.
Não se deve apagar os avisos que acompanham essas dependências.

Referências primárias:
- https://www.ffmpeg.org/legal.html
- https://pillow.readthedocs.io/en/stable/about.html
- https://github.com/opencv/opencv/blob/4.x/LICENSE
- https://github.com/microsoft/playwright/blob/main/LICENSE
- https://pyinstaller.org/en/stable/license.html
- https://jrsoftware.org/isinfo.php

RTMP usa libx264 se disponível na instalação FFmpeg escolhida. A gravação usa mpeg4/AAC.
Os avisos e fontes da versão anterior permanecem intactos na branch main.
