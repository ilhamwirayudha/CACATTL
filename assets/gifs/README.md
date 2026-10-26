# Panduan Penempatan File Animasi GIF / Media

Folder ini (`assets/gifs/`) digunakan khusus untuk menempatkan file animasi (GIF / WebP) yang akan ditampilkan secara otomatis pada aplikasi **CACA Dashboard**, terutama pada tooltip bantuan parameter simulasi:

---

## 📁 Nama File yang Didukung

Aplikasi secara otomatis mengenali file dengan nama-nama berikut:

### 1. Animasi Combo (20ft)
- `combo.gif`
- `combo.webp`
- Alternatif: `combo_20ft.gif`, `combo-20ft.gif`

### 2. Animasi Dual Cycle
- `dual_cycle.gif`
- `dual_cycle.webp`
- Alternatif: `dualcycle.gif`, `dual-cycle.gif`

### 3. Animasi Twin Lift (20ft)
- `twinlift.gif`
- `twinlift.webp`
- Alternatif: `twin_lift.gif`, `twin-lift.gif`

---

## 💡 Rekomendasi Format & Ukuran
- **Format disarankan**: `.gif` atau `.webp` (animasi WebP berukuran jauh lebih ringan dan halus).
- **Rasio Dimensi**: Ideal rasio 16:9 atau 4:3 (contoh resolusi: `480x270` px atau `640x360` px).
- **Ukuran File**: Disarankan di bawah `5 MB` agar tooltip dapat terbuka instan tanpa jeda pemuatan data.

---

> Begitu Anda meletakkan file GIF dengan nama yang sesuai di folder ini, aplikasi akan langsung otomatis menggantikan bingkai placeholder default dengan animasi Anda tanpa perlu restart server!
