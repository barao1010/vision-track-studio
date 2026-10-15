import os
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path(sys._MEIPASS) / 'playwright/driver/package/.local-browsers'))

if '--smoke-test' in sys.argv:
    import tkinter as tk
    from vtrack.app import App
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    from tkinter import messagebox
    messagebox.showerror = lambda title, text: errors.append(text)
    app = App(root)
    from vtrack.output import AVOutput
    import tempfile
    directory = tempfile.TemporaryDirectory()
    destination = str(Path(directory.name) / 'smoke.mkv')
    app.runtime.add_output('record', AVOutput(destination, (app.project.width, app.project.height), app.project.fps))
    root.after(1500, app.close)
    root.mainloop()
    if not Path(destination).exists() or Path(destination).stat().st_size < 1024:
        errors.append('No encoded output')
    directory.cleanup()
    sys.exit(1 if errors else 0)
else:
    from vtrack.app import main
    main()
