import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from vtrack.engine import Project, Scene, Source, Compositor, Studio


class EngineTests(unittest.TestCase):
    def test_layers_clipping_opacity_visibility(self):
        scene = Scene('Teste', [Source('Fundo', value='#0000ff', width=32, height=32),
            Source('Topo', value='#ff0000', x=-8, y=8, width=16, height=16, opacity=.5),
            Source('Oculta', value='white', visible=False)])
        project = Project(32, 32, 25, [scene])
        image = Compositor(project).render(scene)
        self.assertEqual(image.getpixel((4, 12)), (128, 0, 127))
        self.assertEqual(image.getpixel((12, 12)), (0, 0, 255))

    def test_roundtrip_and_schema_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'project.json'
            project = Project(scenes=[Scene('Ação', [Source('Texto', 'text', 'Olá')])])
            project.save(path)
            loaded = Project.load(path)
            self.assertEqual(loaded.scenes[0].sources[0].value, 'Olá')
            self.assertEqual(project.scenes[0].id, loaded.scenes[0].id)
            data = json.loads(path.read_text())
            data['schema'] = 999
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Project.load(path)

    def test_invalid_project_never_replaces_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'project.json'
            project = Project()
            project.save(path)
            saved = path.read_bytes()
            project.width = 17
            with self.assertRaises(ValueError):
                project.save(path)
            self.assertEqual(path.read_bytes(), saved)

    def test_cut_fade_and_interrupted_fade(self):
        scenes = [Scene('Azul', [Source('Azul', value='blue', width=32, height=32)]),
            Scene('Vermelho', [Source('Vermelho', value='red', width=32, height=32)])]
        studio = Studio(Project(32, 32, 25, scenes))
        studio.preview = scenes[1].id
        studio.take(10, 2)
        self.assertEqual(studio.frame(11).getpixel((0, 0)), (127, 0, 127))
        studio.take(11, 2)
        self.assertEqual(studio.frame(11).getpixel((0, 0)), (127, 0, 127))
        self.assertEqual(studio.frame(13).getpixel((0, 0)), (0, 0, 255))
        studio.take(14)
        self.assertEqual(studio.frame(14).getpixel((0, 0)), (255, 0, 0))

    def test_missing_media_reports_error_without_crashing(self):
        scene = Scene('Teste', [Source('Imagem', 'image', '/file-not-found')])
        compositor = Compositor(Project(scenes=[scene]))
        self.assertEqual(compositor.render(scene).getpixel((0, 0)), (0, 0, 0))
        self.assertIn(scene.sources[0].id, compositor.errors)

    def test_image_and_external_video_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'still.png'
            Image.new('RGB', (32, 32), 'green').save(path)
            source = Source('Vídeo', 'video', 'test', x=16, width=16, height=32)
            scene = Scene('Média', [Source('Imagem', 'image', str(path), width=32, height=32), source])
            compositor = Compositor(Project(32, 32, 25, [scene]))
            output = compositor.render(scene, {source.id: Image.new('RGB', (16, 32), 'red')})
            self.assertEqual(output.getpixel((2, 2)), (0, 128, 0))
            self.assertEqual(output.getpixel((20, 2)), (255, 0, 0))


if __name__ == '__main__':
    unittest.main()
