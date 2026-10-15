"""Independent Vision Track desktop studio."""
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageDraw, ImageTk
from . import __version__
from .engine import Project, Scene, Source, Studio
from .runtime import Runtime
from .output import AVOutput
from .capture import devices
from .ptz import PTZSession
from .joystick import Joystick


class App:
    def __init__(self, root):
        self.root = root
        root.title(f'Vision Track Studio - {__version__}')
        root.geometry('1440x940')
        root.minsize(1080, 760)
        self.project = Project(scenes=[Scene('Cena 1', [Source('Fundo', value='#182230'),
            Source('Título', 'text', 'VISION TRACK STUDIO', x=80, y=260, width=1100, height=150)])])
        self.studio = Studio(self.project)
        self.runtime = Runtime()
        self.ptz = None
        self.joystick = None
        self.manual = None
        self.last_camera = None
        self.last_tick = time.monotonic()
        self.closed = False
        self.status = tk.StringVar(value='Base independente em desenvolvimento')
        self.follow = tk.BooleanVar(value=False)
        self.digital = tk.BooleanVar(value=False)
        self.handoff = tk.BooleanVar(value=False)
        self.profile = tk.StringVar(value='Cinema')
        self.zoom = tk.DoubleVar(value=2)
        self.tracker_status = tk.StringVar(value='Selecione uma fonte de vídeo e ative a deteção')
        self.gain = tk.DoubleVar(value=1)
        self.muted = tk.BooleanVar(value=False)
        self.meters = {}
        self.configure_theme()
        self.build()
        self.refresh_lists()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<FocusOut>', self.focus_out)
        self.tick()

    def configure_theme(self):
        self.root.configure(bg='#0b1018')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#182230', foreground='#edf3fc', font=('Segoe UI', 10))
        style.configure('TButton', padding=5, background='#273447')
        style.map('TButton', background=[('active', '#3187ff')])
        style.configure('TLabelFrame', background='#182230', bordercolor='#273447')
        style.configure('TLabelFrame.Label', foreground='#6bb6ff')
        from .brand import icon
        self.logo = ImageTk.PhotoImage(icon(40))
        self.root.iconphoto(True, self.logo)

    def panel(self, parent, text):
        return ttk.LabelFrame(parent, text=text, padding=7)

    def button(self, parent, label, fn):
        button = ttk.Button(parent, text=label, command=lambda: self.guard(fn))
        button.pack(fill='x', pady=2)
        return button

    def build(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill='x')
        ttk.Label(header, image=self.logo).pack(side='left')
        ttk.Label(header, text=' VISION TRACK  STUDIO', font=('Segoe UI', 18, 'bold')).pack(side='left')
        for title, action in [('Novo', self.new), ('Abrir', self.load), ('Guardar', self.save), ('Vídeo', self.format_video)]:
            ttk.Button(header, text=title, command=lambda fn=action: self.guard(fn)).pack(side='right', padx=3)
        body = ttk.Frame(self.root, padding=6)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(body)
        sidebar.grid(row=0, column=0, sticky='nsew', padx=4)
        scenes = self.panel(sidebar, 'CENAS')
        scenes.pack(fill='both', expand=True)
        self.scene_list = self.listbox(scenes, 5)
        self.scene_list.bind('<<ListboxSelect>>', lambda event: self.select_scene())
        self.button(scenes, '+ Cena', self.add_scene)
        self.button(scenes, 'Renomear / remover cena', self.edit_scene)
        sources = self.panel(sidebar, 'FONTES | baixo para topo')
        sources.pack(fill='both', expand=True, pady=6)
        self.source_list = self.listbox(sources, 5)
        self.source_list.bind('<<ListboxSelect>>', lambda event: self.select_source())
        menu_button = ttk.Menubutton(sources, text='+ Adicionar fonte')
        menu = tk.Menu(menu_button, tearoff=False)
        for label, kind in [('Cor', 'color'), ('Imagem', 'image'), ('Texto', 'text'), ('Vídeo', 'video'), ('RTSP', 'rtsp'),
            ('Câmera USB', 'camera'), ('Ecrã', 'desktop'), ('Janela', 'window'), ('Microfone / áudio DirectShow', 'microphone'),
            ('Ficheiro de áudio', 'audio'), ('Som do sistema (WASAPI)', 'system_audio'), ('Link web / CSS', 'browser')]:
            menu.add_command(label=label, command=lambda value=kind: self.guard(lambda: self.add_source(value)))
        menu_button.configure(menu=menu)
        menu_button.pack(fill='x', pady=3)
        actions_button = ttk.Menubutton(sources, text='Ações da fonte')
        actions_menu = tk.Menu(actions_button, tearoff=False)
        for label, fn in [('Editar fonte / CSS', self.edit_value), ('Posição / tamanho', self.edit_transform), ('Filtros A/V', self.edit_effects), ('Plugin de vídeo', self.load_plugin),
            ('Mostrar / ocultar', self.toggle_source), ('Subir camada', self.raise_source), ('Remover', self.remove_source)]:
            actions_menu.add_command(label=label, command=lambda action=fn: self.guard(action))
        actions_button.configure(menu=actions_menu)
        actions_button.pack(fill='x', pady=3)
        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew', padx=4)
        center.columnconfigure(0, weight=1)
        center.columnconfigure(1, weight=1)
        center.rowconfigure(0, weight=1)
        preview = self.panel(center, 'PRÉ-VISUALIZAÇÃO')
        preview.grid(row=0, column=0, sticky='nsew', padx=3)
        self.preview_view = tk.Label(preview, bg='#0b1018', width=1, height=1)
        self.preview_view.pack(fill='both', expand=True)
        program = self.panel(center, 'PROGRAMA')
        program.grid(row=0, column=1, sticky='nsew', padx=3)
        self.program_view = tk.Label(program, bg='#0b1018', width=1, height=1)
        self.program_view.pack(fill='both', expand=True)
        transition = ttk.Frame(center, padding=8)
        transition.grid(row=1, column=0, columnspan=2, sticky='ew')
        ttk.Button(transition, text='CORTE', command=lambda: self.studio.take(time.monotonic())).pack(side='left', padx=5)
        ttk.Button(transition, text='TRANSIÇÃO | 500 ms', command=lambda: self.studio.take(time.monotonic(), .5)).pack(side='left')
        right = ttk.Frame(body)
        right.grid(row=0, column=2, sticky='ns', padx=4)
        mixer = self.panel(right, 'MIXER')
        mixer.pack(fill='both', expand=True)
        self.meter_frame = ttk.Frame(mixer)
        self.meter_frame.pack(fill='x')
        ttk.Label(mixer, text='Volume da fonte selecionada').pack()
        ttk.Scale(mixer, from_=0, to=2, variable=self.gain, command=lambda value: self.change_gain()).pack(fill='x')
        ttk.Checkbutton(mixer, text='Mute', variable=self.muted, command=self.change_gain).pack(anchor='w')
        self.button(mixer, 'Áudio da fonte: ligar/desligar', self.toggle_audio)
        self.button(mixer, 'Listar câmeras / microfones', self.list_devices)
        self.button(mixer, 'Monitorizar áudio: ligar/desligar', self.toggle_monitor)
        controls = self.panel(right, 'SAÍDA')
        controls.pack(fill='x', pady=6)
        self.record_button = self.button(controls, 'Gravar MKV', self.record)
        self.live_button = self.button(controls, 'Transmitir RTMP', self.live)
        self.button(controls, 'Sobre / estado', lambda: messagebox.showinfo('Vision Track Studio',
            f'Vision Track Studio {__version__}\nBase independente em desenvolvimento.\nPython/Tk, Pillow, NumPy, OpenCV, Playwright, pyserial e FFmpeg externo.\nNão foi validada com câmeras físicas.\nConsulte docs/PARIDADE.md.'))
        self.build_tracking()
        ttk.Label(self.root, textvariable=self.status, padding=7).pack(fill='x')

    def listbox(self, parent, height):
        box = tk.Listbox(parent, height=height, width=25, bg='#0b1018', fg='#edf3fc', selectbackground='#3187ff', exportselection=False)
        box.pack(fill='both', expand=True)
        return box

    def build_tracking(self):
        bottom = self.panel(self.root, 'RASTREIO E CÂMERAS | experimental')
        bottom.pack(fill='x', padx=10, pady=4)
        preview = ttk.Frame(bottom)
        preview.pack(side='left', padx=5)
        self.camera_view = tk.Label(preview, bg='#0b1018', width=300, height=165)
        self.camera_view.pack()
        # Pixel sizing is established with an initial image rather than character units.
        self.camera_view.photo = ImageTk.PhotoImage(Image.new('RGB', (300, 165)))
        self.camera_view.configure(image=self.camera_view.photo, width=300, height=165)
        self.camera_view.bind('<Button-1>', self.select_person)
        ttk.Label(preview, textvariable=self.tracker_status, wraplength=300).pack()
        options = ttk.Frame(bottom)
        options.pack(side='left', padx=10)
        self.button(options, 'Detetar na fonte selecionada', self.enable_tracking)
        ttk.Combobox(options, textvariable=self.profile, values=['Cinema', 'Suave', 'Dinâmico'], state='readonly', width=18).pack(fill='x')
        ttk.Checkbutton(options, text='Recorte digital automático', variable=self.digital).pack(anchor='w')
        ttk.Scale(options, from_=1, to=4, variable=self.zoom).pack(fill='x')
        ttk.Checkbutton(options, text='Movimento PTZ automático', variable=self.follow).pack(anchor='w')
        ttk.Checkbutton(options, text='Troca de câmera experimental', variable=self.handoff).pack(anchor='w')
        manual = ttk.Frame(bottom)
        manual.pack(side='left', padx=10)
        grid = ttk.Frame(manual)
        grid.pack()
        for label, velocity, row, col in [('Cima', (0, .35, 0), 0, 1), ('Esq.', (-.35, 0, 0), 1, 0),
            ('STOP', (0, 0, 0), 1, 1), ('Dir.', (.35, 0, 0), 1, 2), ('Baixo', (0, -.35, 0), 2, 1),
            ('Zoom +', (0, 0, .3), 3, 0), ('Zoom -', (0, 0, -.3), 3, 2)]:
            button = ttk.Button(grid, text=label, width=7)
            button.grid(row=row, column=col, padx=2, pady=2)
            button.bind('<ButtonPress-1>', lambda event, value=velocity: self.manual_start(value))
            button.bind('<ButtonRelease-1>', lambda event: self.manual_stop())
            button.bind('<Leave>', lambda event: self.manual_stop())
        self.button(manual, 'Configurar / ligar PTZ', self.connect_ptz)
        self.button(manual, 'Joystick: ligar / desligar', self.toggle_joystick)
        presets = ttk.Frame(bottom)
        presets.pack(side='left', padx=10)
        self.preset_number = tk.IntVar(value=1)
        ttk.Label(presets, text='Preset').pack()
        ttk.Spinbox(presets, from_=1, to=16, textvariable=self.preset_number, width=6).pack()
        self.button(presets, 'Guardar preset', lambda: self.preset(True))
        self.button(presets, 'Chamar preset', lambda: self.preset(False))
        self.button(presets, 'PARAR / desligar PTZ', self.disconnect_ptz)

    def guard(self, fn):
        try:
            return fn()
        except Exception as error:
            messagebox.showerror('Vision Track Studio', str(error))

    def all_sources(self):
        return [source for scene in self.project.scenes for source in scene.sources]

    def refresh_lists(self):
        chosen = self.selected_source()
        self.scene_list.delete(0, 'end')
        for index, scene in enumerate(self.project.scenes):
            self.scene_list.insert('end', scene.name)
            if scene.id == self.studio.preview:
                self.scene_list.selection_set(index)
        self.source_list.delete(0, 'end')
        for index, source in enumerate(self.studio.scene(self.studio.preview).sources):
            self.source_list.insert('end', ('● ' if source.visible else '○ ') + source.name)
            if chosen and source.id == chosen.id:
                self.source_list.selection_set(index)
        for child in self.meter_frame.winfo_children():
            child.destroy()
        self.meters = {}
        for source in self.all_sources():
            if source.id in self.runtime.audio:
                ttk.Label(self.meter_frame, text=source.name).pack(anchor='w')
                meter = ttk.Progressbar(self.meter_frame, maximum=1, length=175)
                meter.pack(fill='x', pady=2)
                self.meters[source.id] = meter

    def select_scene(self):
        selected = self.scene_list.curselection()
        if selected:
            self.studio.preview = self.project.scenes[selected[0]].id
            self.source_list.selection_clear(0, 'end')
            self.refresh_lists()

    def select_source(self):
        source = self.selected_source()
        if source:
            self.gain.set(source.settings.get('gain', 1))
            self.muted.set(source.settings.get('mute', False))

    def change_gain(self):
        source = self.selected_source()
        if source:
            source.settings.update(gain=self.gain.get(), mute=self.muted.get())

    def selected_source(self):
        selection = self.source_list.curselection() if hasattr(self, 'source_list') else ()
        sources = self.studio.scene(self.studio.preview).sources
        return sources[selection[0]] if selection and selection[0] < len(sources) else None

    def add_scene(self):
        name = simpledialog.askstring('Cena', 'Nome da cena:')
        if name:
            scene = Scene(name)
            self.project.scenes.append(scene)
            self.studio.preview = scene.id
            self.refresh_lists()

    def edit_scene(self):
        scene = self.studio.scene(self.studio.preview)
        name = simpledialog.askstring('Cena', 'Novo nome (vazio para remover):', initialvalue=scene.name)
        if name is None:
            return
        if name:
            scene.name = name
        elif len(self.project.scenes) > 1 and scene.id != self.studio.program and not self.studio.transition:
            for source in scene.sources:
                self.runtime.detach(source.id)
            self.project.scenes.remove(scene)
            self.studio.preview = self.project.scenes[0].id
        else:
            raise ValueError('Não pode remover a última cena ou uma cena em programa/transição')
        self.refresh_lists()

    def add_source(self, kind):
        if kind in {'image', 'video', 'audio'}:
            value = filedialog.askopenfilename(title='Escolher ficheiro')
        elif kind == 'system_audio':
            if self.runtime.monitor:
                raise ValueError('Desligue a monitorização antes de capturar som do sistema para evitar retorno')
            value = 'default'
        elif kind == 'desktop':
            value = 'desktop'
        else:
            value = simpledialog.askstring('Nova fonte', {'color': 'Cor hexadecimal:', 'text': 'Texto:', 'rtsp': 'URL RTSP:',
                'camera': 'Nome exato da câmera DirectShow:', 'window': 'Título exato da janela:',
                'microphone': 'Nome exato do dispositivo áudio DirectShow:', 'browser': 'URL HTTP/HTTPS:'}[kind])
        if not value:
            return
        if kind == 'rtsp' and not value.startswith(('rtsp://', 'rtsps://')):
            raise ValueError('URL RTSP inválida')
        if kind == 'color':
            Image.new('RGB', (1, 1), value)
        name = Path(value).name if kind in {'image', 'video', 'audio'} else kind.title()
        source = Source(name, kind, value, width=self.project.width, height=self.project.height)
        self.runtime.attach(source, self.project.fps)
        self.studio.scene(self.studio.preview).sources.append(source)
        self.refresh_lists()

    def edit_value(self):
        source = self.selected_source()
        if not source:
            return
        if source.kind == 'browser':
            self.css_editor(source)
            return
        value = simpledialog.askstring('Fonte', 'Texto / endereço / ficheiro / dispositivo:', initialvalue=source.value)
        if value:
            if source.kind == 'color':
                Image.new('RGB', (1, 1), value)
            self.runtime.detach(source.id)
            source.value = value
            self.runtime.attach(source, self.project.fps)

    def css_editor(self, source):
        dialog = tk.Toplevel(self.root)
        dialog.title('CSS da fonte web')
        editor = tk.Text(dialog, width=80, height=22, bg='#0b1018', fg='white', insertbackground='white')
        editor.pack(fill='both', expand=True)
        editor.insert('1.0', source.settings.get('css', 'body { background: transparent !important; margin: 0; }'))
        def apply():
            source.settings['css'] = editor.get('1.0', 'end-1c')
            self.runtime.detach(source.id)
            self.runtime.attach(source, self.project.fps)
            dialog.destroy()
        self.button(dialog, 'Aplicar CSS', apply)

    def edit_transform(self):
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
            Source('Teste', x=x, y=y, width=width, height=height, opacity=opacity).validate()
            source.x, source.y, source.width, source.height, source.opacity = x, y, width, height, opacity

    def toggle_source(self):
        source = self.selected_source()
        if source:
            source.visible = not source.visible
            self.refresh_lists()

    def toggle_audio(self):
        source = self.selected_source()
        if not source:
            return
        if source.kind not in {'video', 'rtsp'}:
            raise ValueError('Use esta opção numa fonte Vídeo ou RTSP; microfone tem fonte própria')
        enabled = source.id not in self.runtime.audio
        self.runtime.detach(source.id)
        source.settings['audio'] = enabled
        self.runtime.attach(source, self.project.fps)
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
            self.runtime.detach(source.id)
            self.studio.scene(self.studio.preview).sources.remove(source)
            self.refresh_lists()

    def toggle_monitor(self):
        if not self.runtime.monitor and any(source.kind == 'system_audio' for source in self.all_sources()):
            raise ValueError('Remova a fonte Som do sistema antes de ligar monitorização para evitar retorno')
        self.runtime.toggle_monitor()

    def load_plugin(self):
        source = self.selected_source()
        if not source:
            return
        if source.id in self.studio.compositor.plugins:
            self.studio.compositor.plugins.pop(source.id)
            return
        path = filedialog.askopenfilename(filetypes=[('Plugin Python', '*.py')])
        if path and messagebox.askyesno('Executar plugin', 'Plugins executam código com acesso ao computador. Confia no ficheiro escolhido?'):
            from .plugins import VideoPlugin
            self.studio.compositor.plugins[source.id] = VideoPlugin(path)

    def edit_effects(self):
        source = self.selected_source()
        if not source:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('Filtros e ajuste de sincronização')
        defaults = {'brightness': 1, 'contrast': 1, 'chroma': '', 'chroma_threshold': 80, 'gate_db': -120, 'compressor_db': 0, 'compressor_ratio': 4, 'delay_ms': 0}
        labels = {'brightness': 'Brilho (0 a 3)', 'contrast': 'Contraste (0 a 3)', 'chroma': 'Cor chroma (#00ff00 ou vazio)', 'chroma_threshold': 'Tolerância chroma (0 a 255)', 'gate_db': 'Gate dB (-120 desliga)', 'compressor_db': 'Compressor dB (0 desliga)', 'compressor_ratio': 'Razão compressor (1 a 20)', 'delay_ms': 'Atraso áudio ms (0 a 2000)'}
        variables = {}
        for row, (key, default) in enumerate(defaults.items()):
            ttk.Label(dialog, text=labels[key], padding=5).grid(row=row, column=0)
            variables[key] = tk.StringVar(value=str(source.settings.get(key, default)))
            ttk.Entry(dialog, textvariable=variables[key]).grid(row=row, column=1)
        def apply():
            import math
            updates = {}
            for key, variable in variables.items():
                value = variable.get()
                if key == 'chroma':
                    if value:
                        from PIL import ImageColor
                        ImageColor.getrgb(value)
                    updates[key] = value
                else:
                    updates[key] = float(value)
                    if not math.isfinite(updates[key]):
                        raise ValueError('Valor numérico inválido')
            source.settings.update(updates)
            dialog.destroy()
        ttk.Button(dialog, text='Aplicar', command=lambda: self.guard(apply)).grid(row=len(defaults), columnspan=2, pady=8)

    def list_devices(self):
        found = devices()
        messagebox.showinfo('Dispositivos DirectShow', '\n'.join(f'{kind}: {name}' for name, kind in found) or 'Sem dispositivos')

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension='.vtrack.json', filetypes=[('Projeto Vision Track', '*.json')])
        if path:
            if any(source.kind in {'rtsp', 'browser'} for source in self.all_sources()):
                if not messagebox.askyesno('Projeto', 'Endereços com credenciais/chaves serão guardados em texto. Continuar?'):
                    return
            self.project.settings.update(geometry=self.root.geometry(), profile=self.profile.get(), zoom=self.zoom.get(), preview=self.studio.preview, program=self.studio.program)
            self.project.save(path)

    def replace_project(self, project):
        if self.runtime.outputs:
            raise RuntimeError('Pare as saídas antes de trocar de projeto')
        replacement = Runtime()
        try:
            for scene in project.scenes:
                for source in scene.sources:
                    replacement.attach(source, project.fps)
        except Exception:
            replacement.close()
            raise
        self.disconnect_ptz()
        self.runtime.close()
        self.runtime = replacement
        self.project, self.studio = project, Studio(project)
        settings = project.settings
        if 'geometry' in settings:
            self.root.geometry(settings['geometry'])
        if settings.get('profile') in {'Cinema', 'Suave', 'Dinâmico'}:
            self.profile.set(settings['profile'])
        self.zoom.set(max(1, min(4, float(settings.get('zoom', 2)))))
        ids = {scene.id for scene in project.scenes}
        for key in ('preview', 'program'):
            if settings.get(key) in ids:
                setattr(self.studio, key, settings[key])
        self.refresh_lists()

    def new(self):
        if messagebox.askyesno('Novo projeto', 'Criar novo projeto? Guarde primeiro as alterações que pretende manter.'):
            self.replace_project(Project())

    def load(self):
        path = filedialog.askopenfilename(filetypes=[('Projeto Vision Track', '*.json')])
        if path:
            self.replace_project(Project.load(path))

    def format_video(self):
        if self.runtime.outputs:
            raise ValueError('Pare a gravação/transmissão antes de mudar o formato')
        answer = simpledialog.askstring('Formato de vídeo', 'largura, altura, fps', initialvalue=f'{self.project.width}, {self.project.height}, {self.project.fps}')
        if answer:
            width, height, fps = map(int, answer.split(','))
            probe = Project(width, height, fps)
            probe.validate()
            self.project.width, self.project.height, self.project.fps = width, height, fps

    def stop_output(self, name):
        try:
            self.runtime.remove_output(name)
        finally:
            self.record_button.configure(text='Parar gravação' if 'record' in self.runtime.outputs else 'Gravar MKV')
            self.live_button.configure(text='Parar transmissão' if 'live' in self.runtime.outputs else 'Transmitir RTMP')

    def record(self):
        if 'record' in self.runtime.outputs:
            return self.stop_output('record')
        path = filedialog.asksaveasfilename(defaultextension='.mkv', filetypes=[('Vídeo Matroska', '*.mkv')])
        if path:
            output = AVOutput(path, (self.project.width, self.project.height), self.project.fps)
            self.runtime.add_output('record', output)
            self.record_button.configure(text='Parar gravação')

    def live(self):
        if 'live' in self.runtime.outputs:
            return self.stop_output('live')
        url = simpledialog.askstring('Transmissão', 'URL RTMP completa (incluindo chave):', show='*')
        if url:
            self.runtime.add_output('live', AVOutput(url, (self.project.width, self.project.height), self.project.fps, live=True))
            self.live_button.configure(text='Parar transmissão')

    def enable_tracking(self):
        source = self.selected_source()
        if source:
            self.follow.set(False)
            self.runtime.enable_vision(source.id)

    def select_person(self, event):
        worker = self.runtime.vision.get(self.runtime.selected_camera)
        if worker and hasattr(self, 'camera_bounds'):
            x, y, width, height = self.camera_bounds
            self.guard(lambda: worker.select_at((event.x - x) / width, (event.y - y) / height))

    def manual_start(self, velocity):
        self.follow.set(False)
        self.joystick = None
        self.manual = velocity
        if self.ptz:
            self.ptz.move(*velocity)

    def manual_stop(self):
        self.manual = None
        if self.ptz:
            self.ptz.move(0, 0, 0)

    def focus_out(self, event):
        # Delay lets focus move between widgets in the same app without disabling control.
        def check():
            if not self.closed and self.root.focus_displayof() is None:
                self.follow.set(False)
                self.joystick = None
                self.manual_stop()
        self.root.after(50, check)

    def connect_ptz(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Ligação PTZ')
        fields = {}
        defaults = {'protocol': 'VISCA IP', 'host': '', 'port': '52381', 'address': '1', 'serial': 'COM3', 'baud': '9600', 'username': '', 'password': ''}
        labels = {'protocol': 'Protocolo', 'host': 'IP / host', 'port': 'Porta (ONVIF: 80)', 'address': 'Endereço', 'serial': 'Porta série', 'baud': 'Baud', 'username': 'Utilizador ONVIF', 'password': 'Palavra-passe ONVIF'}
        for row, (key, value) in enumerate(defaults.items()):
            ttk.Label(dialog, text=labels[key], padding=5).grid(row=row, column=0)
            variable = tk.StringVar(value=value)
            fields[key] = variable
            if key == 'protocol':
                ttk.Combobox(dialog, textvariable=variable, values=['VISCA IP', 'VISCA Serial', 'Pelco-D TCP', 'Pelco-D Serial', 'ONVIF'], state='readonly').grid(row=row, column=1)
            else:
                ttk.Entry(dialog, textvariable=variable, show='*' if key == 'password' else '').grid(row=row, column=1)
        def connect():
            self.disconnect_ptz()
            self.ptz = PTZSession({key: value.get() for key, value in fields.items()})
            dialog.destroy()
        ttk.Button(dialog, text='Ligar', command=lambda: self.guard(connect)).grid(row=len(defaults), columnspan=2, pady=8)

    def disconnect_ptz(self):
        self.follow.set(False)
        self.manual = self.joystick = None
        if self.ptz:
            self.ptz.close()
            self.ptz = None

    def toggle_joystick(self):
        self.follow.set(False)
        self.manual_stop()
        self.joystick = None if self.joystick else Joystick()

    def preset(self, save):
        if not self.ptz:
            raise ValueError('Ligue primeiro uma câmera PTZ')
        self.follow.set(False)
        self.joystick = None
        self.manual_stop()
        self.ptz.preset(self.preset_number.get(), save)

    def update_tracking(self, now):
        key = self.runtime.selected_camera
        worker = self.runtime.vision.get(key)
        target = None
        if worker:
            detections, target, state, _, stamp = worker.snapshot()
            self.tracker_status.set(worker.error or f'{state} | clique numa caixa para selecionar')
            decoder = self.runtime.video.get(key)
            frame = decoder.frame() if decoder else None
            if frame:
                annotated = frame.copy()
                drawing = ImageDraw.Draw(annotated)
                for detection in detections:
                    x, y, width, height = detection.box
                    rectangle = (x * frame.width, y * frame.height, (x + width) * frame.width, (y + height) * frame.height)
                    drawing.rectangle(rectangle, outline='#31ff98' if detection == target else '#3187ff', width=3)
                self.camera_bounds = self.display(self.camera_view, annotated, fixed=(300, 165))
        if self.ptz:
            if self.ptz.error:
                self.status.set(self.ptz.error)
                self.follow.set(False)
                return
            if self.joystick:
                try:
                    self.ptz.move(*self.joystick.poll())
                except Exception as error:
                    self.joystick = None
                    self.ptz.move(0, 0, 0)
                    self.status.set(str(error))
            elif self.manual is not None:
                self.ptz.move(*self.manual)
            elif self.follow.get():
                if target and now - stamp < .3:
                    x, y, width, height = target.box
                    gain = {'Cinema': .4, 'Suave': .65, 'Dinâmico': 1.}[self.profile.get()]
                    pan, tilt = x + width / 2 - .5, .5 - y - height / 2
                    pan = 0 if abs(pan) < .06 else max(-.5, min(.5, pan * gain))
                    tilt = 0 if abs(tilt) < .07 else max(-.35, min(.35, tilt * gain))
                    self.ptz.move(pan, tilt, 0)
                else:
                    self.ptz.move(0, 0, 0)
            else:
                self.ptz.move(0, 0, 0)

    def display(self, widget, frame, fixed=None):
        size = fixed or (max(16, widget.winfo_width()), max(16, widget.winfo_height()))
        image = frame.copy()
        image.thumbnail(size)
        canvas = Image.new('RGB', size, '#0b1018')
        x, y = (size[0] - image.width) // 2, (size[1] - image.height) // 2
        canvas.paste(image, (x, y))
        widget.photo = ImageTk.PhotoImage(canvas)
        widget.configure(image=widget.photo)
        return x, y, image.width, image.height

    def tick(self):
        if self.closed:
            return
        start = time.monotonic()
        dt = start - self.last_tick
        self.last_tick = start
        frames = self.runtime.frames(start, self.digital.get(), self.profile.get(), self.zoom.get(), dt, self.handoff.get())
        if self.runtime.selected_camera != self.last_camera:
            if self.last_camera is not None:
                self.disconnect_ptz()
            self.last_camera = self.runtime.selected_camera
        self.runtime.update_audio(self.studio, start)
        preview = self.studio.compositor.render(self.studio.scene(self.studio.preview), frames)
        program = self.studio.frame(start, frames)
        self.display(self.preview_view, preview)
        self.display(self.program_view, program)
        for key, meter in self.meters.items():
            channel = self.runtime.mixer.channels.get(key)
            if channel:
                meter.configure(value=channel.peak)
        errors = list(self.studio.compositor.errors.values())
        errors += [plugin.error for plugin in self.studio.compositor.plugins.values() if plugin.error]
        errors += [decoder.error for decoder in list(self.runtime.video.values()) + list(self.runtime.audio.values()) if decoder.error]
        failures = []
        for name, output in list(self.runtime.outputs.items()):
            output.submit(program)
            if output.error or output.process.poll() is not None:
                failures.append(name)
        self.status.set((errors + [self.runtime.audio_error] if self.runtime.audio_error else errors +
            [f'Base independente | {self.project.width}x{self.project.height}/{self.project.fps} | A/V | saturações: {self.runtime.mixer.clipped}'])[0])
        self.update_tracking(start)
        for name in failures:
            self.guard(lambda key=name: self.stop_output(key))
        self.root.after(max(1, round((1 / self.project.fps - (time.monotonic() - start)) * 1000)), self.tick)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.disconnect_ptz()
        errors = self.runtime.close()
        if errors:
            messagebox.showerror('Finalização', '\n'.join(errors))
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
