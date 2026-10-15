# Vision Track Studio — base independente

Versão 0.2.0-dev.1. Motor novo em Python, Pillow e FFmpeg externo, com interface desktop
própria em grafite/azul. Esta branch contém apenas a nova implementação e sua documentação.
A versão anterior continua em `main`.

**Em desenvolvimento: não tem ainda a mesma funcionalidade completa da versão anterior.**
Consulte [a matriz de equivalência](docs/PARIDADE.md) antes de testar.

## Executar

Instale Python 3.12 com Tk e FFmpeg no PATH (ou defina VISION_TRACK_FFMPEG).

```sh
python -m pip install -r requirements.txt
python -m vtrack
```

Escolha/crie uma cena, adicione fontes e configure posição/tamanho. A última fonte da lista
fica por cima das restantes. Selecione outra cena e use Corte ou Transição para enviar ao
Programa. Guarde projetos em JSON. RTSP com credenciais é guardado em texto apenas após
confirmação na interface. Não partilhe projetos que contenham palavras-passe.

Gravar MKV grava o Programa **sem áudio**. Transmitir RTMP também envia apenas vídeo e
necessita libx264 no FFmpeg escolhido; não foi validado contra um serviço real.
O botão muda para Parar enquanto a saída está ativa. Erros de codificação são reportados.

## Verificação

```sh
python -m unittest discover -s tests -v
```

A suite verifica pixels, transições, persistência, perda/recuperação de identidade por dados
sintéticos e criação/descodificação de vídeo real. Não comprova funcionamento com câmeras.
O workflow Windows valida arranque Tk e executa a suite; não publica um instalador final.

[Dependências e créditos](docs/DEPENDENCIAS.md) · [Recursos e limitações](docs/PARIDADE.md)
