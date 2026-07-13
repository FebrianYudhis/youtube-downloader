import customtkinter as ctk
import yt_dlp
import threading
import requests
from PIL import Image
import os
import io
import re
from datetime import datetime

# Setup theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Constants
APP_WIDTH = 550
APP_HEIGHT = 600
ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


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

        self.current_info = None
        self.is_downloading = False
        self._thumb_image = None

        # ── Top: Page container ──
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=(20, 5))

        # ── Bottom: Shared Log Panel (always visible) ──
        log_wrapper = ctk.CTkFrame(self, corner_radius=10)
        log_wrapper.pack(fill="x", padx=20, pady=(0, 20))
        log_wrapper.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_wrapper, fg_color="transparent")
        log_header.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(log_header, text="📋 Log", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        log_title.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(log_header, text="Bersihkan", width=50, height=22, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=1, border_color="gray", hover_color=("gray80", "gray30"), command=self._clear_log)
        clear_btn.grid(row=0, column=1)

        self.log_box = ctk.CTkTextbox(log_wrapper, height=130, font=ctk.CTkFont(family="Consolas", size=11), fg_color=("gray90", "#1a1a2e"), text_color=("gray30", "#8892b0"), corner_radius=6, activate_scrollbars=True)
        self.log_box.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.log_box.configure(state="disabled")

        # Tag colors
        self.log_box.tag_config("warning", foreground="#f39c12")
        self.log_box.tag_config("error", foreground="#e74c3c")
        self.log_box.tag_config("info", foreground="#8892b0")
        self.log_box.tag_config("debug", foreground="#636e88")

        # Create pages
        self.pages = {}
        self._create_page_home()
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
    # PAGE: HOME
    # ──────────────────────────────────────────────
    def _create_page_home(self):
        page = ctk.CTkFrame(self.container, corner_radius=15)
        self.pages["home"] = page

        page.grid_columnconfigure(0, weight=1)

        # Icon / Branding
        icon_label = ctk.CTkLabel(page, text="🎬", font=ctk.CTkFont(size=48))
        icon_label.grid(row=0, column=0, pady=(40, 5))

        title = ctk.CTkLabel(page, text="YT Downloader", font=ctk.CTkFont(size=28, weight="bold"))
        title.grid(row=1, column=0, pady=(0, 5))

        subtitle = ctk.CTkLabel(page, text="Unduh video & audio dari YouTube", font=ctk.CTkFont(size=13), text_color="gray")
        subtitle.grid(row=2, column=0, pady=(0, 25))

        # URL Input
        self.url_entry = ctk.CTkEntry(page, placeholder_text="Tempel tautan YouTube di sini...", height=45, font=ctk.CTkFont(size=14))
        self.url_entry.grid(row=3, column=0, padx=35, sticky="ew")

        # Fetch Button
        self.fetch_btn = ctk.CTkButton(page, text="Cari Video", height=45, font=ctk.CTkFont(size=14, weight="bold"), command=self.fetch_video)
        self.fetch_btn.grid(row=4, column=0, padx=35, pady=(15, 10), sticky="ew")

        # Status
        self.home_status = ctk.CTkLabel(page, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.home_status.grid(row=5, column=0, padx=35, pady=(0, 30))

    # ──────────────────────────────────────────────
    # PAGE: DOWNLOAD
    # ──────────────────────────────────────────────
    def _create_page_download(self):
        page = ctk.CTkFrame(self.container, corner_radius=15)
        self.pages["download"] = page

        page.grid_columnconfigure(0, weight=1)

        # ── Video Info Card ──
        self.info_card = ctk.CTkFrame(page, corner_radius=10)
        self.info_card.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        self.info_card.grid_columnconfigure(1, weight=1)

        self.dl_thumb = ctk.CTkLabel(self.info_card, text="")
        self.dl_thumb.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=12)

        self.dl_title = ctk.CTkLabel(self.info_card, text="", font=ctk.CTkFont(size=13, weight="bold"), wraplength=280, anchor="w", justify="left")
        self.dl_title.grid(row=0, column=1, padx=(0, 15), pady=(12, 2), sticky="nw")

        self.dl_detail = ctk.CTkLabel(self.info_card, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.dl_detail.grid(row=1, column=1, padx=(0, 15), pady=(0, 12), sticky="nw")

        # ── Format + Quality Row ──
        options_frame = ctk.CTkFrame(page, fg_color="transparent")
        options_frame.grid(row=1, column=0, pady=(5, 0))

        self.format_var = ctk.StringVar(value="mp4")

        self.radio_mp4 = ctk.CTkRadioButton(options_frame, text="MP4", variable=self.format_var, value="mp4", command=self._on_format_change, font=ctk.CTkFont(size=13))
        self.radio_mp4.grid(row=0, column=0, padx=(0, 10))

        self.radio_mp3 = ctk.CTkRadioButton(options_frame, text="MP3", variable=self.format_var, value="mp3", command=self._on_format_change, font=ctk.CTkFont(size=13))
        self.radio_mp3.grid(row=0, column=1, padx=(0, 15))

        self.quality_label = ctk.CTkLabel(options_frame, text="Kualitas:", font=ctk.CTkFont(size=13))
        self.quality_label.grid(row=0, column=2, padx=(10, 5))

        self.quality_var = ctk.StringVar(value="Terbaik")
        self.quality_menu = ctk.CTkOptionMenu(options_frame, variable=self.quality_var, values=["Terbaik"], width=150, font=ctk.CTkFont(size=12))
        self.quality_menu.grid(row=0, column=3)

        self._quality_widgets = [self.quality_label, self.quality_menu]

        # ── Download Button ──
        self.download_btn = ctk.CTkButton(page, text="⬇  Mulai Unduh", height=42, font=ctk.CTkFont(size=14, weight="bold"), command=self.start_download)
        self.download_btn.grid(row=2, column=0, padx=25, pady=(12, 5), sticky="ew")

        # ── Progress Section ──
        self.progress_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, padx=25, pady=(3, 3), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.dl_status = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.dl_status.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, pady=(3, 0), sticky="ew")
        self.progress_bar.set(0)
        self.progress_frame.grid_remove()

        # ── Back Button ──
        self.back_btn = ctk.CTkButton(page, text="⟵  Unduh Lagi", height=38, font=ctk.CTkFont(size=13), fg_color="transparent", border_width=1, border_color="gray", hover_color=("gray80", "gray30"), command=self._go_home)
        self.back_btn.grid(row=4, column=0, padx=25, pady=(5, 20), sticky="ew")

    # ──────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────
    def _show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def _go_home(self):
        self.url_entry.delete(0, "end")
        self.home_status.configure(text="")
        self.format_var.set("mp4")
        self._show_quality(True)
        self.progress_frame.grid_remove()
        self.progress_bar.set(0)
        self.dl_status.configure(text="")
        self.download_btn.configure(state="normal")
        self._show_page("home")

    # ──────────────────────────────────────────────
    # FORMAT CHANGE
    # ──────────────────────────────────────────────
    def _on_format_change(self):
        self._show_quality(self.format_var.get() == "mp4")

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
        url = self.url_entry.get().strip()
        if not url:
            self.home_status.configure(text="Silakan masukkan URL YouTube", text_color="#e74c3c")
            return

        self.fetch_btn.configure(state="disabled", text="Mencari...")
        self.home_status.configure(text="Mencari info video...", text_color="gray")

        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

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
                quality_options.insert(0, f"Terbaik ({quality_options[0]})")
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
        if image:
            self._thumb_image = image
            self.dl_thumb.configure(image=image, text="")
        else:
            self.dl_thumb.configure(image=None, text="🎬")

        self.quality_menu.configure(values=quality_options)
        self.quality_var.set(quality_options[0])
        self.format_var.set("mp4")
        self._show_quality(True)

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
        url = self.url_entry.get().strip()
        if not url or self.is_downloading:
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_frame.grid()
        self.dl_status.configure(text="Memulai unduhan...", text_color="gray")

        fmt = self.format_var.get()
        quality = self.quality_var.get()

        os.makedirs("downloads", exist_ok=True)

        self._log(f"Memulai unduhan: format={fmt}, kualitas={quality}")
        threading.Thread(target=self._download_thread, args=(url, fmt, quality), daemon=True).start()

    def _progress_hook(self, d):
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

    def _update_progress(self, val, msg):
        self.progress_bar.set(val)
        self.dl_status.configure(text=msg)

    def _download_thread(self, url, fmt, quality):
        logger = YtLogger(self._log)
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
            'progress_hooks': [self._progress_hook],
            'logger': logger,
        }

        if fmt == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            self._log("Format: MP3 (ekstraksi audio)")
        else:
            if quality.startswith('Terbaik'):
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                height = quality.replace('p', '')
                ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            self._log(f"Format: MP4 ({quality})")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._log("Unduhan selesai ✅")
            self.after(0, self._on_download_complete)
        except Exception as e:
            self._log(str(e), "error")
            self.after(0, self._on_download_error, str(e))

    def _on_download_complete(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.back_btn.configure(state="normal")
        self.dl_status.configure(text="✅ Unduhan selesai! Cek folder 'downloads'.", text_color="#2ecc71")
        self.progress_bar.set(1)

    def _on_download_error(self, err):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.back_btn.configure(state="normal")
        self.dl_status.configure(text=f"❌ {err}", text_color="#e74c3c")


if __name__ == "__main__":
    app = App()
    app.mainloop()
