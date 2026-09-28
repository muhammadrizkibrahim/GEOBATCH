import streamlit as st
from PIL import Image
import io
import zipfile
import re
import easyocr
import numpy as np

# --- Inisialisasi AI Reader (EasyOCR) ---
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

reader = load_reader()

# --- TEMA & UI SENSUS EKONOMI 2026 ---
st.set_page_config(page_title="Auto-Rename Peta SE2026", page_icon="🗺️", layout="centered")

st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1 {color: #0056b3; text-align: center; font-family: 'Arial', sans-serif;}
    .stButton>button {background-color: #fd7e14; color: white; border-radius: 5px; border: none; width: 100%; font-weight: bold;}
    .stButton>button:hover {background-color: #e86e04; color: white;}
    .stDownloadButton>button {background-color: #28a745; color: white; border-radius: 5px; width: 100%; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Auto-Rename Peta Sensus Ekonomi 2026")
st.markdown("<p style='text-align: center;'><b>Satuan Kerja BPS - Pengolahan Peta Wilayah Kerja Statistik</b></p>", unsafe_allow_html=True)
st.write("---")

# --- INPUT USER ---
col1, col2 = st.columns(2)
with col1:
    prefix = st.text_input("Awalan Nama File (Prefix)", value="WS_", help="Contoh: WS_")
with col2:
    suffix = st.text_input("Akhiran Nama File (Suffix)", value="_WSS", help="Contoh: _WSS")

uploaded_files = st.file_uploader("Unggah Gambar Peta (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# --- PROSES UTAMA ---
if st.button("Proses Rename File"):
    if not uploaded_files:
        st.warning("⚠️ Silakan unggah minimal satu file peta terlebih dahulu.")
    else:
        zip_buffer = io.BytesIO()
        
        with st.spinner('Sedang mendeteksi ID menggunakan AI dan merename file...'):
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                
                for index, uploaded_file in enumerate(uploaded_files):
                    try:
                        image = Image.open(uploaded_file)
                        width, height = image.size
                        
                        # LOGIKA CROP DIPERBAIKI: 
                        # Area dipersempit (Top 10%, Right 40%) agar lebih fokus ke kotak ID saja
                        left = width * 0.60
                        top = 0
                        right = width
                        bottom = height * 0.10
                        
                        cropped_image = image.crop((left, top, right, bottom))
                        cropped_np = np.array(cropped_image)
                        
                        # Ekstrak teks
                        result = reader.readtext(cropped_np, detail=0)
                        extracted_text = " ".join(result)
                        
                        # --- PERBAIKAN LOGIKA PENGAMBILAN ID ---
                        # Cari semua kelompok angka (Regex \d+ akan memisahkan angka jika ada spasi/huruf di antaranya)
                        all_numbers = re.findall(r'\d+', extracted_text)
                        
                        if all_numbers:
                            # Ambil kelompok angka yang memiliki digit paling banyak (ID peta = 14/16 digit)
                            # Ini akan otomatis membuang angka-angka koordinat tepi yang hanya 2-4 digit
                            map_id = max(all_numbers, key=len)
                            
                            # Validasi: Jika angka terpanjang masih di bawah 10 digit, berarti ID tidak terbaca sempurna
                            if len(map_id) < 10:
                                map_id = f"ID_TIDAK_VALID_{index+1}"
                        else:
                            map_id = f"ID_TIDAK_TERBACA_{index+1}"
                        
                        # Susun nama file baru
                        file_extension = uploaded_file.name.split('.')[-1]
                        new_filename = f"{prefix}{map_id}{suffix}.{file_extension}"
                        
                        # Simpan ke ZIP
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format)
                        zip_file.writestr(new_filename, img_byte_arr.getvalue())
                        
                    except Exception as e:
                        st.error(f"❌ Gagal memproses {uploaded_file.name}: {e}")
        
        st.success("✅ Proses Selesai! Silakan unduh hasilnya di bawah ini.")
        
        st.download_button(
            label="⬇️ Unduh File ZIP Hasil Rename",
            data=zip_buffer.getvalue(),
            file_name="Peta_SE2026_Renamed.zip",
            mime="application/zip"
        )