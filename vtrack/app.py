"""Desktop studio built on the independent engine."""
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageDraw, ImageTk
from . import __version__
from .engine import Project, Scene, Source, Studio
from .media import Decoder, VideoOutput


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f'Vision Track Studio — {__version__}')
        self.root.geometry('1440x900')
        self.root.minsize(1000, 650)
        self.project = Project()
        self.project.scenes[0].sources = [Source('Fundo', value='#182230'),
            Source('Título', 'text', 'VISION TRACK STUDIO', x=80, y=260, width=1100, height=150)]
        self.studio = Studio(self.project)
        self.decoders = {}
        self.outputs = {}
        self.status = tk.StringVar(value='Base independente • desenvolvimento • saída de vídeo sem áudio')
        self.configure_theme()
        self.build()
        self.refresh_lists()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.tick()

    def configure_theme(self):
        self.root.configure(bg='#0b1018')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#182230', foreground='#edf3fc', font=('Segoe UI', 10))
        style.configure('TButton', padding=7, background='#273447')
        style.map('TButton', background=[('active', '#3187ff')])
        style.configure('TLabelFrame', background='#182230', bordercolor='#273447')
        style.configure('TLabelFrame.Label', foreground='#6bb6ff')
        self.logo = tk.PhotoImage(width=40, height=40)
        for row in range(5, 34):
            left = 5 + (row - 5) // 2
            right = 33 - (row - 5) // 2
            for col in range(40):
                if abs(col - left) < 3 or abs(col - right) < 3:
                    self.logo.put('#3187ff', (col, row))
        self.root.iconphoto(True, self.logo)

    def panel(self, parent, text):
        return ttk.LabelFrame(parent, text=text, padding=10)

    def build(self):
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill='x')
        ttk.Label(header, image=self.logo).pack(side='left')
        ttk.Label(header, text=' VISION TRACK  STUDIO', font=('Segoe UI', 18, 'bold')).pack(side='left')
        for title, action in [('Novo', self.new), ('Abrir', self.load), ('Guardar', self.save)]:
            ttk.Button(header, text=title, command=lambda fn=action: self.guard(fn)).pack(side='right', padx=3)
        body = ttk.Frame(self.root, padding=8)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(body, width=235)
        sidebar.grid(row=0, column=0, sticky='nsew', padx=5)
        scenes = self.panel(sidebar, 'CENAS')
        scenes.pack(fill='both', expand=True)
        self.scene_list = tk.Listbox(scenes, bg='#0b1018', fg='#edf3fc', selectbackground='#3187ff', exportselection=False)
        self.scene_list.pack(fill='both', expand=True)
        self.scene_list.bind('<<ListboxSelect>>', lambda event: self.select_scene())
        ttk.Button(scenes, text='+ Cena', command=self.add_scene).pack(fill='x', pady=5)
        sources = self.panel(sidebar, 'FONTES • baixo → topo')
        sources.pack(fill='both', expand=True, pady=8)
        self.source_list = tk.Listbox(sources, bg='#0b1018', fg='#edf3fc', selectbackground='#3187ff', exportselection=False)
        self.source_list.pack(fill='both', expand=True)
        for label, kind in [('Cor', 'color'), ('Imagem', 'image'), ('Texto', 'text'), ('Vídeo', 'video'), ('RTSP', 'rtsp')]:
            ttk.Button(sources, text='+ ' + label, command=lambda value=kind: self.guard(lambda: self.add_source(value))).pack(fill='x', pady=2)
        for label, fn in [('Editar posição/tamanho', self.edit_source), ('Mostrar / ocultar', self.toggle_source), ('Subir camada', self.raise_source), ('Remover fonte', self.remove_source)]:
            ttk.Button(sources, text=label, command=lambda action=fn: self.guard(action)).pack(fill='x', pady=2)
        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew', padx=5)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)
        center.rowconfigure(2, weight=1)
        preview = self.panel(center, 'PRÉ-VISUALIZAÇÃO')
        preview.grid(row=0, column=0, sticky='nsew')
        self.preview_view = tk.Label(preview, bg='#0b1018')
        self.preview_view.pack(fill='both', expand=True)
        transition = ttk.Frame(center, padding=8)
        transition.grid(row=1, column=0, sticky='ew')
        ttk.Button(transition, text='CORTE', command=lambda: self.studio.take(time.monotonic())).pack(side='left', padx=6)
        ttk.Button(transition, text='TRANSIÇÃO • 500 ms', command=lambda: self.studio.take(time.monotonic(), .5)).pack(side='left')
        program = self.panel(center, 'PROGRAMA')
        program.grid(row=2, column=0, sticky='nsew')
        self.program_view = tk.Label(program, bg='#0b1018')
        self.program_view.pack(fill='both', expand=True)
        controls = self.panel(body, 'SAÍDA DE VÍDEO')
        controls.grid(row=0, column=2, sticky='ns', padx=5)
        self.record_button = ttk.Button(controls, text='Gravar MKV', command=lambda: self.guard(self.record))
        self.record_button.pack(fill='x', pady=5)
        self.live_button = ttk.Button(controls, text='Transmitir RTMP', command=lambda: self.guard(self.live))
        self.live_button.pack(fill='x', pady=5)
        ttk.Label(controls, text='Nesta etapa: vídeo sem áudio.\n\nMixer, rastreio e PTZ\nainda em implementação.', wraplength=185).pack(pady=20)
        ttk.Button(controls, text='Sobre', command=lambda: messagebox.showinfo('Vision Track Studio',
            f'Vision Track Studio {__version__}\nMotor independente em desenvolvimento.\nPython/Tk, Pillow e FFmpeg externo.\nConsulte docs/DEPENDENCIAS.md.')).pack(fill='x')
        ttk.Label(self.root, textvariable=self.status, padding=8).pack(fill='x')

    def guard(self, fn):
        try:
            return fn()
        except Exception as error:
            messagebox.showerror('Vision Track Studio', str(error))

    def refresh_lists(self):
        self.scene_list.delete(0, 'end')
        for index, scene in enumerate(self.project.scenes):
            self.scene_list.insert('end', scene.name)
            if scene.id == self.studio.preview:
                self.scene_list.selection_set(index)
        self.source_list.delete(0, 'end')
        for source in self.studio.scene(self.studio.preview).sources:
            self.source_list.insert('end', ('● ' if source.visible else '○ ') + source.name)

    def select_scene(self):
        selected = self.scene_list.curselection()
        if selected:
            self.studio.preview = self.project.scenes[selected[0]].id
            self.refresh_lists()

    def add_scene(self):
        name = simpledialog.askstring('Cena', 'Nome da cena:')
        if name:
            scene = Scene(name)
            self.project.scenes.append(scene)
            self.studio.preview = scene.id
            self.refresh_lists()

    def add_source(self, kind):
        if kind in {'image', 'video'}:
            value = filedialog.askopenfilename(title='Escolher ficheiro')
        else:
            value = simpledialog.askstring('Nova fonte', {'color': 'Cor hexadecimal:', 'text': 'Texto:', 'rtsp': 'URL RTSP:'}[kind])
        if not value:
            return
        if kind == 'rtsp' and not value.startswith(('rtsp://', 'rtsps://')):
            raise ValueError('URL RTSP inválida')
        if kind == 'color':
            Image.new('RGB', (1, 1), value)
        source = Source(kind.title(), kind, value, width=self.project.width, height=self.project.height)
        if kind in {'video', 'rtsp'}:
            self.decoders[source.id] = Decoder(value, (source.width, source.height), kind == 'rtsp')
        self.studio.scene(self.studio.preview).sources.append(source)
        self.refresh_lists()

    def selected_source(self):
        selection = self.source_list.curselection()
        return self.studio.scene(self.studio.preview).sources[selection[0]] if selection else None

    def edit_source(self):
        source = self.selected_source()
        if not source:
            return
        answer = simpledialog.askstring('Transformação', 'x, y, largura, altura, opacidade (0 a 1)',
            initialvalue=f'{source.x}, {source.y}, {source.width}, {source.height}, {source.opacity}')
        if answer:
            parts = answer.split(',')
            if len(parts) != 5:
                raise ValueError('Indique cinco valores')
            x, y, width, height = map(int, parts[:4])
            opacity = float(parts[4])
            probe = Source('Teste', x=x, y=y, width=width, height=height, opacity=opacity)
            probe.validate()
            source.x, source.y, source.width, source.height, source.opacity = x, y, width, height, opacity

    def toggle_source(self):
        source = self.selected_source()
        if source:
            source.visible = not source.visible
            self.refresh_lists()

    def raise_source(self):
        source = self.selected_source()
        if source:
            sources = self.studio.scene(self.studio.preview).sources
            index = sources.index(source)
            if index < len(sources) - 1:
                sources[index], sources[index + 1] = sources[index + 1], sources[index]
            self.refresh_lists()

    def remove_source(self):
        source = self.selected_source()
        if source:
            if source.id in self.decoders:
                self.decoders.pop(source.id).close()
            self.studio.scene(self.studio.preview).sources.remove(source)
            self.refresh_lists()

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension='.vtrack.json', filetypes=[('Projeto Vision Track', '*.json')])
        if path:
            # Stream addresses can contain credentials; saving requires explicit warning.
            if any(s.kind == 'rtsp' and '@' in s.value for scene in self.project.scenes for s in scene.sources):
                if not messagebox.askyesno('Projeto', 'O projeto contém credenciais RTSP e será guardado em texto. Continuar?'):
                    return
            self.project.save(path)

    def replace_project(self, project):
        if self.outputs:
            raise RuntimeError('Pare as saídas antes de trocar de projeto')
        decoders = {}
        try:
            for scene in project.scenes:
                for source in scene.sources:
                    if source.kind in {'video', 'rtsp'}:
                        decoders[source.id] = Decoder(source.value, (source.width, source.height), source.kind == 'rtsp')
        except Exception:
            for decoder in decoders.values():
                decoder.close()
            raise
        for decoder in self.decoders.values():
            decoder.close()
        self.decoders = decoders
        self.project, self.studio = project, Studio(project)
        self.refresh_lists()

    def new(self):
        self.replace_project(Project())

    def load(self):
        path = filedialog.askopenfilename(filetypes=[('Projeto Vision Track', '*.json')])
        if path:
            self.replace_project(Project.load(path))

    def stop_output(self, name):
        output = self.outputs.pop(name)
        try:
            output.close()
        finally:
            self.record_button.configure(text='Gravar MKV')
            self.live_button.configure(text='Transmitir RTMP')
            if 'record' in self.outputs:
                self.record_button.configure(text='Parar gravação')
            if 'live' in self.outputs:
                self.live_button.configure(text='Parar transmissão')

    def record(self):
        if 'record' in self.outputs:
            return self.stop_output('record')
        path = filedialog.asksaveasfilename(defaultextension='.mkv', filetypes=[('Vídeo Matroska', '*.mkv')])
        if path:
            self.outputs['record'] = VideoOutput(path, (self.project.width, self.project.height), self.project.fps)
            self.record_button.configure(text='Parar gravação')

    def live(self):
        if 'live' in self.outputs:
            return self.stop_output('live')
        url = simpledialog.askstring('Transmissão', 'URL RTMP completa (incluindo chave):', show='*')
        if url:
            self.outputs['live'] = VideoOutput(url, (self.project.width, self.project.height), self.project.fps, live=True)
            self.live_button.configure(text='Parar transmissão')

    def display(self, widget, frame):
        image = frame.copy()
        image.thumbnail((max(16, widget.winfo_width()), max(16, widget.winfo_height())))
        widget.photo = ImageTk.PhotoImage(image)
        widget.configure(image=widget.photo)

    def tick(self):
        start = time.monotonic()
        frames = {key: decoder.frame() for key, decoder in self.decoders.items()}
        frames = {key: frame for key, frame in frames.items() if frame is not None}
        preview = self.studio.compositor.render(self.studio.scene(self.studio.preview), frames)
        program = self.studio.frame(start, frames)
        self.display(self.preview_view, preview)
        self.display(self.program_view, program)
        failures = []
        for name, output in self.outputs.items():
            output.submit(program)
            if output.error or output.process.poll() is not None:
                failures.append(name)
        for name in failures:
            self.guard(lambda key=name: self.stop_output(key))
        errors = list(self.studio.compositor.errors.values())
        decoder_errors = [decoder.error for decoder in self.decoders.values() if decoder.error]
        drops = sum(output.dropped for output in self.outputs.values())
        self.status.set((errors + decoder_errors + [f'Vídeo sem áudio • frames descartados: {drops}'])[0])
        delay = max(1, round((1 / self.project.fps - (time.monotonic() - start)) * 1000))
        self.root.after(delay, self.tick)

    def close(self):
        for name in list(self.outputs):
            self.guard(lambda key=name: self.stop_output(key))
        for decoder in self.decoders.values():
            decoder.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
