"""
Modul Tampilan, Template HTML & Injeksi Desain
Terminal Teluk Lamong - Pelindo

Menyediakan fungsi untuk memuat template HTML mandiri, menginjeksi stylesheet CSS,
script transisi JavaScript, serta rendering kartu dan komponen grafis.
"""

from pathlib import Path
import base64
import io
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"


def find_asset_file(candidates: list[str]) -> Path | None:
    """Mencari file aset dari daftar kandidat nama file."""
    for name in candidates:
        p = ASSETS_DIR / name
        if p.exists() and p.is_file():
            return p
    return None


@st.cache_resource
def setup_template_and_asset_watchers():
    """
    Mengaktifkan pemantauan otomatis (live reload) untuk folder templates/ dan assets/.
    Ketika pengguna atau developer mengedit file HTML atau CSS, Streamlit akan otomatis
    melakukan rerun pada browser secara real-time tanpa perlu refresh halaman web.
    """
    try:
        from streamlit.watcher.path_watcher import watch_dir
        from streamlit.runtime import Runtime

        def _on_resource_changed(changed_path: str):
            if Runtime.exists():
                try:
                    rt = Runtime.instance()
                    for s_info in rt._session_mgr.list_active_sessions():
                        s_info.session.request_rerun(s_info.session._client_state)
                except Exception:
                    pass

        watch_dir(str(TEMPLATES_DIR.resolve()), _on_resource_changed)
        watch_dir(str(ASSETS_DIR.resolve()), _on_resource_changed)
        return True
    except Exception:
        return False


# Inisialisasi watcher templates dan assets saat modul dimuat
setup_template_and_asset_watchers()



