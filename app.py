import customtkinter as ctk
import yt_dlp
import threading
import requests
from PIL import Image
import os
import io
import re
import json
import subprocess
import sys
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Constants
APP_WIDTH = 560
APP_HEIGHT = 650
ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "download_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    "format": "mp4",
    "quality": "Terbaik",
}

# ── Light Theme with YouTube Accent ──
ACCENT = "#FF0000"        # YouTube Red
ACCENT_HOVER = "#CC0000"  # Darker red on hover
ACCENT_LIGHT = "#FF4E45"  # Lighter red for highlights
SUCCESS = "#2E7D32"       # Green
SUCCESS_HOVER = "#1B5E20"
DANGER = "#D32F2F"        # Error red
DANGER_HOVER = "#B71C1C"
WARNING_CLR = "#E65100"   # Deep orange

# Light theme surfaces
BG_MAIN = "#F5F5F5"       # Soft gray background
CARD_BG = "#FFFFFF"       # White cards
CARD_BORDER = "#E0E0E0"   # Light gray border
SUBTLE_TEXT = "#757575"   # Medium gray text
LOG_BG = "#FAFAFA"        # Slightly off-white log area
LOG_TEXT = "#212121"       # Near-black log text
SURFACE = "#F0F0F0"       # Light surface
BTN_TEXT = "#424242"      # Dark gray button text


