"""
CACA - Cycle Analysis & Cargo Accelaration Dashboard
Pelindo Terminal Teluk Lamong

Aplikasi analitis berbasis web untuk rekonstruksi siklus truk dermaga,
evaluasi rasio Dual Cycle, utilisasi Twin Lift, serta agregasi produktivitas per kapal.
"""

import datetime
from pathlib import Path
import time
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

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
    render_html,
    render_hybrid_loading_indicator,
    render_kpi_card,
    render_template,
    show_activity_detail_dialog,
    show_combo_detail_dialog,
    show_twinlift_detail_dialog,
)



# ----------------------------------------------------------------
# Konfigurasi Halaman Streamlit
# ----------------------------------------------------------------
st.set_page_config(
    page_title="CACA - Dashboard Analisis Dual Cycle & Twin Lift | Pelindo TTL",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
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
    th1, th2, th3 = st.columns([1, 1, 1], gap="medium")
    with th1:
        ambang_combo = st.number_input(
            "Ambang Combo (menit)",
            min_value=1,
            value=AMBANG_COMBO_MENIT_DEFAULT,
            step=1,
            help="Selisih waktu 2 container 20ft pada truk dan aktivitas yang sama",
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Gap 2 container 20ft pada truk yang sama</div>'
        )

    with th2:
        ambang_dual = st.number_input(
            "Parameter Dual Cycle (menit)",
            min_value=1,
            value=AMBANG_DUAL_MENIT_DEFAULT,
            step=10,
            help=(
                "Selisih waktu konfirmasi truk mendapatkan muatan, baik di lapangan atau dermaga"
            ),
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Waktu konfirmasi angkat dan angkut kontainer di truk</div>'
        )

    with th3:
        ambang_twinlift = st.number_input(
            "Ambang Twinlift (menit)",
            min_value=1,
            value=AMBANG_TWINLIFT_MENIT_DEFAULT,
            step=1,
            help=(
                "Selisih waktu konfirmasi 2 kontainer dalam 1 aktivitas"
            ),
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

    # Validasi integritas cache hasil analisis jika ada
    CALC_VERSION = "v1.2_dual_round"
    auto_recompute = False
    if "hasil" in st.session_state:
        _cached_out_df = st.session_state["hasil"].get("out_df")
        if _cached_out_df is None or st.session_state.get("_calc_ver") != CALC_VERSION:
            st.session_state.pop("hasil", None)
            session_store.pop("hasil", None)
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
        on_calc_progress(6, "Memulai analisis...", "Inisialisasi pipeline komputasi")

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
    st.session_state["_ambang_terakhir"] = (
        ambang_combo,
        ambang_dual,
        ambang_twinlift,
        st.session_state.get("_init_period_range"),
    )
    st.session_state["_calc_ver"] = CALC_VERSION

    # Simpan hasil komputasi ke session_store server agar persisten terhadap refresh browser (F5)
    session_store["hasil"] = st.session_state["hasil"]
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

    # Smooth scroll otomatis menggeser halaman ke Langkah 3 saat komputasi selesai dijalankan
    if run:
        components.html(
            """
            <script>
            (function() {
                function doScroll() {
                    try {
                        var win = window.parent;
                        if (win && win.triggerScrollToStep3) {
                            win.triggerScrollToStep3();
                        } else {
                            var doc = window.parent.document;
                            var t = doc.getElementById('step3-card-marker');
                            if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    } catch(e) {}
                }
                doScroll();
                setTimeout(doScroll, 100);
                setTimeout(doScroll, 300);
                setTimeout(doScroll, 600);
            })();
            </script>
            """,
            height=0,
            width=0,
        )

    monthly = summary["monthly"].reset_index().rename(columns={"BULAN": "Bulan"})
    # Basis kontainer 20ft — dipakai untuk breakdown Combo/Single & Twinlift/Bukan
    # Twinlift, karena keduanya secara definisi cuma mungkin terjadi di 20ft.
    monthly_20ft = summary["monthly_20ft"].reset_index().rename(columns={"BULAN": "Bulan"})

    # 3 Tab Hasil Analisis
    tab_dual, tab_twinlift, tab_download = st.tabs(
        ["Dual Cycle", "Twinlift", "Download Hasil Analisis"]
    )

    # ----------------------------------------------------------------
    # TAB 1: DUAL CYCLE
    # ----------------------------------------------------------------
    with tab_dual:
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
            col_b1, col_b2, col_b3 = st.columns(3)
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

            with col_b3:
                if st.button("⚠️ Rincian Issue", use_container_width=True, key="btn_quick_issue_detail", help="Lihat Gap 0 menit (human error) dan potensi dual cycle dengan gap berlebih"):
                    st.session_state["modal_activity_status"] = "Issue"
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
                col_cb1, col_cb2, col_cb3 = st.columns(3)
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

                with col_cb3:
                    if st.button("⚠️ Rincian Issue", use_container_width=True, key="btn_quick_combo_issue_detail", help="Lihat Gap 0 menit dan potensi Combo dengan jeda waktu melebihi ambang batas"):
                        st.session_state["modal_combo_status"] = "Issue"
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
            apply_glass_theme(fig_month_dual)
            st.plotly_chart(fig_month_dual, width="stretch")

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
    with tab_twinlift:
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

                fig_month_twin = px.bar(
                    monthly_twin_pct,
                    x="Bulan",
                    y="Persentase",
                    color="Kategori",
                    barmode="stack",
                    title="Breakdown Bulanan: Twinlift vs Bukan Twinlift (% dari Kontainer 20ft)",
                    color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                    text="Label",
                )
                fig_month_twin.update_traces(textposition="inside", insidetextanchor="middle")
                fig_month_twin.update_layout(
                    xaxis=dict(type="category"),
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
        render_html('<div style="height:8px;"></div>')
        st.markdown(
            "##### Performa Crane (QC) dalam Twinlift",
            help=(
                "**Syarat Twinlift:** 2 kontainer 20ft dari kapal yang sama, diangkut truk yang sama, "
                "DAN diangkat oleh Crane yang sama pada kegiatan di dermaga (bongkar DISC maupun "
                "muat LOAD), dalam ambang waktu yang ditentukan.\n\n"
                "Twinlift hanya bisa dilakukan crane kade internasional (ID berakhiran I); "
                "crane kade domestik (berakhiran D) selalu 0%.\n\n"
                "Persentase di bawah dihitung dari kontainer 20ft yang ditangani tiap crane, "
                "bukan dari seluruh kontainer yang ditangani crane tersebut."
            ),
        )

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
            crane_perf_valid = crane_perf[crane_perf["total_20ft"] > 0].copy()
            top_n = min(15, len(crane_perf_valid))

            if top_n == 0:
                st.info("Tidak ada crane dengan kontainer 20ft pada data ini.")
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

                crane_disp = crane_perf.rename(
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
                    height=320,
                )

    # ----------------------------------------------------------------
    # TAB 3: DOWNLOAD HASIL ANALISIS
    # ----------------------------------------------------------------
    with tab_download:
        st.dataframe(out_df.head(1000), use_container_width=True, height=400)

        hasil_sig = (
            hasil["ambang_combo"],
            hasil["ambang_dual"],
            hasil["ambang_twinlift"],
            len(out_df),
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
                        st.session_state["_excel_bytes"] = build_excel_data_only(out_df)
                        st.session_state["_excel_sig"] = hasil_sig
                        st.rerun()
                    except Exception as err:
                        st.error(f"Gagal membuat file Excel: {err}.")
