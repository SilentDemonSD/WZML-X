import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import subprocess
import threading
import shutil
import queue
import re
import time
import tempfile

# Color scheme
COLORS = {
    'bg': '#0a0e27',
    'panel': '#1a1f3a',
    'accent': '#e94560',
    'accent2': '#0f4c75',
    'text': '#e8e8e8',
    'success': '#4caf50',
    'warning': '#ff9800',
    'hover': '#2d3561'
}

class OrsozoxCompressor:
    def __init__(self, root):
        self.root = root
        self.root.title("✠ Orsozox Movies Compressor v9.0 GPU ✠")
        self.root.geometry("1200x800")
        self.root.configure(bg=COLORS['bg'])
        
        # Make responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Communication
        self.msg_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.process = None
        
        # Variables
        self.video_path = tk.StringVar()
        self.sub_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.mode = tk.StringVar(value="auto")
        self.quality = tk.StringVar(value="Original (Same as Source)")
        self.codec = tk.StringVar(value="H.264")
        self.burn_subs = tk.BooleanVar(value=True)
        self.add_intro = tk.BooleanVar(value=False)
        self.enable_gpu = tk.BooleanVar(value=False)  # خيار تفعيل GPU (الافتراضي: CPU)
        
        # Manual mode
        self.crf = tk.StringVar(value="25")
        self.preset = tk.StringVar(value="medium")
        self.minrate = tk.StringVar(value="1500k")
        self.maxrate = tk.StringVar(value="3000k")
        self.bufsize = tk.StringVar(value="4000k")
        self.scale = tk.StringVar(value="scale=-2:1080")
        self.audio_bitrate = tk.StringVar(value="192k")
        
        # Metadata
        self.meta_title = tk.StringVar(value="Powered By:- @inoshyi")
        self.meta_author = tk.StringVar(value="@OrSoZoXch")
        
        # Intro text
        self.intro_text = tk.StringVar(value="""تمت الترجمة بواسطة قناة ارثوذكس للافلام & المهندس ابراهيم نصحي
https://t.me/orsozox_media
✠ Orsozox Movies | أفلام أرثوذكس ✠
WwW.OrSoZoX.CoM""")
        
        # GPU Detection
        self.gpu_available = False
        self.gpu_h264 = False
        self.gpu_h265 = False
        
        # Advanced Tools
        self.extract_video_path = tk.StringVar()
        self.extract_tracks = []  # List of available tracks
        self.track_checkboxes = []  # Checkboxes for track selection
        
        self.merge_video_path = tk.StringVar()
        self.merge_audio_path = tk.StringVar()
        self.merge_mode = tk.StringVar(value="replace")
        
        self.check_gpu()
        self.create_gui()
        self.refresh_files()
        self.check_messages()
    
    def check_gpu(self):
        """Check for NVIDIA GPU encoding support"""
        try:
            # أولوية للنسخ: Kepler ثم العادية ثم النظام
            ffmpeg_paths = []
            if os.path.exists("ffmpeg_kepler.exe"):
                ffmpeg_paths.append(os.path.abspath("ffmpeg_kepler.exe"))
            if os.path.exists("ffmpeg.exe"):
                ffmpeg_paths.append(os.path.abspath("ffmpeg.exe"))
            system_ffmpeg = shutil.which("ffmpeg")
            if system_ffmpeg:
                ffmpeg_paths.append(system_ffmpeg)
            
            for ffmpeg in ffmpeg_paths:
                if not ffmpeg:
                    continue
                    
                result = subprocess.run([ffmpeg, '-encoders'], 
                                      capture_output=True, text=True, errors='ignore', timeout=10)
                output = result.stdout + result.stderr
                
                if 'h264_nvenc' in output:
                    self.gpu_h264 = True
                    self.gpu_available = True
                    
                    # تحديد نوع FFmpeg المستخدم
                    if "ffmpeg_kepler.exe" in ffmpeg:
                        self.root.title(f"✠ Orsozox Compressor v9.0 GPU ✠ [GTX 660 ✓ H.264]")
                    else:
                        self.root.title(f"✠ Orsozox Compressor v9.0 GPU ✠ [NVIDIA GPU H.264✓]")
                    return
                    
                if 'hevc_nvenc' in output:
                    self.gpu_h265 = True
            
            # إذا وصل هنا يبقى مفيش دعم GPU
            if os.path.exists("ffmpeg_kepler.exe"):
                self.root.title(f"✠ Orsozox Compressor v9.0 ✠ [GTX 660 - GPU غير مدعوم]")
            else:
                self.root.title(f"✠ Orsozox Compressor v9.0 ✠ [GPU غير متاح]")
                
        except Exception as e:
            pass
    
    def create_gui(self):
        # Main container with grid
        main = tk.Frame(self.root, bg=COLORS['bg'])
        main.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        
        # Left panel - File list
        left = self.create_panel(main, "📂 Files in Current Folder")
        left.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(left, bg=COLORS['panel'], fg=COLORS['text'],
                                       selectbackground=COLORS['accent'], 
                                       selectforeground='white',
                                       font=('Consolas', 9), bd=0, highlightthickness=0)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_click)
        
        self.create_button(left, "🔄 Refresh", self.refresh_files, COLORS['accent2']).pack(pady=5, padx=5, fill=tk.X)
        
        # Right panel
        right = tk.Frame(main, bg=COLORS['bg'])
        right.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        right.grid_rowconfigure(2, weight=1)  # Changed from 1 to 2 - give weight to tabs, not input files
        right.grid_columnconfigure(0, weight=1)
        
        # Header
        header = tk.Label(right, text="✠ Orsozox Movies Compressor ✠",
                         font=('Arial', 18, 'bold'), fg=COLORS['accent'], bg=COLORS['bg'])
        header.grid(row=0, column=0, pady=10)
        
        # File inputs
        files = self.create_panel(right, "Input Files")
        files.grid(row=1, column=0, sticky='ew', pady=5)
        
        self.create_file_row(files, "🎬 Video:", self.video_path, self.browse_video, 0)
        self.create_file_row(files, "📝 Subtitle:", self.sub_path, self.browse_sub, 1)
        self.create_file_row(files, "📂 Output:", self.output_dir, self.browse_output, 2)
        
        # Tabs
        tabs = ttk.Notebook(right)
        tabs.grid(row=2, column=0, sticky='nsew', pady=5)
        
        # Compression tab
        comp = self.create_tab(tabs, "⚙ Compression")
        tabs.add(comp, text="⚙ Compression")
        
        # Mode selection
        mode_frame = tk.Frame(comp, bg=COLORS['panel'])
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(mode_frame, text="Mode:", fg=COLORS['text'], bg=COLORS['panel'],
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="Auto", variable=self.mode, value="auto",
                      command=self.toggle_mode, bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(mode_frame, text="Manual", variable=self.mode, value="manual",
                      command=self.toggle_mode, bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel']).pack(side=tk.LEFT, padx=10)
        
        # Codec selection
        tk.Label(mode_frame, text="Codec:", fg=COLORS['text'], bg=COLORS['panel'],
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(20, 5))
        
        tk.Radiobutton(mode_frame, text="H.264", variable=self.codec, value="H.264",
                      bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="H.265", variable=self.codec, value="H.265",
                      bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel']).pack(side=tk.LEFT, padx=5)
        
        # GPU/CPU selection
        tk.Label(mode_frame, text="|", fg=COLORS['accent'], bg=COLORS['panel'],
                font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(mode_frame, text="🚀 Enable GPU (تفعيل GPU)", variable=self.enable_gpu,
                      bg=COLORS['panel'], fg=COLORS['success'], selectcolor=COLORS['accent2'],
                      activebackground=COLORS['panel'], font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Auto frame
        self.auto_frame = tk.Frame(comp, bg=COLORS['panel'])
        self.auto_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.auto_frame, text="Quality Preset:", fg=COLORS['text'],
                bg=COLORS['panel']).pack(side=tk.LEFT, padx=5)
        
        qualities = ["Original (Same as Source)", "1080p Standard", "1080p High", "720p Standard", "720p Small",
                    "480p Standard", "480p Small"]
        ttk.Combobox(self.auto_frame, textvariable=self.quality, values=qualities,
                    state="readonly", width=25).pack(side=tk.LEFT, padx=5)
        
        # Manual frame
        self.manual_frame = tk.Frame(comp, bg=COLORS['panel'])
        
        manual_grid = tk.Frame(self.manual_frame, bg=COLORS['panel'])
        manual_grid.pack(padx=10, pady=5)
        
        settings = [
            ("CRF:", self.crf, [str(i) for i in range(18, 29)]),
            ("Preset:", self.preset, ["veryslow", "slower", "slow", "medium", "fast", "faster", "veryfast"]),
            ("Min Rate:", self.minrate, ["500k", "1000k", "1500k", "2000k", "3000k"]),
            ("Max Rate:", self.maxrate, ["1000k", "2000k", "3000k", "4000k", "6000k"]),
            ("Bufsize:", self.bufsize, ["2000k", "4000k", "6000k", "8000k"]),
            ("Scale:", self.scale, ["Original", "scale=-2:1080", "scale=-2:720", "scale=-2:480"])
        ]
        
        for i, (label, var, values) in enumerate(settings):
            row, col = divmod(i, 2)
            tk.Label(manual_grid, text=label, fg=COLORS['text'], bg=COLORS['panel']).grid(
                row=row, column=col*2, sticky=tk.W, padx=5, pady=3)
            ttk.Combobox(manual_grid, textvariable=var, values=values, width=15).grid(
                row=row, column=col*2+1, padx=5, pady=3)
        
        # Audio/Metadata tab
        meta = self.create_tab(tabs, "🎵 Audio & Metadata")
        tabs.add(meta, text="🎵 Audio & Metadata")
        
        tk.Checkbutton(meta, text="Burn Subtitles", variable=self.burn_subs,
                      bg=COLORS['panel'], fg=COLORS['text'], selectcolor=COLORS['accent2'],
                      activebackground=COLORS['panel']).pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Label(meta, text="Audio Bitrate:", fg=COLORS['text'], bg=COLORS['panel']).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Combobox(meta, textvariable=self.audio_bitrate,
                    values=["64k", "96k", "128k", "192k", "256k", "320k"],
                    width=15).pack(anchor=tk.W, padx=10)
        
        tk.Label(meta, text="Title:", fg=COLORS['text'], bg=COLORS['panel']).pack(anchor=tk.W, padx=10, pady=(10, 0))
        tk.Entry(meta, textvariable=self.meta_title, width=50, bg=COLORS['bg'],
                fg=COLORS['text'], insertbackground=COLORS['text']).pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Label(meta, text="Author:", fg=COLORS['text'], bg=COLORS['panel']).pack(anchor=tk.W, padx=10, pady=(10, 0))
        tk.Entry(meta, textvariable=self.meta_author, width=50, bg=COLORS['bg'],
                fg=COLORS['text'], insertbackground=COLORS['text']).pack(anchor=tk.W, padx=10, pady=2)
        
        # Subtitle Intro tab
        intro = self.create_tab(tabs, "📢 Subtitle Intro")
        tabs.add(intro, text="📢 Subtitle Intro")
        
        tk.Checkbutton(intro, text="Add Subtitle Intro (at video start)", variable=self.add_intro,
                      bg=COLORS['panel'], fg=COLORS['text'], selectcolor=COLORS['accent2'],
                      activebackground=COLORS['panel'], font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=10)
        
        tk.Label(intro, text="Intro Text (will be shown for ~15 seconds at start):",
                fg=COLORS['text'], bg=COLORS['panel']).pack(anchor=tk.W, padx=10, pady=5)
        
        self.intro_textbox = scrolledtext.ScrolledText(intro, height=8, width=70,
                                                       bg=COLORS['bg'], fg=COLORS['text'],
                                                       insertbackground=COLORS['text'],
                                                       font=('Arial', 10))
        self.intro_textbox.pack(padx=10, pady=5)
        self.intro_textbox.insert('1.0', self.intro_text.get())
        
        # Advanced Tools tab
        advanced = self.create_tab(tabs, "🔧 Advanced Tools")
        tabs.add(advanced, text="🔧 Advanced Tools")
        self.create_advanced_tab(advanced)
        
        # Progress section
        prog = self.create_panel(right, "Progress")
        prog.grid(row=3, column=0, sticky='ew', pady=5)
        
        self.progress_bar = ttk.Progressbar(prog, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(prog, height=6, bg='#000', fg='#0f0',
                                                  font=('Consolas', 9), state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Control buttons
        btn_frame = tk.Frame(right, bg=COLORS['bg'])
        btn_frame.grid(row=4, column=0, sticky='ew', pady=10)
        
        self.start_btn = self.create_button(btn_frame, "🚀 START ENCODING", 
                                           self.start_compression, COLORS['success'])
        self.start_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.cancel_btn = self.create_button(btn_frame, "⛔ CANCEL",
                                            self.cancel_compression, COLORS['warning'])
        self.cancel_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.cancel_btn.config(state='disabled')

        self.exit_btn = self.create_button(btn_frame, "🚪 EXIT",
                                            self.exit_app, '#d32f2f')
        self.exit_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    def create_panel(self, parent, title):
        frame = tk.LabelFrame(parent, text=title, bg=COLORS['panel'], fg=COLORS['accent'],
                             font=('Arial', 11, 'bold'), bd=2, relief=tk.GROOVE)
        return frame
    
    def create_tab(self, parent, title):
        frame = tk.Frame(parent, bg=COLORS['panel'])
        return frame
    
    def create_button(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command, bg=color, fg='white',
                       font=('Arial', 11, 'bold'), relief=tk.FLAT, bd=0,
                       activebackground=color, cursor='hand2', padx=20, pady=10)
        btn.bind('<Enter>', lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        return btn
    
    def lighten_color(self, hex_color):
        # Simple color lightening
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def create_file_row(self, parent, label, var, cmd, row):
        tk.Label(parent, text=label, fg=COLORS['text'], bg=COLORS['panel'],
                font=('Arial', 10)).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(parent, textvariable=var, width=45, bg=COLORS['bg'], fg=COLORS['text'],
                insertbackground=COLORS['text']).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        tk.Button(parent, text="Browse", command=cmd, bg=COLORS['accent2'], fg='white',
                 relief=tk.FLAT).grid(row=row, column=2, padx=5, pady=5)
        parent.grid_columnconfigure(1, weight=1)
    
    def toggle_mode(self):
        if self.mode.get() == "auto":
            self.manual_frame.pack_forget()
            self.auto_frame.pack(fill=tk.X, padx=10, pady=5)
        else:
            self.auto_frame.pack_forget()
            self.manual_frame.pack(fill=tk.X, padx=10, pady=5)
    
    def create_advanced_tab(self, parent):
        """Create Advanced Tools tab with Extract and Merge features"""
        # Create canvas with scrollbar for scrolling
        canvas = tk.Canvas(parent, bg=COLORS['panel'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        
        # Main container inside canvas
        main_container = tk.Frame(canvas, bg=COLORS['panel'])
        
        # Configure canvas
        main_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=main_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # ===== Extract Tracks Section =====
        extract_frame = tk.LabelFrame(main_container, text="📹 Extract Tracks", 
                                     bg=COLORS['panel'], fg=COLORS['accent'],
                                     font=('Arial', 11, 'bold'), padx=10, pady=10)
        extract_frame.pack(fill=tk.X, padx=10, pady=10)  # Changed from grid to pack
        
        # Video selection row
        video_row = tk.Frame(extract_frame, bg=COLORS['panel'])
        video_row.pack(fill=tk.X, pady=5)
        
        tk.Label(video_row, text="Video:", fg=COLORS['text'], 
                bg=COLORS['panel'], font=('Arial', 9)).pack(side=tk.LEFT, padx=3)
        tk.Entry(video_row, textvariable=self.extract_video_path, width=30,
                bg=COLORS['bg'], fg=COLORS['text'], insertbackground=COLORS['text'],
                font=('Arial', 9)).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        tk.Button(video_row, text="Browse", command=self.browse_extract_video,
                 bg=COLORS['accent2'], fg='white', relief=tk.FLAT,
                 font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(video_row, text="⬅ Selected", command=self.use_selected_for_extract,
                 bg=COLORS['success'], fg='white', relief=tk.FLAT, 
                 font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        
        # Buttons row
        btn_row = tk.Frame(extract_frame, bg=COLORS['panel'])
        btn_row.pack(fill=tk.X, pady=5)
        
        self.create_button(btn_row, "🔍 Analyze", self.analyze_video, 
                          COLORS['accent2']).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.extract_btn = self.create_button(btn_row, "📦 Extract", 
                                             self.extract_selected_tracks, COLORS['success'])
        self.extract_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.extract_btn.config(state='disabled')
        
        # Tracks list frame with scrollbar
        tracks_container = tk.Frame(extract_frame, bg=COLORS['panel'])
        tracks_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tracks_scroll = ttk.Scrollbar(tracks_container)
        tracks_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tracks_canvas = tk.Canvas(tracks_container, bg=COLORS['panel'], 
                                      height=120, highlightthickness=0,
                                      yscrollcommand=tracks_scroll.set)
        self.tracks_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tracks_scroll.config(command=self.tracks_canvas.yview)
        
        self.tracks_frame = tk.Frame(self.tracks_canvas, bg=COLORS['panel'])
        self.tracks_canvas.create_window((0, 0), window=self.tracks_frame, anchor='nw')
        
        self.tracks_frame.bind('<Configure>', 
                              lambda e: self.tracks_canvas.configure(scrollregion=self.tracks_canvas.bbox('all')))
        
        # ===== Add Audio Section =====
        merge_frame = tk.LabelFrame(main_container, text="🎵 Add Audio Track",
                                   bg=COLORS['panel'], fg=COLORS['accent'],
                                   font=('Arial', 11, 'bold'), padx=10, pady=10)
        merge_frame.pack(fill=tk.X, padx=10, pady=10)  # Changed from grid to pack
        
        # Video selection row
        video_row2 = tk.Frame(merge_frame, bg=COLORS['panel'])
        video_row2.pack(fill=tk.X, pady=3)
        
        tk.Label(video_row2, text="Video:", fg=COLORS['text'],
                bg=COLORS['panel'], font=('Arial', 9)).pack(side=tk.LEFT, padx=3)
        tk.Entry(video_row2, textvariable=self.merge_video_path, width=30,
                bg=COLORS['bg'], fg=COLORS['text'], insertbackground=COLORS['text'],
                font=('Arial', 9)).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        tk.Button(video_row2, text="Browse", command=self.browse_merge_video,
                 bg=COLORS['accent2'], fg='white', relief=tk.FLAT,
                 font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(video_row2, text="⬅ Selected", command=self.use_selected_for_merge,
                 bg=COLORS['success'], fg='white', relief=tk.FLAT,
                 font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        
        # Audio selection row
        audio_row = tk.Frame(merge_frame, bg=COLORS['panel'])
        audio_row.pack(fill=tk.X, pady=3)
        
        tk.Label(audio_row, text="Audio:", fg=COLORS['text'],
                bg=COLORS['panel'], font=('Arial', 9)).pack(side=tk.LEFT, padx=3)
        tk.Entry(audio_row, textvariable=self.merge_audio_path, width=30,
                bg=COLORS['bg'], fg=COLORS['text'], insertbackground=COLORS['text'],
                font=('Arial', 9)).pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        tk.Button(audio_row, text="Browse", command=self.browse_merge_audio,
                 bg=COLORS['accent2'], fg='white', relief=tk.FLAT,
                 font=('Arial', 8)).pack(side=tk.LEFT, padx=2)
        
        # Mode selection - compact
        mode_frame = tk.Frame(merge_frame, bg=COLORS['panel'])
        mode_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mode_frame, text="Mode:", fg=COLORS['text'],
                bg=COLORS['panel'], font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="Replace", variable=self.merge_mode,
                      value="replace", bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel'],
                      font=('Arial', 8)).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="Add Track", variable=self.merge_mode, 
                      value="add", bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel'],
                      font=('Arial', 8)).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="Mix", variable=self.merge_mode,
                      value="mix", bg=COLORS['panel'], fg=COLORS['text'],
                      selectcolor=COLORS['accent2'], activebackground=COLORS['panel'],
                      font=('Arial', 8)).pack(side=tk.LEFT, padx=5)
        
        # Merge button
        self.create_button(merge_frame, "🔀 Merge Audio", self.merge_audio_track,
                          COLORS['success']).pack(fill=tk.X, pady=5)
    
    def refresh_files(self):
        self.file_listbox.delete(0, tk.END)
        try:
            exts = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.webm', '.srt', '.ass', '.vtt'}
            files = [f for f in Path('.').iterdir() if f.suffix.lower() in exts and not f.name.startswith('[Orsozox]')]
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                self.file_listbox.insert(tk.END, f.name)
        except Exception as e:
            self.add_log(f"Error: {e}")
    
    def on_file_click(self, event):
        if not self.file_listbox.curselection():
            return
        filename = self.file_listbox.get(self.file_listbox.curselection()[0])
        path = Path('.') / filename
        ext = path.suffix.lower()
        
        if ext in ['.srt', '.ass', '.vtt']:
            self.sub_path.set(str(path.absolute()))
            self.add_log(f"Selected subtitle: {filename}")
        else:
            self.video_path.set(str(path.absolute()))
            self.add_log(f"Selected video: {filename}")
            for sub_ext in ['.srt', '.ass', '.vtt']:
                sub = path.with_suffix(sub_ext)
                if sub.exists():
                    self.sub_path.set(str(sub.absolute()))
                    self.add_log(f"Auto-detected: {sub.name}")
                    break
    
    def browse_video(self):
        path = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if path:
            self.video_path.set(path)
    
    def browse_sub(self):
        path = filedialog.askopenfilename(filetypes=[("Subtitles", "*.srt *.ass *.vtt")])
        if path:
            self.sub_path.set(path)
    
    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)
    
    # ===== Advanced Tools Functions =====
    def browse_extract_video(self):
        path = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if path:
            self.extract_video_path.set(path)
    
    def browse_merge_video(self):
        path = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if path:
            self.merge_video_path.set(path)
    
    def browse_merge_audio(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.aac *.ac3 *.m4a *.wav *.flac")])
        if path:
            self.merge_audio_path.set(path)
    
    def use_selected_for_extract(self):
        """Use the selected video from the file list for extraction"""
        video_path = self.video_path.get()
        if video_path and os.path.exists(video_path):
            self.extract_video_path.set(video_path)
            self.add_log(f"📹 Using selected video for extraction: {Path(video_path).name}")
        else:
            messagebox.showwarning("تحذير", "الرجاء اختيار ملف فيديو من القائمة أولاً")
    
    def use_selected_for_merge(self):
        """Use the selected video from the file list for merging"""
        video_path = self.video_path.get()
        if video_path and os.path.exists(video_path):
            self.merge_video_path.set(video_path)
            self.add_log(f"📹 Using selected video for merging: {Path(video_path).name}")
        else:
            messagebox.showwarning("تحذير", "الرجاء اختيار ملف فيديو من القائمة أولاً")
    
    def analyze_video(self):
        """Analyze video and display available tracks"""
        video_path = self.extract_video_path.get()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("خطأ", "الرجاء اختيار ملف فيديو صحيح")
            return
        
        # Clear previous tracks
        for widget in self.tracks_frame.winfo_children():
            widget.destroy()
        self.track_checkboxes.clear()
        self.extract_tracks.clear()
        
        try:
            # Use ffprobe to get stream information
            import json
            
            # البحث عن ffprobe بطريقة أفضل
            ffprobe_path = None
            
            # محاولة 1: في نفس مجلد ffmpeg_kepler.exe
            if os.path.exists("ffmpeg_kepler.exe"):
                test_path = os.path.abspath("ffprobe_kepler.exe")
                if os.path.exists(test_path):
                    ffprobe_path = test_path
            
            # محاولة 2: في نفس مجلد ffmpeg.exe
            if not ffprobe_path and os.path.exists("ffmpeg.exe"):
                test_path = os.path.abspath("ffprobe.exe")
                if os.path.exists(test_path):
                    ffprobe_path = test_path
            
            # محاولة 3: في النظام
            if not ffprobe_path:
                ffprobe_path = shutil.which("ffprobe")
            
            if not ffprobe_path:
                messagebox.showerror("خطأ", 
                    "ffprobe غير موجود!\n"
                    "ضع ffprobe.exe في نفس مجلد ffmpeg.exe\n"
                    "أو ثبته في النظام")
                return
            
            cmd = [ffprobe_path, '-v', 'quiet', '-print_format', 'json', 
                   '-show_streams', video_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            
            if 'streams' not in data:
                messagebox.showwarning("تحذير", "لم يتم العثور على مسارات في الفيديو")
                return
            
            # Process streams
            audio_count = 0
            subtitle_count = 0
            
            for stream in data['streams']:
                stream_type = stream.get('codec_type', '')
                index = stream.get('index', 0)
                
                if stream_type == 'audio':
                    audio_count += 1
                    codec = stream.get('codec_name', 'unknown')
                    lang = stream.get('tags', {}).get('language', 'und')
                    bitrate = stream.get('bit_rate', '0')
                    bitrate_kb = f"{int(bitrate)//1000}k" if bitrate.isdigit() else 'N/A'
                    
                    track_info = {
                        'type': 'audio',
                        'index': index,
                        'codec': codec,
                        'language': lang,
                        'bitrate': bitrate_kb,
                        'stream_index': f"0:a:{audio_count-1}"
                    }
                    self.extract_tracks.append(track_info)
                    
                    # Create checkbox
                    var = tk.BooleanVar(value=False)
                    text = f"🎵 Audio {audio_count}: {lang} [{codec}, {bitrate_kb}]"
                    cb = tk.Checkbutton(self.tracks_frame, text=text, variable=var,
                                       bg=COLORS['panel'], fg=COLORS['text'],
                                       selectcolor=COLORS['accent2'], 
                                       activebackground=COLORS['panel'])
                    cb.pack(anchor=tk.W, padx=5, pady=2)
                    self.track_checkboxes.append((var, track_info))
                
                elif stream_type == 'subtitle':
                    subtitle_count += 1
                    codec = stream.get('codec_name', 'unknown')
                    lang = stream.get('tags', {}).get('language', 'und')
                    
                    track_info = {
                        'type': 'subtitle',
                        'index': index,
                        'codec': codec,
                        'language': lang,
                        'stream_index': f"0:s:{subtitle_count-1}"
                    }
                    self.extract_tracks.append(track_info)
                    
                    # Create checkbox
                    var = tk.BooleanVar(value=False)
                    text = f"📝 Subtitle {subtitle_count}: {lang} [{codec}]"
                    cb = tk.Checkbutton(self.tracks_frame, text=text, variable=var,
                                       bg=COLORS['panel'], fg=COLORS['text'],
                                       selectcolor=COLORS['accent2'],
                                       activebackground=COLORS['panel'])
                    cb.pack(anchor=tk.W, padx=5, pady=2)
                    self.track_checkboxes.append((var, track_info))
            
            if audio_count == 0 and subtitle_count == 0:
                tk.Label(self.tracks_frame, text="⚠️ لم يتم العثور على مسارات صوت أو ترجمة",
                        fg=COLORS['warning'], bg=COLORS['panel']).pack(pady=10)
                self.extract_btn.config(state='disabled')
            else:
                self.extract_btn.config(state='normal')
                messagebox.showinfo("نجح", f"تم العثور على:\n{audio_count} مسار صوت\n{subtitle_count} مسار ترجمة")
        
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل تحليل الفيديو:\n{str(e)}")
            self.add_log(f"Error analyzing video: {e}")
    
    def extract_selected_tracks(self):
        """Extract selected tracks from video"""
        video_path = self.extract_video_path.get()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("خطأ", "الرجاء اختيار ملف فيديو صحيح")
            return
        
        # Get selected tracks
        selected = [(info, var.get()) for var, info in self.track_checkboxes if var.get()]
        
        if not selected:
            messagebox.showwarning("تحذير", "الرجاء اختيار مسار واحد على الأقل")
            return
        
        output_dir = self.output_dir.get()
        base_name = Path(video_path).stem
        
        try:
            ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg.exe"
            
            for info, _ in selected:
                # Determine output extension
                if info['type'] == 'audio':
                    ext_map = {'aac': 'aac', 'mp3': 'mp3', 'ac3': 'ac3', 'opus': 'opus'}
                    ext = ext_map.get(info['codec'], 'mka')
                    output_file = os.path.join(output_dir, 
                                              f"{base_name}_audio_{info['language']}.{ext}")
                else:  # subtitle
                    ext_map = {'srt': 'srt', 'ass': 'ass', 'ssa': 'ssa', 'subrip': 'srt'}
                    ext = ext_map.get(info['codec'], 'srt')
                    output_file = os.path.join(output_dir,
                                              f"{base_name}_sub_{info['language']}.{ext}")
                
                # Extract track
                cmd = [ffmpeg_path, '-i', video_path, '-map', info['stream_index'],
                       '-c', 'copy', '-y', output_file]
                
                subprocess.run(cmd, capture_output=True, timeout=60)
                self.add_log(f"Extracted: {Path(output_file).name}")
            
            messagebox.showinfo("نجح", f"تم استخراج {len(selected)} مسار بنجاح!")
        
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل استخراج المسارات:\n{str(e)}")
            self.add_log(f"Error extracting tracks: {e}")
    
    def merge_audio_track(self):
        """Merge audio file with video"""
        video_path = self.merge_video_path.get()
        audio_path = self.merge_audio_path.get()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("خطأ", "الرجاء اختيار ملف فيديو صحيح")
            return
        
        if not audio_path or not os.path.exists(audio_path):
            messagebox.showerror("خطأ", "الرجاء اختيار ملف صوت صحيح")
            return
        
        mode = self.merge_mode.get()
        output_dir = self.output_dir.get()
        base_name = Path(video_path).stem
        output_file = os.path.join(output_dir, f"[Merged] {base_name}.mp4")
        
        # Add sequential number if exists
        counter = 1
        while os.path.exists(output_file):
            output_file = os.path.join(output_dir, f"[Merged] {base_name} ({counter}).mp4")
            counter += 1
        
        try:
            ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg.exe"
            
            if mode == "replace":
                # Replace audio: take video from input 0, audio from input 1
                cmd = [ffmpeg_path, '-i', video_path, '-i', audio_path,
                       '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
                       '-b:a', '192k', '-y', output_file]
            
            elif mode == "add":
                # Add as new track: keep all from input 0, add audio from input 1
                cmd = [ffmpeg_path, '-i', video_path, '-i', audio_path,
                       '-map', '0', '-map', '1:a', '-c', 'copy', '-c:a:1', 'aac',
                       '-b:a:1', '192k', '-y', output_file]
            
            else:  # mix
                # Mix audio tracks
                cmd = [ffmpeg_path, '-i', video_path, '-i', audio_path,
                       '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest',
                       '-map', '0:v', '-c:v', 'copy', '-c:a', 'aac',
                       '-b:a', '192k', '-y', output_file]
            
            self.add_log(f"Merging audio ({mode} mode)...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.add_log(f"✅ Merged successfully: {Path(output_file).name}")
                messagebox.showinfo("نجح", f"تم دمج الصوت بنجاح!\n{Path(output_file).name}")
            else:
                raise Exception(result.stderr)
        
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل دمج الصوت:\n{str(e)}")
            self.add_log(f"Error merging audio: {e}")
    
    def add_log(self, msg):
        self.msg_queue.put(("log", msg))
    
    def check_messages(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_text.config(state='normal')
                    self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {data}\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state='disabled')
                elif msg_type == "progress":
                    self.progress_bar['value'] = data
                elif msg_type == "done":
                    self.finish_compression(True)
                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                    self.finish_compression(False)
                elif msg_type == "cancelled":
                    self.add_log("Cancelled by user")
                    self.finish_compression(False)
        except queue.Empty:
            pass
        self.root.after(100, self.check_messages)
    
    def create_subtitle_with_intro(self, original_sub):
        """Create a temporary subtitle file with intro"""
        try:
            intro_text = self.intro_textbox.get('1.0', tk.END).strip()
            
            content = ""
            first_ms = 0
            
            # Read original subtitle if exists
            if original_sub and os.path.exists(original_sub):
                with open(original_sub, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find first timestamp
                first_time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->', content)
                if first_time_match:
                    first_time = first_time_match.group(1)
                    # Convert to milliseconds
                    h, m, s_ms = first_time.split(':')
                    s, ms = s_ms.split(',')
                    first_ms = int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
            
            # Set intro end time
            if first_ms > 0:
                intro_end_ms = min(first_ms - 500, 15000)
            else:
                intro_end_ms = 15000
            
            # Convert back to SRT format
            intro_end_h = intro_end_ms // 3600000
            intro_end_m = (intro_end_ms % 3600000) // 60000
            intro_end_s = (intro_end_ms % 60000) // 1000
            intro_end_ms_part = intro_end_ms % 1000
            intro_end = f"{intro_end_h:02d}:{intro_end_m:02d}:{intro_end_s:02d},{intro_end_ms_part:03d}"
            
            # Create intro subtitle entry with HTML formatting
            lines = intro_text.split('\\n')
            formatted_lines = []
            
            for line in lines:
                if "تمت الترجمة بواسطة" in line:
                    parts = line.split("تمت الترجمة بواسطة")
                    if len(parts) > 1:
                        suffix = parts[1]
                        formatted_line = f'<font face="Segoe UI" color="#40bfff">تمت الترجمة بواسطة</font><font face="Segoe UI" color="#ffa500">{suffix}</font>'
                        formatted_lines.append(f'<b>{formatted_line}</b>')
                    else:
                        formatted_lines.append(f'<b><font face="Segoe UI" color="#40bfff">{line}</font></b>')
                else:
                    formatted_lines.append(f'<b><font face="Segoe UI" color="#40bfff">{line}</font></b>')
            
            intro_formatted = '<br>'.join(formatted_lines)
            
            intro_entry = f"""1
00:00:00,431 --> {intro_end}
{intro_formatted}

"""
            
            # Adjust numbering of original subtitles
            if content:
                def increment_sub_number(match):
                    num = int(match.group(1))
                    return str(num + 1)
                
                content = re.sub(r'^(\d+)$', increment_sub_number, content, flags=re.MULTILINE)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.srt', delete=False)
            temp_file.write(intro_entry + content)
            temp_file.close()
            
            self.add_log(f"Created subtitle with intro (ends at {intro_end})")
            return temp_file.name
            
        except Exception as e:
            self.add_log(f"Error creating intro: {e}")
            return original_sub
    
    def start_compression(self):
        # المنطق الجديد: CPU هو الافتراضي، GPU اختياري
        # عند تفعيل GPU: نختبر FFmpeg الحديث أولاً، ثم Kepler كبديل
        
        if not self.enable_gpu.get():
            # CPU Mode (الافتراضي): نستخدم FFmpeg الحديث
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                self.add_log("✅ CPU Mode: استخدام FFmpeg الحديث من النظام")
            elif os.path.exists("ffmpeg.exe"):
                ffmpeg = os.path.abspath("ffmpeg.exe")
                self.add_log("✅ CPU Mode: استخدام ffmpeg.exe من المجلد")
            elif os.path.exists("ffmpeg_kepler.exe"):
                ffmpeg = os.path.abspath("ffmpeg_kepler.exe")
                self.add_log("⚠️ CPU Mode: استخدام ffmpeg_kepler.exe (قد لا تظهر الرموز)")
            else:
                messagebox.showerror("خطأ", "FFmpeg غير موجود!\nثبت FFmpeg في النظام أو ضع ffmpeg.exe في مجلد البرنامج")
                return
        else:
            # GPU Mode: اختبار ذكي للعثور على أفضل FFmpeg يدعم GPU
            self.add_log("🚀 GPU Mode مفعّل - جاري البحث عن أفضل FFmpeg...")
            
            # الأولوية 1: FFmpeg الحديث من النظام
            system_ffmpeg = shutil.which("ffmpeg")
            if system_ffmpeg:
                self.add_log("🔍 اختبار FFmpeg الحديث من النظام...")
                # سنختبره لاحقاً في compress_worker
                ffmpeg = system_ffmpeg
                self.add_log("✅ سيتم استخدام FFmpeg الحديث من النظام")
            # الأولوية 2: ffmpeg.exe من المجلد
            elif os.path.exists("ffmpeg.exe"):
                ffmpeg = os.path.abspath("ffmpeg.exe")
                self.add_log("✅ سيتم استخدام ffmpeg.exe من المجلد")
            # الأولوية 3: ffmpeg_kepler.exe (للكروت القديمة)
            elif os.path.exists("ffmpeg_kepler.exe"):
                ffmpeg = os.path.abspath("ffmpeg_kepler.exe")
                self.add_log("✅ سيتم استخدام ffmpeg_kepler.exe (دعم GTX 660)")
            else:
                messagebox.showerror("خطأ", "FFmpeg غير موجود!\nثبت FFmpeg في النظام أو ضع ffmpeg.exe في مجلد البرنامج")
                return
        
        settings = {
            'ffmpeg': ffmpeg,
            'input': self.video_path.get(),
            'subtitle': self.sub_path.get(),
            'output_dir': self.output_dir.get(),
            'mode': self.mode.get(),
            'quality': self.quality.get(),
            'codec': self.codec.get(),
            'burn_subs': self.burn_subs.get(),
            'add_intro': self.add_intro.get(),
            'crf': self.crf.get(),
            'preset': self.preset.get(),
            'minrate': self.minrate.get(),
            'maxrate': self.maxrate.get(),
            'bufsize': self.bufsize.get(),
            'scale': self.scale.get(),
            'audio_bitrate': self.audio_bitrate.get(),
            'meta_title': self.meta_title.get(),
            'meta_author': self.meta_author.get(),
            'gpu_h264': self.gpu_h264,
            'gpu_h265': self.gpu_h265,
            'enable_gpu': self.enable_gpu.get()  # خيار تفعيل GPU
        }
        
        self.start_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.progress_bar['value'] = 0
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.stop_flag.clear()
        
        threading.Thread(target=self.compress_worker, args=(settings,), daemon=True).start()
    
    def cancel_compression(self):
        if self.process:
            self.stop_flag.set()
            try:
                self.process.terminate()
            except:
                pass
            self.msg_queue.put(("cancelled", None))
    
    def exit_app(self):
        if messagebox.askokcancel("Exit", "Do you want to exit?"):
            self.cancel_compression()
            self.root.quit()
            self.root.destroy()
    
    def finish_compression(self, success):
        self.start_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        if success:
            messagebox.showinfo("Success", "✅ Compression completed successfully!")
    
    def compress_worker(self, cfg):
        temp_sub = None
        try:
            self.add_log("Starting compression...")
            
            input_file = cfg['input']
            quality_tag = cfg['quality'] if cfg['mode'] == 'auto' else 'Custom'
            if quality_tag.startswith("Original"):
                quality_tag = "Original"
            
            # إضافة علامة GPU إذا كان مفعّل
            gpu_tag = "[GPU] " if cfg['enable_gpu'] else ""
            
            # إنشاء اسم الملف الأساسي
            base_name = f"[Orsozox] {Path(input_file).stem} {gpu_tag}[{quality_tag}]"
            output_file = os.path.join(cfg['output_dir'], f"{base_name}.mp4")
            
            # إضافة رقم تسلسلي إذا كان الملف موجود
            counter = 1
            while os.path.exists(output_file):
                output_file = os.path.join(cfg['output_dir'], f"{base_name} ({counter}).mp4")
                counter += 1
            
            if counter > 1:
                self.add_log(f"📝 الملف موجود، تم إضافة رقم ({counter-1})")
            
            # Get duration and resolution
            duration = 0
            video_width = 854
            video_height = 480
            try:
                r = subprocess.run([cfg['ffmpeg'], '-i', input_file], 
                                 stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 text=True, errors='ignore')
                
                m_dur = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", r.stderr)
                if m_dur:
                    h, m2, s = map(float, m_dur.groups())
                    duration = h * 3600 + m2 * 60 + s
                
                m_res = re.search(r"Stream #.*Video:.*,\s*(\d{3,})x(\d{3,})", r.stderr)
                if m_res:
                    video_width = int(m_res.group(1))
                    video_height = int(m_res.group(2))
            except:
                pass
            
            # Calculate responsive font size
            min_dim = min(video_width, video_height)
            font_size = max(14, int(min_dim / 30))
            
            # Handle subtitle with intro
            sub_file = cfg['subtitle']
            if (sub_file or cfg['add_intro']) and cfg['burn_subs']:
                if cfg['add_intro']:
                    temp_sub = self.create_subtitle_with_intro(sub_file)
                    sub_file = temp_sub
            
            # Video settings based on codec and GPU
            use_gpu = False
            ffmpeg_to_use = cfg['ffmpeg']  # سيتم تحديثه إذا تم التحويل لـ Kepler
            
            # Test GPU compatibility first (only if Enable GPU is checked)
            if not cfg['enable_gpu']:
                # CPU Mode: لا نستخدم GPU
                if cfg['codec'] == 'H.265':
                    codec_name = 'libx265'
                else:
                    codec_name = 'libx264'
                use_gpu = False
            elif cfg['codec'] == 'H.265' and cfg['gpu_h265']:
                # Test if hevc_nvenc works with current FFmpeg
                test_cmd = [cfg['ffmpeg'], '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1', 
                           '-c:v', 'hevc_nvenc', '-f', 'null', '-']
                try:
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True, 
                                                timeout=5, errors='ignore')
                    if test_result.returncode == 0:
                        codec_name = 'hevc_nvenc'
                        use_gpu = True
                        self.add_log("🚀 استخدام NVIDIA GPU (H.265)")
                    else:
                        # فشل الاختبار - محاولة ffmpeg_kepler.exe
                        self.add_log("⚠️ GPU غير متوافق مع FFmpeg الحالي - محاولة Kepler...")
                        if os.path.exists("ffmpeg_kepler.exe"):
                            kepler_path = os.path.abspath("ffmpeg_kepler.exe")
                            test_kepler = [kepler_path, '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1',
                                         '-c:v', 'hevc_nvenc', '-f', 'null', '-']
                            try:
                                kepler_result = subprocess.run(test_kepler, capture_output=True, text=True,
                                                              timeout=5, errors='ignore')
                                if kepler_result.returncode == 0:
                                    ffmpeg_to_use = kepler_path
                                    codec_name = 'hevc_nvenc'
                                    use_gpu = True
                                    self.add_log("✅ نجح! استخدام ffmpeg_kepler.exe مع GPU (H.265)")
                                else:
                                    codec_name = 'libx265'
                                    self.add_log("⚠️ Kepler فشل أيضاً - استخدام CPU (H.265)")
                            except:
                                codec_name = 'libx265'
                                self.add_log("⚠️ خطأ في اختبار Kepler - استخدام CPU (H.265)")
                        else:
                            codec_name = 'libx265'
                            self.add_log("⚠️ ffmpeg_kepler.exe غير موجود - استخدام CPU (H.265)")
                except:
                    codec_name = 'libx265'
                    self.add_log("⚠️ فشل اختبار GPU - استخدام CPU (H.265)")
            elif cfg['codec'] == 'H.264' and cfg['gpu_h264']:
                # Test if h264_nvenc works with current FFmpeg
                test_cmd = [cfg['ffmpeg'], '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1', 
                           '-c:v', 'h264_nvenc', '-f', 'null', '-']
                try:
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True, 
                                                timeout=5, errors='ignore')
                    if test_result.returncode == 0:
                        codec_name = 'h264_nvenc'
                        use_gpu = True
                        self.add_log("🚀 استخدام NVIDIA GPU (H.264)")
                    else:
                        # فشل الاختبار - محاولة ffmpeg_kepler.exe
                        self.add_log("⚠️ GPU غير متوافق مع FFmpeg الحالي - محاولة Kepler...")
                        if os.path.exists("ffmpeg_kepler.exe"):
                            kepler_path = os.path.abspath("ffmpeg_kepler.exe")
                            test_kepler = [kepler_path, '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1',
                                         '-c:v', 'h264_nvenc', '-f', 'null', '-']
                            try:
                                kepler_result = subprocess.run(test_kepler, capture_output=True, text=True,
                                                              timeout=5, errors='ignore')
                                if kepler_result.returncode == 0:
                                    ffmpeg_to_use = kepler_path
                                    codec_name = 'h264_nvenc'
                                    use_gpu = True
                                    self.add_log("✅ نجح! استخدام ffmpeg_kepler.exe مع GPU (H.264)")
                                else:
                                    codec_name = 'libx264'
                                    self.add_log("⚠️ Kepler فشل أيضاً - استخدام CPU (H.264)")
                            except:
                                codec_name = 'libx264'
                                self.add_log("⚠️ خطأ في اختبار Kepler - استخدام CPU (H.264)")
                        else:
                            codec_name = 'libx264'
                            self.add_log("⚠️ ffmpeg_kepler.exe غير موجود - استخدام CPU (H.264)")
                except:
                    codec_name = 'libx264'
                    self.add_log("⚠️ فشل اختبار GPU - استخدام CPU (H.264)")
            else:
                # No GPU or not selected
                if cfg['codec'] == 'H.265':
                    codec_name = 'libx265'
                else:
                    codec_name = 'libx264'
            
            # Build command with the correct FFmpeg (بعد اختبار GPU)
            cmd = [ffmpeg_to_use, '-y', '-i', input_file]
            
            if cfg['mode'] == 'auto':
                if cfg['quality'].startswith("Original"):
                    # Same as source with specific compression settings
                    scale = None
                    crf, maxrate, bufsize = "25", "3000k", "4000k"
                    minrate, preset = "1500k", "medium"
                else:
                    presets = {
                        "1080p Standard": ("25", "3000k", "4000k", "scale=-2:1080"),
                        "1080p High": ("23", "4500k", "6000k", "scale=-2:1080"),
                        "720p Standard": ("26", "1500k", "3000k", "scale=-2:720"),
                        "720p Small": ("28", "1000k", "2000k", "scale=-2:720"),
                        "480p Standard": ("27", "800k", "1500k", "scale=-2:480"),
                        "480p Small": ("28", "500k", "1000k", "scale=-2:480")
                    }
                    crf, maxrate, bufsize, scale = presets.get(cfg['quality'], presets["1080p Standard"])
                    minrate, preset = "500k", "medium"
            else:
                crf, preset = cfg['crf'], cfg['preset']
                minrate, maxrate, bufsize = cfg['minrate'], cfg['maxrate'], cfg['bufsize']
                scale = None if cfg['scale'] == "Original" else cfg['scale']
            
            if use_gpu:
                # NVENC parameters with CRF for better compression
                # استخدام CRF مع GPU لتقليل حجم الملف
                cmd.extend(['-c:v', codec_name, '-preset', 'medium', '-cq', crf,
                           '-b:v', maxrate, '-maxrate', maxrate, '-bufsize', bufsize])
            else:
                cmd.extend(['-c:v', codec_name, '-preset', preset, '-crf', crf,
                           '-minrate', minrate, '-maxrate', maxrate, '-bufsize', bufsize])
                if codec_name == 'libx265':
                    cmd.extend(['-x265-params', 'log-level=error'])
            
            cmd.extend(['-pix_fmt', 'yuv420p', '-movflags', 'faststart'])
            
            if codec_name == 'libx264':
                cmd.extend(['-tune', 'film', '-profile:v', 'main', '-level', '4.1'])
            
            # Filters
            filters = []
            if sub_file and cfg['burn_subs']:
                sub_esc = sub_file.replace('\\', '/').replace(':', '\\:')
                style = f"FontName=Segoe UI,FontSize={font_size},PrimaryColour=&H00FFFFFF,Outline=2,Shadow=1,MarginV=30,Alignment=2,BorderStyle=1"
                filters.append(f"subtitles='{sub_esc}':force_style='{style}'")
            if scale:
                filters.append(scale)
            filters.append("drawtext=font='DejaVuSans':text='✠ Orsozox Movies ✠':x=w-tw-10:y=10:fontsize=(h/36):fontcolor=white:shadowcolor=black:shadowx=5:shadowy=5")
            cmd.extend(['-vf', ','.join(filters)])
            
            # Audio
            cmd.extend(['-c:a', 'aac', '-rematrix_maxval', '1.0', '-ac', '2', '-b:a', cfg['audio_bitrate']])
            
            # Metadata
            title, author = cfg['meta_title'], cfg['meta_author']
            cmd.extend([
                '-metadata', f'title={title}',
                '-metadata', f'author={author}',
                '-metadata:s:s', f"title=Subtitled By :- {title.split(':- ')[-1] if ':- ' in title else '@inoshyi'}",
                '-metadata:s:a', f"title=By :- {title.split(':- ')[-1] if ':- ' in title else '@inoshyi'}",
                '-metadata:s:v', f'title=By:- {author}'
            ])
            
            cmd.append(output_file)
            
            self.add_log(f"Codec: {cfg['codec']} | Quality: {quality_tag}")
            self.add_log(f"Output: {Path(output_file).name}")
            
            # Execute
            self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                          universal_newlines=True, errors='ignore')
            
            while True:
                if self.stop_flag.is_set():
                    break
                line = self.process.stderr.readline()
                if not line and self.process.poll() is not None:
                    break
                if line and duration > 0:
                    m = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                    if m:
                        h, m2, s = map(float, m.groups())
                        current = h * 3600 + m2 * 60 + s
                        self.msg_queue.put(("progress", (current / duration) * 100))
            
            if self.stop_flag.is_set():
                return
            
            if self.process.returncode == 0:
                self.msg_queue.put(("progress", 100))
                self.add_log("✅ Compression completed successfully!")
                self.msg_queue.put(("done", None))
            else:
                self.add_log("❌ Compression failed!")
                self.msg_queue.put(("error", "FFmpeg returned an error"))
        
        except Exception as e:
            self.msg_queue.put(("error", str(e)))
        finally:
            if temp_sub and os.path.exists(temp_sub):
                try:
                    os.unlink(temp_sub)
                except:
                    pass

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = OrsozoxCompressor(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
