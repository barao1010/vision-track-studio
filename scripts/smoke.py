"""Launch actual desktop, record screenshot and fail on callback errors."""
from pathlib import Path
import os
import tkinter as tk
from PIL import ImageGrab
from vtrack.app import App
root = tk.Tk()
errors = []
root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
app = App(root)
def capture():
    try:
        Path('assets').mkdir(exist_ok=True)
        root.geometry('1440x940+0+0')
        image = ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')) if os.name != 'nt' else ImageGrab.grab()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        image.crop((x, y, x + root.winfo_width(), y + root.winfo_height())).save('assets/desktop.png')
    except Exception as error:
        errors.append(str(error))
root.after(1500, capture)
root.after(2200, app.close)
root.mainloop()
if errors:
    raise RuntimeError('\n'.join(errors))
