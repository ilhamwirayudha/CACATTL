# ATURAN PENGUNCIAN LOGIKA PROYEK (LOCKED CORE LOGIC RULES)

Seluruh logika perhitungan, kualifikasi pasangan, pembentukan ritase, visualisasi analitis, dan penyusunan tabel rincian di dalam proyek **CACA — Dashboard Analisis Dual Cycle & Twinlift** ini telah **DIKUNCI SECARA PERMANEN (FINAL & VERIFIED)**.

---

## 🚨 PROTOKOL WAJIB BAGI AI AGENT (MANDATORY CONFIRMATION PROTOCOL)

1. **DILARANG KERAS MENGUBAH LOGIKA TANPA KONFIRMASI EKSPLISIT**:
   - Setiap kali ada permintaan fitur baru, perbaikan UI/styling, pengurutan tabel, atau perubahan kode apa pun yang **berpotensi menyentuh, menggeser, atau berdampak pada logika perhitungan** (baik secara langsung maupun efek berantai / *ripple effect*), Agent **WAJIB BERHENTI** dan **MEMINTA KONFIRMASI TERLEBIH DAHULU** kepada User sebelum mengedit kode logika tersebut.
   - Jelaskan secara rinci kepada User:
     1. Bagian logika mana yang akan terdampak,
     2. Apa dampaknya terhadap angka KPI / persentase (misalnya `% Dual Cycle`, jumlah `Total Ritase`, `Combo`, `Single`, `Twinlift`, `Durasi`, atau `Gap`),
     3. Minta persetujuan eksplisit User sebelum menerapkan perubahan.

---

## 🔒 DAFTAR LOGIKA INTI YANG DIKUNCI (DO NOT MODIFY WITHOUT APPROVAL)

### 1. Layer 1 — Pembentukan Grup Combo & Single (`layer1_combo` di `modules/calculations.py` & `prepare_combo_table` di `modules/ui.py`)
- **Syarat Kualifikasi Pasangan Combo**:
  - Ukuran kontainer eligible (`20ft`), armada truk (`CAR_CHE_ID`) sama, dan aktivitas (`ACTIVITY`: `DISC` atau `LOAD`) sama.
  - Kandidat pasangan dievaluasi pada rentang waktu Dermaga (`TS_G` / `DISC_LOAD_TS`) maupun Lapangan (`TS_H` / `STACK_UNSTACK_TS`) $\le \text{ambang\_combo}$ (default `3 menit`).
- **Rumus Perhitungan Gap Combo (`if-else` Bertingkat)**:
  - **Prioritas 1 (Dermaga)**: Hitung `gap_dermaga = |DISC_LOAD_TS2 - DISC_LOAD_TS1|`. Jika `gap_dermaga <= ambang_combo`, gunakan `gap_dermaga`.
  - **Prioritas 2 (Fallback Lapangan)**: Jika `gap_dermaga > ambang_combo`, hitung `gap_lapangan = |STACK_UNSTACK_TS2 - STACK_UNSTACK_TS1|`. Gunakan `gap_lapangan`.
  - **Gagal Keduanya**: Jika keduanya $> \text{ambang\_combo}$, maka kontainer tidak terkualifikasi Combo dan masuk ke kategori Single (1x 20ft).

### 2. Layer 1b — Deteksi Twinlift (`deteksi_twinlift` di `modules/calculations.py`)
- Hanya dievaluasi dari pasangan grup Combo (`2x 20ft`) dengan 6 syarat mutlak:
  1. Ukuran kedua kontainer adalah `20ft`,
  2. Kapal (`VES_ID`) sama,
  3. Truk (`CAR_CHE_ID`) sama (otomatis terjamin dari Layer 1),
  4. Quay Crane (`CRANE_ID`) sama,
  5. Crane berada di kade internasional (ID berakhiran `"I"`: `01I` – `05I`). Crane kade domestik (`"D"`) secara fisik dan operasional tidak dapat melakukan Twinlift, sehingga selalu berstatus `"Bukan Twinlift"`,
  6. Selisih waktu Dermaga (`|DISC_LOAD_TS2 - DISC_LOAD_TS1|`) $\le \text{ambang\_twinlift}$ (default `1 menit`).

