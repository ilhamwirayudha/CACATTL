"""
CACA - Cycle Analysis & Cargo Accelaration Dashboard
Pelindo Terminal Teluk Lamong

Aplikasi analitis berbasis web untuk rekonstruksi siklus truk dermaga,
Tab Simulasi: Simulasi efisiensi operasional Dual Cycle (Two-Way Load), eliminasi ritase kosong, dan penghematan BBM Solar.
"""

import datetime
from pathlib import Path
import time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------
# Konfigurasi Halaman Streamlit (Wajib menjadi perintah Streamlit pertama)
# ----------------------------------------------------------------
st.set_page_config(
    page_title="CACA - Dashboard Analisis Dual Cycle & Twin Lift | Pelindo TTL",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import gc
import modules.charts
import modules.ui

from modules.calculations import (
    AMBANG_COMBO_MENIT_DEFAULT,
    AMBANG_DUAL_MENIT_DEFAULT,
    AMBANG_TWINLIFT_MENIT_DEFAULT,
    SIZE_ELIGIBLE,
    compute_period_bounds,
    extract_period_options_from_events,
    filter_dataset_by_period,
    guess,
    hitung_ringkasan,
    proses_analisis_lengkap,
)
from modules.charts import apply_glass_theme
from modules.data_loader import baca_file, build_excel_data_only
from modules.ui import (
    find_asset_file,
    format_decimal,
    format_number,
    format_percent,
    inject_css,
    inject_transition_script,
    render_artistic_hero,
    render_dual_cycle_kpi_section,
    get_parameter_tooltip,
    render_html,
    render_hybrid_loading_indicator,
    render_kpi_card,
    render_template,
    show_activity_detail_dialog,
    show_combo_detail_dialog,
    show_twinlift_detail_dialog,
)

# ----------------------------------------------------------------
# Path Aset Media & Branding
# ----------------------------------------------------------------
LOGO_CACA_ICON_PATH = find_asset_file([
    "caca-logo.png",
    "caca.png",
    "CACA.png",
    "logo-caca.png",
    "logo_caca.png",
    "caca.webp",
    "caca-logo.webp",
])
LOGO_PATH = find_asset_file([
    "pelindo.png",
    "logo-pelindo.png",
    "logo_pelindo.png",
    "logo.png",
])
HERO_BG_PATH = find_asset_file([
    "DJI_20250716133943_0169_D.JPG",
    "DJI_20250716133714_0162_D.JPG",
    "hero-bg.jpg",
    "hero-bg.png",
    "hero.jpg",
    "hero.png",
])

# ----------------------------------------------------------------
# Injeksi Desain CSS & Komponen Hero Banner Artistik
# ----------------------------------------------------------------
inject_css("style.css")
render_artistic_hero(HERO_BG_PATH, LOGO_CACA_ICON_PATH, LOGO_PATH)
inject_transition_script("transition.js")

# Anchor point untuk smooth scroll dari hero banner
render_html(
    '<div id="langkah-analisis" style="scroll-margin-top: 36px; display: block; width: 100%; height: 1px; visibility: hidden; margin: 0; padding: 0;"></div>'
)

# ----------------------------------------------------------------
# Manajemen Sesi Persisten (Auto-Restore Hasil Analisis Terakhir)
# Menjamin hasil analisis tidak hilang saat browser direfresh (F5)
# ----------------------------------------------------------------
@st.cache_resource
def get_global_session_store() -> dict:
    """Menyimpan data dan hasil komputasi terakhir di memori server agar tahan refresh browser."""
    return {}

session_store = get_global_session_store()
has_stored_session = session_store.get("file_bytes") is not None


# ----------------------------------------------------------------
# Komponen Fragment: Breakdown Bulanan Dual Cycle vs Non Dual
# Diisolasi dengan @st.fragment agar interaksi input & checkbox garis target
# tidak memicu full rerun halaman dan menjaga posisi scroll pengguna tetap stabil.
# ----------------------------------------------------------------
@st.fragment
def render_monthly_breakdown_section(monthly: pd.DataFrame):
    if len(monthly) == 0:
        return

    render_html(
        """
        <style>
        div[data-testid="stHorizontalBlock"]:has(input[aria-label*="Target Optimal"]) {
            justify-content: flex-start !important;
            gap: 16px !important;
            align-items: flex-start !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(#step3-card-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:has(input[aria-label*="Target Optimal"]),
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:has(input[aria-label*="Target Optimal"]),
        div[data-testid="stColumn"]:has(input[aria-label*="Target Optimal"]),
        div[data-testid="column"]:has(input[aria-label*="Target Optimal"]) {
            flex: 0 0 345px !important;
            width: 345px !important;
            max-width: 345px !important;
            min-width: 345px !important;
        }
        div[data-testid="stNumberInput"]:has(input[aria-label*="Target Optimal"]) {
            margin-left: 14px !important;
            margin-top: 40px !important;
            width: 330px !important;
            max-width: 330px !important;
        }
        div[data-testid="stNumberInput"]:has(input[aria-label*="Target Optimal"]) label,
        div[data-testid="stNumberInput"]:has(input[aria-label*="Target Optimal"]) label p,
        div[data-testid="stNumberInput"]:has(input[aria-label*="Target Optimal"]) [data-testid="stWidgetLabel"] p {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            margin-bottom: 5px !important;
            white-space: nowrap !important;
        }
        div[data-testid="stNumberInput"]:has(input[aria-label*="Target Optimal"]) div[data-testid="stNumberInputContainer"] {
            height: 34px !important;
            width: 330px !important;
            max-width: 330px !important;
            border-radius: 8px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(#step3-card-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:has(div[data-testid="stCheckbox"]),
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:has(div[data-testid="stCheckbox"]),
        div[data-testid="stColumn"]:has(div[data-testid="stCheckbox"]),
        div[data-testid="column"]:has(div[data-testid="stCheckbox"]) {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: auto !important;
            max-width: none !important;
        }
        div[data-testid="stCheckbox"] {
            margin-left: 0 !important;
            margin-top: 62px !important;
        }
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p,
        div[data-testid="stCheckbox"] label span {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            white-space: nowrap !important;
        }
        </style>
        <div style="height:36px; min-height:36px; line-height:36px; display:block; clear:both;">&nbsp;</div>
        """
    )
    col_m_input, col_m_check, col_m_space = st.columns([345, 260, 1000], gap="small")
    with col_m_input:
        if "monthly_target_optimal_pct" not in st.session_state:
            st.session_state["monthly_target_optimal_pct"] = 50.0
        target_optimal_pct = st.number_input(
            "Target Optimal (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            format="%.1f",
            key="monthly_target_optimal_pct",
            disabled=not st.session_state.get("show_monthly_target_line", True),
        )
    with col_m_check:
        if "show_monthly_target_line" not in st.session_state:
            st.session_state["show_monthly_target_line"] = True
        show_target_line = st.checkbox(
            "Tampilkan Garis Target",
            key="show_monthly_target_line",
        )

    monthly_dual_pct = monthly.melt(
        id_vars="Bulan",
        value_vars=["pct_dual", "pct_non_dual"],
        var_name="Kategori",
        value_name="Persentase",
    )
    monthly_dual_pct["Kategori"] = monthly_dual_pct["Kategori"].map(
        {"pct_dual": "Dual Cycle", "pct_non_dual": "Non Dual"}
    )
    monthly_dual_pct["Persentase"] = monthly_dual_pct["Persentase"] * 100
    monthly_dual_pct["Label"] = monthly_dual_pct["Persentase"].apply(lambda p: format_percent(p, 1))

    fig_month_dual = px.bar(
        monthly_dual_pct,
        x="Bulan",
        y="Persentase",
        color="Kategori",
        barmode="stack",
        title="Breakdown Bulanan: Dual Cycle vs Non Dual (%)",
        color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
        text="Label",
    )
    fig_month_dual.update_traces(textposition="inside", insidetextanchor="middle")
    fig_month_dual.update_layout(
        xaxis=dict(type="category"),
        yaxis=dict(title="% dari Total Ritase", range=[0, 100]),
    )

    # Garis batas merah target optimal melintang dari kiri ke kanan jika checklist aktif & target ditentukan (> 0)
    if show_target_line and target_optimal_pct is not None and target_optimal_pct > 0:
        fig_month_dual.add_hline(
            y=target_optimal_pct,
            layer="above",
            line_dash="dash",
            line_color="#EF4444",
            line_width=2.5,
            annotation_text=f"Target: {target_optimal_pct:g}%",
            annotation_position="top left",
            annotation_font=dict(family="Plus Jakarta Sans", size=11, color="#ffffff"),
            annotation_bgcolor="rgba(239, 68, 68, 0.85)",
            annotation_bordercolor="rgba(239, 68, 68, 1.0)",
            annotation_borderwidth=1,
        )

    apply_glass_theme(fig_month_dual)
    st.plotly_chart(fig_month_dual, width="stretch")


# ================================================================
# LANGKAH 1 (ATAS): Unggah File Data Operasional
# ================================================================
with st.container(border=True):
    render_html('<div id="step1-card-marker" style="display:none;"></div>')
    u_col1, u_col2 = st.columns([2.4, 1.6], vertical_alignment="center", gap="medium")
    with u_col1:
        render_template("step1_header.html")

    with u_col2:
        uploaded = st.file_uploader(
            "Pilih file data aktivitas kontainer",
            type=["xlsx"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key="file_uploader_widget",
        )
        if uploaded is None:
            if has_stored_session:
                stored_fname = session_store.get("filename", "data_operasional.xlsx")
                status_subtext = "Analisis dipulihkan otomatis" if session_store.get("hasil") is not None else "File siap dianalisis"
                render_html(
                    f'<div class="session-restored-pill">'
                    f'<span class="session-restored-text">📂 <strong>Sesi Aktif:</strong> {stored_fname} &nbsp;•&nbsp; '
                    f'<span style="color:#38bdf8;font-weight:600;">{status_subtext}</span></span>'
                    f'</div>'
                )
                if st.button("✕ Reset & Unggah File Baru", key="btn_reset_session", help="Klik untuk mereset dan mengunggah file baru"):
                    session_store.clear()
                    st.session_state.clear()
                    st.query_params.clear()
                    st.rerun()
            else:
                render_html('<div class="step1-upload-hint">(Khusus format .xlsx &lt;200 MB)</div>')

# Alur Penentuan Sumber Data: Dari file upload baru atau dari sesi tersimpan di server
if uploaded is not None:
    uploaded_name = uploaded.name
    file_bytes = uploaded.getvalue()
    file_sig = (uploaded.name, len(file_bytes), hash(file_bytes[:1_000_000]))
    if st.session_state.get("_last_file_sig") != file_sig:
        st.session_state.pop("hasil", None)
        st.session_state.pop("_cached_sheets", None)
        st.session_state["_last_file_sig"] = file_sig
        session_store.clear()
    session_store["filename"] = uploaded_name
    session_store["file_bytes"] = file_bytes
    session_store["file_sig"] = file_sig
elif has_stored_session:
    # Memulihkan file dan hasil analisis dari memori server (mode semi-database)
    uploaded_name = session_store["filename"]
    file_bytes = session_store["file_bytes"]
    file_sig = session_store["file_sig"]
    if "sheets" in session_store:
        sheets = session_store["sheets"]
        st.session_state["_cached_sheets"] = sheets
    if "hasil" in session_store:
        st.session_state["hasil"] = session_store["hasil"]
        if "_ambang_terakhir" in session_store:
            st.session_state["_ambang_terakhir"] = session_store["_ambang_terakhir"]
        else:
            h_saved = session_store["hasil"]
            st.session_state["_ambang_terakhir"] = (
                int(h_saved.get("ambang_combo", AMBANG_COMBO_MENIT_DEFAULT)),
                int(h_saved.get("ambang_dual", AMBANG_DUAL_MENIT_DEFAULT)),
                int(h_saved.get("ambang_twinlift", AMBANG_TWINLIFT_MENIT_DEFAULT)),
                h_saved.get("period_range"),
            )
    st.session_state["_last_file_sig"] = file_sig

else:
    # Belum ada file atau sesi tersimpan: Berhenti di Langkah 1
    st.session_state.pop("hasil", None)
    st.session_state.pop("_last_file_sig", None)
    st.session_state.pop("_cached_sheets", None)
    st.stop()

# ================================================================
# LANGKAH 2 (TENGAH): Parameter Ambang Batas & Konfigurasi
# ================================================================
# Indikator hybrid loading saat file dibaca pertama kali atau file baru diupload
loading_placeholder = st.empty()

if "_cached_sheets" not in st.session_state:
    def on_read_progress(pct: int, status_text: str, detail_text: str = ""):
        render_hybrid_loading_indicator(
            uploaded_name,
            len(file_bytes),
            pct=pct,
            status_text=status_text,
            detail_text=detail_text,
            placeholder=loading_placeholder,
        )

    try:
        sheets = baca_file(file_bytes, uploaded_name, progress_callback=on_read_progress)
        st.session_state["_cached_sheets"] = sheets
        session_store["sheets"] = sheets
        time.sleep(0.45)
        loading_placeholder.empty()
    except Exception as e:
        loading_placeholder.empty()
        st.error(
            "Gagal membaca file yang diupload. Pastikan file tidak corrupt dan "
            "formatnya benar-benar file Excel (.xlsx)."
        )
        with st.expander("Detail error (untuk dilaporkan)"):
            st.exception(e)
        st.stop()
else:
    sheets = st.session_state["_cached_sheets"]
    session_store["sheets"] = sheets

if not sheets:
    st.error("File tidak berisi sheet/data apa pun.")
    st.stop()

sheet_name = None
raw = None

with st.container(border=True):
    render_template("step2_header.html")

    sheet_keys = list(sheets.keys())
    sheet_name = sheet_keys[0]
    raw = sheets[sheet_name]

    # Deteksi rentang tanggal dari data sheet
    cand_cols = list(raw.columns)
    ts_g_cand_idx = guess(cand_cols, ["disc_load", "disc_loading", "waktu", "time", "date"])
    ts_g_col_cand = cand_cols[ts_g_cand_idx]
    raw_dummy_ts = pd.DataFrame({"START_TS": raw[ts_g_col_cand]})
    _, _, _, step2_min_d, step2_max_d = extract_period_options_from_events(raw_dummy_ts)

    # ----------------------------------------------------------------
    # Filter Periode Data Operasional yang Mau Ditampilkan (Datepicker)
    # ----------------------------------------------------------------
    if not step2_min_d or not step2_max_d:
        st.info(f"📅 Menampilkan seluruh data ({format_number(len(raw))} baris kontainer)")
        st.session_state["_init_period_range"] = None
        st.session_state["_init_period_label"] = "Semua Tanggal Data"
    else:
        default_range = (step2_min_d, step2_max_d)

        step2_date_val = st.date_input(
            "Rentang Tanggal (Mulai - Selesai):",
            value=default_range,
            min_value=step2_min_d,
            max_value=step2_max_d,
            format="DD/MM/YYYY",
            key="step2_date_range_picker",
            help="Pilih rentang tanggal yang ingin dianalisis",
        )

        if isinstance(step2_date_val, (tuple, list)):
            if len(step2_date_val) == 2:
                r_start, r_end = step2_date_val
                if r_start > r_end:
                    r_start, r_end = r_end, r_start
                n_days = (r_end - r_start).days + 1
                lbl = f"({r_start.strftime('%d/%m/%Y')}) - ({r_end.strftime('%d/%m/%Y')}) ({format_number(n_days)} Hari)"
                rng = (r_start, r_end)

                st.session_state["_init_period_range"] = rng
                st.session_state["_init_period_label"] = lbl
            elif len(step2_date_val) == 1:
                # Pemilihan sedang berlangsung (baru memilih 1 tanggal)
                r_single = step2_date_val[0]
                st.session_state["_init_period_range"] = (r_single, r_single)
                st.session_state["_init_period_label"] = f"({r_single.strftime('%d/%m/%Y')}) (1 Hari)"
        else:
            r_single = step2_date_val
            st.session_state["_init_period_range"] = (r_single, r_single)
            st.session_state["_init_period_label"] = f"({r_single.strftime('%d/%m/%Y')}) (1 Hari)"

    # Baris 2: 3 Kolom Parameter Ambang Batas Berjejer Horizontal
    def_combo = int(st.session_state.get("hasil", {}).get("ambang_combo", AMBANG_COMBO_MENIT_DEFAULT))
    def_dual = int(st.session_state.get("hasil", {}).get("ambang_dual", AMBANG_DUAL_MENIT_DEFAULT))
    def_twin = int(st.session_state.get("hasil", {}).get("ambang_twinlift", AMBANG_TWINLIFT_MENIT_DEFAULT))

    th1, th2, th3 = st.columns([1, 1, 1], gap="medium")
    with th1:
        ambang_combo = st.number_input(
            "Ambang Combo (menit)",
            min_value=1,
            value=def_combo,
            step=1,
            help=get_parameter_tooltip("combo"),
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Gap 2 container 20ft pada truk yang sama</div>'
        )

    with th2:
        ambang_dual = st.number_input(
            "Parameter Dual Cycle (menit)",
            min_value=1,
            value=def_dual,
            step=10,
            help=get_parameter_tooltip("dual_cycle"),
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Waktu konfirmasi angkat dan angkut kontainer di truk</div>'
        )

    with th3:
        ambang_twinlift = st.number_input(
            "Ambang Twinlift (menit)",
            min_value=1,
            value=def_twin,
            step=1,
            help=get_parameter_tooltip("twinlift"),
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Gap waktu konfirmasi 2 kontainer 20ft</div>'
        )

    # Pemetaan Kolom Otomatis
    cols = list(raw.columns)
    col_map = {
        "ves_id": cols[guess(cols, ["ves", "kapal", "vessel"])],
        "size": cols[guess(cols, ["size", "ctr_size", "ukuran"])],
        "truck": cols[guess(cols, ["car_che", "truck", "che", "trailer", "truk"])],
        "activity": cols[guess(cols, ["activity", "aktivitas", "aktifitas", "act"])],
        "ts_g": cols[guess(cols, ["disc_load", "disc_loading", "waktu", "time", "date"])],
        "ts_h": cols[guess(cols, ["stack_unstack", "unstack_stack", "waktu", "time", "date"])],
    }

    # Pemetaan Kolom Crane (QC) — dipakai sebagai syarat tambahan 'sama crane'
    # pada deteksi Twinlift, serta laporan performa Twinlift per Crane.
    # Dikecualikan dari kandidat: kolom yang sudah dipakai sebagai kolom truk
    # (mis. skema 'CHE_ID' vs 'CAR_CHE_ID' — keduanya sama-sama mengandung 'che').
    truck_col_terpilih = col_map["truck"]
    crane_kandidat = [c for c in cols if c != truck_col_terpilih]
    crane_keywords = ["crane", "qc_id", "qc", "gantry", "quay", "che_id", "che"]
    if crane_kandidat:
        nama_tebakan_crane = crane_kandidat[guess(crane_kandidat, crane_keywords)]
        col_map["crane"] = nama_tebakan_crane
    else:
        col_map["crane"] = None

    # Validasi integritas cache hasil analisis & deteksi perubahan parameter ambang
    CALC_VERSION = "v1.4_simulasi_tab"
    auto_recompute = False

    curr_params = (
        int(ambang_combo),
        int(ambang_dual),
        int(ambang_twinlift),
        st.session_state.get("_init_period_range"),
    )

    if "hasil" in st.session_state:
        _cached_out_df = st.session_state["hasil"].get("out_df")
        if _cached_out_df is None or st.session_state.get("_calc_ver") != CALC_VERSION:
            st.session_state.pop("hasil", None)
            session_store.pop("hasil", None)
            auto_recompute = True
        elif (
            st.session_state.get("_ambang_terakhir") is not None
            and st.session_state.get("_ambang_terakhir") != curr_params
        ):
            auto_recompute = True

    # Tombol Eksekusi di Bagian Paling Bawah Container Langkah 2 (Ukuran Ringkas & Center)
    render_html('<div style="height:6px;"></div>')
    b_col1, b_col2, b_col3 = st.columns([1.4, 1.2, 1.4])
    with b_col2:
        run = st.button("Jalankan Analisis", type="primary", use_container_width=True)
    if auto_recompute:
        run = True

# Jika belum dijalankan dan belum ada hasil: Berhenti di sini
if not run and "hasil" not in st.session_state:
    st.stop()

# Eksekusi Komputasi Analisis
if run:
    loading_calc_placeholder = st.empty()

    def on_calc_progress(pct: int, status_text: str, detail_text: str = ""):
        render_hybrid_loading_indicator(
            uploaded_name,
            len(file_bytes),
            pct=pct,
            status_text=status_text,
            detail_text=detail_text,
            placeholder=loading_calc_placeholder,
        )

    try:
        status_msg = "Memperbarui analisis parameter..." if auto_recompute else "Memulai analisis..."
        detail_msg = "Menghitung ulang data dengan parameter baru" if auto_recompute else "Inisialisasi pipeline komputasi"
        on_calc_progress(6, status_msg, detail_msg)

        # Filter dataset mentah sebelum komputasi jika pengguna memilih rentang tanggal tertentu di Step 2
        raw_to_process = raw
        init_range = st.session_state.get("_init_period_range")
        if init_range is not None:
            r_start, r_end = init_range
            ts_col = col_map["ts_g"]
            ts_series = pd.to_datetime(raw_to_process[ts_col], errors="coerce", dayfirst=True)
            if ts_series.isna().any() and col_map.get("ts_h"):
                ts_h_series = pd.to_datetime(raw_to_process[col_map["ts_h"]], errors="coerce", dayfirst=True)
                ts_series = ts_series.fillna(ts_h_series)
            start_dt = pd.to_datetime(r_start)
            end_dt = pd.to_datetime(r_end) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
            date_mask = (ts_series >= start_dt) & (ts_series <= end_dt)
            raw_to_process = raw_to_process[date_mask].copy()

            if len(raw_to_process) == 0:
                loading_calc_placeholder.empty()
                st.error(
                    f"Tidak ada data kontainer pada rentang tanggal "
                    f"{st.session_state.get('_init_period_label', '')}. "
                    f"Silakan sesuaikan kembali pemilihan rentang tanggal di Langkah 2."
                )
                st.stop()

        out_df, events, summary = proses_analisis_lengkap(
            raw_to_process,
            col_map,
            SIZE_ELIGIBLE,
            ambang_combo,
            ambang_dual,
            ambang_twinlift,
            progress_callback=on_calc_progress,
        )
        time.sleep(0.45)
        loading_calc_placeholder.empty()
        gc.collect()

        if out_df is None or len(out_df) == 0:
            st.error(
                "Setelah pembersihan, tidak ada baris data yang tersisa. "
                "Kemungkinan kolom waktu DISC_LOAD_TS & STACK_UNSTACK_TS tidak valid."
            )
            st.stop()
    except Exception as e:
        loading_calc_placeholder.empty()
        st.error("Terjadi error saat memproses data.")
        with st.expander("Detail error (untuk dilaporkan)", expanded=True):
            st.exception(e)
        st.stop()

    st.session_state["hasil"] = {
        "out_df": out_df,
        "events": events,
        "summary": summary,
        "ambang_combo": ambang_combo,
        "ambang_dual": ambang_dual,
        "ambang_twinlift": ambang_twinlift,
        "period_label": st.session_state.get("_init_period_label", "Seluruh Data Excel"),
        "period_range": st.session_state.get("_init_period_range"),
    }
    st.session_state["_ambang_terakhir"] = curr_params
    st.session_state["_calc_ver"] = CALC_VERSION

    # Simpan hasil komputasi ke session_store server agar persisten terhadap refresh browser (F5)
    session_store["hasil"] = st.session_state["hasil"]
    session_store["_ambang_terakhir"] = curr_params
    session_store["sheets"] = sheets
    session_store["filename"] = uploaded_name
    session_store["file_bytes"] = file_bytes
    session_store["file_sig"] = file_sig


hasil = st.session_state["hasil"]
out_df = hasil["out_df"]
events = hasil["events"]
summary = hasil["summary"]

# ================================================================
# LANGKAH 3: EXECUTIVE KPI & HASIL ANALISIS
# ================================================================
with st.container(border=True):
    # Sinkronisasi label periode secara dinamis jika rentang tanggal sesuai dengan hasil komputasi
    curr_label = st.session_state.get("_init_period_label")
    curr_rng = st.session_state.get("_init_period_range")
    if curr_label and hasil.get("period_range") == curr_rng:
        hasil["period_label"] = curr_label
        if "hasil" in session_store:
            session_store["hasil"]["period_label"] = curr_label

    period_lbl = hasil.get("period_label", curr_label or "Seluruh Data Excel")
    render_template("step3_header.html", period_label=period_lbl)

    # Otomatis menggeser atau memulihkan posisi scroll ke Langkah 3 / posisi sebelumnya saat refresh atau komputasi
    scroll_behavior = "smooth" if run else "instant"
    components.html(
        f"""
        <script>
        (function() {{
            function doScrollRestore() {{
                try {{
                    var win = window.parent || window;
                    if (win && win.restoreCacaScroll) {{
                        win.restoreCacaScroll('{scroll_behavior}');
                    }} else if (win && win.triggerScrollToStep3) {{
                        win.triggerScrollToStep3();
                    }}
                }} catch(e) {{}}
            }}
            doScrollRestore();
            setTimeout(doScrollRestore, 50);
            setTimeout(doScrollRestore, 150);
            setTimeout(doScrollRestore, 350);
            setTimeout(doScrollRestore, 700);
            setTimeout(doScrollRestore, 1200);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

    monthly = summary["monthly"].reset_index().rename(columns={"BULAN": "Bulan"})
    # Basis kontainer 20ft — dipakai untuk breakdown Combo/Single & Twinlift/Bukan
    # Twinlift, karena keduanya secara definisi cuma mungkin terjadi di 20ft.
    monthly_20ft = summary["monthly_20ft"].reset_index().rename(columns={"BULAN": "Bulan"})

    # 4 Tab Hasil Analisis: Dual Cycle, Twinlift, Simulasi, Download Hasil Analisis
    TAB_OPTIONS = ["Dual Cycle", "Twinlift", "Simulasi", "Download Hasil Analisis"]

    # Inisialisasi atau sinkronisasi tab aktif dari query parameter (agar persisten saat F5 / reload)
    url_tab = st.query_params.get("tab")
    if url_tab in TAB_OPTIONS:
        if st.session_state.get("active_analysis_tab") != url_tab:
            st.session_state["active_analysis_tab"] = url_tab
    elif "active_analysis_tab" not in st.session_state:
        st.session_state["active_analysis_tab"] = "Dual Cycle"

    # Pastikan tab yang tersimpan valid
    if st.session_state.get("active_analysis_tab") not in TAB_OPTIONS:
        st.session_state["active_analysis_tab"] = "Dual Cycle"

    def _on_tab_change():
        new_tab = st.session_state.get("active_analysis_tab")
        if new_tab in TAB_OPTIONS:
            st.query_params["tab"] = new_tab

    active_tab = st.radio(
        "Pilih Tab Analisis",
        options=TAB_OPTIONS,
        horizontal=True,
        key="active_analysis_tab",
        on_change=_on_tab_change,
        label_visibility="collapsed",
    )

    # Pastikan URL query parameter selalu sinkron dengan tab aktif
    if st.query_params.get("tab") != active_tab:
        st.query_params["tab"] = active_tab

    # ----------------------------------------------------------------
    # TAB 1: DUAL CYCLE
    # ----------------------------------------------------------------
    if active_tab == "Dual Cycle":
        # Mini Card KPI Interaktif (Default 5 kartu, klik Total Petikemas untuk menampilkan Container LOAD & DISC)
        render_dual_cycle_kpi_section(summary)

        cc1, cc2 = st.columns(2)
        with cc1:
            pie_df = pd.DataFrame(
                {"Status": ["Dual Cycle", "Non Dual"], "Jumlah": [summary["total_dual"], summary["total_single"]]}
            )
            pie_df = pie_df[pie_df["Jumlah"] > 0]
            fig_pie = px.pie(
                pie_df,
                names="Status",
                values="Jumlah",
                hole=0.52,
                title="Dual Cycle vs Non Dual",
                color="Status",
                color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
                custom_data=["Status"],
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                textposition="inside",
                insidetextorientation="horizontal",
                textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                marker=dict(line=dict(color="#ffffff", width=2)),
                hovertemplate="<b>%{label}</b><br>Jumlah: %{value:,.0f} ritase (%{percent})<extra></extra>",
            )
            apply_glass_theme(fig_pie)
            fig_pie.update_layout(
                height=380,
                margin=dict(t=60, b=20, l=20, r=20),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                ),
            )

            # Render chart donut
            st.plotly_chart(
                fig_pie,
                use_container_width=True,
                key="donut_dual_cycle_chart",
            )

            # Tombol aksi langsung untuk membuka rincian modal
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🔍 Rincian Dual Cycle", use_container_width=True, key="btn_quick_dual_detail"):
                    st.session_state["modal_activity_status"] = "Dual Cycle"
                    st.session_state["show_activity_modal"] = True
                    st.rerun()

            with col_b2:
                if st.button("🔍 Rincian Non Dual", use_container_width=True, key="btn_quick_non_dual_detail"):
                    st.session_state["modal_activity_status"] = "Non Dual"
                    st.session_state["show_activity_modal"] = True
                    st.rerun()

            # Tampilkan Pop-up Dialog Modal jika dipicu
            if st.session_state.get("show_activity_modal") and st.session_state.get("modal_activity_status"):
                status_to_open = st.session_state["modal_activity_status"]
                st.session_state["show_activity_modal"] = False
                show_activity_detail_dialog(status_to_open, events, out_df, summary)

        with cc2:
            # FIX LOGIKA: Combo cuma mungkin terjadi pada kontainer 20ft, jadi
            # breakdown Combo vs Single di sini dihitung dari basis kontainer
            # 20ft SAJA — bukan dari seluruh kontainer (yang dulu bikin %
            # Combo terlihat kecil secara palsu karena tercampur 40ft dst).
            combo20_df = pd.DataFrame(
                {"Status": ["Combo", "Single"], "Jumlah": [summary["combo_20ft"], summary["single_20ft"]]}
            )
            combo20_df = combo20_df[combo20_df["Jumlah"] > 0]
            if len(combo20_df) > 0:
                fig_combo20 = px.pie(
                    combo20_df,
                    names="Status",
                    values="Jumlah",
                    hole=0.52,
                    title="Combo vs Single (Kontainer 20ft)",
                    color="Status",
                    color_discrete_map={"Combo": "#0EA5E9", "Single": "#64748B"},
                )
                fig_combo20.update_traces(
                    textinfo="percent+label",
                    textposition="inside",
                    insidetextorientation="horizontal",
                    textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                    marker=dict(line=dict(color="#ffffff", width=2)),
                    hovertemplate="<b>%{label}</b><br>Jumlah: %{value:,.0f} kontainer (%{percent})<extra></extra>",
                )
                apply_glass_theme(fig_combo20)
                fig_combo20.update_layout(
                    height=380,
                    margin=dict(t=60, b=20, l=20, r=20),
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.02,
                    ),
                )
                st.plotly_chart(fig_combo20, use_container_width=True, key="donut_combo_single_chart")

                # Tombol aksi langsung untuk membuka rincian modal Combo & Single
                col_cb1, col_cb2 = st.columns(2)
                with col_cb1:
                    if st.button("🔍 Rincian Combo", use_container_width=True, key="btn_quick_combo_detail"):
                        st.session_state["modal_combo_status"] = "Combo"
                        st.session_state["show_combo_modal"] = True
                        st.rerun()

                with col_cb2:
                    if st.button("🔍 Rincian Single", use_container_width=True, key="btn_quick_single_detail"):
                        st.session_state["modal_combo_status"] = "Single"
                        st.session_state["show_combo_modal"] = True
                        st.rerun()

                # Tampilkan Pop-up Dialog Modal jika dipicu
                if st.session_state.get("show_combo_modal") and st.session_state.get("modal_combo_status"):
                    status_to_open = st.session_state["modal_combo_status"]
                    st.session_state["show_combo_modal"] = False
                    show_combo_detail_dialog(status_to_open, out_df, events, summary)
            else:
                st.info("Tidak ada kontainer 20ft pada data ini.")

        if len(monthly) > 0:
            render_monthly_breakdown_section(monthly)

        if len(monthly_20ft) > 0:
            # FIX LOGIKA: % Combo/Single bulanan sekarang dihitung dari basis
            # kontainer 20ft (monthly_20ft), bukan dari seluruh event/kontainer.
            monthly_container_pct = monthly_20ft.melt(
                id_vars="Bulan",
                value_vars=["pct_combo", "pct_single"],
                var_name="Kategori",
                value_name="Persentase",
            )
            monthly_container_pct["Kategori"] = monthly_container_pct["Kategori"].map(
                {"pct_combo": "Combo", "pct_single": "Single"}
            )
            monthly_container_pct["Persentase"] = monthly_container_pct["Persentase"] * 100
            monthly_container_pct["Label"] = monthly_container_pct["Persentase"].apply(lambda p: format_percent(p, 1))

            fig_month_container = px.bar(
                monthly_container_pct,
                x="Bulan",
                y="Persentase",
                color="Kategori",
                barmode="stack",
                title="Breakdown Bulanan: Combo vs Single (% dari Kontainer 20ft)",
                color_discrete_map={"Combo": "#0EA5E9", "Single": "#64748B"},
                text="Label",
            )
            fig_month_container.update_traces(textposition="inside", insidetextanchor="middle")
            fig_month_container.update_layout(
                xaxis=dict(type="category"),
                yaxis=dict(title="% dari Kontainer 20ft", range=[0, 100]),
            )
            apply_glass_theme(fig_month_container)
            st.plotly_chart(fig_month_container, width="stretch")
        else:
            st.info("Tidak ada kontainer 20ft pada data ini untuk breakdown bulanan Combo/Single.")

        # --------------------------------------------------------
        # Breakdown Dual Cycle: Per Shift
        # --------------------------------------------------------
        render_html('<div style="height:8px;"></div>')
        shift_df = summary["shift"]

        # --- Chart 1: Dual vs Non Dual per Shift (jumlah + persentase) ---
        if len(shift_df) > 0:
            shift_pct = shift_df.melt(
                id_vars="SHIFT",
                value_vars=["dual", "non_dual"],
                var_name="Kategori",
                value_name="Jumlah",
            )
            shift_pct["Kategori"] = shift_pct["Kategori"].map(
                {"dual": "Dual Cycle", "non_dual": "Non Dual"}
            )
            shift_pct["Total_Shift"] = shift_pct.groupby("SHIFT")["Jumlah"].transform("sum")
            shift_pct["Persen"] = np.where(
                shift_pct["Total_Shift"] > 0, shift_pct["Jumlah"] / shift_pct["Total_Shift"] * 100, 0
            )
            shift_pct["Label"] = (
                shift_pct["Jumlah"].apply(format_number)
                + " ("
                + shift_pct["Persen"].apply(lambda p: format_percent(p, 1))
                + ")"
            )

            fig_shift = px.bar(
                shift_pct,
                x="SHIFT",
                y="Jumlah",
                color="Kategori",
                barmode="stack",
                title="Dual Cycle vs Non Dual per Shift (Jumlah & %)",
                color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
                text="Label",
            )
            fig_shift.update_traces(textposition="inside", insidetextanchor="middle")
            fig_shift.update_layout(xaxis=dict(title=""), yaxis=dict(title="Jumlah Ritase"))
            apply_glass_theme(fig_shift)
            st.plotly_chart(fig_shift, width="stretch")
        else:
            st.info("Tidak ada data shift pada hasil analisis ini.")

    # ----------------------------------------------------------------
    # TAB 2: TWINLIFT
    # ----------------------------------------------------------------
    elif active_tab == "Twinlift":
        # FIX LOGIKA: info "Total Event"/ritase dihapus dari tab ini karena
        # tidak ada hubungannya dengan Twinlift (Twinlift adalah properti
        # per-kontainer, bukan per-ritase truk). Yang relevan cukup: jumlah
        # total kontainer, jumlah yang 20ft, dan Twinlift/Bukan Twinlift
        # dihitung sebagai persentase dari kontainer 20ft SAJA.
        total_kontainer_20ft = summary["total_20ft"]
        total_twinlift_kontainer = summary["total_twinlift_kontainer"]
        total_bukan_twinlift_kontainer = summary["total_bukan_twinlift_kontainer"]
        pct_twinlift_20ft_val = summary["pct_twinlift_of_20ft"] * 100

        t1, t2, t3, t4, t5 = st.columns(5)
        with t1:
            render_kpi_card(
                "Total Kontainer",
                format_number(summary["container_total"]),
                subtext="Semua Ukuran (20ft, 40ft, 45ft)",                
                variant="purple",
                tooltip="Total seluruh kontainer (20ft, 40ft, 45ft).",
            )
        with t2:
            render_kpi_card(
                "Jumlah 20ft",
                format_number(total_kontainer_20ft),
                subtext=f"{format_percent(summary['pct_20ft_of_total'] * 100)} dari Total Kontainer",
                variant="amber",
                tooltip="Jumlah kontainer 20ft.",
            )
        with t3:
            render_kpi_card(
                "Twinlift",
                format_number(total_twinlift_kontainer),
                subtext="dari Kontainer 20ft",
                variant="blue",
                tooltip="Jumlah kontainer 20ft yang bisa diangkat secara bersamaan.",
            )
        with t4:
            render_kpi_card(
                "Bukan Twinlift",
                format_number(total_bukan_twinlift_kontainer),
                subtext="dari Kontainer 20ft",
                variant="slate",
                tooltip="Jumlah kontainer 20ft yang tidak diangkat secara bersamaan.",
            )
        with t5:
            render_kpi_card(
                "% Twinlift",
                format_percent(pct_twinlift_20ft_val),
                subtext="Basis Kontainer 20ft",
                variant="blue",
                tooltip="Persentase kontainer 20ft yang diangkat secara bersamaan (Twinlift ÷ Total 20ft × 100%).",
                align_tooltip_right=True,
            )

        tc1, tc2 = st.columns(2)
        with tc1:
            if total_kontainer_20ft > 0:
                twin_df = pd.DataFrame(
                    {
                        "Status": ["Twinlift", "Bukan Twinlift"],
                        "Jumlah": [total_twinlift_kontainer, total_bukan_twinlift_kontainer],
                    }
                )
                twin_df = twin_df[twin_df["Jumlah"] > 0]
                fig_twin_pie = px.pie(
                    twin_df,
                    names="Status",
                    values="Jumlah",
                    hole=0.52,
                    title="Twinlift vs Bukan Twinlift (dari Kontainer 20ft)",
                    color="Status",
                    color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                )
                fig_twin_pie.update_traces(
                    textinfo="percent+label",
                    textposition="inside",
                    insidetextorientation="horizontal",
                    textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                    marker=dict(line=dict(color="#ffffff", width=2)),
                    hovertemplate="<b>%{label}</b><br>Jumlah: %{value:,.0f} kontainer (%{percent})<extra></extra>",
                )
                apply_glass_theme(fig_twin_pie)
                fig_twin_pie.update_layout(
                    height=380,
                    margin=dict(t=60, b=20, l=20, r=20),
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.02,
                    ),
                )
                st.plotly_chart(fig_twin_pie, use_container_width=True, key="donut_twinlift_chart")

                # Tombol aksi langsung untuk membuka rincian modal Twinlift & Bukan Twinlift
                col_tw1, col_tw2 = st.columns(2)
                with col_tw1:
                    if st.button("🔍 Rincian Twinlift", use_container_width=True, key="btn_quick_twinlift_detail"):
                        st.session_state["modal_twinlift_status"] = "Twinlift"
                        st.session_state["show_twinlift_modal"] = True
                        st.rerun()

                with col_tw2:
                    if st.button("🔍 Rincian Bukan Twinlift", use_container_width=True, key="btn_quick_non_twinlift_detail"):
                        st.session_state["modal_twinlift_status"] = "Bukan Twinlift"
                        st.session_state["show_twinlift_modal"] = True
                        st.rerun()
            else:
                st.info("Tidak ada kontainer 20ft pada data ini.")

        with tc2:
            if len(monthly_20ft) > 0:
                monthly_twin_pct = monthly_20ft.melt(
                    id_vars="Bulan",
                    value_vars=["pct_twinlift", "pct_bukan_twinlift"],
                    var_name="Kategori",
                    value_name="Persentase",
                )
                monthly_twin_pct["Kategori"] = monthly_twin_pct["Kategori"].map(
                    {"pct_twinlift": "Twinlift", "pct_bukan_twinlift": "Bukan Twinlift"}
                )
                monthly_twin_pct["Persentase"] = monthly_twin_pct["Persentase"] * 100
                monthly_twin_pct["Label"] = monthly_twin_pct["Persentase"].apply(lambda p: format_percent(p, 1))

                # Format sumbu X dari 'YYYY-MM' (contoh: '2026-01') menjadi 'YY-Mon' (contoh: '26-Jan', '26-Feb')
                order_bulan_twin = [pd.to_datetime(b).strftime("%y-%b") for b in monthly_20ft["Bulan"].unique()]
                monthly_twin_pct["Bulan"] = pd.to_datetime(monthly_twin_pct["Bulan"]).dt.strftime("%y-%b")

                fig_month_twin = px.bar(
                    monthly_twin_pct,
                    x="Bulan",
                    y="Persentase",
                    color="Kategori",
                    barmode="stack",
                    title="Breakdown Bulanan: Twinlift vs Bukan Twinlift (% dari Kontainer 20ft)",
                    color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                    category_orders={"Bulan": order_bulan_twin},
                    text="Label",
                )
                fig_month_twin.update_traces(textposition="inside", insidetextanchor="middle")
                fig_month_twin.update_layout(
                    xaxis=dict(type="category", categoryorder="array", categoryarray=order_bulan_twin),
                    yaxis=dict(title="% dari Kontainer 20ft", range=[0, 100]),
                )
                apply_glass_theme(fig_month_twin)
                st.plotly_chart(fig_month_twin, width="stretch")
            else:
                st.info("Tidak ada kontainer 20ft pada data ini untuk breakdown bulanan.")

        # Tampilkan Pop-up Dialog Modal jika dipicu
        if st.session_state.get("show_twinlift_modal") and st.session_state.get("modal_twinlift_status"):
            status_twin_to_open = st.session_state["modal_twinlift_status"]
            st.session_state["show_twinlift_modal"] = False
            show_twinlift_detail_dialog(status_twin_to_open, out_df, summary)

        # --------------------------------------------------------
        # Performa Crane (QC) dalam Twinlift — basis 20ft
        # --------------------------------------------------------
        render_html('<div style="height:12px;"></div>')

        crane_perf = summary["crane_performa"]
        crane_tidak_terpetakan = (
            len(crane_perf) == 0
            or (len(crane_perf) == 1 and crane_perf.iloc[0]["CRANE_ID"] == "(Tidak Diketahui)")
        )

        if crane_tidak_terpetakan:
            st.info(
                "Kolom Crane belum dipetakan dari data sumber, sehingga performa per crane "
                "belum bisa dihitung. Atur kolom Crane di bagian \"Pengaturan Lanjutan\" pada "
                "Langkah 2, lalu jalankan ulang analisis."
            )
        else:
            # Filter hanya crane yang memiliki aktivitas Twinlift (> 0) agar crane kade domestik (01D-05D) yang selalu 0% tidak memenuhi chart
            crane_perf_valid = crane_perf[(crane_perf["total_20ft"] > 0) & (crane_perf["total_twinlift"] > 0)].copy()
            top_n = min(15, len(crane_perf_valid))

            if top_n == 0:
                st.info("Tidak ada crane dengan aktivitas Twinlift pada data ini.")
            else:
                crane_chart_df = (
                    crane_perf_valid.sort_values("pct_twinlift_dari_20ft", ascending=False).head(top_n).copy()
                )
                crane_chart_df["Label_Twin"] = (crane_chart_df["pct_twinlift_dari_20ft"] * 100).apply(lambda p: format_percent(p, 1))

                fig_crane = px.bar(
                    crane_chart_df.sort_values("pct_twinlift_dari_20ft"),
                    x="pct_twinlift_dari_20ft",
                    y="CRANE_ID",
                    orientation="h",
                    title=f"Top {top_n} Crane Berdasarkan % Twinlift (dari 20ft)",
                    text="Label_Twin",
                    color="pct_twinlift_dari_20ft",
                    color_continuous_scale=["#94A3B8", "#0284C7"],
                )
                fig_crane.update_traces(texttemplate="%{text}", textposition="outside", cliponaxis=False)
                fig_crane.update_layout(
                    xaxis=dict(title="% Twinlift (dari 20ft)", tickformat=".0%", range=[0, 1.15]),
                    yaxis=dict(title=""),
                    coloraxis_showscale=False,
                )
                apply_glass_theme(fig_crane)
                st.plotly_chart(fig_crane, width="stretch")

                render_html('<div style="height:12px;"></div>')
                st.markdown(
                    '<span style="font-size: 14px; font-weight: 700; color: #ffffff; font-family: \'Plus Jakarta Sans\', sans-serif; display: inline-block; margin-bottom: 6px;">Tabel Breakdown Performa Twinlift per Crane (QC)</span>',
                    unsafe_allow_html=True,
                )

                crane_table_df = crane_perf[crane_perf["total_twinlift"] > 0].copy()
                crane_disp = crane_table_df.rename(
                    columns={
                        "CRANE_ID": "Crane",
                        "total_kontainer": "Total Kontainer",
                        "total_20ft": "Total 20ft",
                        "total_twinlift": "Twinlift",
                    }
                ).copy()
                crane_disp["Total Kontainer"] = crane_disp["Total Kontainer"].apply(format_number)
                crane_disp["Total 20ft"] = crane_disp["Total 20ft"].apply(format_number)
                crane_disp["Twinlift"] = crane_disp["Twinlift"].apply(format_number)
                crane_disp["% Twinlift (dari 20ft)"] = (crane_disp["pct_twinlift_dari_20ft"] * 100).apply(lambda x: format_percent(x, 1))
                crane_disp["% Twinlift (dari Total)"] = (crane_disp["pct_twinlift_dari_total"] * 100).apply(lambda x: format_percent(x, 1))
                st.dataframe(
                    crane_disp[
                        [
                            "Crane",
                            "Total Kontainer",
                            "Total 20ft",
                            "Twinlift",
                            "% Twinlift (dari 20ft)",
                            "% Twinlift (dari Total)",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=240,
                )

    # ----------------------------------------------------------------
    # TAB 3: SIMULASI POTENSI
    # ----------------------------------------------------------------
    elif active_tab == "Simulasi":
        # --------------------------------------------------------
        # Ambil Ground Truth 100% dari File Terupload yang Dianalisis
        # --------------------------------------------------------
        act_dual_count = int(summary.get("total_dual", 0))
        act_single_count = int(summary.get("total_single", 0))
        act_total_ritase = act_dual_count + act_single_count
        act_pct_dual = (act_dual_count / act_total_ritase * 100.0) if act_total_ritase > 0 else 50.0
        act_pct_non_dual = 100.0 - act_pct_dual

        default_baseline_ritase = act_total_ritase if act_total_ritase > 0 else 659

        # Panel Parameter Interaktif (Ukuran Input Field & Judul Terposisi Simetris)
        col_f1, col_f2, col_f3 = st.columns(3, gap="medium")
        with col_f1:
            st.markdown(
                '<div style="font-size: 0.92rem; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">'
                '<span>⚙️</span> Parameter Asumsi BBM & Biaya'
                '</div>',
                unsafe_allow_html=True,
            )
            bbm_per_rit_input = st.number_input(
                "Rata-rata BBM (L/Rit)",
                min_value=0.10,
                max_value=25.00,
                value=3.52,
                step=0.05,
                format="%.2f",
                key="sim_bbm_per_rit",
                help="Konsumsi rata-rata bahan bakar per ritase truk (acuan baseline: 2.322,3 Liter / 659 Rit = 3,52 L/Rit).",
            )
            render_html(
                '<div class="step2-param-hint" style="font-size:0.72rem;color:#94a3b8;margin-top:-6px;line-height:1.3;">'
                'Konsumsi solar truk</div>'
            )

        with col_f2:
            st.markdown(
                '<div style="font-size: 0.92rem; font-weight: 700; color: transparent; margin-bottom: 8px; user-select: none;">'
                '&nbsp;'
                '</div>',
                unsafe_allow_html=True,
            )
            harga_solar_input = st.number_input(
                "Harga Solar (Rp/L)",
                min_value=5000,
                max_value=50000,
                value=15000,
                step=500,
                format="%d",
                key="sim_harga_solar",
                help="Estimasi harga solar industri operasional per liter untuk perhitungan dampak finansial.",
            )
            render_html(
                '<div class="step2-param-hint" style="font-size:0.72rem;color:#94a3b8;margin-top:-6px;line-height:1.3;">'
                'Tarif per liter BBM</div>'
            )

        with col_f3:
            st.markdown(
                '<div style="font-size: 0.92rem; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">'
                '<span>🎯</span> Target Penetrasi Dual Cycle'
                '</div>',
                unsafe_allow_html=True,
            )

            # Sinkronisasi nilai default isian ketik dengan data file yang sedang aktif dianalisis
            current_file_key = f"{act_total_ritase}_{act_dual_count}_{act_single_count}"
            if st.session_state.get("sim_synced_file_key") != current_file_key or "sim_penetrasi_input" not in st.session_state:
                st.session_state["sim_synced_file_key"] = current_file_key
                st.session_state["sim_penetrasi_input"] = float(round(act_pct_dual, 1))

            # Pastikan nilai di session_state berada dalam batas valid 0.0 - 100.0
            st.session_state["sim_penetrasi_input"] = max(0.0, min(100.0, float(st.session_state["sim_penetrasi_input"])))

            sim_penetrasi_pct = st.number_input(
                "Target Penetrasi (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                key="sim_penetrasi_input",
                help=f"Ketikkan persentase target Dual Cycle yang ingin disimulasikan (kondisi aktual file: {act_pct_dual:.1f}% / {format_number(act_dual_count)} rit).",
            )
            render_html(
                f'<div class="step2-param-hint" style="font-size:0.72rem;color:#94a3b8;margin-top:-6px;line-height:1.3;">'
                f'Aktual kapal: <strong style="color:#38bdf8;">{act_pct_dual:.1f}% ({format_number(act_dual_count)} Rit)</strong></div>'
            )

        # Delta dihitung terhadap KONDISI AKTUAL FILE TERUPLOAD
        delta_pct_from_act = sim_penetrasi_pct - act_pct_dual

        # --------------------------------------------------------
        # Komputasi Model Efisiensi Dihitung Terhadap Data Aktual File
        # --------------------------------------------------------
        baseline_ritase = float(act_total_ritase)
        bbm_per_rit = float(bbm_per_rit_input)
        harga_solar = float(harga_solar_input)

        # Jika target simulasi berada pada kondisi aktual file (selisih < 0.08%),
        # gunakan nilai riil murni dari hasil analisis Dual Cycle:
        # Dual Cycle = 2.062 Rit, Non-Dual = 2.056 Rit
        if abs(delta_pct_from_act) < 0.08:
            sim_ritase_dc = act_dual_count
            sim_ritase_non_dc = act_single_count
            delta_rit_vs_act = 0
            delta_pct_from_act = 0.0
        else:
            delta_rit_vs_act = int(round((delta_pct_from_act / 100.0) * baseline_ritase))
            sim_ritase_dc = max(0, min(int(baseline_ritase), act_dual_count + delta_rit_vs_act))
            sim_ritase_non_dc = int(baseline_ritase - sim_ritase_dc)

        # Total Solar dihemat vs Single Cycle murni (karena tiap rit DC meniadakan 1 trip kosong)
        total_bbm_baseline = baseline_ritase * bbm_per_rit
        solar_dihemat_total = sim_ritase_dc * bbm_per_rit
        total_bbm_operasional = max(0.0, total_bbm_baseline - solar_dihemat_total)
        bbm_per_rit_efektif = (total_bbm_operasional / baseline_ritase) if baseline_ritase > 0 else 0.0

        # Tambahan Solar Dihemat & Finansial (dibandingkan kondisi aktual riil)
        delta_solar_vs_act = delta_rit_vs_act * bbm_per_rit
        finansial_delta_rp = delta_solar_vs_act * harga_solar
        total_solar_hemat_rp = solar_dihemat_total * harga_solar

        # Solar dan Biaya yang saat ini dihasilkan oleh kondisi aktual Dual Cycle file
        solar_dihemat_aktual = act_dual_count * bbm_per_rit
        biaya_saat_ini_rp = solar_dihemat_aktual * harga_solar

        # --------------------------------------------------------
        # Baris Kartu KPI Hasil Simulasi
        # --------------------------------------------------------
        render_html('<div style="height:12px;"></div>')
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            render_kpi_card(
                label="Total Ritase Baseline",
                value=f"{format_number(act_total_ritase)} Rit",
                subtext="Otomatis dari file kapal",
                variant="purple",
                tooltip=f"Total seluruh ritase operasional dari file kapal yang dianalisis ({format_number(act_total_ritase)} rit) sebagai acuan perhitungan efisiensi.",
            )
        with r1_c2:
            dc_sub = f"Sesuai Kondisi Aktual ({act_pct_dual:.1f}%)" if delta_rit_vs_act == 0 else f"Target: {sim_penetrasi_pct:.1f}% ({delta_rit_vs_act:+d} Rit)"
            render_kpi_card(
                label="Ritase Dual Cycle Target",
                value=f"{format_number(sim_ritase_dc)} Rit",
                subtext=dc_sub,
                variant="blue",
                tooltip=f"Jumlah ritase 2 arah (kondisi aktual dari file: {format_number(act_dual_count)} rit).",
            )
        with r1_c3:
            ndc_sub = f"Sesuai Kondisi Aktual ({act_pct_non_dual:.1f}%)" if delta_rit_vs_act == 0 else f"Target: {100.0-sim_penetrasi_pct:.1f}% ({-delta_rit_vs_act:+d} Rit)"
            render_kpi_card(
                label="Ritase Non-Dual Target",
                value=f"{format_number(sim_ritase_non_dc)} Rit",
                subtext=ndc_sub,
                variant="slate",
                tooltip=f"Jumlah ritase 1 arah yang tersisa (kondisi aktual dari file: {format_number(act_single_count)} rit).",
                align_tooltip_right=True,
            )

        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            render_kpi_card(
                label="Biaya Saat Ini",
                value=f"Rp {format_number(int(biaya_saat_ini_rp))}",
                subtext=f"Dari {format_number(act_dual_count)} Rit DC ({format_decimal(solar_dihemat_aktual, 1)} L)",
                variant="emerald",
                tooltip=f"Nilai efisiensi biaya bahan bakar yang dihasilkan dari {format_number(act_dual_count)} ritase Dual Cycle aktual ({format_decimal(solar_dihemat_aktual, 1)} Liter solar pada tarif Rp {format_number(int(harga_solar))}/L).",
            )
        with r2_c2:
            if abs(delta_rit_vs_act) == 0:
                fin_val_str = "Rp 0"
                fin_sub_str = "Sesuai Data Riil Kapal"
                fin_variant = "blue"
            elif finansial_delta_rp > 0:
                fin_val_str = f"+Rp {format_number(int(finansial_delta_rp))}"
                fin_sub_str = f"+{format_decimal(delta_solar_vs_act, 1)} L vs Aktual"
                fin_variant = "emerald"
            else:
                fin_val_str = f"-Rp {format_number(int(abs(finansial_delta_rp)))}"
                fin_sub_str = f"{format_decimal(delta_solar_vs_act, 1)} L vs Aktual"
                fin_variant = "rose"

            render_kpi_card(
                label=f"Dampak Finansial (vs {act_pct_dual:.1f}%)",
                value=fin_val_str,
                subtext=fin_sub_str,
                variant=fin_variant,
                tooltip=f"Proyeksi penghematan atau pembengkakan biaya bahan bakar dibandingkan data aktual kapal ({act_pct_dual:.1f}% / {format_number(act_dual_count)} rit).",
                align_tooltip_right=True,
            )

        # --------------------------------------------------------
        # --------------------------------------------------------
        # Bar Chart Sensitivitas Penetrasi
        # --------------------------------------------------------
        render_html('<div style="height:14px;"></div>')
        # Skala interval standar tetap (setiap 5%) agar seluruh batang grafik teratur dan tidak bertumpukan
        pct_range = [30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]

        curve_data = []
        for p_val in pct_range:
            p_ratio = p_val / 100.0
            dc_val = int(round(p_ratio * baseline_ritase))
            ndc_val = int(baseline_ritase - dc_val)
            curve_data.append({
                "Penetrasi (%)": p_val,
                "Ritase DC": dc_val,
                "Ritase Non-DC": ndc_val,
                "Selected": (p_val == sim_penetrasi_pct),
            })
        df_curve = pd.DataFrame(curve_data)

        fig_curve = go.Figure()

        # Bar Ritase Dual Cycle
        fig_curve.add_trace(
            go.Bar(
                x=df_curve["Penetrasi (%)"],
                y=df_curve["Ritase DC"],
                name="Ritase Dual Cycle",
                marker_color="#0284C7",
                hovertemplate="Penetrasi: %{x}%<br>Ritase DC: %{y:,.0f} rit<extra></extra>",
            )
        )

        # Bar Ritase Non-Dual Cycle
        fig_curve.add_trace(
            go.Bar(
                x=df_curve["Penetrasi (%)"],
                y=df_curve["Ritase Non-DC"],
                name="Ritase Non-Dual",
                marker_color="#475569",
                hovertemplate="Penetrasi: %{x}%<br>Ritase Non-DC: %{y:,.0f} rit<extra></extra>",
            )
        )

        # Garis Penanda Vertikal Posisi Target Slider
        fig_curve.add_vline(
            x=sim_penetrasi_pct,
            line_width=2,
            line_dash="dash",
            line_color="#38bdf8",
        )

        fig_curve.add_annotation(
            x=sim_penetrasi_pct,
            y=1.04,
            yref="paper",
            text=f"🎯 Target: {sim_penetrasi_pct}%",
            showarrow=False,
            font=dict(family="Plus Jakarta Sans", size=11, color="#38bdf8"),
            bgcolor="rgba(13, 22, 38, 0.9)",
            bordercolor="rgba(56, 189, 248, 0.4)",
            borderwidth=1,
            borderpad=4,
        )

        apply_glass_theme(fig_curve)
        fig_curve.update_layout(
            title=dict(text=f"Sensitivitas Penetrasi terhadap Komposisi Ritase (Aktual: {act_pct_dual:.1f}%)"),
            barmode="stack",
            height=550,
            margin=dict(t=65, b=50, l=55, r=25),
            xaxis=dict(
                title="Penetrasi Dual Cycle (%)",
                tickmode="array",
                tickvals=pct_range,
                ticktext=[f"{p}%" for p in pct_range],
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                title="Jumlah Ritase",
                gridcolor="rgba(255,255,255,0.06)",
                nticks=10,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
            ),
        )
        st.plotly_chart(fig_curve, use_container_width=True, key="curve_sensitivity_sim_chart")

        # --------------------------------------------------------
        # Tabel Matriks Skema Sensitivitas Dinamis Berpusat pada Aktual File
        # --------------------------------------------------------
        render_html('<div style="height:16px;"></div>')
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
            f'<span style="font-size: 15px; font-weight: 700; color: #ffffff; font-family: \'Plus Jakarta Sans\', sans-serif;">Skema Sensitivitas Penetrasi (Titik Acuan: Aktual File {act_pct_dual:.1f}%)</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Hasilkan skenario sensitivitas dinamis seputar rasio aktual
        act_point = round(act_pct_dual, 1)
        base_int = int(round(act_pct_dual))
        rel_deltas = [-15, -10, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30]
        # Hilangkan nilai integer 50% jika terlalu berhimpitan dengan 50.1% agar tidak ada baris duplikat
        regular_pcts = [max(10, min(95, base_int + d)) for d in rel_deltas if abs((base_int + d) - act_point) >= 0.5]

        all_pcts = set(regular_pcts)
        all_pcts.add(act_point)
        if abs(sim_penetrasi_pct - act_point) >= 0.5:
            all_pcts.add(round(sim_penetrasi_pct, 1))

        skenario_pcts = sorted(list(all_pcts))

        table_rows = []
        for p in skenario_pcts:
            is_actual_point = (abs(p - act_pct_dual) < 0.15)
            is_target_point = (abs(p - sim_penetrasi_pct) < 0.05 and not is_actual_point)

            if is_actual_point:
                status_label = "📍 Kondisi Saat Ini"
                dc = act_dual_count          # 2.062 Rit (Murni hasil perhitungan file terupload)
                ndc = act_single_count       # 2.056 Rit (Murni hasil perhitungan file terupload)
                delta_p = 0.0
                delta_rit = 0
                sol_hemat = int(round(dc * bbm_per_rit))
                tot_bbm = int(round(ndc * bbm_per_rit))
                bbm_rit = round(tot_bbm / baseline_ritase, 2) if baseline_ritase > 0 else 0.0
                fin_rp = 0.0
            else:
                p_ratio = p / 100.0
                delta_p = p - act_pct_dual
                delta_rit = int(round((delta_p / 100.0) * baseline_ritase))
                dc = max(0, min(int(baseline_ritase), act_dual_count + delta_rit))
                ndc = int(baseline_ritase - dc)
                sol_hemat = int(round(dc * bbm_per_rit))
                tot_bbm = int(round(total_bbm_baseline - sol_hemat))
                bbm_rit = round(tot_bbm / baseline_ritase, 2) if baseline_ritase > 0 else 0.0
                fin_rp = delta_rit * bbm_per_rit * harga_solar
                status_label = "🎯 Target Skenario" if is_target_point else ""

            if abs(delta_p) < 0.05:
                delta_str = "0.0%"
            else:
                delta_str = f"{delta_p:+.1f}%"

            if abs(fin_rp) < 1:
                fin_str = "Rp 0"
            elif fin_rp > 0:
                fin_str = f"+Rp {format_number(int(fin_rp))}"
            else:
                fin_str = f"-Rp {format_number(int(abs(fin_rp)))}"

            table_rows.append({
                "Status": status_label,
                "Skenario Penetrasi": f"{p}%",
                "Delta vs Aktual (±%)": delta_str,
                "Ritase Dual Cycle": format_number(dc),
                "Ritase Non-Dual": format_number(ndc),
                "Solar Dihemat (Liter)": f"{format_number(sol_hemat)} L",
                "Total Penggunaan BBM": f"{format_number(tot_bbm)} L",
                "Total BBM per Rit": f"{bbm_rit:.2f} L/Rit",
                "Efisiensi Finansial (vs Aktual)": fin_str,
            })

        df_sensitivity_table = pd.DataFrame(table_rows)

        st.dataframe(
            df_sensitivity_table,
            use_container_width=True,
            hide_index=True,
            height=540,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Skenario Penetrasi": st.column_config.TextColumn("Skenario", width="small"),
                "Delta vs Aktual (±%)": st.column_config.TextColumn("Delta vs Aktual", width="small"),
                "Ritase Dual Cycle": st.column_config.TextColumn("Ritase DC", width="small"),
                "Ritase Non-Dual": st.column_config.TextColumn("Ritase Non-DC", width="small"),
                "Solar Dihemat (Liter)": st.column_config.TextColumn("Dampak Solar (Liter)", width="medium"),
                "Total Penggunaan BBM": st.column_config.TextColumn("Total BBM (Liter)", width="medium"),
                "Total BBM per Rit": st.column_config.TextColumn("BBM / Rit", width="small"),
                "Efisiensi Finansial (vs Aktual)": st.column_config.TextColumn("Dampak Finansial (vs Aktual)", width="medium"),
            },
        )


    # ----------------------------------------------------------------
    # TAB 4: DOWNLOAD HASIL ANALISIS
    # ----------------------------------------------------------------
    elif active_tab == "Download Hasil Analisis":
        cols_to_exclude = [
            "TWINLIFT_GAP_MENIT",
            "DUAL_PAIR_ID",
            "DUAL_JENIS",
            "DUAL_PASANGAN_EVENT_ID",
            "DUAL_URUTAN",
            "DUAL_GAP_LOKASI",
            "DUAL_GAP_MENIT",
            "DUAL_AMBANG_MENIT",
            "DUAL_SELISIH_AMBANG_MENIT",
            "DUAL_IS_FAST",
        ]
        df_download = out_df.drop(columns=[c for c in cols_to_exclude if c in out_df.columns], errors="ignore")
        st.dataframe(df_download.head(1000), use_container_width=True, height=400)

        hasil_sig = (
            hasil["ambang_combo"],
            hasil["ambang_dual"],
            hasil["ambang_twinlift"],
            len(out_df),
            len(df_download.columns),
        )
        if st.session_state.get("_download_sig") != hasil_sig:
            st.session_state.pop("_excel_bytes", None)
            st.session_state.pop("_excel_sig", None)
            st.session_state["_download_sig"] = hasil_sig

        excel_ready = "_excel_bytes" in st.session_state and st.session_state.get("_excel_sig") == hasil_sig

        if excel_ready:
            st.download_button(
                "📥 Download File Excel (.xlsx)",
                data=st.session_state["_excel_bytes"],
                file_name="Hasil_Analisis_Dual_Cycle.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            if st.button("Download Hasil Analisis (.xlsx)", use_container_width=True):
                with st.spinner("Menyiapkan file Excel (mohon tunggu)..."):
                    try:
                        st.session_state["_excel_bytes"] = build_excel_data_only(df_download)
                        st.session_state["_excel_sig"] = hasil_sig
                        st.rerun()
                    except Exception as err:
                        st.error(f"Gagal membuat file Excel: {err}.")
