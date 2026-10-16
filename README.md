# Vision Track Studio - base independente

**0.2.0-dev.3, em desenvolvimento. Ainda não tem equivalência completa nem aprovação
para uso em produção.** A versão anterior permanece em main. Esta árvore contém
apenas o novo motor e a documentação; o histórico anterior não foi apagado.

Implementa cenas/fontes, camadas, preview/programa, corte/fade, mixer de áudio,
gravação A/V, RTMP, adaptadores de captura Windows, links web/CSS, deteção/seleção,
recorte digital, protocolos PTZ, presets, joystick, som do sistema WASAPI, filtros básicos
e uma API própria de plugins de vídeo. A troca de câmeras continua experimental, agora com encaminhamento de áudio e ligações
PTZ por câmera mediante ativação explícita. Fontes de captura tentam religar após falha.
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

Links web suportam transparência, CSS e áudio de elementos HTML5 compatíveis.
CORS, DRM, páginas com grafos WebAudio próprios e outros limites do navegador podem
impedir captura; não há equivalência completa com todos os tipos de fonte web.
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

## Atualizações e distribuição

O aplicativo consulta o canal de versões finais `independent-vX.Y.Z`. Nunca oferece
releases antigas ou experimentais como atualização final. O download exige SHA256SUMS.txt
correspondente e confirmação do utilizador antes de fechar o app e abrir o instalador.
Repositórios privados requerem VISION_TRACK_GITHUB_TOKEN no computador; nenhum token
compartilhado é incluído no pacote. Não há ainda serviço público de atualização/licenciamento.
O workflow prepara apenas artefactos internos de desenvolvimento, com instalador, portable,
fonte e manual. A entrega e publicação de uma Release ficam bloqueadas até à confirmação
dos critérios de conclusão. Nenhuma versão experimental deve ser apresentada como pronta.
