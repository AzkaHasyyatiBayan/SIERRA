# SIERRA: Sistem Intervensi Ergonomi Real-Time & Risiko Aktivitas

Sistem intervensi ergonomi real-time berbasis **MediaPipe**, **Fuzzy Logic (Mamdani)**, dan **PyQt5 Desktop Overlay Non-Intrusif** yang dirancang khusus untuk kenyamanan dan kesehatan aktivitas gaming di lingkungan Windows.

## Fitur Utama Sistem

### 1. Inti Deteksi & Logika Keputusan
* **Real-Time Pose Tracking**: Ekstraksi 33 titik landmark kerangka tubuh menggunakan Google MediaPipe Pose via webcam (30 FPS, CPU-only).
* **Fuzzy Risk Scoring (Mamdani FIS)**: Mesin kecerdasan berbasis 9 aturan kausal inferensi fuzzy yang memetakan sudut kemiringan leher, sudut deviasi bahu, dan durasi ke dalam tingkat risiko kontinu (0–100):
  - **Aman** (0 – 30)
  - **Waspada** (31 – 65)
  - **Bahaya** (66 – 100)
* **Personalized Baseline Calibration**: Kalibrasi awal selama 10 detik untuk mempelajari postur ideal spesifik pengguna (menyesuaikan tinggi kursi, bentuk tubuh, dan sudut webcam).

### 2. Antarmuka & Intervensi Visual Non-Intrusif
* **Stealth & Click-Through Overlay**: Jendela layar penuh transparan (*always on top*) berbasis PyQt5 dan Windows Win32 API (`WS_EX_TRANSPARENT | WS_EX_LAYERED`), sehingga kursor mouse gamer tetap 100% bebas menembus overlay tanpa terhalang.
* **Adaptive Radial Edge Dimming**: Intervensi visual implisit berupa layar yang meredup halus di bagian sudut/tepi monitor (*vignette fade-in/fade-out*) saat posisi bahaya terdeteksi, memicu refleks perbaikan postur bawah sadar tanpa merusak konsentrasi gaming.
* **Customizable Intervention**: Pengaturan opasitas maksimal dan pilihan palet warna peredupan (*Dark Midnight*, *Stealth Charcoal*, *Crimson Vignette*).

### 3. Keamanan Privasi & Performa Komputasi
* **Ephemeral Frame Dropper**: Frame visual mentah dari webcam segera dihapus dari RAM komputer begitu koordinat landmark diperoleh. Tidak ada video yang direkam, disimpan ke disk, atau dikirim ke internet (**100% Privacy by Design**).
* **Client-Side CPU Optimization**: Model inference berjalan secara lokal dan ringan pada CPU (<3-5% CPU usage) tanpa membebani GPU game.
* **Game-Mode Auto Detect**: Mendeteksi jendela layar penuh atau game kelas AAA yang sedang aktif, lalu otomatis menyesuaikan alokasi thread pelacakan.

### 4. Pelaporan & Analitik Lokal
* **Local Session Analytics**: Penyimpanan lokal berbasis **SQLite** (`sierra.db`) mencatat riwayat durasi postur Aman, Waspada, dan Bahaya, serta skor ergonomi setiap sesi bermain.

### 5. Komponen Interaktif & Animatif
* **Minimalist Wireframe Avatar**: Visualisasi kerangka leher & bahu mini dengan interpolasi gerakan 60 FPS dan pewarnaan dinamis.
* **Circular Risk Gauge**: Indikator meteran melingkar modern dengan animasi *sweep arc* dan skor risiko real-time.

---

## Cara Menjalankan Sistem

### 1. Prasyarat Lingkungan
* Python 3.10 – 3.13 (64-bit)
* Sistem Operasi: Windows 10 / 11

### 2. Instalasi Dependensi
Jalankan perintah berikut di terminal:
```bash
pip install -r requirements.txt
```

### 3. Menjalankan Aplikasi
```bash
python main.py
```

### 4. Menjalankan Pengujian Otomatis (Unit Tests)
```bash
python -m unittest discover tests
``