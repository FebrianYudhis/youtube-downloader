# YT Downloader 🎥🎵

Aplikasi Desktop pengunduh YouTube yang simpel dan elegan, ditenagai oleh `yt-dlp` dan **CustomTkinter**.

## Fitur Utama ✨
- **Navigasi Multi-Halaman** — Alur yang intuitif: masukkan link → Fetch → pilih format & kualitas → Download → kembali untuk download lagi.
- **Deteksi Resolusi Otomatis** — Setelah Fetch, dropdown kualitas otomatis terisi resolusi yang tersedia dari video (360p, 480p, 720p, 1080p, dst.).
- **Thumbnail Preview** — Menampilkan gambar sampul video sebelum mengunduh.
- **Live Progress Bar** — Persentase dan kecepatan download ditampilkan secara real-time tanpa membuat aplikasi macet (menggunakan background threading).
- **In-App Log** — Dilengkapi dengan panel log di bagian bawah aplikasi untuk memantau proses (koneksi, pencarian, dan unduhan) secara transparan.
- **Unduh Video (MP4)** — Pilih kualitas spesifik atau pilih "Terbaik" untuk kualitas tertinggi.
- **Unduh Audio (MP3)** — Otomatis mengekstrak audio dari video (membutuhkan FFmpeg).
- **Dark Mode** — Tema gelap bawaan yang nyaman di mata.

## Persyaratan Sistem (Prerequisites) 🛠️

### 1. Python 3.8+
Disarankan Python 3.10 ke atas. Download: [python.org](https://www.python.org/downloads/)

### 2. Deno (JavaScript Runtime) — Wajib
Versi terbaru `yt-dlp` membutuhkan JavaScript runtime untuk mengekstrak data dari YouTube. **Deno** adalah runtime yang direkomendasikan secara default oleh `yt-dlp`.

**Cara instal:**
- **Windows** (PowerShell):
  ```powershell
  irm https://deno.land/install.ps1 | iex
  ```
- **Linux/Mac:**
  ```bash
  curl -fsSL https://deno.land/install.sh | sh
  ```

> ⚠️ Setelah instalasi, pastikan folder Deno (`~/.deno/bin`) sudah ditambahkan ke **PATH** sistem operasi Anda, lalu **restart terminal**.

### 3. FFmpeg — Wajib
Digunakan oleh `yt-dlp` untuk:
- Menggabungkan (*merge*) video dan audio pada resolusi 720p ke atas (karena YouTube memisahkan track-nya).
- Mengonversi/mengekstrak audio ke format MP3.

**Cara instal:**
- **Windows:** `winget install ffmpeg` atau unduh dari [ffmpeg.org](https://ffmpeg.org/download.html) lalu tambahkan ke PATH.
- **Linux:** `sudo apt install ffmpeg`
- **Mac:** `brew install ffmpeg`

## Cara Instalasi & Menjalankan Aplikasi 🚀

1. Buka terminal di folder proyek ini.
2. Buat *Virtual Environment*:
   ```bash
   python -m venv venv
   ```
3. Aktifkan *Virtual Environment*:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instal dependensi:
   ```bash
   pip install -r requirements.txt
   ```
5. Jalankan aplikasi:
   ```bash
   python app.py
   ```

## Cara Penggunaan 📖
1. **Halaman Home** — Tempel link YouTube, klik **"Cari Video"**.
2. **Halaman Download** — Pilih format (MP4/MP3), pilih kualitas, klik **"Mulai Unduh"**.
3. File tersimpan di folder `downloads/`.
4. Klik **"⟵ Unduh Lagi"** untuk kembali dan mengunduh video lain.

## Struktur Folder 📁
- `app.py` — Inti aplikasi (GUI + logika yt-dlp).
- `requirements.txt` — Daftar dependensi Python.
- `downloads/` — Folder tempat file hasil unduhan tersimpan.

## Catatan Tambahan 📝
- Jika muncul error saat Fetch, pastikan koneksi internet stabil dan URL YouTube valid (bukan video private).
- Jika muncul warning terkait JavaScript runtime, pastikan **Deno** sudah terinstal dan ada di PATH.
- Untuk mengubah tema, edit `ctk.set_appearance_mode()` di bagian atas `app.py` (`"Dark"`, `"Light"`, atau `"System"`).
