# YT Downloader 🎥🎵

Aplikasi Desktop pengunduh YouTube yang simpel dan elegan, ditenagai oleh `yt-dlp` dan **CustomTkinter**.

## Fitur Utama ✨
- **Navigasi Multi-Halaman** — Alur yang intuitif: masukkan link → Fetch → pilih format & kualitas → Download → kembali untuk download lagi.
- **Deteksi Resolusi Otomatis** — Setelah Fetch, dropdown kualitas otomatis terisi resolusi yang tersedia dari video (360p, 480p, 720p, 1080p, dst.).
- **Thumbnail Preview** — Menampilkan gambar sampul video sebelum mengunduh.
- **Live Progress Bar** — Persentase, ukuran file (contoh: 15.0MiB), kecepatan download, dan ETA ditampilkan secara real-time.
- **In-App Log** — Dilengkapi dengan panel log di bagian bawah aplikasi untuk memantau proses (koneksi, pencarian, dan unduhan) secara transparan.
- **Pengecekan FFmpeg Otomatis** — Memperingatkan Anda di halaman depan jika ekstensi penting FFmpeg belum terinstal.
- **Dukungan Playlist & Unduh Massal** — Masukkan tautan *Playlist* atau banyak tautan video sekaligus (pisahkan dengan *Enter*) untuk mengunduhnya secara bersamaan (Mendukung paralel/konkurensi agar lebih cepat).
- **Unduh Video (MP4) Massal** — Pilih resolusi spesifik untuk *masing-masing video* dalam playlist sebelum mengunduh.
- **Unduh Audio (MP3)** — Otomatis mengekstrak audio dari video (membutuhkan FFmpeg).
- **Metadata & Cover Art** — Otomatis menanamkan metadata dan *Thumbnail* YouTube ke dalam file MP3 maupun MP4 hasil unduhan.
- **Lokasi Unduhan Fleksibel** — Bebas pilih folder tujuan penyimpanan Anda kapan saja.
- **Batalkan Kapan Saja** — Tombol **Batal (❌)** menghentikan unduhan secara instan. File sementara (`.part`) akan dibersihkan secara otomatis.
- **Premium Light UI (YouTube Style)** — Desain UI modern dan bersih yang menggunakan palet warna khas YouTube (aksen Merah).

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
1. **Pilih Folder** — Klik tombol "Ubah" di layar utama untuk mengatur direktori penyimpanan Anda.
2. **Halaman Home** — Tempel link YouTube (Video Tunggal atau *Playlist*) ke dalam kotak input.
   - *Single Download:* Masukkan 1 link, lalu klik **"Cari Video"**.
   - *Bulk/Playlist:* Masukkan link playlist atau banyak link sekaligus, klik **"Cari Video"**. Anda akan diarahkan ke layar pemilihan format massal (MP4 atau MP3).
3. **Halaman Download** — Pilih format, pilih kualitas (untuk MP4), lalu klik **"⬇ Mulai Unduh"**.
4. File otomatis tersimpan lengkap dengan sampul (*thumbnail*). Klik **"📂 Buka Folder"** untuk langsung melihat hasilnya.
5. Klik **"⟵ Unduh Lagi"** untuk kembali ke awal.

## Struktur Folder 📁
- `app.py` — Inti aplikasi (GUI + logika yt-dlp + threading).
- `config.json` — Menyimpan preferensi Anda (Folder, Tema, Kualitas terakhir). Dibuat secara otomatis.
- `requirements.txt` — Daftar dependensi Python.

## Catatan Tambahan 📝
- Jika muncul error saat Fetch, pastikan koneksi internet stabil dan URL YouTube valid (bukan video private).
- Jika muncul warning terkait JavaScript runtime, pastikan **Deno** sudah terinstal dan ada di PATH.
- Jika ada *Warning* FFmpeg di layar utama, segera instal FFmpeg sesuai instruksi di atas agar hasil unduhan bisa diproses dengan sempurna.
