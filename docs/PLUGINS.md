# API própria de efeitos de vídeo

Carregue explicitamente um ficheiro .py pelo botão Plugin da fonte selecionada.
Plugins são código executável com os privilégios do aplicativo. Só execute os que conhece.
Não são carregados automaticamente a partir de projetos JSON e não são compatíveis
com plugins binários de outros motores.

```python
from PIL import ImageOps
VISION_TRACK_API = 1

def process_video(image, context):
    # image: RGBA; manter as mesmas dimensões; context: source_id e kind.
    return ImageOps.mirror(image)
```

A execução é síncrona no motor de vídeo. Plugins lentos afetam a taxa de imagem;
erros e resultados incompatíveis desativam o plugin na sessão, preservando a fonte.
A API atual não oferece áudio, interface nativa nem acesso ao grafo de cenas.
