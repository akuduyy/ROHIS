import streamlit as st
import mysql.connector
import pandas as pd
import time 
import datetime 
import io
import tempfile
import os

# ---------------------------------------------------------
# 1. KONFIGURASI HALAMAN UTAMA & SUNTIKAN TEMA WARNA (ROHIS THEME)
# ---------------------------------------------------------
st.set_page_config(page_title="ROHIS-MATCH", page_icon="🕌", layout="wide")

st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #091310 !important; }
        [data-testid="stSidebar"] { background-color: #050a08 !important; border-right: 1px solid #12241f; }
        html, body, [class*="css"] { color: #f1f5f9 !important; }
        button[kind="primary"] { background-color: #10b981 !important; color: white !important; border: 1px solid #059669 !important; border-radius: 8px !important; font-weight: bold !important; transition: all 0.3s ease !important; min-height: 60px !important; }
        button[kind="primary"]:hover { background-color: #eab308 !important; color: #050a08 !important; border: 1px solid #ca8a04 !important; box-shadow: 0px 0px 10px rgba(234, 179, 8, 0.5) !important; }
        button[kind="secondary"] { background-color: #11221c !important; color: #10b981 !important; border: 1px solid #1b382e !important; border-radius: 8px !important; min-height: 60px !important; }
        button[kind="secondary"]:hover { background-color: #1b382e !important; color: #eab308 !important; border: 1px solid #eab308 !important; }
        div[data-baseweb="input"], div[data-baseweb="select"], .stSelectbox div { background-color: #0d1f19 !important; border: 1px solid #1b382e !important; color: white !important; }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within { border-color: #10b981 !important; }
        div[data-testid="stMetricValue"] { color: #eab308 !important; font-weight: bold !important; }
        div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
        div[data-testid="stSidebarUserContent"] label { color: #cbd5e1 !important; }
        th { background-color: #11221c !important; color: #10b981 !important; }
        button[data-baseweb="tab"] { color: #94a3b8 !important; }
        button[aria-selected="true"] { color: #10b981 !important; border-bottom-color: #10b981 !important; font-weight: bold !important; }
        div[data-testid="stNotification"] { background-color: #0d1f19 !important; border-left: 5px solid #10b981 !important; }
        span[data-testid="stMarkdownContainer"] strong { color: #eab308 !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. KONEKSI DATABASE AMAN (Anti-Lost Connection)
# ---------------------------------------------------------
def get_db_cursor():
    if 'db_conn' not in st.session_state or st.session_state['db_conn'] is None:
        st.session_state['db_conn'] = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["username"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            autocommit=True,
            use_pure=True
        )
    
    conn = st.session_state['db_conn']
    
    try:
        conn.ping(reconnect=True, attempts=3, delay=2)
    except Exception:
        st.session_state['db_conn'] = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["username"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            autocommit=True,
            use_pure=True
        )
        conn = st.session_state['db_conn']
        
    return conn, conn.cursor(dictionary=True)

# ---------------------------------------------------------
# 3. MANAJEMEN SESSION STATE & LOGGING SYSTEM
# ---------------------------------------------------------
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'menu_aktif' not in st.session_state: st.session_state['menu_aktif'] = "🏠 Dashboard"
if 'menu_pilihan_key' not in st.session_state: st.session_state['menu_pilihan_key'] = "🏠 Dashboard"
if 'login_attempts' not in st.session_state: st.session_state['login_attempts'] = 0
if 'lockout_until' not in st.session_state: st.session_state['lockout_until'] = 0

def catat_log(aksi):
    role_saat_ini = st.session_state['role'] if st.session_state['logged_in'] else 'anggota'
    waktu_sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn, cursor = get_db_cursor()
        query_log = "INSERT INTO log_aktivitas (waktu, role, aksi) VALUES (%s, %s, %s)"
        cursor.execute(query_log, (waktu_sekarang, role_saat_ini, aksi))
        conn.commit()
        cursor.close()
    except Exception:
        pass 

def proses_logout():
    catat_log("Keluar (logout) dari sistem")
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
    st.session_state['menu_aktif'] = "🏠 Dashboard" 
    st.session_state['menu_pilihan_key'] = "🏠 Dashboard" 
    st.rerun()

@st.dialog("⚠️ Konfirmasi Logout")
def dialog_konfirmasi_logout():
    st.write("Apakah Anda yakin ingin keluar dari sistem?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Keluar", type="primary", width="stretch"):
            proses_logout()
    with col2:
        if st.button("Batal", width="stretch"):
            st.rerun()

# ---------------------------------------------------------
# 4. HALAMAN LOGIN 
# ---------------------------------------------------------
def halaman_login():
    st.markdown("<h2 style='text-align: center; color: #10b981;'>Portal Login Admin/Pembina</h2>", unsafe_allow_html=True)
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("form_login"):
            st.subheader("👤 Silakan Login")
            input_user = st.text_input("Username")
            input_pass = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("Login", type="primary", width="stretch")
            
            if btn_login:
                if time.time() < st.session_state['lockout_until']:
                    sisa_waktu = int(st.session_state['lockout_until'] - time.time())
                    st.error(f"🛑 Akses ditolak! Terlalu banyak percobaan gagal. Silakan coba lagi dalam {sisa_waktu} detik.")
                    catat_log("Mencoba login saat masa penalti")
                else:
                    if not input_user or not input_pass:
                        st.warning("Username dan Password tidak boleh kosong!")
                    else:
                        conn, cursor = get_db_cursor()
                        query = "SELECT * FROM user WHERE username = %s AND password = %s"
                        cursor.execute(query, (input_user, input_pass))
                        user_data = cursor.fetchone()
                        cursor.close()
                        
                        if user_data:
                            st.session_state['login_attempts'] = 0
                            st.session_state['lockout_until'] = 0
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = user_data['username']
                            st.session_state['role'] = user_data['role']
                            st.session_state['menu_aktif'] = "🏠 Dashboard" 
                            st.session_state['menu_pilihan_key'] = "🏠 Dashboard" 
                            catat_log(f"Login berhasil menggunakan akun: {user_data['username']}")
                            st.success("Login berhasil! Memuat sistem...")
                            time.sleep(1) 
                            st.rerun()
                        else:
                            st.session_state['login_attempts'] += 1
                            catat_log(f"Gagal login (Percobaan ke-{st.session_state['login_attempts']} menggunakan username: {input_user})")
                            if st.session_state['login_attempts'] >= 3:
                                st.session_state['lockout_until'] = time.time() + 30 
                                st.error("⚠️ Sistem terkunci sementara dari indikasi Brute Force! Tunggu 30 detik.")
                            else:
                                st.error(f"Username atau Password salah! (Sisa kesempatan: {3 - st.session_state['login_attempts']})")

# ---------------------------------------------------------
# 5. FUNGSI PENGAMBILAN DATA STATISTIK
# ---------------------------------------------------------
def get_statistik():
    try:
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT COUNT(kd_siswa) AS total FROM siswa")
        total_siswa = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(id_divisi) AS total FROM divisi")
        total_divisi = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(id_kriteria) AS total FROM kriteria")
        total_kriteria = cursor.fetchone()['total']
        cursor.close()
        return total_siswa, total_divisi, total_kriteria
    except:
        return 0, 0, 0

# ---------------------------------------------------------
# 6. HALAMAN DASHBOARD
# ---------------------------------------------------------
def halaman_dashboard():
    st.title("🕌 Dashboard ROHIS-MATCH")
    
    if st.session_state['logged_in']:
        role_user = st.session_state['role'].lower()
        nama_user = st.session_state['username']
        if role_user == 'pembina':
            st.success(f"Selamat datang Pembina Rohis SMP Negeri 87 Jakarta, Bapak/Ibu {nama_user}!")
        elif role_user == 'pengurus':
            st.info(f"Selamat datang Pengurus Rohis SMP Negeri 87 Jakarta, Kak {nama_user}!")
    else:
        st.info("Selamat datang di Sistem Pendukung Keputusan Divisi Rohis SMPN 87 Jakarta.")
        st.write("Sistem ini digunakan untuk memetakan bakat dan minat siswa ke divisi yang tepat.")
        
    st.divider()
    st.subheader("📊 Ringkasan Data Saat Ini")
    col1, col2, col3 = st.columns(3)
    total_siswa, total_divisi, total_kriteria = get_statistik()
    
    with col1:
        st.metric(label="Total Anggota Terdaftar", value=f"{total_siswa} Siswa")
    with col2:
        st.metric(label="Total Divisi Tersedia", value=f"{total_divisi} Divisi")
    with col3:
        st.metric(label="Kriteria Penilaian", value=f"{total_kriteria} Kriteria")

    st.divider()
    st.subheader("📈 Analisis & Statistik Penempatan Divisi")
    
    conn, cursor = get_db_cursor()
    
    # -----------------------------------------------------------------
    # PERBAIKAN: FORMAT GROUP BY SESUAI PERMINTAAN EXACT ANDA
    # -----------------------------------------------------------------
    cursor.execute("""
        SELECT d.id_divisi,
               d.nama_divisi,
               COUNT(h.id_ranking) as jumlah
        FROM divisi d
        LEFT JOIN hasil_ranking h
               ON d.id_divisi = h.id_divisi
        GROUP BY d.id_divisi, d.nama_divisi
    """)
    data_sebaran = cursor.fetchall()
    
    cursor.execute("""
        SELECT s.kd_siswa, 
               s.nama_siswa, 
               GROUP_CONCAT(d.nama_divisi SEPARATOR ' / ') as nama_divisi, 
               h.skor_akhir
        FROM hasil_ranking h
        JOIN siswa s ON h.kd_siswa = s.kd_siswa
        JOIN divisi d ON h.id_divisi = d.id_divisi
        WHERE h.skor_akhir = (SELECT MAX(skor_akhir) FROM hasil_ranking)
        GROUP BY s.kd_siswa, s.nama_siswa, h.skor_akhir
        LIMIT 1
    """)
    top_siswa = cursor.fetchone()
    cursor.close()

    col_stat1, col_stat2 = st.columns([2, 1])
    
    with col_stat1:
        st.write("**Visualisasi Sebaran Anggota per Divisi**")
        if data_sebaran:
            df_sebaran = pd.DataFrame(data_sebaran)
            df_sebaran = df_sebaran.rename(columns={'nama_divisi': 'Divisi', 'jumlah': 'Jumlah Siswa'})
            df_sebaran = df_sebaran.set_index('Divisi')
            st.bar_chart(df_sebaran)
        else:
            st.info("Belum ada data penempatan divisi untuk divisualisasikan.")

    with col_stat2:
        st.write("**🏆 Peraih Skor Tertinggi (Top Ranking)**")
        if top_siswa:
            skor_persen = (float(top_siswa['skor_akhir']) / 5.0) * 100
            st.success(f"🎓 **{top_siswa['nama_siswa']}**")
            st.write(f"Rekomendasi: **{top_siswa['nama_divisi']}**")
            st.write(f"Skor Akhir: **{skor_persen:.2f}%**")
            st.caption("Nilai ini dikalkulasikan secara otomatis menggunakan metode Profile Matching.")
        else:
            st.warning("Belum ada data ranking yang tersimpan di database.")

# ---------------------------------------------------------
# 7. HALAMAN MANAJEMEN DATA SISWA (CRUD)
# ---------------------------------------------------------
def halaman_data_siswa():
    st.title("👥 Manajemen Data Anggota")
    st.write("Kelola data anggota Rohis yang akan diseleksi penempatan divisinya.")
    st.divider()

    list_pilihan_kelas = ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "8.1", "8.2", "8.3", "8.4", "8.5", "8.6"]

    st.subheader("📋 Daftar Anggota Terdaftar")
    conn, cursor = get_db_cursor()
    cursor.execute("SELECT kd_siswa, nama_siswa, kelas FROM siswa ORDER BY kd_siswa DESC")
    data_siswa = cursor.fetchall()
    cursor.close()
    
    if data_siswa:
        df_siswa = pd.DataFrame(data_siswa)
        df_siswa.columns = ['ID Siswa', 'Nama Lengkap', 'Kelas']
        st.dataframe(df_siswa, width="stretch", hide_index=True)
    else:
        st.info("Belum ada data anggota yang terdaftar di database.")
        df_siswa = pd.DataFrame() 
        
    st.divider()
    tab_tambah, tab_edit, tab_hapus = st.tabs(["➕ Tambah Data", "✏️ Edit Data", "🗑️ Hapus Data"])

    with tab_tambah:
        with st.form("form_tambah_siswa"):
            st.write("**Masukkan Data Anggota Baru**")
            input_nama = st.text_input("Nama Lengkap Siswa")
            input_kelas = st.selectbox("Kelas", list_pilihan_kelas) 
            btn_simpan = st.form_submit_button("Simpan ke Database", type="primary")
            if btn_simpan:
                if input_nama.strip() == "":
                    st.error("Validasi Gagal: Nama siswa tidak boleh kosong!")
                else:
                    try:
                        conn, cursor = get_db_cursor()
                        query_insert = "INSERT INTO siswa (nama_siswa, kelas) VALUES (%s, %s)"
                        cursor.execute(query_insert, (input_nama, input_kelas))
                        conn.commit() 
                        cursor.close()
                        catat_log(f"Menambahkan data siswa baru: {input_nama} ({input_kelas})")
                        st.success(f"Data {input_nama} berhasil ditambahkan!")
                        time.sleep(1)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Terjadi kesalahan: {e}")

    with tab_edit:
        if not df_siswa.empty:
            st.write("**Edit Data Anggota**")
            opsi_edit = df_siswa['ID Siswa'].astype(str) + " - " + df_siswa['Nama Lengkap']
            pilih_edit = st.selectbox("Pilih Anggota yang akan diedit:", opsi_edit)
            kd_edit = pilih_edit.split(" - ")[0]
            
            conn, cursor = get_db_cursor()
            cursor.execute("SELECT * FROM siswa WHERE kd_siswa = %s", (kd_edit,))
            data_lama = cursor.fetchone()
            cursor.close()
            
            with st.form("form_edit_siswa"):
                edit_nama = st.text_input("Nama Lengkap", value=data_lama['nama_siswa'])
                try:
                    idx_kelas = list_pilihan_kelas.index(data_lama['kelas'])
                except ValueError:
                    idx_kelas = 0
                edit_kelas = st.selectbox("Kelas", list_pilihan_kelas, index=idx_kelas)
                btn_update = st.form_submit_button("Update Data", type="primary")
                
                if btn_update:
                    if edit_nama.strip() == "":
                        st.error("Validasi Gagal: Nama siswa tidak boleh kosong!")
                    else:
                        conn, cursor = get_db_cursor()
                        query_update = "UPDATE siswa SET nama_siswa = %s, kelas = %s WHERE kd_siswa = %s"
                        cursor.execute(query_update, (edit_nama, edit_kelas, kd_edit))
                        conn.commit()
                        cursor.close()
                        catat_log(f"Mengubah data siswa ID {kd_edit} menjadi {edit_nama} ({edit_kelas})")
                        st.success("Data berhasil diperbarui!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.warning("Data kosong. Tidak ada data yang bisa diedit.")

    with tab_hapus:
        if not df_siswa.empty:
            st.write("**Hapus Data Anggota**")
            opsi_hapus = df_siswa['ID Siswa'].astype(str) + " - " + df_siswa['Nama Lengkap']
            pilih_hapus = st.selectbox("Pilih Anggota yang akan dihapus:", opsi_hapus)
            kd_hapus = pilih_hapus.split(" - ")[0]
            nama_dihapus = pilih_hapus.split(" - ")[1]
            
            with st.form("form_hapus_siswa"):
                st.error("⚠️ Peringatan: Data yang dihapus tidak dapat dikembalikan!")
                st.caption("Menghapus siswa ini juga akan menghapus seluruh riwayat nilainya secara otomatis.")
                btn_hapus = st.form_submit_button("Ya, Hapus Data Ini", type="primary")
                
                if btn_hapus:
                    conn, cursor = get_db_cursor()
                    query_delete = "DELETE FROM siswa WHERE kd_siswa = %s"
                    cursor.execute(query_delete, (kd_hapus,))
                    conn.commit()
                    cursor.close()
                    catat_log(f"Menghapus data siswa: {nama_dihapus}")
                    st.success("Data berhasil dihapus selamanya!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.warning("Data kosong. Tidak ada data yang bisa dihapus.")

# ---------------------------------------------------------
# 8. HALAMAN MANAJEMEN PROFIL (PENGATURAN)
# ---------------------------------------------------------
def halaman_profil():
    st.title("⚙️ Pengaturan Akun")
    st.write("Kelola informasi kredensial akun Anda untuk menjaga keamanan sistem.")
    st.divider()

    username_sekarang = st.session_state['username']
    conn, cursor = get_db_cursor()
    cursor.execute("SELECT * FROM user WHERE username = %s", (username_sekarang,))
    user_info = cursor.fetchone()
    cursor.close()

    if not user_info:
        st.error("Gagal memuat data akun dari database.")
        return

    tab_info, tab_user, tab_pass = st.tabs(["ℹ️ Informasi Akun", "✏️ Ubah Username", "🔒 Ubah Password"])

    with tab_info:
        st.subheader("📋 Detail Akun Saat Ini")
        st.write(f"**Username :** `{user_info['username']}`")
        st.write(f"**Hak Akses / Role :** `{user_info['role'].upper()}`")
        st.caption("Hak akses Anda menentukan batasan manipulasi data kriteria dan perhitungan algoritma SPK.")

    with tab_user:
        with st.form("form_ubah_username"):
            st.write("**Ganti Username Akun**")
            new_username = st.text_input("Username Baru", help="Gunakan nama yang mudah diingat")
            btn_username = st.form_submit_button("Perbarui Username", type="primary")

            if btn_username:
                if new_username.strip() == "":
                    st.error("Validasi Gagal: Username baru tidak boleh kosong!")
                elif new_username == username_sekarang:
                    st.warning("Username baru sama dengan username yang Anda gunakan saat ini.")
                else:
                    conn, cursor = get_db_cursor()
                    cursor.execute("SELECT * FROM user WHERE username = %s", (new_username,))
                    username_kembar = cursor.fetchone()
                    if username_kembar:
                        st.error("🛑 Gagal: Username tersebut sudah digunakan oleh akun lain. Silakan cari nama lain!")
                        cursor.close()
                    else:
                        try:
                            query_update_user = "UPDATE user SET username = %s WHERE username = %s"
                            cursor.execute(query_update_user, (new_username, username_sekarang))
                            conn.commit()
                            cursor.close()
                            catat_log(f"Mengubah username menjadi: {new_username}")
                            st.session_state['username'] = new_username
                            st.success("Username berhasil diubah") 
                            time.sleep(1) 
                            st.rerun()
                        except Exception as e:
                            st.error(f"Terjadi kesalahan database: {e}")

    with tab_pass:
        with st.form("form_ubah_password"):
            st.write("**Ganti Kata Sandi Akun**")
            old_password = st.text_input("Password Lama", type="password")
            new_password = st.text_input("Password Baru", type="password")
            confirm_password = st.text_input("Konfirmasi Password Baru", type="password")
            btn_password = st.form_submit_button("Perbarui Password", type="primary")

            if btn_password:
                if old_password != user_info['password']:
                    st.error("❌ Validasi Gagal: Password lama yang Anda masukkan salah!")
                elif new_password.strip() == "":
                    st.error("❌ Validasi Gagal: Password baru tidak boleh kosong!")
                elif new_password != confirm_password:
                    st.error("❌ Validasi Gagal: Konfirmasi password baru tidak cocok!")
                else:
                    try:
                        conn, cursor = get_db_cursor()
                        query_update_pass = "UPDATE user SET password = %s WHERE username = %s"
                        cursor.execute(query_update_pass, (new_password, username_sekarang))
                        conn.commit()
                        cursor.close()
                        catat_log("Mengubah kata sandi akun")
                        st.success("🔒 Password berhasil diperbarui secara aman!")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan database: {e}")

# ---------------------------------------------------------
# 9. HALAMAN INPUT PENILAIAN 
# ---------------------------------------------------------
def halaman_input_nilai():
    st.title("📝 Input Penilaian Aktual Siswa")
    st.write("Modul Core Engine: Menginput nilai tes siswa untuk diproses pada algoritma Profile Matching.")
    st.divider()

    conn, cursor = get_db_cursor()
    cursor.execute("SELECT kd_siswa, nama_siswa FROM siswa ORDER BY nama_siswa ASC")
    data_siswa = cursor.fetchall()
    
    cursor.execute("SELECT id_kriteria, nama_kriteria FROM kriteria")
    data_kriteria = cursor.fetchall()
    cursor.close()

    if not data_siswa or not data_kriteria:
        st.warning("⚠️ Data Master (Siswa atau Kriteria) belum lengkap. Silakan lengkapi di menu Data Anggota.")
        return

    st.subheader("Form Penilaian Aktual Siswa")
    opsi_siswa = {f"{s['kd_siswa']} - {s['nama_siswa']}": s['kd_siswa'] for s in data_siswa}
    pilih_siswa = st.selectbox("Pilih Siswa yang Dinilai:", list(opsi_siswa.keys()))
    kd_siswa_terpilih = opsi_siswa[pilih_siswa]

    pilihan_skala = [
        "1 - Sangat Kurang",
        "2 - Kurang",
        "3 - Cukup / Standar",
        "4 - Baik",
        "5 - Sangat Baik"
    ]

    with st.form("form_input_nilai"):
        nilai_inputan = {}
        col1, col2 = st.columns(2)
        
        for i, kriteria in enumerate(data_kriteria):
            with col1 if i % 2 == 0 else col2:
                nilai_inputan[kriteria['id_kriteria']] = st.selectbox(
                    f"Nilai {kriteria['nama_kriteria']}", 
                    options=pilihan_skala,
                    index=2, 
                    help="Pilih skala penilaian dari 1 hingga 5"
                )
        
        btn_simpan_nilai = st.form_submit_button("Simpan Nilai ke Database", type="primary")
        
        if btn_simpan_nilai:
            try:
                conn, cursor = get_db_cursor()
                cursor.execute("DELETE FROM nilai_siswa WHERE kd_siswa = %s", (kd_siswa_terpilih,))
                
                for id_k, nilai_akt_str in nilai_inputan.items():
                    nilai_angka = int(nilai_akt_str.split(" - ")[0])
                    
                    cursor.execute(
                        "INSERT INTO nilai_siswa (kd_siswa, id_kriteria, nilai_aktual) VALUES (%s, %s, %s)",
                        (kd_siswa_terpilih, id_k, nilai_angka)
                    )
                conn.commit()
                cursor.close()
                catat_log(f"Menginput/Update nilai tes untuk siswa ID: {kd_siswa_terpilih}")
                st.success("✅ Nilai aktual siswa berhasil disimpan ke database!")
            except Exception as e:
                st.error(f"Terjadi kesalahan saat menyimpan nilai: {e}")

# ---------------------------------------------------------
# 10. HALAMAN HASIL RANKING 
# ---------------------------------------------------------
def bobot_gap(gap):
    mapping = {
        0: 5.0, 1: 4.5, -1: 4.0, 2: 3.5, -2: 3.0,
        3: 2.5, -3: 2.0, 4: 1.5, -4: 1.0, 5: 0.5, -5: 0.0   
    }
    return mapping.get(gap, 0.0)

def halaman_hasil_spk():
    st.title("⭐ Hasil Ranking Profile Matching")
    st.divider()

    role_aktif = st.session_state['role'].lower() if st.session_state['logged_in'] else 'publik'

    def render_tabel_klasemen():
        target_divisi = {
            "Syiar": {"K1": 3, "K2": 3, "K3": 4, "K4": 3, "K5": 4},
            "Tilawah (Kesenian)": {"K1": 4, "K2": 4, "K3": 3, "K4": 3, "K5": 4},
            "Da'i (Kesenian)": {"K1": 3, "K2": 4, "K3": 4, "K4": 3, "K5": 4},
            "Seni/Kaligrafi": {"K1": 3, "K2": 3, "K3": 3, "K4": 4, "K5": 4},
            "PSDM": {"K1": 3, "K2": 3, "K3": 4, "K4": 4, "K5": 4},
            "Sosial": {"K1": 3, "K2": 3, "K3": 4, "K4": 3, "K5": 4},
            "Takmir Musholla": {"K1": 4, "K2": 4, "K3": 4, "K4": 3, "K5": 4},
            "CCI (Kesenian)": {"K1": 4, "K2": 4, "K3": 4, "K4": 4, "K5": 4},
            "Tahfidz (Kesenian)": {"K1": 4, "K2": 4, "K3": 3, "K4": 3, "K5": 4}
        }

        conn, cursor = get_db_cursor()
        cursor.execute("""
            SELECT h.kd_siswa, s.nama_siswa, s.kelas, h.skor_akhir, GROUP_CONCAT(d.nama_divisi SEPARATOR ' / ') as nama_divisi
            FROM hasil_ranking h
            JOIN siswa s ON h.kd_siswa = s.kd_siswa
            JOIN divisi d ON h.id_divisi = d.id_divisi
            GROUP BY h.kd_siswa, s.nama_siswa, s.kelas, h.skor_akhir
        """)
        hasil_db = cursor.fetchall()

        if not hasil_db:
            st.info("Belum ada data hasil perankingan yang disimpan di database.")
            cursor.close()
            return

        data_mentah = []
        for row in hasil_db:
            skor_float = float(row['skor_akhir'])
            persentase = (skor_float / 5.0) * 100
            
            kd_s = row['kd_siswa']
            div_name = row['nama_divisi'].split(" / ")[0] 
            
            cursor.execute("SELECT id_kriteria, nilai_aktual FROM nilai_siswa WHERE kd_siswa = %s", (kd_s,))
            marks = cursor.fetchall()
            
            ncf_nilai = 0.0
            if div_name in target_divisi and marks:
                nilai_aktual_dict = {f"K{m['id_kriteria']}": m['nilai_aktual'] for m in marks}
                if len(nilai_aktual_dict) == 5:
                    ncf_total, ncf_count = 0, 0
                    for k in ["K1", "K2", "K3", "K4", "K5"]:
                        t_val = target_divisi[div_name][k]
                        a_val = nilai_aktual_dict[k]
                        gap = a_val - t_val
                        bobot = bobot_gap(gap)
                        if t_val >= 4:
                            ncf_total += bobot
                            ncf_count += 1
                    ncf_nilai = ncf_total / ncf_count if ncf_count > 0 else 0.0
            
            data_mentah.append({
                "Nama Siswa": row['nama_siswa'],
                "Kelas": row['kelas'],
                "Total Nilai (CF)": ncf_nilai,
                "Skor (Persentase)": persentase,
                "Rekomendasi Utama": row['nama_divisi']
            })
            
        cursor.close()
        data_mentah.sort(key=lambda x: (x['Total Nilai (CF)'], x['Skor (Persentase)']), reverse=True)

        tab_individu, tab_keseluruhan = st.tabs(["👤 Cek Hasil Individu", "📊 Data Keseluruhan"])

        with tab_individu:
            st.subheader("🔍 Cek Hasil Rekomendasimu")
            st.write("Cari namamu di bawah ini untuk melihat detail rekomendasi penempatan divisi yang paling cocok dengan potensimu.")
            
            opsi_nama = [f"{d['Nama Siswa']} (Kelas {d['Kelas']})" for d in data_mentah]
            pilih_siswa = st.selectbox("Masukkan Nama Siswa:", opsi_nama, index=None, placeholder="Ketik atau pilih nama kamu...")
            
            if pilih_siswa:
                data_siswa = next(d for d in data_mentah if f"{d['Nama Siswa']} (Kelas {d['Kelas']})" == pilih_siswa)
                divisi_terbaik = data_siswa['Rekomendasi Utama'].split(" / ")[0] 
                
                st.success(f"🎉 **Selamat, {data_siswa['Nama Siswa']}!**")
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric(label="Rekomendasi Divisi Utama", value=divisi_terbaik)
                col_res2.metric(label="Tingkat Kecocokan Profil", value=f"{data_siswa['Skor (Persentase)']:.2f}%")
                col_res3.metric(label="Kekuatan Kompetensi Inti (CF)", value=f"{data_siswa['Total Nilai (CF)']:.2f} / 5.00")
                
                st.markdown(f"""
                **💡 Alasan Rekomendasi:**
                Berdasarkan perhitungan algoritma *Profile Matching*, sistem mendeteksi bahwa profil nilaimu (bakat, minat, dan potensi) memiliki selisih (*gap*) yang sangat kecil dengan profil ideal divisi **{divisi_terbaik}**. Hal ini menunjukkan bahwa kompetensi aktualmu sangat selaras dengan kriteria prioritas (*Core Factor*) yang dibutuhkan oleh divisi tersebut. Dengan tingkat kecocokan mencapai **{data_siswa['Skor (Persentase)']:.2f}%**, kamu diproyeksikan dapat beradaptasi, belajar, dan berkontribusi secara maksimal di divisi ini.
                """)

        with tab_keseluruhan:
            if 'filter_divisi' not in st.session_state:
                st.session_state['filter_divisi'] = "Semua Divisi"

            st.write("**🔍 Filter Berdasarkan Divisi:**")
            list_divisi = [
                "Semua Divisi", "Syiar", "Tilawah (Kesenian)", "Da'i (Kesenian)", "Seni/Kaligrafi", 
                "PSDM", "Sosial", "Takmir Musholla", "CCI (Kesenian)", "Tahfidz (Kesenian)"
            ]
            
            for i in range(0, len(list_divisi), 5):
                cols = st.columns(5)
                for j in range(5):
                    if i + j < len(list_divisi):
                        div = list_divisi[i + j]
                        with cols[j]:
                            btn_type = "primary" if st.session_state['filter_divisi'] == div else "secondary"
                            if st.button(div, type=btn_type, width="stretch", key=f"btn_filter_{i+j}"):
                                st.session_state['filter_divisi'] = div
                                st.rerun()
                        
            st.divider()

            data_filtered = data_mentah.copy()
            if st.session_state['filter_divisi'] != "Semua Divisi":
                data_filtered = [d for d in data_filtered if st.session_state['filter_divisi'] in d['Rekomendasi Utama']]

            data_klasemen = []
            for idx, d in enumerate(data_filtered):
                data_klasemen.append({
                    "Rank": idx + 1,
                    "Nama Siswa": d['Nama Siswa'],
                    "Kelas": d['Kelas'],
                    "Nilai": f"{d['Total Nilai (CF)']:.2f}",
                    "Tingkat Kecocokan": f"{d['Skor (Persentase)']:.2f}%",
                    "Rekomendasi Divisi": d['Rekomendasi Utama']
                })
            
            if data_klasemen:
                df_klasemen = pd.DataFrame(data_klasemen)
                
                col_header, col_pdf, col_excel = st.columns([2, 1, 1])
                with col_header:
                    st.write("### 🏆 Tabel Rekomendasi Keseluruhan")
                    
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_klasemen.to_excel(writer, index=False, sheet_name='Klasemen ROHIS')
                excel_bytes = buffer.getvalue()
                
                with col_excel:
                    st.download_button(
                        label="📊 Download Excel",
                        data=excel_bytes,
                        file_name=f"Laporan_Rohis_{datetime.date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch",
                        type="primary"
                    )

                try:
                    from fpdf import FPDF
                    from fpdf.enums import XPos, YPos  # Import parameter baru fpdf2

                    class PDF(FPDF):
                        def header(self):
                            # Ganti Arial jadi Helvetica
                            self.set_font('Helvetica', 'B', 12)
                            # Ganti ln=1 jadi new_x dan new_y
                            self.cell(0, 10, 'Laporan Hasil Penempatan Divisi ROHIS SMPN 87 Jakarta', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                            
                            if st.session_state['filter_divisi'] != "Semua Divisi":
                                self.set_font('Helvetica', 'I', 10)
                                self.cell(0, 8, f'Kategori: {st.session_state["filter_divisi"]}', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                            self.ln(5)

                    pdf = PDF()
                    pdf.add_page()
                    
                    headers = ["Rank", "Nama Siswa", "Kelas", "Nilai", "Tk. Kecocokan", "Rekomendasi Divisi"]
                    col_widths = [12, 45, 12, 15, 23, 83] 
                    
                    pdf.set_font("Helvetica", 'B', 9)
                    for i, header in enumerate(headers):
                        # Ganti ln=0 jadi parameter baru
                        pdf.cell(col_widths[i], 10, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                    pdf.ln()

                    pdf.set_font("Helvetica", size=8)
                    for index, row in df_klasemen.iterrows():
                        pdf.cell(col_widths[0], 8, str(row['Rank']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                        pdf.cell(col_widths[1], 8, str(row['Nama Siswa'])[:22], border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
                        pdf.cell(col_widths[2], 8, str(row['Kelas']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                        
                        pdf.cell(col_widths[3], 8, str(row['Nilai']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                        pdf.cell(col_widths[4], 8, str(row['Tingkat Kecocokan']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                        
                        rek = str(row['Rekomendasi Divisi'])
                        if len(rek) > 48: rek = rek[:45] + "..."
                        pdf.cell(col_widths[5], 8, rek, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
                        pdf.ln()

                    # SOLUSI SEGMENTATION FAULT: Output langsung ke bytes (RAM), HAPUS tempfile
                    pdf_bytes = bytes(pdf.output())

                    with col_pdf:
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"Laporan_Rohis_{datetime.date.today()}.pdf",
                            mime="application/pdf",
                            width="stretch", 
                            type="primary"
                        )
                except Exception as e:
                    with col_pdf:
                        st.error(f"⚠️ Gagal mencetak PDF: {e}")

                st.dataframe(df_klasemen, hide_index=True, width="stretch")
            else:
                st.warning(f"Belum ada data siswa yang direkomendasikan untuk divisi: {st.session_state['filter_divisi']}")

    if role_aktif == 'pembina':
        tab_kalkulasi, tab_klasemen = st.tabs(["🧮 Kalkulasi Nilai", "📊 Klasemen & Rekomendasi"])

        with tab_kalkulasi:
            data_target = {
                "Divisi / Peminatan": [
                    "Syiar", "Tilawah (Kesenian)", "Da'i (Kesenian)", "Seni/Kaligrafi", 
                    "PSDM", "Sosial", "Takmir Musholla", "CCI (Kesenian)", "Tahfidz (Kesenian)"
                ],
                "K1": [3, 4, 3, 3, 3, 3, 4, 4, 4],
                "K2": [3, 4, 4, 3, 3, 3, 4, 4, 4],
                "K3": [4, 3, 4, 3, 4, 4, 4, 4, 3],
                "K4": [3, 3, 3, 4, 4, 3, 3, 3, 3],
                "K5": [4, 4, 4, 4, 4, 4, 4, 4, 4]
            }
            df_target = pd.DataFrame(data_target)

            divisi_ids = {
                "Syiar": 1, "Tilawah (Kesenian)": 2, "Da'i (Kesenian)": 3, 
                "Seni/Kaligrafi": 4, "PSDM": 5, "Sosial": 6, 
                "Takmir Musholla": 7, "CCI (Kesenian)": 8, "Tahfidz (Kesenian)": 9
            }

            conn, cursor = get_db_cursor()
            cursor.execute("SELECT kd_siswa, nama_siswa FROM siswa")
            data_siswa = cursor.fetchall()

            if not data_siswa:
                st.warning("Belum ada data siswa di database.")
                cursor.close()
            else:
                opsi_siswa = [f"{s['kd_siswa']} - {s['nama_siswa']}" for s in data_siswa]
                pilih_siswa = st.selectbox("Pilih Siswa untuk Dihitung Gap-nya:", opsi_siswa)
                kd_siswa = int(pilih_siswa.split(" - ")[0])

                cursor.execute('''
                    SELECT id_kriteria, nilai_aktual 
                    FROM nilai_siswa 
                    WHERE kd_siswa = %s
                    ORDER BY id_kriteria ASC
                ''', (kd_siswa,))
                data_nilai = cursor.fetchall()
                cursor.close()

                if len(data_nilai) < 5:
                    st.error("Data nilai siswa belum lengkap (harus dinilai pada 5 kriteria terlebih dahulu).")
                else:
                    nilai_aktual = {f"K{n['id_kriteria']}": n['nilai_aktual'] for n in data_nilai}
                    st.write(f"**Nilai Aktual Terdaftar:** {nilai_aktual}")

                    df_gap = df_target.copy()
                    kriteria_list = ["K1", "K2", "K3", "K4", "K5"]
                    hasil_perhitungan = []

                    for index, row in df_gap.iterrows():
                        nama_divisi = row['Divisi / Peminatan']
                        ncf_total, ncf_count = 0, 0
                        nsf_total, nsf_count = 0, 0
                        
                        for k in kriteria_list:
                            target = df_target.loc[index, k]
                            aktual = nilai_aktual[k]
                            gap = aktual - target
                            
                            df_gap.loc[index, k] = gap
                            bobot = bobot_gap(gap)
                            
                            if target >= 4:
                                ncf_total += bobot
                                ncf_count += 1
                            elif target == 3:
                                nsf_total += bobot
                                nsf_count += 1

                        ncf = ncf_total / ncf_count if ncf_count > 0 else 0
                        nsf = nsf_total / nsf_count if nsf_count > 0 else 0
                        skor_akhir = (0.6 * ncf) + (0.4 * nsf) 
                        
                        hasil_perhitungan.append({
                            'Divisi / Peminatan': nama_divisi,
                            'NCF': ncf,
                            'NSF': nsf,
                            'Skor Akhir': skor_akhir
                        })

                    def color_gap(val):
                        if type(val) == int:
                            if val == 0: return 'color: #10b981; font-weight: bold;'
                            elif val > 0: return 'color: #38bdf8;'
                            elif val < 0: return 'color: #ef4444;'
                        return ''

                    with st.expander("Lihat Detail Matriks & NCF/NSF"):
                        st.subheader("1. Matriks Gap")
                        st.dataframe(df_gap.style.map(color_gap, subset=kriteria_list), hide_index=True, width="stretch")
                        df_hasil = pd.DataFrame(hasil_perhitungan)
                        df_hasil = df_hasil.sort_values(by="Skor Akhir", ascending=False).reset_index(drop=True)
                        st.subheader("2. Hasil NCF, NSF, dan Skor Akhir")
                        st.dataframe(df_hasil, hide_index=True, width="stretch")

                    if st.button("Simpan Rekomendasi ke Klasemen", type="primary"):
                        try:
                            max_skor = df_hasil['Skor Akhir'].max()
                            top_divisi_df = df_hasil[df_hasil['Skor Akhir'] == max_skor]

                            conn, cursor = get_db_cursor()
                            cursor.execute("DELETE FROM hasil_ranking WHERE kd_siswa = %s", (kd_siswa,))
                            
                            saved_divisi = []
                            for idx, row in top_divisi_df.iterrows():
                                id_div_top = divisi_ids.get(row['Divisi / Peminatan'])
                                if id_div_top:
                                    skor_final = float(row['Skor Akhir'])
                                    query_insert = "INSERT INTO hasil_ranking (kd_siswa, id_divisi, skor_akhir) VALUES (%s, %s, %s)"
                                    cursor.execute(query_insert, (kd_siswa, id_div_top, skor_final))
                                    saved_divisi.append(row['Divisi / Peminatan'])
                                    
                            conn.commit()
                            cursor.close()
                            
                            nama_div_gabung = " / ".join(saved_divisi)
                            catat_log(f"Menyimpan hasil ranking ({nama_div_gabung}) untuk siswa ID: {kd_siswa}")
                            st.success(f"✅ Berhasil menyimpan rekomendasi final divisi **{nama_div_gabung}**! Silakan cek Tab Klasemen.")
                        except Exception as e:
                            st.error(f"Terjadi kesalahan saat menyimpan data: {e}")

        with tab_klasemen:
            render_tabel_klasemen()

    else:
        st.subheader("📊 Hasil Penempatan Divisi")
        render_tabel_klasemen()

# ---------------------------------------------------------
# 11. LOGIKA ROUTING UTAMA & TATA LETAK SIDEBAR
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    col_kiri, col_kanan = st.columns([8, 1]) 
    
    with col_kanan:
        if st.session_state['menu_aktif'] != "Login Akses":
            if st.button("Login 👤", type="primary", width="stretch"):
                st.session_state['menu_aktif'] = "Login Akses"
                st.rerun()
        else:
            if st.button("Kembali", width="stretch"):
                st.session_state['menu_aktif'] = "🏠 Dashboard"
                st.rerun()

    with st.sidebar:
        st.markdown("""
        <h3 style='color: #10b981; margin-bottom: 0px;'>ROHIS-MATCH</h3>
        <small style='color: #eab308; font-weight: bold;'>SMPN 87 Jakarta</small>
        """, unsafe_allow_html=True)
        st.divider()
        
        if st.session_state['menu_aktif'] != "Login Akses":
            menu_pilihan_publik = st.radio("Pilih Halaman:", ["🏠 Dashboard", "⭐ Hasil Ranking"])
            st.info("Silakan login menggunakan tombol di pojok kanan atas layar untuk mengakses menu pengurus/pembina.")
            
            if st.session_state['menu_aktif'] != menu_pilihan_publik:
                catat_log(f"Membuka halaman {menu_pilihan_publik}") 
                st.session_state['menu_aktif'] = menu_pilihan_publik
                st.rerun()
        else:
            st.info("Anda sedang berada di halaman portal login.")

    if st.session_state['menu_aktif'] == "🏠 Dashboard":
        halaman_dashboard()
    elif st.session_state['menu_aktif'] == "⭐ Hasil Ranking":
        halaman_hasil_spk()
    elif st.session_state['menu_aktif'] == "Login Akses":
        halaman_login()

else:
    col_kiri, col_kanan = st.columns([8, 1]) 
            
    with col_kanan:
        if st.button("Keluar 🚪", width="stretch"):
            dialog_konfirmasi_logout()

    with st.sidebar:
        st.markdown("""
        <h3 style='color: #10b981; margin-bottom: 0px;'>ROHIS-MATCH</h3>
        <small style='color: #eab308; font-weight: bold;'>SMPN 87 Jakarta</small>
        """, unsafe_allow_html=True)
        st.divider()
        
        role_aktif = st.session_state['role'].lower()
        
        if role_aktif == 'pengurus':
            daftar_menu = ["🏠 Dashboard", "👥 Data Anggota", "⭐ Hasil Ranking", "⚙️ Pengaturan"]
        elif role_aktif == 'pembina':
            daftar_menu = ["🏠 Dashboard", "📝 Input Penilaian", "⭐ Hasil Ranking", "⚙️ Pengaturan"]
        else:
            daftar_menu = ["🏠 Dashboard", "⚙️ Pengaturan"]
            
        menu_pilihan = st.radio("Pilih Halaman:", daftar_menu, key="menu_pilihan_key")
        st.divider()
        st.caption(f"Login sebagai: <b style='color: #10b981;'>{role_aktif.upper()}</b>", unsafe_allow_html=True)

    if menu_pilihan == "🏠 Dashboard":
        halaman_dashboard()
    elif menu_pilihan == "👥 Data Anggota":
        halaman_data_siswa()
    elif menu_pilihan == "📝 Input Penilaian":
        halaman_input_nilai()
    elif menu_pilihan == "⭐ Hasil Ranking":
        halaman_hasil_spk()
    elif menu_pilihan == "⚙️ Pengaturan":
        halaman_profil()
