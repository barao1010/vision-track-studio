# Vision Track Studio - base independente

**0.2.0-dev.2, em desenvolvimento. Ainda não tem equivalência completa nem aprovação
para uso em produção.** A versão anterior permanece em main. Esta árvore contém
apenas o novo motor e a documentação; o histórico anterior não foi apagado.

Implementa cenas/fontes, camadas, preview/programa, corte/fade, mixer de áudio,
gravação A/V, RTMP, adaptadores de captura Windows, links web/CSS, deteção/seleção,
recorte digital, protocolos PTZ, presets, joystick, som do sistema WASAPI, filtros básicos
e uma API própria de plugins de vídeo. A troca de câmeras é experimental.
Leia os limites na [matriz de equivalência](docs/PARIDADE.md).

## Executar

Instale Python 3.12 com Tk e FFmpeg no PATH ou configure VISION_TRACK_FFMPEG.

```sh
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m scripts.fetch_models
python -m vtrack
```

Adicione fontes e prepare a cena em Pré-visualização; use Corte ou Transição para enviar
a Programa. A última fonte fica por cima. Vídeos com áudio criam um canal automaticamente;
RTSP permite ativá-lo no botão de áudio. Som do sistema usa WASAPI no Windows
e não pode ser usado com a monitorização ligada. Microfone é uma fonte separada. Nome de dispositivo
DirectShow e título de janela devem corresponder exatamente ao Windows.

Links web suportam transparência e CSS personalizado; não capturam áudio da página.
Gravação MKV usa vídeo MPEG-4 + áudio AAC. RTMP usa libx264 e AAC do FFmpeg externo.
Não são incluídos executáveis FFmpeg no pacote; instale uma compilação adequada.

Selecione uma fonte de vídeo e clique Detetar; clique numa caixa para selecionar uma pessoa.
PTZ automático, recorte e troca de câmeras são opções explícitas. Os protocolos e joystick
precisam de validação com hardware real; deteção por YOLOX e associação por aparência não garantem identidade. HOG é apenas fallback
quando o modelo não está instalado.

## Verificar / empacotar

```sh
python -m unittest discover -s tests -v
```

Defina VISION_TRACK_TEST_WEB=1 e VISION_TRACK_TEST_RTMP=1 para testes locais de navegador
e RTMP. Os testes de interface requerem ambiente gráfico. O workflow Windows executa estes
testes, gera captura real da interface e manual, empacota com PyInstaller e Inno Setup e
verifica o arranque do executável. Os pacotes são **artefactos de desenvolvimento**, não
uma Release final. Não há publicação automática de uma versão estável.

[Manual](docs/Vision-Track-Studio-Manual-PT.pdf) · [Dependências](docs/DEPENDENCIAS.md)