@st.cache_data(show_spinner=False)
def _get_hero_img_src(path_str: str | None, mtime: float = 0.0) -> str:
    """Mengoptimalkan gambar hero agar cepat dimuat di web tanpa lag ukuran file besar."""
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    try:
        from PIL import Image

        with Image.open(p) as img:
            max_width = 1920
            if img.width > max_width:
                h = int((max_width / img.width) * img.height)
                img = img.resize((max_width, h), Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return _img_to_base64_src_cached(path_str, mtime)


@st.cache_data(show_spinner=False)
def _img_to_base64_src_cached(path_str: str, mtime: float = 0.0) -> str:
    p = Path(path_str)
    if not p.exists():
        return ""
    ext = p.suffix.lower()
    if ext == ".webp":
        mime = "image/webp"
    elif ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".svg":
        mime = "image/svg+xml"
    else:
        mime = "image/png"
    encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def img_to_base64_src(path: Path | None) -> str:
    if not path:
        return ""
    p = path.resolve()
    if not p.exists():
        return ""
    mtime = p.stat().st_mtime
    return _img_to_base64_src_cached(str(p), mtime)


def render_html(content: str):
    """Merender HTML secara murni menggunakan st.html tanpa distorsi parser Markdown."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


def load_template(_template_name: str, **context) -> str:
    """Memuat file template HTML dari folder templates/ dan melakukan interpolasi variabel."""
    file_path = TEMPLATES_DIR / _template_name
    if not file_path.exists():
        raise FileNotFoundError(f"Template HTML tidak ditemukan: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    for key, val in context.items():
        placeholder = f"{{{{ {key} }}}}"
        placeholder_no_spaces = f"{{{{{key}}}}}"
        val_str = "" if val is None else str(val)
        content = content.replace(placeholder, val_str)
        content = content.replace(placeholder_no_spaces, val_str)
    return content


def render_template(_template_name: str, **context):
    """Memuat template HTML dan langsung merendernya ke Streamlit."""
    html = load_template(_template_name, **context)
    render_html(html)


def inject_css(css_filename: str = "style.css"):
    """Membaca file CSS dari folder assets/ dan menginjeksikannya ke dalam aplikasi."""
    css_path = ASSETS_DIR / css_filename
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        mtime = int(css_path.stat().st_mtime)
        style_tag = f"<style id=\"caca-custom-style\" data-v=\"{mtime}\">\n{css_content}\n</style>"
        if hasattr(st, "html"):
            st.html(style_tag)
        else:
            st.markdown(style_tag, unsafe_allow_html=True)


def inject_transition_script(js_filename: str = "transition.js"):
    """Membaca file JavaScript dari assets/ dan menginjeksikannya melalui components.html."""
    js_path = ASSETS_DIR / js_filename
    if js_path.exists():
        js_content = js_path.read_text(encoding="utf-8")
        components.html(f"<script>\n{js_content}\n</script>", height=1, width=1)


def render_artistic_hero(hero_path: Path | None, icon_path: Path | None, brand_path: Path | None):
    """Merender komponen hero banner menggunakan template templates/hero.html."""
    hero_mtime = hero_path.stat().st_mtime if hero_path and hero_path.exists() else 0.0
    img_src = _get_hero_img_src(str(hero_path.resolve()), hero_mtime) if hero_path else ""
    icon_src = img_to_base64_src(icon_path)
    brand_src = img_to_base64_src(brand_path)

    caca_logo_html = (
        f'<img src="{icon_src}" style="height:74px;width:auto;display:block;object-fit:contain;background:transparent;filter:drop-shadow(0 4px 14px rgba(0, 0, 0, 0.85)) drop-shadow(0 0 18px rgba(255, 255, 255, 0.25));" alt="CACA Logo" />'
        if icon_src
        else '<span style="font-size:1.85rem;font-weight:900;color:#ffffff;letter-spacing:-0.5px;text-shadow:0 3px 12px rgba(0,0,0,0.85);">CACA</span>'
    )
    pelindo_logo_html = (
        f'<img src="{brand_src}" style="height:52px;width:auto;display:block;object-fit:contain;background:transparent;filter:drop-shadow(0 3px 8px rgba(0, 0, 0, 0.75)) drop-shadow(0 8px 24px rgba(0, 0, 0, 0.55));" alt="Pelindo Logo" />'
        if brand_src
        else '<span style="font-size:1.35rem;font-weight:800;color:#ffffff;text-shadow:0 3px 12px rgba(0,0,0,0.85);">PELINDO</span>'
    )

    bg_style = (
        f"background-image: linear-gradient(180deg, rgba(7, 12, 24, 0.16) 0%, rgba(7, 12, 24, 0.02) 35%, rgba(7, 12, 24, 0.30) 75%, #070c18 100%), url('{img_src}');"
        if img_src
        else "background: #070c18;"
    )

    render_template(
        "hero.html",
        bg_style=bg_style,
        caca_logo_html=caca_logo_html,
        pelindo_logo_html=pelindo_logo_html,
    )


def format_number(val: int | float | str | None) -> str:
    """
    Memformat angka bulat dengan pemisah ribuan titik (format Indonesia/ID),
    contoh: 51045 -> '51.045'.
    """
    if val is None:
        return "0"
    if isinstance(val, (int, np.integer)):
        return f"{val:,}".replace(",", ".")
    if isinstance(val, (float, np.floating)):
        if pd.isna(val):
            return "0"
        if val.is_integer():
            return f"{int(val):,}".replace(",", ".")
        return format_decimal(val, 1)
    s = str(val).strip()
    if s.endswith("%"):
        return format_percent(s)
    import re
    if re.match(r"^-?\d{1,3}(,\d{3})+$", s):
        return s.replace(",", ".")
    if s.lstrip("-").isdigit():
        return f"{int(s):,}".replace(",", ".")
    return s


def format_percent(val: int | float | str | None, decimals: int = 1) -> str:
    """
    Memformat angka persentase dengan pemisah desimal koma (format Indonesia/ID),
    contoh: 53.8 -> '53,8%'.
    """
    if val is None:
        dec_part = "," + ("0" * decimals) if decimals > 0 else ""
        return f"0{dec_part}%"
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val):
            return "0%"
        fmt = f"{{:.{decimals}f}}%"
        return fmt.format(val).replace(".", ",")
    s = str(val).strip()
    if s.endswith("%"):
        s_num = s[:-1].strip()
        try:
            num = float(s_num.replace(",", "."))
            fmt = f"{{:.{decimals}f}}%"
            return fmt.format(num).replace(".", ",")
        except ValueError:
            return s.replace(".", ",")
    try:
        num = float(s.replace(",", "."))
        fmt = f"{{:.{decimals}f}}%"
        return fmt.format(num).replace(".", ",")
    except ValueError:
        return s


def format_decimal(val: int | float | str | None, decimals: int = 1) -> str:
    """
    Memformat angka desimal dengan koma desimal dan titik ribuan (format Indonesia/ID),
    contoh: 1234.56 -> '1.234,6'.
    """
    if val is None:
        dec_part = "," + ("0" * decimals) if decimals > 0 else ""
        return f"0{dec_part}"
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val):
            return "0"
        raw = f"{val:,.{decimals}f}"
        return raw.replace(",", "TEMP_DOT").replace(".", ",").replace("TEMP_DOT", ".")
    s = str(val).strip()
    try:
        num = float(s.replace(",", "."))
        raw = f"{num:,.{decimals}f}"
        return raw.replace(",", "TEMP_DOT").replace(".", ",").replace("TEMP_DOT", ".")
    except ValueError:
        return s


def get_tooltip_html(label: str, tooltip: str | None = None, align_right: bool = True) -> str:
    """Menghasilkan markup HTML untuk icon tanda tanya (?) persis seperti icon help bawaan Streamlit."""
    if not tooltip:
        return ""
    align_class = "align-right" if align_right else ""
    return (
        f'<div class="kpi-tooltip-container">'
        f'<span class="kpi-tooltip-trigger" aria-label="Penjelasan {label}" onclick="event.stopPropagation();">'
        f'<span class="kpi-help-icon">?</span>'
        f'</span>'
        f'<div class="kpi-tooltip-bubble {align_class}" role="tooltip">'
        f'<div class="kpi-tooltip-header"><span class="kpi-tooltip-title">{label}</span></div>'
        f'<div class="kpi-tooltip-text">{tooltip}</div>'
        f'</div>'
        f'</div>'
    )


def render_kpi_card(
    label: str,
    value: str | int | float,
    subtext: str = None,
    badge: str = None,
    variant: str = "blue",
    tooltip: str = None,
    align_tooltip_right: bool = False,
    extra_class: str = "",
):
    """Merender kartu KPI glassmorphism menggunakan template templates/kpi_card.html."""
    formatted_value = format_number(value)
    subtext_html = f'<div class="kpi-subtext">{subtext}</div>' if subtext else ""
    badge_variant = f"badge-{variant}" if variant in ["emerald", "coral", "purple", "amber", "slate", "blue"] else ""
    badge_html = f'<span class="kpi-badge {badge_variant}">{badge}</span>' if badge else ""
    tooltip_html = get_tooltip_html(label, tooltip, align_tooltip_right)

    render_template(
        "kpi_card.html",
        label=label,
        value=formatted_value,
        subtext_html=subtext_html,
        badge_html=badge_html,
        variant=variant,
        tooltip_html=tooltip_html,
        extra_class=extra_class,
    )


def render_dual_cycle_kpi_section(summary: dict):
    """
    Merender seluruh komponen KPI untuk Tab Dual Cycle:
    - Default 5 kartu: Total Petikemas, Total Ritase, Dual Cycle, Non Dual, % Dual Cycle.
    - Toggle interaktif murni CSS: Container LOAD & Container DISC muncul saat Total Petikemas diklik.
    - Icon tanda tanya (?) dengan tooltip penjelasan pada setiap kartu.
    """
    pct_dual_val = summary.get("pct_dual", 0) * 100
    render_template(
        "dual_cycle_kpis.html",
        container_total=format_number(summary.get("container_total", 0)),
        total_event=format_number(summary.get("total_event", 0)),
        container_load=format_number(summary.get("container_load", 0)),
        container_disc=format_number(summary.get("container_disc", 0)),
        total_dual=format_number(summary.get("total_dual", 0)),
        total_single=format_number(summary.get("total_single", 0)),
        pct_dual_formatted=format_percent(pct_dual_val, 1),
    )


def format_file_size(size_bytes: int) -> str:
    """Memformat ukuran byte file ke representasi yang ramah pengguna (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{format_decimal(size_bytes / 1024, 1)} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{format_decimal(size_bytes / (1024 * 1024), 1)} MB"
    return f"{format_decimal(size_bytes / (1024 * 1024 * 1024), 2)} GB"


def get_hybrid_loading_indicator_html(
    filename: str,
    file_size_bytes: int,
    pct: int = 0,
    status_text: str = "Mempersiapkan data...",
    detail_text: str = "",
) -> str:
    """Menghasilkan string HTML untuk komponen hybrid loading indicator."""
    file_size = format_file_size(file_size_bytes)
    pct_clamped = max(0, min(100, int(pct)))
    # SVG 88x88, r=36 -> C = 2 * pi * 36 = 226.19
    stroke_dashoffset = round(226.19 * (1 - pct_clamped / 100.0), 2)

    is_done = pct_clamped >= 100
    done_class = "is-done" if is_done else ""
    stroke_color = "#10b981" if is_done else "#38bdf8"
    track_color = "rgba(16, 185, 129, 0.2)" if is_done else "rgba(56, 189, 248, 0.16)"

    if not detail_text:
        formatted_detail = file_size
    else:
        formatted_detail = f"{file_size} • {detail_text}"

    return load_template(
        "hybrid_loading_indicator.html",
        filename=filename,
        file_size=file_size,
        pct=pct_clamped,
        stroke_dashoffset=stroke_dashoffset,
        status_text=status_text,
        detail_text=formatted_detail,
        done_class=done_class,
        stroke_color=stroke_color,
        track_color=track_color,
    )


def render_hybrid_loading_indicator(
    filename: str,
    file_size_bytes: int,
    pct: int = 0,
    status_text: str = "Mempersiapkan data...",
    detail_text: str = "",
    placeholder=None,
):
    """Merender komponen hybrid loading indicator berbasis progres riil Python."""
    html = get_hybrid_loading_indicator_html(
        filename=filename,
        file_size_bytes=file_size_bytes,
        pct=pct,
        status_text=status_text,
        detail_text=detail_text,
    )
    target = placeholder if placeholder is not None else st
    target.markdown(html, unsafe_allow_html=True)


def prepare_dual_cycle_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyusun tabel rincian pasangan Dual Cycle (vektorisasi cepat via merge).
    Menghubungkan event DISC dan LOAD pada truk yang sama dengan format:
    Truk | DISC (Kapal, Crane) -> Gap -> LOAD (Kapal, Crane) | Jenis Dual
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()
    ev_dual = events[(events["STATUS"] == "Dual Cycle") & (events["DUAL_PAIR_ID"] > 0)].copy()
    if len(ev_dual) == 0:
        return pd.DataFrame()

    ev_dual["START_TS"] = pd.to_datetime(ev_dual["START_TS"])
    ev_dual["END_TS"] = pd.to_datetime(ev_dual["END_TS"])

    ves_map = {}
    size_map = {}
    if out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        ves_map = out_df.groupby("EVENT_ID")["VES_ID"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique())
        ).to_dict()
    if out_df is not None and len(out_df) > 0 and "CTR_SIZE" in out_df.columns:
        size_map = out_df.groupby("EVENT_ID")["CTR_SIZE"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique()) + "ft"
        ).to_dict()

    ev_dual["VES_ID"] = ev_dual["EVENT_ID"].map(ves_map).fillna("-")
    ev_dual["UKURAN_CTR"] = ev_dual["EVENT_ID"].map(size_map).fillna("-")
    ev_dual["CRANE_ID"] = ev_dual["CRANE_ID"].fillna("-").astype(str)

    disc = ev_dual[ev_dual["ACTIVITY"] == "DISC"].drop_duplicates(subset=["DUAL_PAIR_ID"])
    load = ev_dual[ev_dual["ACTIVITY"] == "LOAD"].drop_duplicates(subset=["DUAL_PAIR_ID"])

    merged = pd.merge(disc, load, on="DUAL_PAIR_ID", suffixes=("_DISC", "_LOAD"))
    if len(merged) == 0:
        return pd.DataFrame()

    merged["TRUK_ID"] = merged["CAR_CHE_ID_DISC"].fillna(merged["CAR_CHE_ID_LOAD"]).astype(str)
    merged["TRUK_ID"] = merged["TRUK_ID"].str.replace(r"\.0$", "", regex=True)

    disc_first = merged["START_TS_DISC"] <= merged["START_TS_LOAD"]
    gap_forward = (merged["START_TS_LOAD"] - merged["END_TS_DISC"]).dt.total_seconds() / 60.0
    gap_backward = (merged["START_TS_DISC"] - merged["END_TS_LOAD"]).dt.total_seconds() / 60.0

    merged["URUTAN"] = np.where(disc_first, "DISC ➔ LOAD", "LOAD ➔ DISC")
    calc_gap = pd.Series(np.where(disc_first, gap_forward, gap_backward), index=merged.index)
    if "DUAL_GAP_MENIT_DISC" in merged.columns and merged["DUAL_GAP_MENIT_DISC"].notna().any():
        merged["GAP_MENIT"] = merged["DUAL_GAP_MENIT_DISC"].fillna(calc_gap)
    else:
        merged["GAP_MENIT"] = calc_gap
    merged["GAP_MENIT"] = np.maximum(0.0, merged["GAP_MENIT"].fillna(0.0)).round(1)

    merged["WAKTU_DERMAGA"] = merged["START_TS_DISC"].dt.strftime("%d/%m/%y %H:%M")
    merged["WAKTU_LAPANGAN"] = merged["START_TS_LOAD"].dt.strftime("%d/%m/%y %H:%M")

    # Format ringkasan siklus urutannya disesuaikan dengan kolom urutan:
    # Jika DISC ➔ LOAD: Truk | DISC (Kapal, Crane) | ➔ Gap mnt ➔ | LOAD (Kapal, Crane)
    # Jika LOAD ➔ DISC: Truk | LOAD (Kapal, Crane) | ➔ Gap mnt ➔ | DISC (Kapal, Crane)
    # Keterangan 'Campuran' & 'Murni' dihapus sesuai instruksi
    ringkasan_disc_first = (
        merged["TRUK_ID"]
        + " | DISC ("
        + merged["VES_ID_DISC"]
        + ", "
        + merged["CRANE_ID_DISC"]
        + ") | ➔ "
        + merged["GAP_MENIT"].apply(lambda g: format_decimal(g, 1))
        + " mnt ➔ | LOAD ("
        + merged["VES_ID_LOAD"]
        + ", "
        + merged["CRANE_ID_LOAD"]
        + ")"
    )

    ringkasan_load_first = (
        merged["TRUK_ID"]
        + " | LOAD ("
        + merged["VES_ID_LOAD"]
        + ", "
        + merged["CRANE_ID_LOAD"]
        + ") | ➔ "
        + merged["GAP_MENIT"].apply(lambda g: format_decimal(g, 1))
        + " mnt ➔ | DISC ("
        + merged["VES_ID_DISC"]
        + ", "
        + merged["CRANE_ID_DISC"]
        + ")"
    )

    merged["RINGKASAN_PASANGAN"] = np.where(disc_first, ringkasan_disc_first, ringkasan_load_first)

    merged = merged.sort_values(by=["START_TS_DISC", "TRUK_ID"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": merged["TRUK_ID"],
            "Format Rincian": merged["RINGKASAN_PASANGAN"],
            "Urutan": merged["URUTAN"],
            "Crane DISC": merged["CRANE_ID_DISC"],
            "Tipe DISC": merged["CONTAINER_STATUS_DISC"],
            "Crane LOAD": merged["CRANE_ID_LOAD"],
            "Tipe LOAD": merged["CONTAINER_STATUS_LOAD"],
            "Waktu Dermaga": merged["WAKTU_DERMAGA"],
            "Waktu Lapangan": merged["WAKTU_LAPANGAN"],
            "Gap (Menit)": merged["GAP_MENIT"],
        }
    )

    # Ekstraksi total kapal (VES_ID unik) yang terlibat dalam Dual Cycle
    vessels = set()
    for col in ["VES_ID_DISC", "VES_ID_LOAD"]:
        if col in merged.columns:
            for val in merged[col].dropna().astype(str):
                for part in val.split(","):
                    p = part.strip()
                    if p and p != "-":
                        vessels.add(p)
    res.attrs["total_kapal"] = len(vessels)

    return res