### 3. Rekonstruksi Event Ritase (`bentuk_event` di `modules/calculations.py`)
- Titik waktu mulai (`START_TS`) dan selesai (`END_TS`) per ritase mengikuti alur fisik pergerakan kontainer di pelabuhan:
  - Untuk **DISC (Bongkar)**: Mulai di Dermaga dan Selesai di Lapangan Penumpukan:
    $$\text{START\_TS} = \min(\text{DISC\_LOAD\_TS}), \quad \text{END\_TS} = \max(\text{STACK\_UNSTACK\_TS})$$
  - Untuk **LOAD (Muat)**: Mulai di Lapangan Penumpukan dan Selesai di Dermaga:
    $$\text{START\_TS} = \min(\text{STACK\_UNSTACK\_TS}), \quad \text{END\_TS} = \max(\text{DISC\_LOAD\_TS})$$

### 4. Layer 2 — Deteksi & Gap Dual Cycle (`layer2_dual` di `modules/calculations.py` & `prepare_dual_cycle_table` di `modules/ui.py`)
- Pasangan lintas aktivitas (`DISC` vs `LOAD`) pada truk (`CAR_CHE_ID`) yang sama.
- **Rumus Perhitungan Gap Dual Cycle (DIKUNCI - 50,1% / 2.062 Ritase)**:
  - Jika urutan **`DISC ➔ LOAD`** (`START_TS_DISC <= START_TS_LOAD`):
    $$\text{Gap} = \text{START\_TS\_LOAD} - \text{END\_TS\_DISC}$$
  - Jika urutan **`LOAD ➔ DISC`** (`START_TS_LOAD < START_TS_DISC`):
    $$\text{Gap} = \text{START\_TS\_DISC} - \text{END\_TS\_LOAD}$$
  - **Aturan Overlap di `layer2_dual` & `prepare_dual_cycle_table`**:
    Jika terjadi overlap (`gap_ab < 0` dan `gap_ba < 0`), hanya dikualifikasikan apabila $\text{overlap} = \min(|\text{gap}_{ab}|, |\text{gap}_{ba}|) \le 10.0\text{ menit}$ dan $\text{start\_diff} \le \text{ambang\_dual} + 60\text{ menit}$. Dengan aturan ini, anomali overlap lintas hari / puluhan jam tereliminasi dan masuk ke Non-Dual.
    Pada tabel rincian (`prepare_dual_cycle_table`), nilai `Gap` untuk baris overlap menggunakan nilai riil overlap dari `layer2_dual` (`min(|gap_forward|, |gap_backward|)`), bukan dipaksa 0.0.
  - Dikualifikasikan sebagai Dual Cycle apabila $\text{round}(\text{gap}, 1) \le \text{ambang\_dual}$ (default `30 menit`).

### 5. Perhitungan Durasi Non-Dual & Single (`prepare_non_dual_table` & `prepare_single_table` di `modules/ui.py`)
- **Durasi Non-Dual**: $\text{END\_TS} - \text{START\_TS}$ (presisi ke detik, tanpa pembulatan desimal `.round(1)`).
- **Durasi Single (20ft)**: $|\text{STACK\_UNSTACK\_TS} - \text{DISC\_LOAD\_TS}|$ (presisi ke detik).