class YtLogger:
    """Custom logger that captures yt-dlp output and sends it to the GUI."""
    def __init__(self, callback):
        self.callback = callback

    def debug(self, msg):
        if msg.startswith('[debug]'):
            self.callback(msg, "debug")
        else:
            self.callback(msg, "info")

    def info(self, msg):
        self.callback(msg, "info")

    def warning(self, msg):
        self.callback(msg, "warning")

    def error(self, msg):
        self.callback(msg, "error")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YT Downloader")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.resizable(False, False)

        self.config = self._load_config()
        self.download_folder = self.config.get("download_folder", DEFAULT_CONFIG["download_folder"])

        # Force light theme
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_MAIN)

        self.current_info = None
        self.is_downloading = False
        self.is_cancelled = False
        self._thumb_image = None
        self.bulk_urls = []
        self.bulk_progress = {}
        self.pending_bulk_urls = []
        self.bulk_mp4_infos = []
        self.bulk_mp4_vars = {}
        self.bulk_format_mode = "mp3"


        # ── Page container ──
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=22, pady=(8, 5))

        # ── Bottom: Shared Log Panel (always visible) ──
        log_wrapper = ctk.CTkFrame(self, corner_radius=12, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        log_wrapper.pack(fill="x", padx=22, pady=(5, 16))
        log_wrapper.grid_columnconfigure(0, weight=1)
        log_wrapper.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(log_wrapper, fg_color="transparent")
        log_header.grid(row=0, column=0, padx=14, pady=(10, 0), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(log_header, text="📋 Log Aktivitas", font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        log_title.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(log_header, text="Bersihkan", width=70, height=26, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=1, border_color=CARD_BORDER, hover_color=CARD_BORDER, text_color=BTN_TEXT, corner_radius=8, command=self._clear_log)
        clear_btn.grid(row=0, column=1)

        self.log_box = ctk.CTkTextbox(log_wrapper, height=140, font=ctk.CTkFont(family="Consolas", size=11), fg_color=LOG_BG, text_color=LOG_TEXT, corner_radius=8, border_width=1, border_color=CARD_BORDER, activate_scrollbars=True)
        self.log_box.grid(row=1, column=0, padx=14, pady=(8, 14), sticky="nsew")
        self.log_box.configure(state="disabled")

        # Tag colors
        self.log_box.tag_config("warning", foreground=WARNING_CLR)
        self.log_box.tag_config("error", foreground=DANGER)
        self.log_box.tag_config("info", foreground=LOG_TEXT)
        self.log_box.tag_config("debug", foreground="#6B7280")

        # Create pages
        self.pages = {}
        self._create_page_home()
        self._create_page_format_choice()
        self._create_page_bulk_mp4()
        self._create_page_download()

        self._show_page("home")

    # ──────────────────────────────────────────────
    # LOG
    # ──────────────────────────────────────────────
    def _log(self, msg, level="info"):
        """Thread-safe append to the shared log panel."""
        clean_msg = ANSI_RE.sub('', str(msg)).strip()
        if not clean_msg:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {clean_msg}\n"

        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line, level)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(0, _do)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ──────────────────────────────────────────────
    # CONFIG
    # ──────────────────────────────────────────────
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self._log(f"Gagal menyimpan pengaturan: {e}", "error")



    # ──────────────────────────────────────────────
    # PAGE: HOME
    # ──────────────────────────────────────────────
    def _create_page_home(self):
        page = ctk.CTkFrame(self.container, corner_radius=18, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.pages["home"] = page

        page.grid_columnconfigure(0, weight=1)

        # Icon / Branding
        icon_label = ctk.CTkLabel(page, text="🎬", font=ctk.CTkFont(size=52))
        icon_label.grid(row=0, column=0, pady=(35, 2))

        title = ctk.CTkLabel(page, text="YT Downloader", font=ctk.CTkFont(size=32, weight="bold"))
        title.grid(row=1, column=0, pady=(0, 3))

        subtitle = ctk.CTkLabel(page, text="Unduh video & audio dari YouTube\nGunakan Enter untuk memasukkan banyak tautan / playlist", font=ctk.CTkFont(size=13), text_color=SUBTLE_TEXT)
        subtitle.grid(row=2, column=0, pady=(0, 22))

        # URL Input
        self.url_entry = ctk.CTkTextbox(page, height=80, font=ctk.CTkFont(size=14), corner_radius=10, fg_color=LOG_BG, border_width=1, border_color=CARD_BORDER, activate_scrollbars=True)
        self.url_entry.grid(row=3, column=0, padx=30, sticky="ew")

        # Fetch Button
        self.fetch_btn = ctk.CTkButton(page, text="🔍  Cari Video", height=48, font=ctk.CTkFont(size=15, weight="bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=12, command=self.fetch_video)
        self.fetch_btn.grid(row=4, column=0, padx=30, pady=(15, 8), sticky="ew")

        # Status
        self.home_status = ctk.CTkLabel(page, text="", font=ctk.CTkFont(size=12), text_color=SUBTLE_TEXT)
        self.home_status.grid(row=5, column=0, padx=30, pady=(0, 8))
        
        # Folder Selection
        folder_frame = ctk.CTkFrame(page, fg_color="transparent")
        folder_frame.grid(row=6, column=0, padx=30, pady=(0, 20), sticky="ew")
        
        self.folder_label = ctk.CTkLabel(folder_frame, text=f"📂 {self.download_folder}", font=ctk.CTkFont(size=11), text_color=SUBTLE_TEXT, anchor="w")
        self.folder_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        folder_btn = ctk.CTkButton(folder_frame, text="Ubah", width=55, height=26, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=1, border_color=CARD_BORDER, hover_color=CARD_BORDER, text_color=BTN_TEXT, command=self._choose_folder)
        folder_btn.pack(side="right")

    def _choose_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.download_folder, title="Pilih Folder Unduhan")
        if folder:
            self.download_folder = folder
            self.folder_label.configure(text=f"📂 {self.download_folder}")
            self.config["download_folder"] = self.download_folder
            self._save_config()

    # ──────────────────────────────────────────────
    # PAGE: FORMAT CHOICE (BULK)
    # ──────────────────────────────────────────────
    def _create_page_format_choice(self):
        page = ctk.CTkFrame(self.container, corner_radius=18, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.pages["format_choice"] = page
        page.grid_columnconfigure(0, weight=1)

        self.fc_title = ctk.CTkLabel(page, text="📦 Pilih Format", font=ctk.CTkFont(size=26, weight="bold"))
        self.fc_title.grid(row=0, column=0, pady=(45, 5))

        self.fc_subtitle = ctk.CTkLabel(page, text="Ditemukan N video.", font=ctk.CTkFont(size=14), text_color=SUBTLE_TEXT)
        self.fc_subtitle.grid(row=1, column=0, pady=(0, 35))

        btn_frame = ctk.CTkFrame(page, fg_color="transparent")
        btn_frame.grid(row=2, column=0)

        mp3_btn = ctk.CTkButton(btn_frame, text="🎵 MP3", width=140, height=55, font=ctk.CTkFont(size=17, weight="bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=14, command=lambda: self._on_bulk_format_chosen("mp3"))
        mp3_btn.grid(row=0, column=0, padx=12)

        mp4_btn = ctk.CTkButton(btn_frame, text="🎬 MP4", width=140, height=55, font=ctk.CTkFont(size=17, weight="bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=14, command=lambda: self._on_bulk_format_chosen("mp4"))
        mp4_btn.grid(row=0, column=1, padx=12)

        back_btn = ctk.CTkButton(page, text="← Kembali", width=110, fg_color="transparent", border_width=1, border_color=CARD_BORDER, hover_color=CARD_BORDER, text_color=BTN_TEXT, command=self._go_home)
        back_btn.grid(row=3, column=0, pady=(50, 0))

    # ──────────────────────────────────────────────
    # PAGE: BULK MP4 QUALITY SELECTION
    # ──────────────────────────────────────────────
    def _create_page_bulk_mp4(self):
        page = ctk.CTkFrame(self.container, corner_radius=18, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.pages["bulk_mp4"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(page, text="🎬 Pilih Kualitas Video", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, pady=(25, 12))

        self.scroll_frame = ctk.CTkScrollableFrame(page, corner_radius=10, fg_color=LOG_BG)
        self.scroll_frame.grid(row=1, column=0, padx=20, sticky="nsew")

        action_frame = ctk.CTkFrame(page, fg_color="transparent")
        action_frame.grid(row=2, column=0, pady=20)

        back_btn = ctk.CTkButton(action_frame, text="← Kembali", width=110, fg_color="transparent", border_width=1, border_color=CARD_BORDER, hover_color=CARD_BORDER, text_color=BTN_TEXT, command=self._go_home)
        back_btn.grid(row=0, column=0, padx=10)

        start_btn = ctk.CTkButton(action_frame, text="⬇  Mulai Unduh", width=140, height=40, font=ctk.CTkFont(size=14, weight="bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=12, command=self._start_bulk_mp4_download)
        start_btn.grid(row=0, column=1, padx=10)

    # ──────────────────────────────────────────────
    # PAGE: DOWNLOAD
    # ──────────────────────────────────────────────
    def _create_page_download(self):
        page = ctk.CTkFrame(self.container, corner_radius=18, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.pages["download"] = page

        page.grid_columnconfigure(0, weight=1)

        # ── Video Info Card ──
        self.info_card = ctk.CTkFrame(page, corner_radius=12, fg_color=SURFACE, border_width=1, border_color=CARD_BORDER)
        self.info_card.grid(row=0, column=0, padx=22, pady=(18, 10), sticky="ew")
        self.info_card.grid_columnconfigure(1, weight=1)

        self.dl_thumb = ctk.CTkLabel(self.info_card, text="")
        self.dl_thumb.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=14)

        self.dl_title = ctk.CTkLabel(self.info_card, text="", font=ctk.CTkFont(size=14, weight="bold"), wraplength=280, anchor="w", justify="left")
        self.dl_title.grid(row=0, column=1, padx=(0, 15), pady=(14, 2), sticky="nw")

        self.dl_detail = ctk.CTkLabel(self.info_card, text="", font=ctk.CTkFont(size=11), text_color=SUBTLE_TEXT, anchor="w")
        self.dl_detail.grid(row=1, column=1, padx=(0, 15), pady=(0, 14), sticky="nw")

        # ── Format + Quality Row ──
        options_frame = ctk.CTkFrame(page, fg_color="transparent")
        options_frame.grid(row=1, column=0, pady=(5, 0))

        self.format_var = ctk.StringVar(value=self.config.get("format", "mp4"))

        self.radio_mp4 = ctk.CTkRadioButton(options_frame, text="MP4", variable=self.format_var, value="mp4", command=self._on_format_change, font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_LIGHT)
        self.radio_mp4.grid(row=0, column=0, padx=(0, 10))

        self.radio_mp3 = ctk.CTkRadioButton(options_frame, text="MP3", variable=self.format_var, value="mp3", command=self._on_format_change, font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_LIGHT)
        self.radio_mp3.grid(row=0, column=1, padx=(0, 15))

        self.quality_label = ctk.CTkLabel(options_frame, text="Kualitas:", font=ctk.CTkFont(size=13))
        self.quality_label.grid(row=0, column=2, padx=(10, 5))

        self.quality_var = ctk.StringVar(value=self.config.get("quality", "Terbaik"))
        self.quality_menu = ctk.CTkOptionMenu(options_frame, variable=self.quality_var, values=["Terbaik"], width=150, font=ctk.CTkFont(size=12), fg_color=ACCENT, button_color=ACCENT_HOVER, button_hover_color=ACCENT_LIGHT, command=self._on_quality_change)
        self.quality_menu.grid(row=0, column=3)

        self._quality_widgets = [self.quality_label, self.quality_menu]

        # ── Download Button ──
        self.download_btn = ctk.CTkButton(page, text="⬇  Mulai Unduh", height=46, font=ctk.CTkFont(size=15, weight="bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=12, command=self.start_download)
        self.download_btn.grid(row=2, column=0, padx=25, pady=(12, 5), sticky="ew")

        # ── Progress Section ──
        self.progress_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, padx=25, pady=(3, 3), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame.grid_columnconfigure(1, weight=1)

        self.dl_status = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=12), text_color=SUBTLE_TEXT, anchor="w")
        self.dl_status.grid(row=0, column=0, sticky="w")
        
        self.dl_count = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT, anchor="e")
        self.dl_count.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color=ACCENT, corner_radius=6)
        self.progress_bar.grid(row=1, column=0, columnspan=2, pady=(3, 0), sticky="ew")
        self.progress_bar.set(0)
        self.progress_frame.grid_remove()

        # ── Action Buttons ──
        action_frame = ctk.CTkFrame(page, fg_color="transparent")
        action_frame.grid(row=4, column=0, padx=25, pady=(5, 20), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        self.back_btn = ctk.CTkButton(action_frame, text="⟵  Unduh Lagi", height=40, font=ctk.CTkFont(size=13), fg_color="transparent", border_width=1, border_color=CARD_BORDER, hover_color=CARD_BORDER, text_color=BTN_TEXT, corner_radius=10, command=self._go_home)
        self.back_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.cancel_btn = ctk.CTkButton(action_frame, text="❌  Batal", height=40, font=ctk.CTkFont(size=13), fg_color=DANGER, hover_color=DANGER_HOVER, corner_radius=10, command=self.cancel_download)
        self.cancel_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.cancel_btn.grid_remove()

        self.open_folder_btn = ctk.CTkButton(action_frame, text="📂  Buka Folder", height=40, font=ctk.CTkFont(size=13), fg_color=SUCCESS, hover_color=SUCCESS_HOVER, corner_radius=10, command=self._open_download_folder)
        self.open_folder_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        self.open_folder_btn.grid_remove()

    # ──────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────
    def _show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def _go_home(self):
        self.url_entry.delete("1.0", "end")
        self.home_status.configure(text="")
        self.format_var.set(self.config.get("format", "mp4"))
        self.radio_mp4.configure(state="normal")
        self.radio_mp3.configure(state="normal")
        self._show_quality(self.format_var.get() == "mp4")
        self.progress_frame.grid_remove()
        self.progress_bar.set(0)
        self.dl_status.configure(text="")
        self.download_btn.configure(state="normal")
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.grid_remove()
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.grid_remove()
            self.cancel_btn.configure(state="normal", text="❌  Batal")
        if hasattr(self, "back_btn"):
            self.back_btn.grid()
        self.bulk_urls = []
        self.bulk_progress = {}
        self.pending_bulk_urls = []
        self.bulk_mp4_infos = []
        self.bulk_mp4_vars = {}
        self.bulk_format_mode = "mp3"
        self._show_page("home")

    def _open_download_folder(self):
        try:
            if os.name == 'nt':
                os.startfile(self.download_folder)
            else:
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', self.download_folder])
        except Exception as e:
            self._log(f"Gagal membuka folder: {e}", "error")

    def cancel_download(self):
        if self.is_downloading:
            self.is_cancelled = True
            self.cancel_btn.configure(state="disabled", text="Membatalkan...")
            self._log("Proses pembatalan diminta oleh pengguna...", "warning")

    def _cleanup_part_files(self):
        try:
            for ext in ('*.part', '*.ytdl', '*.temp'):
                for f in glob.glob(os.path.join(self.download_folder, ext)):
                    os.remove(f)
            self._log("Membersihkan file sementara (.part) selesai.", "info")
        except Exception as e:
            self._log(f"Gagal membersihkan file sisa: {e}", "warning")

    # ──────────────────────────────────────────────
    # FORMAT & QUALITY CHANGE
    # ──────────────────────────────────────────────
    def _on_format_change(self):
        fmt = self.format_var.get()
        self._show_quality(fmt == "mp4")
        self.config["format"] = fmt
        self._save_config()

    def _on_quality_change(self, choice):
        self.config["quality"] = choice
        self._save_config()

    def _show_quality(self, show):
        for w in self._quality_widgets:
            if show:
                w.grid()
            else:
                w.grid_remove()

    # ──────────────────────────────────────────────
    # FETCH
    # ──────────────────────────────────────────────
    def fetch_video(self):
        raw_text = self.url_entry.get("1.0", "end").strip()
        urls = [u.strip() for u in raw_text.split('\n') if u.strip()]
        
        if not urls:
            self.home_status.configure(text="Silakan masukkan URL YouTube", text_color="#e74c3c")
            return

        self.fetch_btn.configure(state="disabled", text="Mencari...")
        self.home_status.configure(text="Memeriksa tautan...", text_color="gray")
        threading.Thread(target=self._resolve_urls_thread, args=(urls,), daemon=True).start()

    def _resolve_urls_thread(self, urls):
        logger = YtLogger(self._log)
        resolved_urls = []
        ydl_opts = {'extract_flat': True, 'logger': logger, 'ignoreerrors': True}
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for url in urls:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        if 'entries' in info:
                            # Playlist detected
                            for entry in info['entries']:
                                if entry and entry.get('url'):
                                    resolved_urls.append(entry['url'])
                        else:
                            resolved_urls.append(info.get('webpage_url', url))
        except Exception as e:
            self._log(f"Error memeriksa tautan: {e}", "error")
            
        if not resolved_urls:
            self.after(0, self._on_fetch_error, "Tidak ada video yang ditemukan.")
            return

        if len(resolved_urls) == 1:
            self.bulk_urls = []
            self.after(0, lambda: self.home_status.configure(text="Mendapatkan info detail..."))
            self._fetch_thread(resolved_urls[0])
        else:
            self.pending_bulk_urls = resolved_urls
            self.after(0, self._show_format_choice)

    def _show_format_choice(self):
        self.fetch_btn.configure(state="normal", text="Cari Video")
        self.home_status.configure(text="")
        self.fc_subtitle.configure(text=f"Ditemukan {len(self.pending_bulk_urls)} video dalam daftar/playlist.\nPilih format unduhan:")
        self._show_page("format_choice")

    def _on_bulk_format_chosen(self, fmt):
        self.bulk_format_mode = fmt
        self.bulk_urls = self.pending_bulk_urls
        if fmt == "mp3":
            self.dl_title.configure(text=f"Unduhan Massal MP3 ({len(self.bulk_urls)} Item)")
            self.dl_detail.configure(text="Tautan akan diunduh secara paralel.")
            self.dl_thumb.grid_remove()
            self.format_var.set("mp3")
            self.radio_mp4.grid_remove()
            self.radio_mp3.grid_remove()
            self._show_quality(False)
            self._show_page("download")
        else:
            self._log(f"Memuat info resolusi untuk {len(self.bulk_urls)} video...")
            self.fc_subtitle.configure(text=f"Memuat info resolusi...\nIni mungkin butuh waktu agak lama.")
            threading.Thread(target=self._fetch_bulk_mp4_infos_thread, daemon=True).start()

    def _fetch_bulk_mp4_infos_thread(self):
        logger = YtLogger(self._log)
        ydl_opts = {'skip_download': True, 'logger': logger, 'ignoreerrors': True}
        
        self.bulk_mp4_infos = []
        total = len(self.bulk_urls)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for idx, url in enumerate(self.bulk_urls, 1):
                self._log(f"[{idx}/{total}] Resolusi: {url}")
                try:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        title = info.get('title', 'Video Tidak Diketahui')
                        available_res = set()
                        for f in info.get('formats', []):
                            h = f.get('height')
                            if h and f.get('vcodec', 'none') != 'none':
                                available_res.add(h)
                        
                        sorted_res = sorted(available_res, reverse=True)
                        quality_options = [f"{h}p" for h in sorted_res]
                        if not quality_options:
                            quality_options = ["Terbaik"]
                        
                        self.bulk_mp4_infos.append({
                            'url': url,
                            'title': title,
                            'qualities': quality_options
                        })
                except Exception:
                    pass
        
        self.after(0, self._render_bulk_mp4_page)

    def _render_bulk_mp4_page(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        self.bulk_mp4_vars = {}
        for idx, info in enumerate(self.bulk_mp4_infos):
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color=("gray90", "gray15"))
            row_frame.pack(fill="x", pady=2, padx=5)
            row_frame.grid_columnconfigure(0, weight=1)
            
            lbl = ctk.CTkLabel(row_frame, text=f"{idx+1}. {info['title']}", anchor="w", wraplength=350, justify="left")
            lbl.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
            
            var = ctk.StringVar(value=info['qualities'][0])
            self.bulk_mp4_vars[info['url']] = var
            
            opt = ctk.CTkOptionMenu(row_frame, values=info['qualities'], variable=var, width=100)
            opt.grid(row=0, column=1, padx=10, pady=5)
            
        self._show_page("bulk_mp4")

    def _start_bulk_mp4_download(self):
        self.dl_title.configure(text=f"Unduhan Massal MP4 ({len(self.bulk_mp4_infos)} Item)")
        self.dl_detail.configure(text="Setiap video akan diunduh dengan resolusi terpilih.")
        self.dl_thumb.grid_remove()
        self.format_var.set("mp4")
        self.radio_mp4.grid_remove()
        self.radio_mp3.grid_remove()
        self._show_quality(False)
        self._show_page("download")
        self.start_download()

    def _fetch_thread(self, url):
        logger = YtLogger(self._log)
        ydl_opts = {
            'skip_download': True,
            'socket_timeout': 10,
            'logger': logger,
        }
        try:
            self._log(f"Menghubungkan ke: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            self.current_info = info
            self._log(f"Video ditemukan: {info.get('title', 'Tidak diketahui')}")

            # Extract available resolutions
            available_res = set()
            for f in info.get('formats', []):
                height = f.get('height')
                if height and f.get('vcodec', 'none') != 'none':
                    available_res.add(height)

            sorted_res = sorted(available_res, reverse=True)
            quality_options = [f"{h}p" for h in sorted_res]
            if quality_options:
                quality_options[0] = f"Terbaik ({quality_options[0]})"
            else:
                quality_options = ["Terbaik"]

            self._log(f"Tersedia: {', '.join(quality_options)}")

            # Format duration
            duration = info.get('duration', 0)
            mins, secs = divmod(int(duration), 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                duration_str = f"{hours}j {mins}m {secs}d"
            else:
                duration_str = f"{mins}m {secs}d"

            detail_text = f"⏱ {duration_str}   |   📺 {', '.join(quality_options[1:5])}"

            # Fetch Thumbnail
            ctk_img = None
            thumb_url = info.get('thumbnail')
            if thumb_url:
                try:
                    response = requests.get(thumb_url, timeout=5)
                    image = Image.open(io.BytesIO(response.content))
                    image.thumbnail((140, 80))
                    ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(140, 80))
                except Exception:
                    pass

            self._log("Pencarian selesai ✅")
            self.after(0, self._on_fetch_success, info['title'], ctk_img, detail_text, quality_options)

        except Exception as e:
            self._log(str(e), "error")
            self.after(0, self._on_fetch_error, str(e))

    def _on_fetch_success(self, title, image, detail_text, quality_options):
        self.fetch_btn.configure(state="normal", text="Cari Video")
        self.home_status.configure(text="")

        self.dl_title.configure(text=title)
        self.dl_detail.configure(text=detail_text)
        
        # Re-enable radio buttons for single download
        self.radio_mp4.grid()
        self.radio_mp4.configure(state="normal")
        self.radio_mp3.grid()
        self.radio_mp3.configure(state="normal")

        # Re-enable thumbnail area for single download
        self.dl_thumb.grid()
        
        if image:
            self._thumb_image = image
            self.dl_thumb.configure(image=image, text="")
        else:
            self.dl_thumb.configure(image=None, text="🎬")

        self.quality_menu.configure(values=quality_options)
        
        # Try to restore saved quality if it exists in options, else use best
        saved_q = self.config.get("quality", "Terbaik")
        if saved_q in quality_options:
            self.quality_var.set(saved_q)
        else:
            self.quality_var.set(quality_options[0])
            
        self.format_var.set(self.config.get("format", "mp4"))
        self._show_quality(self.format_var.get() == "mp4")

        self.progress_frame.grid_remove()
        self.progress_bar.set(0)
        self.dl_status.configure(text="")
        self.download_btn.configure(state="normal")

        self._show_page("download")

    def _on_fetch_error(self, error_msg):
        self.fetch_btn.configure(state="normal", text="Cari Video")
        self.home_status.configure(text=f"Error: {error_msg}", text_color="#e74c3c")

    # ──────────────────────────────────────────────
    # DOWNLOAD
    # ──────────────────────────────────────────────
    def start_download(self):
        raw_text = self.url_entry.get("1.0", "end").strip()
        if not raw_text or self.is_downloading:
            return

        self.is_downloading = True
        self.is_cancelled = False
        self.download_btn.configure(state="disabled")
        self.back_btn.grid_remove()
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.grid()
            self.cancel_btn.configure(state="normal", text="❌  Batal")
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.grid_remove()
        self.progress_bar.set(0)
        self.progress_frame.grid()
        self.dl_status.configure(text="Memulai unduhan...", text_color="gray")

        fmt = self.format_var.get()
        quality = self.quality_var.get()

        os.makedirs(self.download_folder, exist_ok=True)

        if self.bulk_urls:
            self.bulk_progress = {}
            self._log(f"Memulai unduhan massal paralel: {len(self.bulk_urls)} video")
            threading.Thread(target=self._bulk_download_manager, daemon=True).start()
        else:
            url = raw_text
            self._log(f"Memulai unduhan: format={fmt}, kualitas={quality}")
            threading.Thread(target=self._download_thread, args=(url, fmt, quality), daemon=True).start()

    def _progress_hook(self, d):
        if getattr(self, "is_cancelled", False):
            raise Exception("USER_CANCEL")
            
        if d['status'] == 'downloading':
            percent_str = ANSI_RE.sub('', d.get('_percent_str', '0%').strip())
            speed = ANSI_RE.sub('', d.get('_speed_str', ''))
            eta = ANSI_RE.sub('', d.get('_eta_str', ''))

            try:
                percent_val = float(percent_str.replace('%', '')) / 100.0
            except ValueError:
                percent_val = 0.0

            msg = f"⬇ {percent_str}  •  {speed}  •  Sisa waktu {eta}"
            self.after(0, self._update_progress, percent_val, msg)

        elif d['status'] == 'finished':
            filename = os.path.basename(d.get('filename', ''))
            self._log(f"Selesai mengunduh: {filename}")
            self.after(0, self._update_progress, 1.0, "⏳ Memproses file...")

    def _update_progress(self, val, msg, count_msg=""):
        self.progress_bar.set(val)
        self.dl_status.configure(text=msg)
        if hasattr(self, "dl_count"):
            self.dl_count.configure(text=count_msg)

    def _bulk_progress_hook(self, d, idx, total):
        if getattr(self, "is_cancelled", False):
            raise Exception("USER_CANCEL")
            
        if d['status'] == 'downloading':
            percent_str = ANSI_RE.sub('', d.get('_percent_str', '0%').strip())
            
            try:
                percent_val = float(percent_str.replace('%', '')) / 100.0
            except ValueError:
                percent_val = 0.0
                
            # Update individual progress
            self.bulk_progress[idx] = percent_val
            
            # Calculate overall progress
            overall_progress = sum(self.bulk_progress.values()) / total
            finished_count = sum(1 for p in self.bulk_progress.values() if p >= 1.0)
            
            msg = "Sedang mengunduh..."
            count_msg = f"{finished_count}/{total} berhasil"
            self.after(0, self._update_progress, overall_progress, msg, count_msg)
            
        elif d['status'] == 'finished':
            self.bulk_progress[idx] = 1.0
            filename = os.path.basename(d.get('filename', ''))
            self._log(f"✅ Selesai: {filename}")
            
            overall_progress = sum(self.bulk_progress.values()) / total
            finished_count = sum(1 for p in self.bulk_progress.values() if p >= 1.0)
            
            msg = "Selesai memproses..." if finished_count == total else "Sedang mengunduh..."
            count_msg = f"{finished_count}/{total} berhasil"
            self.after(0, self._update_progress, overall_progress, msg, count_msg)

    def _bulk_download_manager(self):
        total = len(self.bulk_urls)
        self.after(0, self._update_progress, 0, f"⏳ Memulai {total} unduhan...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, url in enumerate(self.bulk_urls, 1):
                self.bulk_progress[idx] = 0.0
                futures.append(executor.submit(self._bulk_download_single, url, idx, total))
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self._log(f"Error tidak terduga pada unduhan: {e}", "error")

        if self.is_cancelled:
            self._cleanup_part_files()
            self.after(0, self._on_download_cancelled)
        elif self.is_downloading:
            self._log("Semua unduhan massal selesai ✅")
            self.after(0, self._on_download_complete)

    def _bulk_download_single(self, url, idx, total):
        if not self.is_downloading or getattr(self, "is_cancelled", False):
            return
            
        logger = YtLogger(self._log)
        self._log(f"[{idx}/{total}] Mulai: {url}")
        
        ydl_opts = {
            'outtmpl': os.path.join(self.download_folder, '%(title)s_%(id)s.%(ext)s'),
            'progress_hooks': [lambda d, i=idx, t=total: self._bulk_progress_hook(d, i, t)],
            'logger': logger,
            'ignoreerrors': True,
        }

        if getattr(self, "bulk_format_mode", "mp3") == "mp3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'},
            ]
        else:
            var = self.bulk_mp4_vars.get(url)
            chosen_q = var.get() if var else "Terbaik"
            if chosen_q.startswith('Terbaik') or chosen_q == "Terbaik":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                h = chosen_q.replace('p', '')
                ydl_opts['format'] = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'},
            ]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            if str(e) == "USER_CANCEL":
                self._log(f"[{idx}/{total}] Dibatalkan.", "warning")
            else:
                self._log(f"Error pada {url}: {e}", "error")

    def _download_thread(self, url, fmt, quality):
        logger = YtLogger(self._log)
        ydl_opts = {
            'outtmpl': os.path.join(self.download_folder, '%(title)s_%(id)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'logger': logger,
        }

        if fmt == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'},
            ]
            self._log("Format: MP3 (ekstraksi audio)")
        else:
            if quality.startswith('Terbaik'):
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                height = quality.replace('p', '')
                ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegMetadata'},
                {'key': 'EmbedThumbnail'},
            ]
            self._log(f"Format: MP4 ({quality})")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not self.is_cancelled:
                self._log("Unduhan selesai ✅")
                self.after(0, self._on_download_complete)
        except Exception as e:
            if str(e) == "USER_CANCEL":
                self._cleanup_part_files()
                self.after(0, self._on_download_cancelled)
            else:
                self._log(str(e), "error")
                self.after(0, self._on_download_error, str(e))

    def _on_download_complete(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.grid_remove()
        self.back_btn.grid()
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.grid()
        self.dl_status.configure(text="✅ Unduhan selesai! Silakan buka folder tujuan.", text_color=SUCCESS)
        if hasattr(self, "dl_count"):
            self.dl_count.configure(text="")
        self.progress_bar.set(1)

    def _on_download_error(self, err):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.grid_remove()
        self.back_btn.grid()
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.grid_remove()
        self.dl_status.configure(text=f"❌ {err}", text_color=DANGER)
        if hasattr(self, "dl_count"):
            self.dl_count.configure(text="")

    def _on_download_cancelled(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.grid_remove()
        self.back_btn.grid()
        if hasattr(self, "open_folder_btn"):
            self.open_folder_btn.grid_remove()
        self.dl_status.configure(text="⚠️ Unduhan dibatalkan pengguna.", text_color=WARNING_CLR)
        if hasattr(self, "dl_count"):
            self.dl_count.configure(text="")
        self.progress_bar.set(0)


if __name__ == "__main__":
    app = App()
    app.mainloop()
