import streamlit as st
from PIL import Image
import io
import zipfile
import re
import easyocr
import numpy as np
import datetime

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
    .footer {text-align: center; color: #6c757d; font-size: 14px; margin-top: 50px; border-top: 1px solid #dee2e6; padding-top: 20px;}
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Auto-Rename Peta Wilayah Kerja Statistik BPS")
st.markdown("<p style='text-align: center;'><b>Satuan Kerja BPS Provinsi Kepulauan Riau - Pengolahan Peta Wilayah Kerja Statistik</b></p>", unsafe_allow_html=True)
st.write("---")

# --- PANDUAN PENGGUNAAN ---
st.info("""
**📖 Panduan Penggunaan Sistem:**
1. **Atur Penamaan:** Tentukan teks tambahan sebelum dan sesudah ID peta. (Contoh: awalan `WS_` dan akhiran `_WSS` akan menghasilkan nama `WS_3674020013000700_WSS.jpg`).
2. **Unggah File:** Anda dapat mengunggah file satuan/banyak sekaligus (format **.JPG / .PNG**), ATAU mengunggah dalam bentuk borongan (format **.ZIP**). Keduanya bisa diunggah bersamaan.
3. **Proses:** Klik tombol **"Proses Rename File"**. Sistem akan otomatis memotong (crop) ujung kanan atas peta dan mendeteksi ID Wilkerstat yang berjumlah **tepat 16 digit**.
4. **Unduh:** Setelah pemrosesan selesai, semua peta yang berhasil di-rename akan dibungkus menjadi satu file `.zip` baru agar mudah diunduh ke komputer Anda.
""")

# --- INPUT USER ---
col1, col2 = st.columns(2)
with col1:
    prefix = st.text_input("Awalan Nama File (Prefix)", value="WS_", help="Contoh: WS_")
with col2:
    suffix = st.text_input("Akhiran Nama File (Suffix)", value="_WSS", help="Contoh: _WSS")

uploaded_files = st.file_uploader("Unggah File Peta (.JPG/.PNG) atau (.ZIP)", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True)


# --- FUNGSI PEMROSESAN GAMBAR ---
def process_image(image_bytes, original_filename, count_index, zip_out, prefix_text, suffix_text):
    try:
        # Buka gambar dari memori
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        # LOGIKA CROP: 30% lebar kanan, 5% tinggi atas
        left = width * 0.70
        top = 0
        right = width
        bottom = height * 0.05
        
        cropped_image = image.crop((left, top, right, bottom))
        cropped_np = np.array(cropped_image)
        
        # Deteksi OCR
        result = reader.readtext(cropped_np, detail=0)
        extracted_text = " ".join(result)
        
        # Ekstrak semua angka dan filter WAJIB 16 DIGIT
        all_numbers = re.findall(r'\d+', extracted_text)
        valid_numbers = [num for num in all_numbers if len(num) == 16]
        
        if valid_numbers:
            map_id = valid_numbers[0]
        else:
            map_id = f"ID_TIDAK_DITEMUKAN_{count_index}"
        
        # Susun nama baru
        file_extension = original_filename.split('.')[-1]
        new_filename = f"{prefix_text}{map_id}{suffix_text}.{file_extension}"
        
        # Simpan ke ZIP Output
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format)
        zip_out.writestr(new_filename, img_byte_arr.getvalue())
        
    except Exception as e:
        st.error(f"❌ Gagal memproses {original_filename}: {e}")


# --- PROSES UTAMA ---
if st.button("Proses Rename File"):
    if not uploaded_files:
        st.warning("⚠️ Silakan unggah minimal satu file terlebih dahulu.")
    else:
        zip_output_buffer = io.BytesIO()
        processed_count = 0
        
        with st.spinner('Memproses file, mendeteksi ID (16 digit), dan mengemas ulang...'):
            with zipfile.ZipFile(zip_output_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_out:
                
                for uploaded_file in uploaded_files:
                    
                    if uploaded_file.name.lower().endswith('.zip'):
                        with zipfile.ZipFile(uploaded_file, 'r') as zip_in:
                            file_list = zip_in.namelist()
                            
                            valid_images = [
                                f for f in file_list 
                                if not f.startswith('__MACOSX/') 
                                and not f.endswith('.DS_Store') 
                                and not f.endswith('/') 
                                and f.lower().endswith(('.jpg', '.jpeg', '.png'))
                            ]
                            
                            for filename in valid_images:
                                img_bytes = zip_in.read(filename)
                                processed_count += 1
                                process_image(img_bytes, filename, processed_count, zip_out, prefix, suffix)
                                
                    else:
                        img_bytes = uploaded_file.read()
                        processed_count += 1
                        process_image(img_bytes, uploaded_file.name, processed_count, zip_out, prefix, suffix)
                        
        if processed_count > 0:
            st.success(f"✅ Berhasil memproses {processed_count} peta! Silakan unduh hasilnya.")
            
            st.download_button(
                label="⬇️ Unduh File ZIP Hasil Rename",
                data=zip_output_buffer.getvalue(),
                file_name="Peta_SE2026_Renamed.zip",
                mime="application/zip"
            )
        else:
            st.error("❌ Tidak ada file gambar yang valid untuk diproses.")

# --- FOOTER COPYRIGHT ---
current_year = datetime.datetime.now().year
st.markdown(
    f"""
    <div class="footer">
        &copy; {current_year} Hak Cipta Tim Metodologi BPS Provinsi Kepulauan Riau<br>
        <small>Dikembangkan untuk Pengolahan Kerangka Wilayah Kerja Statistik</small>
    </div>
    """, 
    unsafe_allow_html=True
)