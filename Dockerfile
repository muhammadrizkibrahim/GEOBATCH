# Menggunakan base image Python yang ringan
FROM python:3.10-slim

# Mencegah Python menulis file .pyc ke disk dan mem-buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Mengatur direktori kerja di dalam kontainer
WORKDIR /app

# Menginstal dependensi sistem dasar untuk OpenCV & C/C++
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

# Konfigurasi Streamlit Wajib untuk Coolify / Reverse Proxy
RUN mkdir -p ~/.streamlit && \
    echo "\n\
[server]\n\
headless = true\n\
port = 8501\n\
address = \"0.0.0.0\"\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
maxUploadSize = 200\n\
" > ~/.streamlit/config.toml

# Expose port internal kontainer
EXPOSE 8501

# Perintah utama untuk menjalankan aplikasi
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
