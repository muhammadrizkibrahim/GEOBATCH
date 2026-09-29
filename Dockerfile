# Menggunakan base image Python yang ringan
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Buat config.toml internal mengarah ke 8501
RUN mkdir -p ~/.streamlit && \
    echo "\n\
[server]\n\
headless = true\n\
port = 8502\n\
address = \"0.0.0.0\"\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
maxUploadSize = 200\n\
" > ~/.streamlit/config.toml

# Expose port internal 8501
EXPOSE 8502

# Jalankan Streamlit internal di port 8501
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
