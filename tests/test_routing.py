import unittest
from vtrack.audio import PCMBuffer
from vtrack.engine import Project, Scene, Source, Studio
from vtrack.runtime import Runtime


class RoutingTests(unittest.TestCase):
    def test_camera_handoff_moves_audio_and_keeps_source_fader(self):
        origin = Source('Original', 'rtsp', 'rtsp://one', settings={'gain': .4})
        other = Source('Outra', 'rtsp', 'rtsp://two')
        studio = Studio(Project(scenes=[Scene('Programa', [origin]), Scene('Outra câmera', [other])]))
        runtime = Runtime()
        class Capture:
            def close(self): pass
        try:
            for source in (origin, other):
                runtime.audio[source.id] = Capture()
                runtime.mixer.add(source.id, PCMBuffer())
            runtime.routed_source = origin.id
            runtime.selected_camera = other.id
            runtime.route_active = True
            runtime.update_audio(studio, 0)
            self.assertFalse(runtime.mixer.channels[origin.id].active)
            self.assertTrue(runtime.mixer.channels[other.id].active)
            self.assertEqual(runtime.mixer.channels[other.id].gain, .4)
            runtime.route_audio = False
            runtime.update_audio(studio, 0)
            self.assertTrue(runtime.mixer.channels[origin.id].active)
            self.assertFalse(runtime.mixer.channels[other.id].active)
        finally:
            runtime.close()

    def test_handoff_to_camera_without_audio_does_not_leave_old_audio(self):
        origin = Source('Original', 'rtsp', 'rtsp://one')
        studio = Studio(Project(scenes=[Scene('Programa', [origin])]))
        runtime = Runtime()
        class Capture:
            def close(self): pass
        try:
            runtime.audio[origin.id] = Capture()
            runtime.mixer.add(origin.id, PCMBuffer())
            runtime.routed_source, runtime.selected_camera = origin.id, 'camera_without_audio'
            runtime.route_active = True
            runtime.update_audio(studio, 0)
            self.assertFalse(runtime.mixer.channels[origin.id].active)
        finally:
            runtime.close()
