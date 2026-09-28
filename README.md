
# 🗺️ GeoBatch: Sistem Pengolahan Peta Sensus Ekonomi 2026

**GeoBatch** adalah aplikasi berbasis web efisien yang dirancang untuk mengotomatisasi pengolahan peta wilayah kerja statistik secara massal (*batch*). Aplikasi ini dikembangkan untuk lingkungan **Satuan Kerja BPS - Pengolahan Peta Wilayah Kerja Statistik (Tim Metodologi BPS Provinsi Kepulauan Riau)** untuk menunjang kegiatan Sensus Ekonomi 2026.

Aplikasi ini mengintegrasikan teknologi pembacaan teks otomatis (*OCR*) menggunakan **EasyOCR** untuk proses *auto-rename* nama file peta, serta fitur georeferensi cerdas berbasis **OpenCV** dan **Rasterio** yang mengubah peta raster menjadi format spasial standar (**GeoTIFF**) secara instan menggunakan acuan poligon **GeoJSON**—tanpa memotong elemen visual peta asli.

---

## 🌟 Fitur Utama

1. **🔄 Tab 1: Auto-Rename Peta Massal**

   - Mengunggah file peta secara satuan (`.jpg`, `.png`) maupun borongan dalam berkas archive (`.zip`).
   - Deteksi otomatis Wilkerstat ID 16 digit pada area header peta menggunakan Optical Character Recognition (EasyOCR).
   - Penamaan ulang file dinamis dengan kustomisasi **Prefix** (awalan) dan **Suffix** (akhiran).
   - Pengemasan otomatis hasil rename ke dalam format ZIP.
2. **🌍 Tab 2: Georeferensi Cerdas (GeoTIFF)**

   - Ekstraksi *bounding box* spasial dinamis dari Master Poligon **GeoJSON** (`idsubsls`).
   - Fitur **Ekstrapolasi Koordinat Berbasis Neatline (OpenCV)**: Mendeteksi bingkai hitam area kartografi utama untuk menghitung skala piksel presisi tanpa memotong margin, judul, atau legenda peta.
   - **Kalibrasi Buffer Margin/Padding**: Input interaktif (*slider/number input*) untuk penyesuaian spasi kanvas peta.
   - Ekspor langsung menjadi file raster spasial **GeoTIFF (EPSG:4326 / WGS 84)**.

---

## 🛠️ Stack Teknologi

- **Bahasa Pemrograman:** Python 3.10+
- **Antarmuka Web:** [Streamlit](https://streamlit.io/)
- **Pustaka OCR & Computer Vision:** [EasyOCR](https://github.com/JaidedAI/EasyOCR), [OpenCV (Headless)](https://opencv.org/)
- **Pemrosesan Spasial & Raster:** [Rasterio](https://rasterio.readthedocs.io/), [NumPy](https://numpy.org/)
- **Pengolahan Gambar & Data:** PIL (Pillow), Pandas
- **Containerization & Deployment:** Docker, Coolify

---

## 📁 Struktur Direktori Project

```text
geobatch/
├── app.py                     # Skrip utama aplikasi Streamlit
├── requirements.txt           # Daftar dependensi Python
├── Dockerfile                 # Konfigurasi containerization Docker
├── .dockerignore              # Exclude file lokal dari kontainer
└── README.md                  # Dokumentasi proyek
```
