"""Explicit opt-in Python video effect API. Plugins run with application privileges."""
import importlib.util
from pathlib import Path
from PIL import Image


class VideoPlugin:
    def __init__(self, path):
        path = Path(path).resolve()
        if path.suffix.lower() != '.py':
            raise ValueError('Escolha um plugin Python .py')
        spec = importlib.util.spec_from_file_location('vision_track_user_plugin_' + str(id(self)), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if getattr(module, 'VISION_TRACK_API', None) != 1 or not callable(getattr(module, 'process_video', None)):
            raise ValueError('Plugin incompatível: requer VISION_TRACK_API=1 e process_video(image, context)')
        self.module = module
        self.error = None
        self.disabled = False

    def apply(self, frame, context):
        if self.disabled:
            return frame
        try:
            result = self.module.process_video(frame.copy(), context)
            if not isinstance(result, Image.Image) or result.size != frame.size:
                raise ValueError('Plugin devolveu uma imagem incompatível')
            return result.convert('RGBA')
        except Exception as error:
            self.error = f'Plugin desativado: {type(error).__name__}'
            self.disabled = True
            return frame