### 6. Format Pengurutan Durasi & Kolom Waktu (`modules/ui.py`)
- **Pengurutan Tabel & Kolom Waktu (`st.dataframe`)**:
  - Kolom `Gap` dan `Durasi` menggunakan helper `format_duration_sortable` dengan digit seragam dan zero-padded (`MMm SSs`, `HHh MMm SSs`, `DDd HHh MMm SSs`) agar pengurutan bawaan Streamlit (sorting ascending/descending) berfungsi konsisten secara numerik.
  - Kolom waktu menggunakan `st.column_config.DatetimeColumn` dengan data bertipe `datetime64` asli agar urutan kronologis tanggal/bulan/tahun tidak terganggu.
  - Tabel rincian Dual Cycle menampilkan kolom waktu transparan: `Mulai DISC` (`START_TS_DISC`), `Selesai DISC` (`END_TS_DISC`), `Mulai LOAD` (`START_TS_LOAD`), dan `Selesai LOAD` (`END_TS_LOAD`), sehingga Gap dapat diverifikasi langsung secara visual:
    - **DISC ➔ LOAD**: $\text{Gap} = \text{Mulai LOAD} - \text{Selesai DISC}$
    - **LOAD ➔ DISC**: $\text{Gap} = \text{Mulai DISC} - \text{Selesai LOAD}$

### 7. Standarisasi Tampilan Modal Pop-up & Kolom Rincian (`modules/ui.py`)
- **Warna Aksen KPI Cards Modal**:
  - Seluruh KPI cards di semua modal pop-up rincian operasional (`Dual Cycle`, `Non-Dual`, `Combo`, `Single`, `Twinlift`, `Bukan Twinlift`, `Potensi Dual Cycle`, `Potensi Combo`) diseragamkan dan dikunci menggunakan garis biru (`variant="blue"`).
- **Satuan Total Ritase Combo**:
  - Satuan pada KPI Card *Total Ritase Combo* dikunci menggunakan satuan **`Rit`** (misal: `2.581 Rit`).
- **Pembersihan Kolom & Keterangan Redundan pada Tabel**:
  - **Tabel Non-Dual**: Kolom `Tipe Kontainer` dan suffix `| Single` / `| Combo` pada kolom *Ringkasan Aktivitas* dihapus permanen agar tidak menimbulkan kerancuan antara kontainer 20ft dan 40ft/45ft.
  - **Tabel Single (20ft)**: Suffix `| 1x 20ft | Single Ritase` pada kolom *Ringkasan Single* dihapus permanen, menyisakan format bersih: `701 | LOAD (HUHE010, 03D)`.
  - **Tabel Dual Cycle**: Kolom `Tipe DISC` dan `Tipe LOAD` dihapus permanen agar kolom DISC dan LOAD simetris (`Crane`, `Mulai`, `Selesai`).
  - **Tabel Twinlift & Bukan Twinlift**:
    - Format tabel disusun **1 baris menyamping (horizontal)** persis seperti tabel Combo, sehingga nilai `Gap` dapat langsung diverifikasi dari selisih `Waktu Dermaga 2` - `Waktu Dermaga 1` pada baris yang sama tanpa harus membandingkan baris atas dan baris bawah.
    - Kolom `Crane 1`, `No Container 1`, `Waktu Dermaga 1` bersanding simetris dengan `Crane 2`, `No Container 2`, dan `Waktu Dermaga 2` untuk memudahkan verifikasi fisik crane dan nomor peti kemas.
    - Kolom `Waktu Lapangan` dihapus permanen agar rincian fokus pada waktu dermaga (`TS_G`) sebagai acuan evaluasi lifting Twinlift.
    - Pada tabel Bukan Twinlift, pasangan Combo gagal Twinlift menampilkan rincian kontainer 1 dan kontainer 2 lengkap dengan masing-masing crane dan gap-nya, sedangkan kontainer Single (1x 20ft) menampilkan kontainer 1 dan crane 1, dengan kontainer 2, crane 2, waktu 2, dan gap berupa tanda strip (`-`).
  - **Teks Footer Tabel**: Keterangan footer `Menampilkan total ...` dihapus permanen dari seluruh tabel rincian modal.