def prepare_non_dual_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyusun tabel rincian aktivitas Non Dual (single cycle ritase truk).
    Format: Truk | Aktivitas (Kapal, Crane) | Durasi | Tipe Kontainer
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()
    ev_non = events[events["STATUS"] == "Non Dual"].copy()
    if len(ev_non) == 0:
        return pd.DataFrame()

    ev_non["START_TS"] = pd.to_datetime(ev_non["START_TS"])
    ev_non["END_TS"] = pd.to_datetime(ev_non["END_TS"])

    ves_map = {}
    size_map = {}
    if out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        ves_map = out_df.groupby("EVENT_ID")["VES_ID"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique())
        ).to_dict()
    if out_df is not None and len(out_df) > 0 and "CTR_SIZE" in out_df.columns:
        size_map = out_df.groupby("EVENT_ID")["CTR_SIZE"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique()) + "ft"
        ).to_dict()

    ev_non["VES_ID"] = ev_non["EVENT_ID"].map(ves_map).fillna("-")
    ev_non["UKURAN_CTR"] = ev_non["EVENT_ID"].map(size_map).fillna("-")
    ev_non["CRANE_ID"] = ev_non["CRANE_ID"].fillna("-").astype(str)

    ev_non["TRUK_ID"] = ev_non["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
    ev_non["DURASI_MENIT"] = ((ev_non["END_TS"] - ev_non["START_TS"]).dt.total_seconds() / 60.0).round(1)
    ev_non["DURASI_MENIT"] = np.maximum(0.0, ev_non["DURASI_MENIT"])

    ev_non["WAKTU_MULAI"] = ev_non["START_TS"].dt.strftime("%d/%m/%y %H:%M:%S")
    ev_non["WAKTU_SELESAI"] = ev_non["END_TS"].dt.strftime("%d/%m/%y %H:%M:%S")

    ev_non["RINGKASAN_EVENT"] = (
        ev_non["TRUK_ID"]
        + " | "
        + ev_non["ACTIVITY"]
        + " ("
        + ev_non["VES_ID"]
        + ", "
        + ev_non["CRANE_ID"]
        + ") | Durasi: "
        + ev_non["DURASI_MENIT"].apply(lambda d: format_decimal(d, 1))
        + " mnt | "
        + ev_non["CONTAINER_STATUS"]
    )

    ev_non = ev_non.sort_values(by=["START_TS", "TRUK_ID"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": ev_non["TRUK_ID"],
            "Format Rincian": ev_non["RINGKASAN_EVENT"],
            "Event ID": ev_non["EVENT_ID"],
            "Aktivitas": ev_non["ACTIVITY"],
            "Kapal": ev_non["VES_ID"],
            "Crane": ev_non["CRANE_ID"],
            "Waktu Mulai": ev_non["WAKTU_MULAI"],
            "Waktu Selesai": ev_non["WAKTU_SELESAI"],
            "Durasi (Menit)": ev_non["DURASI_MENIT"],
            "Tipe Kontainer": ev_non["CONTAINER_STATUS"],
            "Status": "Non Dual (Single Cycle)",
        }
    )
    return res


@st.dialog("Rincian Aktivitas Dual-Cycle", width="large")
def _show_dual_cycle_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    # Proteksi modal client-side: hanya bisa ditutup melalui tombol 'X' di pojok kanan atas
    components.html(
        """
        <script>
        (function() {
            var pDoc = window.parent ? window.parent.document : document;
            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"][aria-modal="true"]') ||
                       pDoc.querySelector('div[data-testid="stDialog"] div[role="dialog"]');
            }
            pDoc.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' || e.keyCode === 27) {
                    var m = getActiveModal();
                    if (m) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            function blockOutside(e) {
                var m = getActiveModal();
                if (m && !m.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    df_data = prepare_dual_cycle_table(events, out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data pasangan Dual Cycle yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_dual", type="secondary"):
            st.rerun()
        return

    # Hitung KPI Summary: Total Kapal (VES_ID unik), Truk Terlibat, Rata-rata Gap
    total_kapal = df_data.attrs.get("total_kapal", 0)
    if total_kapal == 0 and out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        dual_mask = (out_df["STATUS"] == "Dual Cycle") & (out_df.get("DUAL_PAIR_ID", 0) > 0)
        ves_series = out_df.loc[dual_mask, "VES_ID"].dropna().astype(str)
        v_set = set()
        for v in ves_series:
            for part in v.split(","):
                p = part.strip()
                if p and p != "-":
                    v_set.add(p)
        total_kapal = len(v_set)

    total_trucks = df_data["Truk"].nunique()
    avg_gap = df_data["Gap (Menit)"].mean()

    # Mini KPI Summary Row dengan Kartu Glassmorphism & Icon Help (?)
    mk1, mk2, mk3 = st.columns(3)
    with mk1:
        render_kpi_card(
            label="Total Kapal",
            value=f"{format_number(total_kapal)} Kapal",
            variant="blue",
            tooltip="Total jumlah kapal (VES_ID) unik yang terlayani dalam aktivitas pergerakan Dual Cycle.",
        )
    with mk2:
        render_kpi_card(
            label="Truk Terlibat",
            value=f"{format_number(total_trucks)} Truk",
            variant="blue",
            tooltip="Jumlah armada truk (CAR_CHE_ID) unik yang aktif melakukan pergerakan ritase Dual Cycle.",
        )
    with mk3:
        render_kpi_card(
            label="Rata-rata Gap",
            value=f"{format_decimal(avg_gap, 1)} menit",
            variant="blue",
            tooltip="Rata-rata selisih waktu tunggu antar aktivitas (selisih waktu selesai aktivitas pertama ke waktu mulai aktivitas kedua).",
            align_tooltip_right=True,
        )

    # Dataframe Interaktif dengan Column Config Lengkap
    st.dataframe(
        df_data,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Siklus", width="medium"),
            "Urutan": st.column_config.TextColumn("Urutan", width="small"),
            "Crane DISC": st.column_config.TextColumn("Crane DISC", width="small"),
            "Tipe DISC": st.column_config.TextColumn("Tipe DISC", width="small"),
            "Crane LOAD": st.column_config.TextColumn("Crane LOAD", width="small"),
            "Tipe LOAD": st.column_config.TextColumn("Tipe LOAD", width="small"),
            "Waktu Dermaga": st.column_config.TextColumn("Waktu Dermaga", width="small"),
            "Waktu Lapangan": st.column_config.TextColumn("Waktu Lapangan", width="small"),
            "Gap (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
        },
    )

    st.caption(f"Menampilkan total **{format_number(len(df_data))}** pasangan Dual Cycle.")

@st.dialog("Rincian Aktivitas Non-Dual", width="large")
def _show_non_dual_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    df_data = prepare_non_dual_table(events, out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data Non Dual yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_non", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row
    total_events = len(df_data)
    total_trucks = df_data["Truk"].nunique()
    disc_count = int((df_data["Aktivitas"] == "DISC").sum())
    load_count = int((df_data["Aktivitas"] == "LOAD").sum())
    avg_dur = df_data["Durasi (Menit)"].mean()

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        st.metric("Total Event Non Dual", f"{format_number(total_events)} evt")
    with mk2:
        st.metric("Truk Terlibat", f"{format_number(total_trucks)} Truk")
    with mk3:
        st.metric("Bongkar (DISC)", f"{format_number(disc_count)} evt", f"{format_number(load_count)} LOAD")
    with mk4:
        st.metric("Rata-rata Durasi", f"{format_decimal(avg_dur, 1)} mnt")

    # Filter Pencarian & Aktivitas
    fc1, fc2, fc3 = st.columns([1.8, 1.1, 1.1])
    with fc1:
        search_txt = st.text_input(
            "🔍 Cari Truk / Kapal / Crane:",
            placeholder="Ketik nomor truk (cth: 117) atau nama kapal...",
            key="filter_non_search",
        ).strip().lower()
    with fc2:
        act_filter = st.selectbox(
            "Filter Aktivitas:",
            ["Semua Aktivitas", "Hanya DISC (Bongkar)", "Hanya LOAD (Muat)"],
            key="filter_non_act_sel",
        )
    with fc3:
        mode_kolom_non = st.selectbox(
            "Tampilan Kolom:",
            ["Semua Kolom", "Rincian Operasional", "Format Ringkas"],
            key="filter_non_mode_kolom",
        )

    # Terapkan Filtering
    filtered_df = df_data.copy()
    if search_txt:
        mask = (
            filtered_df["Truk"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(search_txt, na=False)
        )
        filtered_df = filtered_df[mask]

    if act_filter == "Hanya DISC (Bongkar)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "DISC"]
    elif act_filter == "Hanya LOAD (Muat)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "LOAD"]

    if mode_kolom_non == "Rincian Operasional":
        filtered_df = filtered_df.drop(columns=["Format Rincian"])
    elif mode_kolom_non == "Format Ringkas":
        filtered_df = filtered_df[["Truk", "Format Rincian", "Aktivitas", "Durasi (Menit)"]]

    display_df = filtered_df.drop(columns=["Status", "Jenis"], errors="ignore")

    # Dataframe Interaktif
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Aktivitas", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "Waktu Mulai": st.column_config.TextColumn("Waktu Mulai", width="small"),
            "Waktu Selesai": st.column_config.TextColumn("Waktu Selesai", width="small"),
            "Durasi (Menit)": st.column_config.NumberColumn("Durasi (Mnt)", format="%.1f mnt", width="small"),
            "Tipe Kontainer": st.column_config.TextColumn("Tipe Kontainer", width="small"),
        },
    )

    st.caption(f"Menampilkan **{format_number(len(filtered_df))}** dari total **{format_number(len(df_data))}** event Non Dual.")



def prepare_issue_gap_zero_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mengambil pasangan Dual Cycle yang memiliki gap 0.0 menit.
    Gap 0 menit terjadi akibat anomali tumpang-tindih waktu (human error keterlambatan
    input konfirmasi atau toleransi pencatatan sensor).
    """
    df_dual = prepare_dual_cycle_table(events, out_df)
    if len(df_dual) == 0:
        return pd.DataFrame()
    return df_dual[df_dual["Gap (Menit)"] == 0.0].reset_index(drop=True)


def prepare_potential_dual_table(
    events: pd.DataFrame, out_df: pd.DataFrame, ambang_dual: float = 30.0, max_gap: float = 360.0
) -> pd.DataFrame:
    """
    Menyusun tabel ritase potensi Dual Cycle yang tidak terkualifikasi karena gap waktu melebihi ambang batas.
    Kriteria: Truk yang sama melakukan aktivitas bergantian (DISC ➔ LOAD atau LOAD ➔ DISC)
    secara berurutan, namun jeda waktu tunggunya > ambang_dual (dan <= max_gap menit).
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()

    ev = events.reset_index(drop=True)
    truck_positions = ev.groupby("CAR_CHE_ID").indices
    start = ev["START_TS"].to_numpy()
    end = ev["END_TS"].to_numpy()
    activity = ev["ACTIVITY"].to_numpy()
    status = ev["STATUS"].to_numpy()

    ves_map = {}
    if out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        col = "EVENT_ID" if "EVENT_ID" in out_df.columns else "GROUP_ID"
        ves_map = out_df.groupby(col)["VES_ID"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique())
        ).to_dict()

    potential_list = []
    for _, pos in truck_positions.items():
        pos_sorted = sorted(pos, key=lambda p: start[p])
        m = len(pos_sorted)
        for a in range(m - 1):
            i = pos_sorted[a]
            k = pos_sorted[a + 1]
            if activity[i] != activity[k] and (status[i] != "Dual Cycle" or status[k] != "Dual Cycle"):
                gap = (start[k] - end[i]) / np.timedelta64(1, "m")
                gap_r = round(gap, 1)
                if gap_r > ambang_dual and gap_r <= max_gap:
                    truk_id = str(ev.loc[i, "CAR_CHE_ID"]).replace(".0", "")
                    act1 = activity[i]
                    act2 = activity[k]
                    eid1 = ev.loc[i, "EVENT_ID"] if "EVENT_ID" in ev.columns else ev.loc[i, "GROUP_ID"]
                    eid2 = ev.loc[k, "EVENT_ID"] if "EVENT_ID" in ev.columns else ev.loc[k, "GROUP_ID"]
                    ves1 = ves_map.get(eid1, "-")
                    ves2 = ves_map.get(eid2, "-")
                    cr1 = str(ev.loc[i, "CRANE_ID"])
                    cr2 = str(ev.loc[k, "CRANE_ID"])
                    ringkasan = f"{truk_id} | {act1} ({ves1}, {cr1}) | ➔ {gap_r:.1f} mnt ➔ | {act2} ({ves2}, {cr2})"
                    t_selesai_1 = pd.to_datetime(ev.loc[i, "END_TS"]).strftime("%d/%m/%y %H:%M")
                    t_mulai_2 = pd.to_datetime(ev.loc[k, "START_TS"]).strftime("%d/%m/%y %H:%M")
                    potential_list.append(
                        {
                            "Truk": truk_id,
                            "Format Rincian": ringkasan,
                            "Urutan": f"{act1} ➔ {act2}",
                            "Kapal Ritase 1": ves1,
                            "Crane Ritase 1": cr1,
                            "Kapal Ritase 2": ves2,
                            "Crane Ritase 2": cr2,
                            "Waktu Selesai Ritase 1": t_selesai_1,
                            "Waktu Mulai Ritase 2": t_mulai_2,
                            "Gap (Menit)": gap_r,
                            "Kelebihan Ambang": round(gap_r - ambang_dual, 1),
                        }
                    )

    if not potential_list:
        return pd.DataFrame()

    df_res = pd.DataFrame(potential_list)
    return df_res.sort_values(by=["Gap (Menit)", "Truk"]).reset_index(drop=True)


@st.dialog("Rincian Issue Operasional & Potensi Dual Cycle", width="large")
def _show_issue_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    # Proteksi modal client-side: hanya bisa ditutup melalui tombol 'X' di pojok kanan atas
    components.html(
        """
        <script>
        (function() {
            var pDoc = window.parent ? window.parent.document : document;
            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"][aria-modal="true"]') ||
                       pDoc.querySelector('div[data-testid="stDialog"] div[role="dialog"]');
            }
            pDoc.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' || e.keyCode === 27) {
                    var m = getActiveModal();
                    if (m) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            function blockOutside(e) {
                var m = getActiveModal();
                if (m && !m.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    ambang_dual = float(summary.get("ambang_dual", 30.0)) if summary else 30.0
    df_anomali = prepare_issue_gap_zero_table(events, out_df)
    df_potensi = prepare_potential_dual_table(events, out_df, ambang_dual=ambang_dual)

    total_anomali = len(df_anomali)
    total_potensi = len(df_potensi)
    truk_anomali = set(df_anomali["Truk"].tolist()) if total_anomali > 0 else set()
    truk_potensi = set(df_potensi["Truk"].tolist()) if total_potensi > 0 else set()
    truk_terdampak = len(truk_anomali.union(truk_potensi))
    avg_gap_potensi = df_potensi["Gap (Menit)"].mean() if total_potensi > 0 else 0.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Gap 0 Mnt",
            value=f"{format_number(total_anomali)} Pasang",
            variant="amber",
            tooltip="Aktivitas Dual Cycle dengan gap 0 menit akibat Human Error dan faktor lainnya.",
        )
    with mk2:
        render_kpi_card(
            label="Potensi Dual Cycle",
            value=f"{format_number(total_potensi)} Ritase",
            variant="blue",
            tooltip=f"Aktivitas Dual Cycle dengan jeda waktu tunggu melebihi ambang batas ({ambang_dual:.0f} mnt).",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(truk_terdampak)} Truk",
            variant="amber",
            tooltip="Total truk yang terlibat aktivitas Dual Cycle, Human Error, dan faktor lainnya.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Gap Potensi",
            value=f"{format_decimal(avg_gap_potensi, 1)} mnt",
            variant="blue",
            tooltip=f"Rata-rata selisih jeda waktu tunggu truk pada potensi Dual Cycle yang melebihi batas {ambang_dual:.0f} menit.",
            align_tooltip_right=True,
        )

    tab_anomali, tab_potensi = st.tabs([
        f"⏱️ Anomali Gap 0 Menit ({format_number(total_anomali)})",
        f"🚛 Potensi Dual Cycle ({format_number(total_potensi)})",
    ])

    with tab_anomali:
        if total_anomali == 0:
            st.success("Tidak ditemukan gap 0 menit pada dataset ini.")
        else:
            q_anomali = st.text_input("🔍 Cari Truk atau Ringkasan Siklus (Anomali Gap 0):", key="search_issue_anomali_q", placeholder="Ketik nomor truk atau kode kapal...")
            df_anom_filtered = df_anomali.copy()
            if q_anomali:
                q_lower = q_anomali.lower()
                m = df_anom_filtered["Truk"].str.lower().str.contains(q_lower, na=False) | df_anom_filtered["Format Rincian"].str.lower().str.contains(q_lower, na=False)
                df_anom_filtered = df_anom_filtered[m]

            st.dataframe(
                df_anom_filtered,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Truk": st.column_config.TextColumn("No Truk", width="small"),
                    "Format Rincian": st.column_config.TextColumn("Ringkasan Siklus", width="medium"),
                    "Urutan": st.column_config.TextColumn("Urutan", width="small"),
                    "Crane DISC": st.column_config.TextColumn("Crane DISC", width="small"),
                    "Tipe DISC": st.column_config.TextColumn("Tipe DISC", width="small"),
                    "Crane LOAD": st.column_config.TextColumn("Crane LOAD", width="small"),
                    "Tipe LOAD": st.column_config.TextColumn("Tipe LOAD", width="small"),
                    "Waktu Dermaga": st.column_config.TextColumn("Waktu Dermaga", width="small"),
                    "Waktu Lapangan": st.column_config.TextColumn("Waktu Lapangan", width="small"),
                    "Gap (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
                },
            )

    with tab_potensi:
        if total_potensi == 0:
            st.success("Tidak ada ritase dengan aktivitas bergantian yang melebihi ambang batas.")
        else:
            fc1, fc2 = st.columns([2, 1.2])
            with fc1:
                q_potensi = st.text_input("🔍 Cari Truk atau Ringkasan Siklus (Potensi Dual):", key="search_issue_potensi_q", placeholder="Ketik nomor truk atau kode kapal...")
            with fc2:
                max_gap_filter = st.slider("Maksimal Gap (Menit):", min_value=int(ambang_dual) + 5, max_value=360, value=180, step=15, key="slider_max_gap_potensi")

            df_pot_filtered = df_potensi[df_potensi["Gap (Menit)"] <= max_gap_filter].copy()
            if q_potensi:
                qp_lower = q_potensi.lower()
                m_pot = df_pot_filtered["Truk"].str.lower().str.contains(qp_lower, na=False) | df_pot_filtered["Format Rincian"].str.lower().str.contains(qp_lower, na=False)
                df_pot_filtered = df_pot_filtered[m_pot]

            st.dataframe(
                df_pot_filtered,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Truk": st.column_config.TextColumn("No Truk", width="small"),
                    "Format Rincian": st.column_config.TextColumn("Ringkasan Potensi Siklus", width="medium"),
                    "Urutan": st.column_config.TextColumn("Urutan", width="small"),
                    "Kapal Ritase 1": st.column_config.TextColumn("Kapal 1", width="small"),
                    "Crane Ritase 1": st.column_config.TextColumn("Crane 1", width="small"),
                    "Kapal Ritase 2": st.column_config.TextColumn("Kapal 2", width="small"),
                    "Crane Ritase 2": st.column_config.TextColumn("Crane 2", width="small"),
                    "Waktu Selesai Ritase 1": st.column_config.TextColumn("Selesai 1", width="small"),
                    "Waktu Mulai Ritase 2": st.column_config.TextColumn("Mulai 2", width="small"),
                    "Gap (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
                    "Kelebihan Ambang": st.column_config.NumberColumn("Kelebihan Ambang", format="+%.1f mnt", width="small"),
                },
            )

def show_activity_detail_dialog(status: str, events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian aktivitas operasional
    ('Dual Cycle', 'Non Dual', atau 'Issue').
    Menyediakan tabel interaktif, format ringkasan truk, filter pencarian,
    serta tombol unduh CSV.
    """
    if status == "Dual Cycle":
        _show_dual_cycle_dialog(events, out_df, summary)
    elif status == "Issue":
        _show_issue_dialog(events, out_df, summary)
    else:
        _show_non_dual_dialog(events, out_df, summary)


def prepare_combo_table(out_df: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """
    Menyusun tabel rincian operasional Combo (basis kontainer 20ft).
    Setiap baris mewakili 1 pasangan Combo (2 kontainer 20ft dalam 1 ritase).
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame()

    df_c = out_df[(out_df["CTR_SIZE"] == 20) & (out_df["CONTAINER_STATUS"] == "Combo")].copy()
    if len(df_c) == 0:
        return pd.DataFrame()

    df_c["TS_G"] = pd.to_datetime(df_c["TS_G"])
    df_c["TS_H"] = pd.to_datetime(df_c["TS_H"])
    df_c = df_c.sort_values(by=["EVENT_ID", "TS_G"])

    g = df_c.groupby("EVENT_ID")
    r1 = g.first().reset_index()
    r2 = g.last().reset_index()

    counts = g.size().reset_index(name="cnt")
    valid_eids = set(counts.loc[counts["cnt"] == 2, "EVENT_ID"])
    r1 = r1[r1["EVENT_ID"].isin(valid_eids)].reset_index(drop=True)
    r2 = r2[r2["EVENT_ID"].isin(valid_eids)].reset_index(drop=True)

    if len(r1) == 0:
        return pd.DataFrame()

    gap_g = (r2["TS_G"] - r1["TS_G"]).dt.total_seconds().abs() / 60.0
    gap_h = (r2["TS_H"] - r1["TS_H"]).dt.total_seconds().abs() / 60.0
    gap = np.minimum(gap_g, gap_h).round(1)

    truk_id = r1["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
    ves_id = r1["VES_ID"].fillna("-").astype(str)
    crane_id = r1["CRANE_ID"].fillna("-").astype(str)
    act = r1["ACTIVITY"].fillna("-").astype(str)
    twin_status = r1.get("TWINLIFT_STATUS", pd.Series(["-"] * len(r1))).fillna("-").astype(str)

    ringkasan = (
        truk_id
        + " | "
        + act
        + " ("
        + ves_id
        + ", "
        + crane_id
        + ") | 2x 20ft | Gap: "
        + gap.apply(lambda g: format_decimal(g, 1))
        + " mnt"
    )

    res = pd.DataFrame(
        {
            "Truk": truk_id,
            "Format Rincian": ringkasan,
            "Event ID": r1["EVENT_ID"],
            "Aktivitas": act,
            "Kapal": ves_id,
            "Crane": crane_id,
            "DISC_LOAD_TS1": r1["TS_G"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "DISC_LOAD_TS2": r2["TS_G"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "STACK_UNSTACK_TS1": r1["TS_H"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "STACK_UNSTACK_TS2": r2["TS_H"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "Gap Combo (Menit)": gap,
        }
    )
    return res.sort_values(by=["Event ID", "Truk"]).reset_index(drop=True)


def prepare_single_table(out_df: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """
    Menyusun tabel rincian operasional Single (basis kontainer 20ft).
    Setiap baris mewakili 1 kontainer 20ft yang diangkut tunggal (1 kontainer per ritase).
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame()

    df_s = out_df[(out_df["CTR_SIZE"] == 20) & (out_df["CONTAINER_STATUS"] == "Single")].copy()
    if len(df_s) == 0:
        return pd.DataFrame()

    df_s["TS_G"] = pd.to_datetime(df_s["TS_G"])
    df_s["TS_H"] = pd.to_datetime(df_s["TS_H"])

    truk_id = df_s["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
    ves_id = df_s["VES_ID"].fillna("-").astype(str)
    crane_id = df_s["CRANE_ID"].fillna("-").astype(str)
    act = df_s["ACTIVITY"].fillna("-").astype(str)

    durasi_mnt = ((df_s["TS_H"] - df_s["TS_G"]).dt.total_seconds().abs() / 60.0).round(1)

    ringkasan = (
        truk_id
        + " | "
        + act
        + " ("
        + ves_id
        + ", "
        + crane_id
        + ") | 1x 20ft | Single Ritase"
    )

    res = pd.DataFrame(
        {
            "Truk": truk_id,
            "Format Rincian": ringkasan,
            "Event ID": df_s["EVENT_ID"],
            "Aktivitas": act,
            "Kapal": ves_id,
            "Crane": crane_id,
            "DISC_LOAD_TS": df_s["TS_G"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "STACK_UNSTACK_TS": df_s["TS_H"].dt.strftime("%d/%m/%y %H:%M:%S"),
            "Durasi (Menit)": durasi_mnt,
        }
    )
    return res.sort_values(by=["Event ID", "Truk"]).reset_index(drop=True)


def prepare_combo_gap_zero_table(out_df: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """
    Menyusun tabel anomali Combo dengan gap 0.0 menit (indikasi timestamp kembar / human error).
    """
    df_combo = prepare_combo_table(out_df, events)
    if len(df_combo) == 0:
        return pd.DataFrame()
    return df_combo[df_combo["Gap Combo (Menit)"] <= 0.0].reset_index(drop=True)


def prepare_potential_combo_table(
    out_df: pd.DataFrame,
    events: pd.DataFrame = None,
    ambang_combo: float = 3.0,
    max_gap: float = 60.0,
) -> pd.DataFrame:
    """
    Menyusun tabel potensi Combo tertunda:
    Kontainer 20ft pada truk yang sama dan aktivitas yang sama (DISC-DISC atau LOAD-LOAD),
    namun jeda waktu tunggunya melebihi ambang_combo (dan <= max_gap menit),
    sehingga terpaksa dihitung sebagai Single terpisah.
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame()

    df20 = out_df[out_df["CTR_SIZE"] == 20].copy()
    if len(df20) < 2:
        return pd.DataFrame()

    df20["TS_G"] = pd.to_datetime(df20["TS_G"])
    df20["TS_H"] = pd.to_datetime(df20["TS_H"])

    potentials = []
    for (truck, act), group in df20.groupby(["CAR_CHE_ID", "ACTIVITY"]):
        g_sorted = group.sort_values("TS_G").reset_index(drop=True)
        m = len(g_sorted)
        for i in range(m - 1):
            r1 = g_sorted.iloc[i]
            r2 = g_sorted.iloc[i + 1]
            if r1["EVENT_ID"] == r2["EVENT_ID"]:
                continue
            gap_g = abs((r2["TS_G"] - r1["TS_G"]).total_seconds()) / 60.0
            gap_h = abs((r2["TS_H"] - r1["TS_H"]).total_seconds()) / 60.0
            gap = min(gap_g, gap_h)
            gap_r = round(gap, 1)

            if gap_r > ambang_combo and gap_r <= max_gap:
                truk_id = str(truck).replace(".0", "")
                ves1 = str(r1["VES_ID"])
                ves2 = str(r2["VES_ID"])
                cr1 = str(r1["CRANE_ID"])
                cr2 = str(r2["CRANE_ID"])
                ringkasan = f"{truk_id} | {act} ({ves1}, {cr1}) | ➔ {gap_r:.1f} mnt ➔ | {act} ({ves2}, {cr2})"
                potentials.append(
                    {
                        "Truk": truk_id,
                        "Format Rincian": ringkasan,
                        "Aktivitas": act,
                        "Kapal 1": ves1,
                        "Crane 1": cr1,
                        "Kapal 2": ves2,
                        "Crane 2": cr2,
                        "Waktu 1": r1["TS_G"].strftime("%d/%m/%y %H:%M"),
                        "Waktu 2": r2["TS_G"].strftime("%d/%m/%y %H:%M"),
                        "Gap (Menit)": gap_r,
                        "Kelebihan Ambang": round(gap_r - ambang_combo, 1),
                    }
                )

    if not potentials:
        return pd.DataFrame()
    df_pot = pd.DataFrame(potentials)
    return df_pot.sort_values(by=["Gap (Menit)", "Truk"]).reset_index(drop=True)


@st.dialog("Rincian Aktivitas Combo (Kontainer 20ft)", width="large")
def _show_combo_dialog(out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up rincian aktivitas Combo (2x 20ft per ritase).
    """
    components.html(
        """
        <script>
        (function() {
            var pDoc = window.parent.document;
            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"]');
            }
            pDoc.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    var m = getActiveModal();
                    if (m) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            function blockOutside(e) {
                var m = getActiveModal();
                if (m && !m.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    df_data = prepare_combo_table(out_df, events)
    if len(df_data) == 0:
        st.info("Tidak ada data aktivitas Combo yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_combo", type="secondary"):
            st.rerun()
        return

    total_ritase = len(df_data)
    total_kontainer = total_ritase * 2
    total_trucks = df_data["Truk"].nunique()
    avg_gap = df_data["Gap Combo (Menit)"].mean()

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Total Ritase Combo",
            value=f"{format_number(total_ritase)} Pasang",
            variant="blue",
            tooltip="Jumlah pergerakan 2 kontainer dalam 1 truk yang sama.",
        )
    with mk2:
        render_kpi_card(
            label="Total Kontainer",
            value=f"{format_number(total_kontainer)} Box",
            variant="purple",
            tooltip="Jumlah kontainer 20ft yang terangkut secara bersamaan.",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(total_trucks)} Truk",
            variant="amber",
            tooltip="Jumlah truk yang membawa 2 kontainer.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Gap Combo",
            value=f"{format_decimal(avg_gap, 1)} mnt",
            variant="blue",
            tooltip="Rata-rata selisih waktu aktivitas 2 kontainer.",
            align_tooltip_right=True,
        )

    q = st.text_input("🔍 Cari Truk, Kapal, atau Ringkasan Combo:", key="search_combo_detail_q", placeholder="Ketik nomor truk, kode kapal, crane...")
    filtered_df = df_data.copy()
    if q:
        q_lower = q.lower()
        mask = (
            filtered_df["Truk"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Crane"].str.lower().str.contains(q_lower, na=False)
        )
        filtered_df = filtered_df[mask]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Combo", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "DISC_LOAD_TS1": st.column_config.TextColumn("DISC_LOAD_TS1", width="small"),
            "DISC_LOAD_TS2": st.column_config.TextColumn("DISC_LOAD_TS2", width="small"),
            "STACK_UNSTACK_TS1": st.column_config.TextColumn("STACK_UNSTACK_TS1", width="small"),
            "STACK_UNSTACK_TS2": st.column_config.TextColumn("STACK_UNSTACK_TS2", width="small"),
            "Gap Combo (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
        },
    )

@st.dialog("Rincian Aktivitas Single (Kontainer 20ft)", width="large")
def _show_single_dialog(out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up rincian aktivitas Single (1x 20ft per ritase).
    """
    components.html(
        """
        <script>
        (function() {
            var pDoc = window.parent.document;
            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"]');
            }
            pDoc.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    var m = getActiveModal();
                    if (m) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            function blockOutside(e) {
                var m = getActiveModal();
                if (m && !m.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    df_data = prepare_single_table(out_df, events)
    if len(df_data) == 0:
        st.info("Tidak ada data aktivitas Single 20ft yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_single", type="secondary"):
            st.rerun()
        return

    total_ritase = len(df_data)
    total_kontainer = total_ritase
    total_trucks = df_data["Truk"].nunique()
    avg_durasi = df_data["Durasi (Menit)"].mean() if "Durasi (Menit)" in df_data.columns else 0.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Total Ritase Single",
            value=f"{format_number(total_ritase)} Ritase",
            variant="blue",
            tooltip="Jumlah pergerakan 1 kontainer dalam 1 truk yang sama (Single).",
        )
    with mk2:
        render_kpi_card(
            label="Total Kontainer",
            value=f"{format_number(total_kontainer)} Box",
            variant="purple",
            tooltip="Jumlah kontainer 20ft yang diangkut tunggal (1 kontainer per ritase).",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(total_trucks)} Truk",
            variant="amber",
            tooltip="Jumlah truk yang membawa 1 kontainer.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Durasi Single",
            value=f"{format_decimal(avg_durasi, 1)} mnt",
            variant="blue",
            tooltip="Rata-rata durasi pergerakan aktivitas ritase kontainer Single.",
            align_tooltip_right=True,
        )

    q = st.text_input("🔍 Cari Truk, Kapal, atau Ringkasan Single:", key="search_single_detail_q", placeholder="Ketik nomor truk, kode kapal, crane...")
    filtered_df = df_data.copy()
    if q:
        q_lower = q.lower()
        mask = (
            filtered_df["Truk"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(q_lower, na=False)
            | filtered_df["Crane"].str.lower().str.contains(q_lower, na=False)
        )
        filtered_df = filtered_df[mask]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Single", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "DISC_LOAD_TS": st.column_config.TextColumn("DISC_LOAD_TS", width="small"),
            "STACK_UNSTACK_TS": st.column_config.TextColumn("STACK_UNSTACK_TS", width="small"),
            "Durasi (Menit)": st.column_config.NumberColumn("Durasi (Mnt)", format="%.1f mnt", width="small"),
        },
    )


@st.dialog("Rincian Issue Operasional & Potensi Combo (Kontainer 20ft)", width="large")
def _show_combo_issue_dialog(out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up rincian anomali dan potensi Combo tertunda.
    """
    components.html(
        """
        <script>
        (function() {
            var pDoc = window.parent.document;
            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"]');
            }
            pDoc.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    var m = getActiveModal();
                    if (m) {
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            function blockOutside(e) {
                var m = getActiveModal();
                if (m && !m.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    ambang_combo = float(summary.get("ambang_combo", 3.0)) if summary else 3.0
    df_anomali = prepare_combo_gap_zero_table(out_df, events)
    df_potensi = prepare_potential_combo_table(out_df, events, ambang_combo=ambang_combo)

    total_anomali = len(df_anomali)
    total_potensi = len(df_potensi)
    truk_anomali = set(df_anomali["Truk"].tolist()) if total_anomali > 0 else set()
    truk_potensi = set(df_potensi["Truk"].tolist()) if total_potensi > 0 else set()
    truk_terdampak = len(truk_anomali.union(truk_potensi))
    avg_gap_potensi = df_potensi["Gap (Menit)"].mean() if total_potensi > 0 else 0.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Gap 0 Mnt",
            value=f"{format_number(total_anomali)} Pasang",
            variant="amber",
            tooltip="Pasangan Combo dengan perbedaan waktu lifting persis 0.0 menit (indikasi timestamp ganda / human error).",
        )
    with mk2:
        render_kpi_card(
            label="Potensi Combo",
            value=f"{format_number(total_potensi)} Pasang",
            variant="blue",
            tooltip=f"Pasangan kontainer 20ft pada aktivitas sama yang tidak ter-combo karena jeda waktu melebihi ambang batas ({ambang_combo:.0f} mnt).",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(truk_terdampak)} Truk",
            variant="amber",
            tooltip="Total armada truk unik yang teridentifikasi memiliki anomali atau potensi Combo.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Gap Potensi",
            value=f"{format_decimal(avg_gap_potensi, 1)} mnt",
            variant="blue",
            tooltip=f"Rata-rata jeda waktu pada pasangan kontainer potensi Combo yang melebihi ambang batas ({ambang_combo:.0f} mnt).",
            align_tooltip_right=True,
        )

    tab_anomali, tab_potensi = st.tabs([
        f"⏱️ Anomali Gap 0 Menit ({format_number(total_anomali)})",
        f"📦 Potensi Combo ({format_number(total_potensi)})",
    ])

    with tab_anomali:
        if total_anomali == 0:
            st.success("Tidak ditemukan anomali gap 0 menit pada ritase Combo.")
        else:
            q_anomali = st.text_input("🔍 Cari Truk atau Ringkasan Anomali (Gap 0):", key="search_combo_issue_anomali_q", placeholder="Ketik nomor truk atau kode kapal...")
            df_anom_filtered = df_anomali.copy()
            if q_anomali:
                q_lower = q_anomali.lower()
                m = df_anom_filtered["Truk"].str.lower().str.contains(q_lower, na=False) | df_anom_filtered["Format Rincian"].str.lower().str.contains(q_lower, na=False)
                df_anom_filtered = df_anom_filtered[m]

            st.dataframe(
                df_anom_filtered,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Truk": st.column_config.TextColumn("No Truk", width="small"),
                    "Format Rincian": st.column_config.TextColumn("Ringkasan Combo", width="medium"),
                    "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
                    "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
                    "Kapal": st.column_config.TextColumn("Kapal", width="small"),
                    "Crane": st.column_config.TextColumn("Crane", width="small"),
                    "DISC_LOAD_TS1": st.column_config.TextColumn("DISC_LOAD_TS1", width="small"),
                    "DISC_LOAD_TS2": st.column_config.TextColumn("DISC_LOAD_TS2", width="small"),
                    "STACK_UNSTACK_TS1": st.column_config.TextColumn("STACK_UNSTACK_TS1", width="small"),
                    "STACK_UNSTACK_TS2": st.column_config.TextColumn("STACK_UNSTACK_TS2", width="small"),
                    "Gap Combo (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
                },
            )

    with tab_potensi:
        if total_potensi == 0:
            st.success("Tidak ada kontainer dengan aktivitas sama yang jeda waktunya melebihi ambang batas.")
        else:
            fc1, fc2 = st.columns([2, 1.2])
            with fc1:
                q_potensi = st.text_input("🔍 Cari Truk atau Ringkasan Siklus (Potensi Combo):", key="search_combo_issue_potensi_q", placeholder="Ketik nomor truk atau kode kapal...")
            with fc2:
                max_gap_filter = st.slider("Maksimal Gap (Menit):", min_value=int(ambang_combo) + 1, max_value=60, value=30, step=5, key="slider_max_gap_combo_potensi")

            df_pot_filtered = df_potensi[df_potensi["Gap (Menit)"] <= max_gap_filter].copy()
            if q_potensi:
                qp_lower = q_potensi.lower()
                m_pot = df_pot_filtered["Truk"].str.lower().str.contains(qp_lower, na=False) | df_pot_filtered["Format Rincian"].str.lower().str.contains(qp_lower, na=False)
                df_pot_filtered = df_pot_filtered[m_pot]

            st.dataframe(
                df_pot_filtered,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Truk": st.column_config.TextColumn("No Truk", width="small"),
                    "Format Rincian": st.column_config.TextColumn("Ringkasan Potensi Combo", width="medium"),
                    "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
                    "Kapal 1": st.column_config.TextColumn("Kapal 1", width="small"),
                    "Crane 1": st.column_config.TextColumn("Crane 1", width="small"),
                    "Kapal 2": st.column_config.TextColumn("Kapal 2", width="small"),
                    "Crane 2": st.column_config.TextColumn("Crane 2", width="small"),
                    "Waktu 1": st.column_config.TextColumn("Waktu 1", width="small"),
                    "Waktu 2": st.column_config.TextColumn("Waktu 2", width="small"),
                    "Gap (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
                    "Kelebihan Ambang": st.column_config.NumberColumn("Kelebihan Ambang", format="+%.1f mnt", width="small"),
                },
            )


def show_combo_detail_dialog(status: str, out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Combo
    ('Combo', 'Single', atau 'Issue').
    """
    if status == "Combo":
        _show_combo_dialog(out_df, events, summary)
    elif status == "Single":
        _show_single_dialog(out_df, events, summary)
    elif status == "Issue":
        _show_combo_issue_dialog(out_df, events, summary)


def prepare_twinlift_table(out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyusun tabel rincian operasional Twinlift (basis kontainer 20ft).
    Menyajikan informasi truk, kapal, crane (QC), waktu dermaga (DISC_LOAD_TS),
    waktu lapangan (STACK_UNSTACK_TS), gap waktu, serta status Twinlift.
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame()

    # Filter basis kontainer 20ft (satu-satunya ukuran yang eligible Twinlift)
    df20 = out_df[out_df["CTR_SIZE"] == 20].copy()
    if len(df20) == 0:
        return pd.DataFrame()

    df20["TS_G"] = pd.to_datetime(df20["TS_G"])
    df20["TS_H"] = pd.to_datetime(df20["TS_H"])

    truk_id = df20["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
    ves_id = df20["VES_ID"].fillna("-").astype(str)
    crane_id = df20["CRANE_ID"].fillna("-").astype(str)
    activity = df20["ACTIVITY"].fillna("-").astype(str)
    status_twin = df20["TWINLIFT_STATUS"].fillna("Bukan Twinlift").astype(str)
    container_status = df20["CONTAINER_STATUS"].fillna("Single").astype(str)

    # Gap menit dibulatkan 2 desimal
    gap_val = df20["TWINLIFT_GAP_MENIT"].fillna(0.0).round(2)

    waktu_dermaga = df20["TS_G"].dt.strftime("%d/%m/%y %H:%M:%S")
    waktu_lapangan = df20["TS_H"].dt.strftime("%d/%m/%y %H:%M:%S")

    ringkasan = (
        truk_id
        + " | "
        + activity
        + " ("
        + ves_id
        + ", "
        + crane_id
        + ") | Gap: "
        + gap_val.apply(lambda g: format_decimal(g, 2))
        + " mnt | "
        + status_twin
    )

    df20["_SORT_TS"] = df20["TS_G"]
    df20["_TRUK"] = truk_id
    df20["_RINGKASAN"] = ringkasan
    df20["_VES"] = ves_id
    df20["_CRANE"] = crane_id
    df20["_ACT"] = activity
    df20["_WAKTU_DERMAGA"] = waktu_dermaga
    df20["_WAKTU_LAPANGAN"] = waktu_lapangan
    df20["_GAP"] = gap_val
    df20["_STATUS_TWIN"] = status_twin
    df20["_CONTAINER_STATUS"] = container_status

    df20 = df20.sort_values(by=["_SORT_TS", "EVENT_ID", "_TRUK"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": df20["_TRUK"],
            "Format Rincian": df20["_RINGKASAN"],
            "Event ID": df20["EVENT_ID"],
            "Aktivitas": df20["_ACT"],
            "Kapal": df20["_VES"],
            "Crane": df20["_CRANE"],
            "Waktu Dermaga": df20["_WAKTU_DERMAGA"],
            "Waktu Lapangan": df20["_WAKTU_LAPANGAN"],
            "Gap Twinlift": df20["_GAP"],
            "Status Twinlift": df20["_STATUS_TWIN"],
            "Tipe Muatan": df20["_CONTAINER_STATUS"],
        }
    )
    return res


@st.dialog("Rincian Aktivitas Twinlift (Kontainer 20ft)", width="large")
def _show_twinlift_dialog(out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Twinlift
    saat tombol 'Rincian Twinlift' di bawah donut chart diklik.
    """
    df_data = prepare_twinlift_table(out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data kontainer 20ft yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_twin", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row
    total_20ft = len(df_data)
    twin_mask = df_data["Status Twinlift"] == "Twinlift"
    total_twinlift = int(twin_mask.sum())
    pct_twinlift = (total_twinlift / total_20ft * 100) if total_20ft > 0 else 0
    total_pasangan = total_twinlift // 2

    df_twin = df_data[twin_mask]
    truk_terlibat = df_twin["Truk"].nunique() if total_twinlift > 0 else 0
    crane_terlibat = df_twin["Crane"].nunique() if total_twinlift > 0 else 0
    avg_gap_twin = df_twin["Gap Twinlift"].mean() if total_twinlift > 0 else 0.0

    ambang_tw_label = f"Ambang batas: ≤ {format_number(summary.get('ambang_twinlift', 1))} mnt" if summary and "ambang_twinlift" in summary else "Toleransi lifting"

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        st.metric("Total Twinlift", f"{format_number(total_twinlift)} Ctr", f"{format_number(total_pasangan)} pasang lift")
    with mk2:
        st.metric("% Twinlift (20ft)", format_percent(pct_twinlift, 1), f"dari {format_number(total_20ft)} Ctr 20ft")
    with mk3:
        st.metric("Truk & Crane", f"{format_number(truk_terlibat)} Truk", f"{format_number(crane_terlibat)} Crane (QC)")
    with mk4:
        st.metric("Rata-rata Gap", f"{format_decimal(avg_gap_twin, 2)} mnt", ambang_tw_label)

    # Filter Pencarian & Kategori
    fc1, fc2, fc3, fc4 = st.columns([1.8, 1.1, 1.1, 1.1])
    with fc1:
        search_txt = st.text_input(
            "🔍 Cari Truk / Kapal / Crane / Event:",
            placeholder="Ketik ID Truk / Kapal / Crane...",
            key="filter_twin_search",
        ).strip().lower()
    with fc2:
        status_filter = st.selectbox(
            "Status Operasi:",
            ["Hanya Twinlift", "Semua Kontainer 20ft", "Hanya Bukan Twinlift"],
            key="filter_twin_status_sel",
        )
    with fc3:
        act_filter = st.selectbox(
            "Filter Aktivitas:",
            ["Semua Aktivitas", "Hanya DISC (Bongkar)", "Hanya LOAD (Muat)"],
            key="filter_twin_act_sel",
        )
    with fc4:
        mode_kolom = st.selectbox(
            "Tampilan Kolom:",
            ["Semua Kolom", "Rincian Operasional", "Format Ringkas"],
            key="filter_twin_mode_kolom",
        )

    # Terapkan Filtering
    filtered_df = df_data.copy()
    if search_txt:
        mask = (
            filtered_df["Truk"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Event ID"].astype(str).str.contains(search_txt, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(search_txt, na=False)
        )
        filtered_df = filtered_df[mask]

    if status_filter == "Hanya Twinlift":
        filtered_df = filtered_df[filtered_df["Status Twinlift"] == "Twinlift"]
    elif status_filter == "Hanya Bukan Twinlift":
        filtered_df = filtered_df[filtered_df["Status Twinlift"] == "Bukan Twinlift"]

    if act_filter == "Hanya DISC (Bongkar)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "DISC"]
    elif act_filter == "Hanya LOAD (Muat)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "LOAD"]

    if mode_kolom == "Rincian Operasional":
        filtered_df = filtered_df.drop(columns=["Format Rincian"])
    elif mode_kolom == "Format Ringkas":
        filtered_df = filtered_df[["Truk", "Format Rincian", "Aktivitas", "Gap Twinlift", "Status Twinlift"]]

    # Dataframe Interaktif dengan Column Config Lengkap
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Operasional", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "Waktu Dermaga": st.column_config.TextColumn("Waktu Dermaga", width="small"),
            "Waktu Lapangan": st.column_config.TextColumn("Waktu Lapangan", width="small"),
            "Gap Twinlift": st.column_config.NumberColumn("Gap (Mnt)", format="%.2f mnt", width="small"),
            "Status Twinlift": st.column_config.TextColumn("Status", width="small"),
            "Tipe Muatan": st.column_config.TextColumn("Muatan Truk", width="small"),
        },
    )

    st.caption(f"Menampilkan **{format_number(len(filtered_df))}** dari total **{format_number(len(df_data))}** data kontainer 20ft.")


@st.dialog("Rincian Aktivitas Bukan Twinlift (Kontainer 20ft)", width="large")
def _show_non_twinlift_dialog(out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Bukan Twinlift (Single Lift 20ft)
    saat tombol 'Rincian Bukan Twinlift' di bawah donut chart diklik.
    """
    df_data = prepare_twinlift_table(out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data kontainer 20ft yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_nontwin", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row
    total_20ft = len(df_data)
    non_twin_mask = df_data["Status Twinlift"] == "Bukan Twinlift"
    total_non_twin = int(non_twin_mask.sum())
    pct_non_twin = (total_non_twin / total_20ft * 100) if total_20ft > 0 else 0

    df_non = df_data[non_twin_mask]
    truk_terlibat = df_non["Truk"].nunique() if total_non_twin > 0 else 0
    crane_terlibat = df_non["Crane"].nunique() if total_non_twin > 0 else 0
    disc_count = int((df_non["Aktivitas"] == "DISC").sum())
    load_count = int((df_non["Aktivitas"] == "LOAD").sum())

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        st.metric("Total Bukan Twinlift", f"{format_number(total_non_twin)} Ctr", "Single lift 20ft")
    with mk2:
        st.metric("% Bukan Twinlift", format_percent(pct_non_twin, 1), f"dari {format_number(total_20ft)} Ctr 20ft")
    with mk3:
        st.metric("Truk & Crane", f"{format_number(truk_terlibat)} Truk", f"{format_number(crane_terlibat)} Crane (QC)")
    with mk4:
        st.metric("Aktivitas Operasi", f"{format_number(disc_count)} DISC", f"{format_number(load_count)} LOAD")

    # Filter Pencarian & Kategori
    fc1, fc2, fc3, fc4 = st.columns([1.8, 1.1, 1.1, 1.1])
    with fc1:
        search_txt = st.text_input(
            "🔍 Cari Truk / Kapal / Crane / Event:",
            placeholder="Ketik ID Truk / Kapal / Crane...",
            key="filter_nontwin_search",
        ).strip().lower()
    with fc2:
        status_filter = st.selectbox(
            "Status Operasi:",
            ["Hanya Bukan Twinlift", "Semua Kontainer 20ft", "Hanya Twinlift"],
            key="filter_nontwin_status_sel",
        )
    with fc3:
        act_filter = st.selectbox(
            "Filter Aktivitas:",
            ["Semua Aktivitas", "Hanya DISC (Bongkar)", "Hanya LOAD (Muat)"],
            key="filter_nontwin_act_sel",
        )
    with fc4:
        mode_kolom = st.selectbox(
            "Tampilan Kolom:",
            ["Semua Kolom", "Rincian Operasional", "Format Ringkas"],
            key="filter_nontwin_mode_kolom",
        )

    # Terapkan Filtering
    filtered_df = df_data.copy()
    if search_txt:
        mask = (
            filtered_df["Truk"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Event ID"].astype(str).str.contains(search_txt, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(search_txt, na=False)
        )
        filtered_df = filtered_df[mask]

    if status_filter == "Hanya Bukan Twinlift":
        filtered_df = filtered_df[filtered_df["Status Twinlift"] == "Bukan Twinlift"]
    elif status_filter == "Hanya Twinlift":
        filtered_df = filtered_df[filtered_df["Status Twinlift"] == "Twinlift"]

    if act_filter == "Hanya DISC (Bongkar)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "DISC"]
    elif act_filter == "Hanya LOAD (Muat)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "LOAD"]

    if mode_kolom == "Rincian Operasional":
        filtered_df = filtered_df.drop(columns=["Format Rincian"])
    elif mode_kolom == "Format Ringkas":
        filtered_df = filtered_df[["Truk", "Format Rincian", "Aktivitas", "Gap Twinlift", "Status Twinlift"]]

    # Dataframe Interaktif dengan Column Config Lengkap
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Operasional", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "Waktu Dermaga": st.column_config.TextColumn("Waktu Dermaga", width="small"),
            "Waktu Lapangan": st.column_config.TextColumn("Waktu Lapangan", width="small"),
            "Gap Twinlift": st.column_config.NumberColumn("Gap (Mnt)", format="%.2f mnt", width="small"),
            "Status Twinlift": st.column_config.TextColumn("Status", width="small"),
            "Tipe Muatan": st.column_config.TextColumn("Muatan Truk", width="small"),
        },
    )

    st.caption(f"Menampilkan **{format_number(len(filtered_df))}** dari total **{format_number(len(df_data))}** data kontainer 20ft.")


def show_twinlift_detail_dialog(status: str, out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Twinlift atau Bukan Twinlift
    saat tombol 'Rincian Twinlift' atau 'Rincian Bukan Twinlift' diklik di bawah chart donut.
    """
    if status == "Twinlift":
        _show_twinlift_dialog(out_df, summary)
    else:
        _show_non_twinlift_dialog(out_df, summary)

