import streamlit as st
from PIL import Image
import io
import zipfile
import re
import easyocr
import numpy as np
import datetime
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile
import json
import cv2
import numpy as np
import torch

torch.set_num_threads(4)
torch.set_num_interop_threads(2)


# --- Inisialisasi AI Reader (EasyOCR) ---
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)
# def load_reader():
#     return easyocr.Reader(['en'])

reader = load_reader()

# --- TEMA & UI SENSUS EKONOMI 2026 ---
st.set_page_config(page_title="Auto-Rename & Georef Peta SE2026", page_icon="🗺️", layout="wide")

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

st.title("🗺️ GeoBatch - Aplikasi Penamaan dan Georeferensi Otomatis")
st.markdown("<p style='text-align: center;'><b>Pengolahan Peta Wilayah Kerja Statistik - Lingkungan BPS Provinsi Kepulauan Riau</b></p>", unsafe_allow_html=True)

st.info("""
**GeoBatch** adalah aplikasi berbasis web efisien yang dirancang untuk mengotomatisasi pengolahan peta wilayah kerja statistik secara massal (*batch*). Aplikasi ini mengintegrasikan teknologi pembacaan teks otomatis (*OCR*) untuk proses *auto-rename* nama file peta, serta fitur georeferensi cerdas yang mengubah peta raster menjadi format spasial standar (**GeoTIFF**) secara instan menggunakan acuan poligon **GeoJSON**—tanpa memotong elemen visual peta asli.
""")
st.write("---")

# ==========================================
# FUNGSI-FUNGSI HELPER (GLOBAL SCOPE)
# ==========================================

def extract_map_id(image_bytes):
    """Membaca gambar dan mengembalikan ID 16 digit beserta objek gambarnya."""
    image = Image.open(io.BytesIO(image_bytes))
    width, height = image.size
    
    # CROP: 30% Kanan, 5% Atas
    left = width * 0.70
    top = 0
    right = width
    bottom = height * 0.05
    
    cropped_image = image.crop((left, top, right, bottom))
    cropped_np = np.array(cropped_image)
    
    result = reader.readtext(cropped_np, detail=0)
    extracted_text = " ".join(result)
    
    all_numbers = re.findall(r'\d+', extracted_text)
    valid_numbers = [num for num in all_numbers if len(num) == 16]
    
    return (valid_numbers[0] if valid_numbers else None), image

def process_rename_image(img_bytes, original_filename, count_index, zip_out, prefix_text, suffix_text):
    """Fungsi khusus untuk mengeksekusi proses rename dan memasukkannya ke ZIP."""
    try:
        map_id, image = extract_map_id(img_bytes)
        if not map_id:
            map_id = f"ID_TIDAK_DITEMUKAN_{count_index}"
            
        file_ext = original_filename.split('.')[-1]
        new_filename = f"{prefix_text}{map_id}{suffix_text}.{file_ext}"
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format)
        zip_out.writestr(new_filename, img_byte_arr.getvalue())
        return True
    except Exception as e:
        st.error(f"❌ Gagal memproses {original_filename}: {e}")
        return False

def get_bbox_from_geometry(geometry):
    """Mengekstrak Bounding Box (xmin, ymin, xmax, ymax) dari koordinat GeoJSON."""
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    def extract_coords(coords):
        nonlocal min_x, min_y, max_x, max_y
        if isinstance(coords[0], (int, float)):
            x, y = coords[0], coords[1]
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y
        else:
            for sub_coords in coords:
                extract_coords(sub_coords)

    extract_coords(geometry.get('coordinates', []))
    return min_x, min_y, max_x, max_y

def find_neatline_rect(image_pil):
    """Mendeteksi bingkai hitam peta dan mengembalikan posisi pikselnya (x, y, w, h)."""
    img_np = np.array(image_pil)
    
    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
        
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    img_h, img_w = gray.shape
    img_area = img_h * img_w
    
    best_rect = None
    max_area = 0
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if (img_area * 0.3) < area < (img_area * 0.95):
            if area > max_area:
                max_area = area
                best_rect = (x, y, w, h)
                
    return best_rect    

