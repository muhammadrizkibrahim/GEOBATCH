FROM python:3.10-slim

WORKDIR /app

# WAJIB untuk OpenCV & EasyOCR (Jika tidak ada ini, aplikasi akan crash saat membaca gambar)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8502

# WAJIB tambahkan --server.port=8502 agar Streamlit benar-benar jalan di 8502
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
