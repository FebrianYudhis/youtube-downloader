# Changelog

Semua perubahan yang signifikan pada proyek ini akan didokumentasikan di file ini.

## [1.3.0] - 2026-07-15

### ✨ Fitur Baru & Peningkatan
- **Pengecekan FFmpeg Otomatis**: Aplikasi kini mengecek ketersediaan `ffmpeg` di sistem saat pertama kali dibuka. Jika tidak ditemukan, peringatan krusial akan muncul di layar beranda untuk mencegah hasil video bisu atau error MP3.
- **Informasi Ukuran File**: *Progress bar* untuk unduhan tunggal (Single Download) kini menampilkan total estimasi ukuran file (contoh: "45.0% dari 15.0MiB").
- **Pemisahan Informasi Progress Massal**: Pada mode *Bulk Download*, status "Sedang mengunduh..." dan penghitung jumlah "x/y berhasil" kini dipisah agar lebih mudah dibaca.

### 💅 Perombakan Tema UI (YouTube Style)
- **Tema Terang Kustom (Light Theme)**: Merombak total palet warna aplikasi ke tema terang yang bersih dengan aksen "Merah YouTube" (#FF0000).
- Menghapus fitur *toggle Dark/Light Mode* untuk menjaga konsistensi tampilan premium yang lebih difokuskan pada satu tema utama.
- Menghapus elemen *top bar* (badge versi) agar tampilan lebih luas dan minimalis.

### 🐛 Perbaikan Bug (Bug Fixes)
- **Bug Pembatalan Antrean Massal**: Memperbaiki masalah kritis di mana mengklik "Batal" saat unduhan massal (*bulk*) hanya menghentikan unduhan aktif, sementara sisa tautan di dalam antrean *ThreadPoolExecutor* masih diam-diam memanggil `yt-dlp`. Kini, pembatalan akan instan memblokir seluruh sisa antrean.

## [1.2.0] - 2026-07-14

### ✨ Fitur Baru
- **Dukungan Playlist & MP4 Massal**: Mendukung unduhan seluruh video dari *Playlist* YouTube. Pengguna dapat memilih format massal antara MP3 atau MP4. Untuk MP4, pengguna dapat memilih kualitas/resolusi dari masing-masing video sebelum memulai unduhan.
- **Konkurensi Unduhan**: Unduhan massal kini berjalan secara paralel (*concurrent*) menggunakan *ThreadPoolExecutor* (maksimal 3 unduhan bersamaan), sehingga jauh lebih cepat.
- **Tombol Batal (Cancel)**: Menambahkan tombol pembatalan saat proses unduhan sedang berjalan, lengkap dengan sistem otomatis untuk menghapus file sampah/parsial (`.part`, `.ytdl`).
- **Metadata & Cover Art**: Unduhan format MP3 dan MP4 kini secara otomatis menanamkan metadata lagu/video serta menjadikan *thumbnail* YouTube sebagai gambar sampul (*cover art*) file.
- **Pilih Folder Unduhan**: Pengguna kini bebas memilih dan menentukan direktori/lokasi penyimpanan unduhan sesuai keinginan (tersimpan di `config.json`).
- **Toggle Tema**: Menambahkan sakelar untuk beralih antara *Dark Mode* 🌙 dan *Light Mode* ☀️.

### 💅 Peningkatan UI (UI/UX)
- Perombakan besar pada desain antarmuka (*UI Overhaul*) menjadi lebih premium, rapi, dan modern dengan menggunakan palet warna khusus, padding yang proporsional, dan *layouting* yang lebih responsif.
- Memperbaiki kontras teks dan warna latar belakang agar selalu terbaca jelas di kedua mode (gelap/terang).
- Menyederhanakan tampilan kartu saat mode unduhan massal (*bulk*) aktif.


## [1.1.0] - 2026-07-13

### ✨ Fitur Baru
- **Unduhan Massal (Bulk Download)**: Mendukung pengunduhan banyak tautan sekaligus (MP3). Pengguna kini dapat menekan tombol *Enter* untuk memasukkan banyak tautan YouTube di kotak input utama.

### 🐛 Perbaikan (Bug Fixes)
- **Opsi Kualitas Ganda**: Memperbaiki masalah di mana opsi resolusi terbaik muncul dua kali di dalam menu *dropdown* (contoh: "Terbaik (1080p)" dan "1080p" kini dilebur menjadi satu).

### ♻️ Perubahan (Changes)
- Mengganti komponen antarmuka input tautan dari satu baris (`CTkEntry`) menjadi multi-baris (`CTkTextbox`).
- Menyesuaikan *placeholder* dan judul untuk memperjelas dukungan *Bulk Download*.

## [1.0.0] - 2026-07-13

### 🎉 Rilis Pertama (Initial Release)
Versi 1.0.0 menandai peluncuran awal dari **YT Downloader Desktop Edition**, berpindah dari arsitektur berbasis web menjadi 100% murni Python.

### ✨ Fitur Utama
- **Antarmuka Pengguna (GUI)** — Dibangun sepenuhnya menggunakan `CustomTkinter` dengan desain *Dark Mode* yang elegan.
- **Navigasi Multi-Halaman** — Alur penggunaan yang mulus dari halaman "Home" (masukkan tautan) ke halaman "Download" (detail & eksekusi).
- **Integrasi `yt-dlp` & Deno** — Pengambilan data YouTube yang cepat dan andal.
- **Deteksi Resolusi Dinamis** — Secara otomatis membaca dan menampilkan daftar resolusi video yang tersedia (1080p, 720p, 480p, dll).
- **Opsi Unduhan Fleksibel**:
  - Unduh Video (MP4) dengan opsi kualitas "Terbaik" atau resolusi kustom.
  - Unduh Audio (MP3) dengan ekstraksi otomatis menggunakan FFmpeg.
- **Live Progress Bar** — Lacak status unduhan, persentase, kecepatan, dan sisa waktu (ETA) secara *real-time*.
- **In-App Log (Terminal Mini)** — Panel log bawaan yang tidak mereset saat berpindah halaman, berguna untuk memantau proses *fetch* dan *download* secara transparan.
- **Multi-Threading** — Proses *fetch* dan unduhan berjalan di *background thread* agar aplikasi tidak macet (*freeze*).
- **Dukungan Bahasa Indonesia** — Seluruh teks antarmuka dan log menggunakan Bahasa Indonesia.

### 🛠️ Ketergantungan (Dependencies)
- `customtkinter` (Antarmuka pengguna)
- `yt-dlp` (Mesin pengunduh)
- `Pillow` & `requests` (Pengelola gambar thumbnail)
- **Deno** (Dibutuhkan di sistem untuk *runtime* JavaScript yt-dlp)
- **FFmpeg** (Dibutuhkan di sistem untuk *merge* video/audio dan ekstraksi MP3)