def process_georef_image(img_bytes, original_filename, geojson_data, zip_out, pad_x, pad_y):
    """Georeferensi gambar penuh dengan ekstrapolasi koordinat berbasis neatline."""
    try:
        map_id, image = extract_map_id(img_bytes)
        
        if not map_id:
            st.error(f"❌ {original_filename}: ID Peta tidak terbaca.")
            return False
            
        clean_id = str(map_id).split('_')[0]
        
        target_feature = None
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            if str(props.get('idsubsls', '')) == clean_id:
                target_feature = feature
                break
                
        if not target_feature:
            st.error(f"❌ {original_filename}: ID '{clean_id}' tidak ditemukan di GeoJSON.")
            return False
        
        xmin, ymin, xmax, ymax = get_bbox_from_geometry(target_feature.get('geometry', {}))
        
        if xmin == float('inf') or ymin == float('inf'):
            st.error(f"❌ {original_filename}: Gagal membaca koordinat poligon.")
            return False

        # --- PENAMBAHAN PADDING POLIGON (Kalibrasi Area Dalam) ---
        geo_width = xmax - xmin
        geo_height = ymax - ymin
        
        adjusted_xmin = xmin - (geo_width * pad_x)
        adjusted_xmax = xmax + (geo_width * pad_x)
        adjusted_ymin = ymin - (geo_height * pad_y)
        adjusted_ymax = ymax + (geo_height * pad_y)

        # --- DETEKSI BINGKAI & EKSTRAPOLASI KOORDINAT ---
        img_w, img_h = image.size
        rect = find_neatline_rect(image)
        
        if rect is not None:
            nx, ny, nw, nh = rect
        else:
            # Fallback jika garis bingkai gagal dideteksi OpenCV
            if img_w > img_h:
                nx, ny = int(img_w * 0.02), int(img_h * 0.05)
                nw, nh = int(img_w * 0.73), int(img_h * 0.90)
            else:
                nx, ny = int(img_w * 0.02), int(img_h * 0.04)
                nw, nh = int(img_w * 0.71), int(img_h * 0.93)

        # Hitung resolusi 1 piksel dalam derajat geografis
        pixel_size_x = (adjusted_xmax - adjusted_xmin) / nw
        pixel_size_y = (adjusted_ymax - adjusted_ymin) / nh
        
        # Tarik batas spasial hingga menutupi piksel paling ujung gambar (termasuk legenda)
        full_xmin = adjusted_xmin - (nx * pixel_size_x)
        full_xmax = adjusted_xmax + ((img_w - (nx + nw)) * pixel_size_x)
        full_ymax = adjusted_ymax + (ny * pixel_size_y)
        full_ymin = adjusted_ymin - ((img_h - (ny + nh)) * pixel_size_y)

        # --- PROSES GAMBAR UTUH ---
        img_np = np.array(image)
        
        if img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]
            
        img_np = np.moveaxis(img_np, 2, 0)
        
        # Transformasi kini menggunakan batas luar penuh dan dimensi gambar asli
        transform = from_bounds(full_xmin, full_ymin, full_xmax, full_ymax, img_w, img_h)
        
        with MemoryFile() as memfile:
            with memfile.open(
                driver='GTiff',
                height=img_h,
                width=img_w,
                count=3,
                dtype=img_np.dtype,
                crs='EPSG:4326',
                transform=transform,
            ) as dataset:
                dataset.write(img_np)
            
            tiff_bytes = memfile.read()
        
        new_filename = f"{clean_id}_Georef.tif"
        zip_out.writestr(new_filename, tiff_bytes)
        
        del img_np
        del image
        
        return True
        
    except Exception as e:
        st.error(f"❌ Gagal memproses GeoTIFF {original_filename}: {e}")
        return False

# ==========================================
# TABS LAYOUT
# ==========================================
tab1, tab2 = st.tabs(["🔄 Tab 1: Auto-Rename Peta", "🌍 Tab 2: Georeferensi (GeoTIFF)"])

