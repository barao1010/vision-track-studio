import os
import unittest


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Requer ambiente gráfico')
class DesktopTests(unittest.TestCase):
    def test_startup_scene_switch_and_shutdown(self):
        import tkinter as tk
        from vtrack.app import App
        from vtrack.engine import Scene, Source
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda kind, value, tb: errors.append(value)
        app = App(root)
        scene = Scene('Teste', [Source('Texto', 'text', 'Teste')])
        app.project.scenes.append(scene)
        app.studio.preview = scene.id
        app.refresh_lists()
        app.studio.take(__import__('time').monotonic(), .1)
        deadline = __import__('time').monotonic() + 3
        def verify():
            if app.program_view.winfo_width() <= 100 and __import__('time').monotonic() < deadline:
                root.after(50, verify)
                return
            try:
                self.assertTrue(app.camera_view.winfo_ismapped())
                if app.program_view.winfo_width() <= 100:
                    print('layout diagnostics:', {'root': root.geometry(), 'mapped': root.winfo_ismapped(), 'workspace': (app.workspace.winfo_width(), app.workspace.winfo_height()), 'body': (app.body_panes.winfo_width(), app.body_panes.winfo_height()), 'sashes': (app.body_panes.sashpos(0), app.body_panes.sashpos(1)), 'program': (app.program_view.winfo_width(), app.program_view.winfo_height())}, flush=True)
                self.assertGreater(app.program_view.winfo_width(), 100)
                app.project.settings['panel_sashes'] = [260, 1100]
                app.restore_layout()
                self.assertEqual(app.body_panes.sashpos(0), 260)
            finally:
                app.close()
        root.after(200, verify)
        root.after(4000, app.close)
        root.mainloop()
        self.assertEqual(errors, [])
        self.assertFalse(app.runtime.audio_worker.is_alive())