- **Deteksi & Highlight Baris Anomali Dual Cycle**:
  - Kolom **`Anomali`** pada modal Dual Cycle dikunci dengan rumus:
    - `Anomali`: jika $\text{Gap} < 10.0\text{ menit}$ ($< \text{10m 00s}$).
    - `Normal`: jika $\text{Gap} \ge 10.0\text{ menit}$ ($\ge \text{10m 00s}$).
  - Baris dengan status `Anomali` diwarnai latar merah halus (`rgba(239, 68, 68, 0.22)`) dengan teks merah muda (`#fca5a5`).
  - Legenda baris merah diletakkan di **bawah tabel sebelah kanan**:  
    `🔴 Baris Merah: Anomali (Gap < 10m 00s)`

### 8. Modal Pop-up Potensi Dual Cycle (`modules/ui.py` & `app.py`)
- **Sumber Data & Kualifikasi**:
  - Pasangan ritase diambil murni dari data `STATUS == 'Non Dual'` pada armada truk yang sama (`CAR_CHE_ID`).
  - Aktivitas berurutan harus bergantian (`DISC ➔ LOAD` atau `LOAD ➔ DISC`).
  - Jeda waktu: $\text{ambang\_dual} < \text{Gap} \le \text{max\_gap}$ (default: $30\text{ mnt} < \text{Gap} \le 180\text{ mnt}$).
  - Setiap event Non-Dual hanya dipasangkan 1 kali (*greedy matching* dari gap terkecil) untuk mencegah *double-counting*.
- **Tombol Pemicu**:
  - Tombol aksi `💡 Potensi Dual Cycle` diletakkan di bawah Donut Chart Dual Cycle bersanding dengan tombol `🔍 Rincian Dual Cycle` dan `🔍 Rincian Non Dual` (total 3 kolom tombol).
- **Tampilan Modal**:
  - Judul: `Rincian Potensi Dual Cycle`.
  - 4 KPI cards aksen biru (`variant="blue"`): *Potensi Dual Cycle*, *Jumlah Truk*, *Rata-rata Gap*, *Maksimal Toleransi*.
  - Tabel rincian interaktif dengan format kolom seragam Dual Cycle: *Ringkasan Potensi Siklus*, *Urutan*, *Crane DISC*, *Mulai DISC*, *Selesai DISC*, *Crane LOAD*, *Mulai LOAD*, *Selesai LOAD*, *Gap*, dan *Kelebihan Ambang*.

### 9. Modal Pop-up Potensi Combo (`prepare_potential_combo_table` & `_show_combo_issue_dialog` di `modules/ui.py`)
- **Sumber Data & Kualifikasi**:
  - Pasangan kontainer diambil murni dari data Single 20ft (`CTR_SIZE == 20` dan `CONTAINER_STATUS == "Single"`).
  - Armada truk sama (`CAR_CHE_ID`) dan aktivitas sama (`ACTIVITY`: `DISC ➔ DISC` atau `LOAD ➔ LOAD`).
  - Jeda waktu: $\text{ambang\_combo} < \text{Gap} \le \text{max\_gap}$ (default: $3\text{ mnt} < \text{Gap} \le 30\text{ mnt}$).
  - Evaluasi selisih waktu dilakukan pada Dermaga (`TS_G`) maupun Lapangan (`TS_H`), mengambil nilai terkecil $\min(\text{gap}_g, \text{gap}_h)$.
  - Setiap kontainer Single hanya dipasangkan 1 kali (*greedy matching* dari gap terkecil) untuk mencegah *double-counting*.
- **Tombol Pemicu**:
  - Tombol aksi `💡 Potensi Combo` diletakkan di bawah Donut Chart Combo/Single bersanding dengan tombol `🔍 Rincian Combo` dan `🔍 Rincian Single` (total 3 kolom tombol).
- **Tampilan Modal**:
  - Judul: `Rincian Potensi Combo (Kontainer 20ft)`.
  - 4 KPI cards aksen biru (`variant="blue"`): *Potensi Combo*, *Jumlah Truk*, *Rata-rata Gap Potensi*, *Ambang Batas Combo*.
  - Tabel rincian interaktif dengan format kolom: *Ringkasan Potensi Combo*, *Aktivitas*, *DISC_LOAD_TS1*, *DISC_LOAD_TS2*, *STACK_UNSTACK_TS1*, *STACK_UNSTACK_TS2*, dan *Gap*.