# --- TAB 1: AUTO RENAME ---
with tab1:
    st.info("""
    **📖 Panduan Rename:** 
    1. Unggah file peta (JPG/PNG/ZIP), atur Prefix/Suffix, lalu klik Proses. 
    2. Sistem akan mencari ID 16 Digit dan merename file tersebut.
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        prefix = st.text_input("Awalan Nama File (Opsional)", value="", key="pref_tab1")
    with col2:
        suffix = st.text_input("Akhiran Nama File (WSS, WS, WB, WA)", value="_WSS", key="suff_tab1")

    uploaded_files_t1 = st.file_uploader("Unggah File Peta (.JPG/.PNG) atau (.ZIP)", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True, key="up_t1")

    if st.button("Proses Rename File", key="btn_t1"):
        if not uploaded_files_t1:
            st.warning("⚠️ Silakan unggah minimal satu file terlebih dahulu.")
        else:
            zip_output_buffer = io.BytesIO()
            processed_count = 0
            
            with st.spinner('Memproses file, mendeteksi ID (16 digit), dan mengemas ulang...'):
                with zipfile.ZipFile(zip_output_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_out:
                    for up_file in uploaded_files_t1:
                        if up_file.name.lower().endswith('.zip'):
                            with zipfile.ZipFile(up_file, 'r') as zip_in:
                                valid_imgs = [f for f in zip_in.namelist() if not f.startswith('__MACOSX/') and f.lower().endswith(('.jpg', '.png'))]
                                for filename in valid_imgs:
                                    processed_count += 1
                                    process_rename_image(zip_in.read(filename), filename, processed_count, zip_out, prefix, suffix)
                        else:
                            processed_count += 1
                            process_rename_image(up_file.read(), up_file.name, processed_count, zip_out, prefix, suffix)
                            
            if processed_count > 0:
                st.success(f"✅ Berhasil merename {processed_count} peta!")
                st.download_button(label="⬇️ Unduh Peta Hasil Rename (ZIP)", data=zip_output_buffer.getvalue(), file_name="Peta_Renamed.zip", mime="application/zip")

# --- TAB 2: GEOREFERENSI ---
with tab2:
    st.info("""
    **📖 Panduan Georeferensi:** 
    1. Unggah file **Master Koordinat (GeoJSON)** yang memuat poligon batas blok wilayah.
    2. Unggah file peta (JPG/PNG/ZIP) yang **Sudah Di Rename** sesuai IDSUBSLS. Sistem akan membaca ID peta pada gambar, mencari batas koordinatnya di GeoJSON, lalu menghasilkan file spasial **GeoTIFF (.tif)**.
    """)
    
    master_geojson_file = st.file_uploader("1. Unggah Master Koordinat (.geojson)", type=["geojson", "json"], key="up_geojson")
    uploaded_files_t2 = st.file_uploader("2. Unggah File Peta (.JPG/.PNG) atau (.ZIP)", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True, key="up_t2")

    st.write("---")
    st.markdown("**Pengaturan Kalibrasi (Buffer Margin Peta)**")
    st.caption("Gunakan ini jika poligon meleset karena ada spasi antara area poligon dengan bingkai hitam peta.")
    col_pad1, col_pad2 = st.columns(2)
    with col_pad1:
        pad_x = st.number_input("Padding Sumbu X (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5) / 100.0
    with col_pad2:
        pad_y = st.number_input("Padding Sumbu Y (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5) / 100.0
    st.write("---")

    if st.button("Proses Georeferensi", key="btn_t2"):
        if not master_geojson_file or not uploaded_files_t2:
            st.warning("⚠️ Harap unggah file Master GeoJSON DAN file gambar peta.")
        else:
            try:
                # Muat struktur GeoJSON ke dalam memori Python
                geojson_data = json.load(master_geojson_file)
                
                if 'features' not in geojson_data:
                    st.error("Format GeoJSON tidak valid. Objek 'features' tidak ditemukan.")
                else:
                    zip_output_buffer = io.BytesIO()
                    success_count = 0
                    fail_count = 0
                    
                    with st.spinner('Mendeteksi ID, mencocokkan poligon spasial, dan men-generate GeoTIFF...'):
                        with zipfile.ZipFile(zip_output_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_out:
                            for up_file in uploaded_files_t2:
                                if up_file.name.lower().endswith('.zip'):
                                    with zipfile.ZipFile(up_file, 'r') as zip_in:
                                        valid_imgs = [f for f in zip_in.namelist() if not f.startswith('__MACOSX/') and f.lower().endswith(('.jpg', '.png'))]
                                        for filename in valid_imgs:
                                            # Teruskan geojson_data sebagai argumen pengganti df
                                            if process_georef_image(zip_in.read(filename), filename, geojson_data, zip_out, pad_x, pad_y):
                                                success_count += 1
                                            else:
                                                fail_count += 1
                                else:
                                    if process_georef_image(up_file.read(), up_file.name, geojson_data, zip_out, pad_x, pad_y):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                    
                    if success_count > 0:
                        st.success(f"✅ Selesai! Berhasil membuat {success_count} file GeoTIFF. (Gagal: {fail_count})")
                        st.download_button(label="⬇️ Unduh Peta Spasial (GeoTIFF ZIP)", data=zip_output_buffer.getvalue(), file_name="Peta_GeoTIFF.zip", mime="application/zip")
            
            except json.JSONDecodeError:
                st.error("Gagal membaca file GeoJSON. Pastikan file tidak korup dan berformat JSON yang valid.")
            except Exception as e:
                st.error(f"Terjadi kesalahan sistem: {e}")

# ==========================================
# FOOTER COPYRIGHT
# ==========================================
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
