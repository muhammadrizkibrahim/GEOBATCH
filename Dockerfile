# Menggunakan base image Python yang ringan
FROM python:3.10-slim

# Mencegah Python menulis file .pyc ke disk dan mem-buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Mengatur direktori kerja di dalam kontainer
WORKDIR /app

# Menginstal dependensi sistem dasar yang mungkin dibutuhkan pustaka C/C++
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Menyalin file requirements terlebih dahulu untuk memanfaatkan Docker cache
COPY requirements.txt .

# Menginstal dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh kode aplikasi ke dalam kontainer
COPY . .

# Membuat konfigurasi Streamlit untuk mode produksi dan batas unggahan (200MB)
RUN mkdir -p ~/.streamlit && \
    echo "\n\
[server]\n\
headless = true\n\
port = 8502\n\
enableCORS = false\n\
maxUploadSize = 200\n\
" > ~/.streamlit/config.toml

# Membuka port yang digunakan oleh Streamlit
EXPOSE 8502

# Perintah utama untuk menjalankan aplikasi (sesuaikan 'app.py' dengan nama file Anda)
CMD ["streamlit", "run", "app.py"]