### 10. Filter Lingkup Tab Twinlift (Radio Button Scope) (`app.py`)
- **Radio Button Filter Lingkup**:
  - Ditempatkan di bawah pemilihan Tab Utama pada tab `Twinlift` dengan urutan opsi:
    1. **`Internasional`** (Default)
    2. **`Domestik & Internasional`**
- **Logika & Tampilan Mode "Internasional" (Opsi 1)**:
  - Mengisolasi pergerakan kontainer yang dilayani oleh Quay Crane internasional (ID berakhiran `"I"`: `01I` – `05I`).
  - **KPI Cards & Charts**:
    - *Total Kontainer*: Total kontainer (20ft & 40ft) di kade internasional.
    - *Jumlah 20ft*: Total kontainer 20ft di kade internasional.
    - *Twinlift*: Jumlah kontainer 20ft yang diangkat Twinlift di kade internasional.
    - *Bukan Twinlift*: Jumlah kontainer 20ft yang diangkat Single Lift di kade internasional.
    - *% Twinlift*: Rasio Twinlift terhadap kontainer 20ft internasional ($\approx 67\%$).
    - *Donut Chart & Breakdown Bulanan*: Otomatis menyesuaikan data murni kade internasional.
  - **Modal Pop-up**:
    - Tombol *🔍 Rincian Twinlift* dan *🔍 Rincian Bukan Twinlift* otomatis menyajikan slice data sesuai scope yang sedang aktif (Total atau Internasional).

### 11. Standar Basis Populasi Kontainer 20ft untuk Metrik Combo & Twinlift (`hitung_ringkasan` di `modules/calculations.py`)
- **Pemisahan Basis Populasi Kontainer**:
  - Persentase `% Combo` dan `% Twinlift` **WAJIB** dihitung dari populasi **kontainer 20ft eligible saja**, BUKAN dari total seluruh kontainer (20ft, 40ft, 45ft).
  - Kontainer 40ft dan 45ft secara fisik tidak dapat dijadikan Combo (2x 20ft) maupun Twinlift. Menghitung persentase atas seluruh kontainer akan menghasilkan angka bias rendah palsu.
- **Agregasi Bulanan 20ft (`monthly_20ft`)**:
  - Menyediakan dataframe bulanan khusus kontainer 20ft yang mencatat: `total_20ft`, `combo`, `single`, `twinlift`, `bukan_twinlift`, `% Combo`, dan `% Twinlift`.

### 12. Performa Quay Crane (QC) dalam Pembentukan Twinlift (`hitung_performa_crane` di `modules/calculations.py`)
- Basis perhitungan dilakukan per baris kontainer (bukan per event ritase truk), karena crane bekerja mengangkat fisik kontainer.
- Kolom performa crane: `total_kontainer`, `total_20ft`, `total_twinlift`, `pct_twinlift_dari_total`, dan `pct_twinlift_dari_20ft`.
- Tabel diurutkan berdasarkan `pct_twinlift_dari_20ft` (metrik utama) secara menurun (descending).

### 13. Breakdown Waktu & 3 Shift Kerja Standar (`hitung_breakdown_waktu` di `modules/calculations.py` & `app.py`)
- Pembagian 3 Shift Kerja Operasional:
  - **Shift 1**: `00.00 – 08.00`
  - **Shift 2**: `08.00 – 16.00`
  - **Shift 3**: `16.00 – 00.00`
- Metrik per shift: `total_event`, `dual`, `non_dual`, `pct_dual`, `twinlift`, `pct_twinlift`.
- Komponen breakdown diisolasi menggunakan decorator `@st.fragment` agar penyesuaian slider / input target garis optimal (%) tidak memicu *full rerun* halaman dan menjaga posisi scroll pengguna tetap stabil.

