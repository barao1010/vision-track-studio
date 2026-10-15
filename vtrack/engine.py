"""Original scene graph, persistence, composition and transitions."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math
import os
import tempfile
import uuid
from PIL import Image, ImageDraw, ImageFont


def identifier():
    return uuid.uuid4().hex


@dataclass
class Source:
    name: str
    kind: str = 'color'
    value: str = '#182230'
    x: int = 0
    y: int = 0
    width: int = 1280
    height: int = 720
    opacity: float = 1.0
    visible: bool = True
    id: str = field(default_factory=identifier)
    settings: dict = field(default_factory=dict)

    def validate(self):
        if self.kind not in {'color', 'image', 'text', 'video', 'rtsp', 'camera', 'desktop', 'window', 'microphone', 'audio', 'browser'}:
            raise ValueError('Tipo de fonte inválido')
        if not self.name or not self.id:
            raise ValueError('Fonte sem nome ou identificador')
        if not (1 <= self.width <= 8192 and 1 <= self.height <= 8192):
            raise ValueError('Dimensões de fonte inválidas')
        if not math.isfinite(self.opacity) or not 0 <= self.opacity <= 1:
            raise ValueError('Opacidade inválida')


@dataclass
class Scene:
    name: str
    sources: list[Source] = field(default_factory=list)
    id: str = field(default_factory=identifier)


@dataclass
class Project:
    width: int = 1280
    height: int = 720
    fps: int = 25
    scenes: list[Scene] = field(default_factory=lambda: [Scene('Cena 1')])
    schema: int = 1

    def validate(self):
        if self.schema != 1:
            raise ValueError('Versão de projeto incompatível')
        if not (16 <= self.width <= 3840 and 16 <= self.height <= 2160 and 1 <= self.fps <= 60):
            raise ValueError('Formato de vídeo inválido')
        if self.width % 2 or self.height % 2 or not self.scenes:
            raise ValueError('Use dimensões pares e pelo menos uma cena')
        ids = []
        for scene in self.scenes:
            if not scene.name or not scene.id:
                raise ValueError('Cena inválida')
            ids.append(scene.id)
            for source in scene.sources:
                source.validate()
                ids.append(source.id)
        if len(ids) != len(set(ids)):
            raise ValueError('Identificadores duplicados')

    def save(self, path):
        self.validate()
        path = Path(path).resolve()
        descriptor, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                json.dump(asdict(self), handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        scenes = [Scene(name=s['name'], id=s['id'], sources=[Source(**v) for v in s['sources']]) for s in data.pop('scenes')]
        project = cls(scenes=scenes, **data)
        project.validate()
        # Media paths in a saved project are relative to its own directory.
        root = Path(path).resolve().parent
        for scene in project.scenes:
            for source in scene.sources:
                if source.kind in {'image', 'video', 'audio'} and not Path(source.value).is_absolute():
                    source.value = str(root / source.value)
        return project


class Compositor:
    def __init__(self, project):
        project.validate()
        self.project = project
        self.images = {}
        self.errors = {}
        self.fonts = {}

    def render(self, scene, frames=None):
        canvas = Image.new('RGBA', (self.project.width, self.project.height), 'black')
        frames = frames or {}
        for source in scene.sources:
            if not source.visible or source.kind in {'audio', 'microphone'}:
                continue
            try:
                size = (source.width, source.height)
                if source.kind == 'color':
                    layer = Image.new('RGBA', size, source.value)
                elif source.kind == 'text':
                    layer = Image.new('RGBA', size)
                    font_size = max(12, min(96, source.height // 3))
                    if font_size not in self.fonts:
                        self.fonts[font_size] = ImageFont.load_default(size=font_size)
                    font = self.fonts[font_size]
                    ImageDraw.Draw(layer).text((8, 8), source.value, fill='white', font=font)
                elif source.kind == 'image':
                    stat = Path(source.value).stat()
                    key = (source.value, stat.st_mtime_ns, stat.st_size)
                    if key not in self.images:
                        with Image.open(source.value) as opened:
                            self.images = {k: v for k, v in self.images.items() if k[0] != source.value}
                            self.images[key] = opened.convert('RGBA')
                    layer = self.images[key].resize(size, Image.Resampling.LANCZOS)
                else:
                    if source.id not in frames:
                        raise ValueError('A aguardar vídeo')
                    layer = frames[source.id].convert('RGBA').resize(size)
                if source.opacity != 1:
                    layer.putalpha(layer.getchannel('A').point(lambda value: round(value * source.opacity)))
                canvas.alpha_composite(layer, (source.x, source.y))
                self.errors.pop(source.id, None)
            except (OSError, ValueError) as error:
                self.errors[source.id] = f'{source.name}: {error}'
        return canvas.convert('RGB')


class Studio:
    def __init__(self, project):
        self.project = project
        self.compositor = Compositor(project)
        self.preview = project.scenes[0].id
        self.program = project.scenes[0].id
        self.transition = None
        self.last_frames = {}

    def scene(self, identifier):
        return next(s for s in self.project.scenes if s.id == identifier)

    def take(self, now, duration=0.0):
        if duration < 0 or not math.isfinite(duration):
            raise ValueError('Duração inválida')
        if self.preview == self.program:
            self.transition = None
            return
        # A take during a fade starts from the current composite, avoiding a flash.
        start = self.frame(now, self.last_frames).copy() if self.transition else None
        previous = self.program
        self.program = self.preview
        self.preview = previous
        self.transition = (now, duration, start, previous) if duration else None

    def frame(self, now, frames=None):
        self.last_frames = frames or {}
        target = self.compositor.render(self.scene(self.program), frames)
        if self.transition:
            start, duration, frozen, previous = self.transition
            fraction = min(1.0, max(0.0, (now - start) / duration))
            if fraction >= 1:
                self.transition = None
            else:
                old = frozen if frozen is not None else self.compositor.render(self.scene(previous), frames)
                return Image.blend(old, target, fraction)
        return target