### 14. Filter Periode & Rentang Tanggal Data Operasional (`modules/calculations.py` & `app.py`)
- Fungsi `extract_period_options_from_events` dan `compute_period_bounds` mendukung filter:
  - `Semua Periode (Penuh)`
  - `Per Hari (Harian)`
  - `Per Minggu (Mingguan)`
  - `Per Bulan (Bulanan)`
  - `Rentang Tanggal Bebas`
- Menjamin pemotongan aman (*clipping*) tanggal selalu berada di dalam rentang `[min_d, max_d]`.
- Sinkronisasi penyaringan antara dataframe event ritase (`events`) dan dataframe kontainer per baris (`out_df`).

### 15. Logika Simulasi Potensi Efisiensi BBM & Finansial (`app.py` Tab Simulasi)
- **Ground Truth 100% dari File Terupload**:
  - `Baseline Ritase` diambil murni dari total event hasil analisis file (`act_total_ritase = total_dual + total_single`, misal `4.118 Rit`).
  - `Ritase Dual Cycle Aktual` = `2.062 Rit` (50,1%).
  - `Ritase Non-Dual Aktual` = `2.056 Rit` (49,9%).
- **Parameter Default Teruji**:
  - Konsumsi BBM Truk: `1.75 Liter / Ritase` (slider kelipatan 0,05).
  - Harga Solar Industri: `Rp 15.000 / Liter` (slider kelipatan 500).
- **Rumus Efisiensi BBM & Finansial**:
  - Setiap 1 ritase Dual Cycle menghemat 1 perjalanan truk kosong (menghemat `1 × BBM_per_rit` liter solar).
  - **Total Solar Dihemat**: $\text{Ritase DC} \times \text{BBM\_per\_rit}$
  - **Total BBM Terpakai**: $(\text{Total Ritase} - \text{Ritase DC}) \times \text{BBM\_per\_rit} = \text{Ritase Non-DC} \times \text{BBM\_per\_rit}$
  - **Efisiensi Finansial (vs Aktual)**:
    $$\Delta \text{Finansial} = (\text{Ritase DC}_{\text{skenario}} - \text{Ritase DC}_{\text{aktual}}) \times \text{BBM\_per\_rit} \times \text{Harga\_Solar}$$
- **Slider Simulasi Adaptif Dinamis (`hitung_rentang_ambang_file`)**:
  - Mendeteksi persentil ke-5 (`p5`) dan persentil ke-95 (`p95`) dari rentang jeda waktu riil data yang terupload (dibulatkan ke kelipatan 5 menit, min 5 menit, max 240 menit).
- **Tabel Sensitivitas Penetrasi**:
  - Menampilkan rentang skenario seputar nilai riil dengan indikator:
    - `📍 Kondisi Saat Ini`: Nilai acuan aktual dari file terupload (50,1%).
    - `🎯 Target Skenario`: Nilai penetrasi yang dipilih pada slider simulasi.

### 16. Proteksi Modal Backdrop Click (`inject_modal_backdrop_protection` di `modules/ui.py`)
- Mencegah modal pop-up tertutup secara tidak sengaja saat pengguna mengklik area luar (backdrop/overlay) dialog Streamlit.
- Menjamin pengguna hanya dapat keluar dari modal dialog melalui tombol `Tutup` atau tombol silang (X) yang telah disediakan.

### 17. Standarisasi Download & Ekspor Data Excel (`app.py`)
- Eksklusi permanen kolom internal kalkulasi dari tabel preview dan unduhan file Excel:
  `DUAL_PAIR_ID`, `DUAL_JENIS`, `DUAL_PASANGAN_EVENT_ID`, `DUAL_URUTAN`, `DUAL_GAP_LOKASI`, `DUAL_GAP_MENIT`, `DUAL_AMBANG_MENIT`, `DUAL_SELISIH_AMBANG_MENIT`, `DUAL_IS_FAST`, dan `TWINLIFT_GAP_MENIT`.
- Menggunakan caching signature `_excel_bytes` dan `_excel_sig` agar berkas Excel hanya dibuat saat diminta pertama kali dan tidak memicu pembuatan ulang berulang kali.
