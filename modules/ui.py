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

# Naikkan batas maksimum elemen sel Pandas Styler agar dataset besar (> 262.144 sel)
# tetap dapat dirender tanpa memicu StreamlitAPIException
pd.set_option("styler.render.max_elements", 5000000)

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"
GIFS_DIR = ASSETS_DIR / "gifs"
GIFS_DIR.mkdir(parents=True, exist_ok=True)


def find_asset_file(candidates: list[str]) -> Path | None:
    """Mencari file aset dari daftar kandidat nama file (mendukung pencarian case-insensitive)."""
    for name in candidates:
        p = ASSETS_DIR / name
        if p.exists() and p.is_file():
            return p
        # Coba pencarian case-insensitive di folder target
        target_dir = p.parent
        if target_dir.exists() and target_dir.is_dir():
            target_name_lower = p.name.lower()
            for item in target_dir.iterdir():
                if item.is_file() and item.name.lower() == target_name_lower:
                    return item
    return None


@st.cache_resource
def setup_template_and_asset_watchers():
    """
    Mengaktifkan pemantauan otomatis (live reload) untuk folder templates/ dan assets/.
    Ketika pengguna atau developer mengedit file HTML, CSS, atau menambahkan GIF, Streamlit
    akan otomatis melakukan rerun pada browser secara real-time.
    """
    try:
        from streamlit.watcher.path_watcher import watch_dir
        from streamlit.runtime import Runtime

        def _on_resource_changed(changed_path: str):
            if ".cache" in changed_path:
                return
            if Runtime.exists():
                try:
                    rt = Runtime.instance()
                    for s_info in rt._session_mgr.list_active_sessions():
                        s_info.session.request_rerun(s_info.session._client_state)
                except Exception:
                    pass

        watch_dir(str(TEMPLATES_DIR.resolve()), _on_resource_changed)
        watch_dir(str(ASSETS_DIR.resolve()), _on_resource_changed)
        if GIFS_DIR.exists():
            watch_dir(str(GIFS_DIR.resolve()), _on_resource_changed)
        return True
    except Exception:
        return False


# Inisialisasi watcher templates dan assets dipanggil saat inject_css (setelah st.set_page_config)




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
    setup_template_and_asset_watchers()
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


def inject_modal_backdrop_protection():
    """
    Menyuntikkan script proteksi modal dialog agar dialog hanya dapat ditutup
    melalui tombol 'X' di pojok kanan atas, bukan saat mengklik backdrop
    di luar modal atau menekan tombol Escape.
    Sekaligus menyesuaikan tinggi tabel st.dataframe di dalam modal secara
    responsif mengikuti tinggi viewport (termasuk saat browser di-zoom 90%/80%).
    """
    components.html(
        """
        <script>
        (function() {
            var pWin = window.parent || window;
            var pDoc = pWin.document || document;
            if (!pDoc) return;

            function getActiveModal() {
                return pDoc.querySelector('div[role="dialog"]') ||
                       pDoc.querySelector('div[data-testid="stDialog"] div[role="dialog"]');
            }

            function fitModalDataframeHeight() {
                var modal = getActiveModal();
                if (!modal) return;
                var dfContainer = modal.querySelector('[data-testid="stDataFrame"]');
                if (!dfContainer) return;

                var vh = pWin.innerHeight || pDoc.documentElement.clientHeight || 800;
                var rect = dfContainer.getBoundingClientRect();
                var topOffset = rect.top > 40 ? rect.top : 240;
                // Sisakan ~64px di bagian bawah untuk keterangan footer & padding modal
                var targetHeight = Math.max(420, Math.floor(vh - topOffset - 64));

                dfContainer.style.setProperty('height', targetHeight + 'px', 'important');
                var innerResizable = dfContainer.querySelector('.stDataFrameGlideDataEditor') ||
                                     dfContainer.firstElementChild;
                if (innerResizable) {
                    innerResizable.style.setProperty('height', targetHeight + 'px', 'important');
                    innerResizable.style.setProperty('max-height', targetHeight + 'px', 'important');
                }
            }

            // Jalankan saat modal terbuka dan setiap kali ukuran/zoom browser berubah
            fitModalDataframeHeight();
            setTimeout(fitModalDataframeHeight, 80);
            setTimeout(fitModalDataframeHeight, 220);
            setTimeout(fitModalDataframeHeight, 500);
            pWin.addEventListener('resize', fitModalDataframeHeight);

            function isDropdownOrPortal(target) {
                if (!target || !target.closest) return false;
                return !!(
                    target.closest('[data-baseweb="popover"]') ||
                    target.closest('[data-baseweb="menu"]') ||
                    target.closest('[role="listbox"]') ||
                    target.closest('[role="option"]') ||
                    target.closest('[data-baseweb="select"]') ||
                    target.closest('[data-testid="stSelectboxVirtualDropdown"]') ||
                    target.closest('[data-baseweb="portal"]') ||
                    target.closest('[data-testid="stPortal"]')
                );
            }

            function blockOutside(e) {
                var modal = getActiveModal();
                if (!modal) return;

                // 1. Izinkan interaksi mouse pada dropdown / selectbox / popover BaseWeb
                if (isDropdownOrPortal(e.target)) {
                    return;
                }

                // 2. Jika target klik di luar modal (area backdrop), blokir agar modal TIDAK tertutup!
                if (!modal.contains(e.target)) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                    e.preventDefault();
                }
            }

            function blockEscape(e) {
                if (e.key === 'Escape' || e.keyCode === 27) {
                    var modal = getActiveModal();
                    if (modal) {
                        var openPopover = pDoc.querySelector('[data-baseweb="popover"]');
                        if (openPopover) {
                            return; // Biarkan Escape menutup dropdown menu saja
                        }
                        e.stopImmediatePropagation();
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }

            // Pasang event listener dengan capture phase (true) agar dicegat sebelum event mencapai BaseWeb handler
            pDoc.addEventListener('keydown', blockEscape, true);
            pDoc.addEventListener('mousedown', blockOutside, true);
            pDoc.addEventListener('pointerdown', blockOutside, true);
            pDoc.addEventListener('click', blockOutside, true);
        })();
        </script>
        """,
        height=0,
        width=0,
    )



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


def format_duration(val: int | float | str | None) -> str:
    """
    Memformat durasi dari menit ke format baku durasi operasional (mendukung hari d, jam h, menit m, detik s):
    - Contoh: 0.2 mnt -> '12s'
    - Contoh: 4.7 mnt -> '4m 42s'
    - Contoh: 69.88 mnt -> '1h 9m 53s'
    - Contoh: 1500 mnt -> '1d 1h'
    - Contoh: 0 mnt -> '0s'
    """
    if val is None:
        return "-"
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val):
            return "-"
        minutes = float(val)
    else:
        s = str(val).strip().replace(",", ".")
        if s.lower() in ("nan", "none", "", "-"):
            return "-"
        try:
            minutes = float(s)
            if np.isnan(minutes):
                return "-"
        except ValueError:
            return str(val)

    total_seconds = int(round(abs(minutes) * 60))
    prefix = "-" if minutes < 0 else ""

    if total_seconds == 0:
        return "0s"

    d = total_seconds // 86400
    rem = total_seconds % 86400
    h = rem // 3600
    rem = rem % 3600
    m = rem // 60
    s = rem % 60

    parts = []
    if d > 0:
        parts.append(f"{d}d")
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0:
        parts.append(f"{s}s")

    return prefix + " ".join(parts)


def format_duration_sortable(val: int | float | str | None, max_minutes: float = 0.0) -> str:
    """
    Memformat durasi untuk kolom tabel st.dataframe agar pengurutan (sort ↑ / ↓)
    di browser (Intl.Collator) 100% akurat dari waktu terkecil hingga terbesar:
    - Jika tabel hanya memuat durasi < 60 menit (seperti Dual Cycle & Combo): 'MMm SSs' ('00m 09s', '14m 48s')
    - Jika tabel memuat durasi >= 60 menit (< 1 hari): 'HHh MMm SSs' ('00h 46m 53s', '01h 09m 53s')
    - Jika tabel memuat durasi >= 1 hari (>= 1440 menit): 'DDd HHh MMm SSs' ('00d 00h 46m 53s', '01d 04h 20m 15s')
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
    """
    if val is None:
        return "-"
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val):
            return "-"
        minutes = float(val)
    else:
        s = str(val).strip().replace(",", ".")
        if s.lower() in ("nan", "none", "", "-"):
            return "-"
        try:
            minutes = float(s)
            if np.isnan(minutes):
                return "-"
        except ValueError:
            return str(val)

    total_seconds = max(0, int(round(abs(minutes) * 60)))
    prefix = "-" if minutes < 0 else ""

    d = total_seconds // 86400
    rem = total_seconds % 86400
    h = rem // 3600
    rem = rem % 3600
    m = rem // 60
    s = rem % 60

    max_days = max(d, int(max(0.0, float(max_minutes)) // 1440.0))
    d_width = max(2, len(str(max_days)))

    if max_minutes >= 1440.0 or d > 0:
        return f"{prefix}{d:0{d_width}d}d {h:02d}h {m:02d}m {s:02d}s"
    if max_minutes >= 60.0 or h > 0:
        return f"{prefix}{h:02d}h {m:02d}m {s:02d}s"
    return f"{prefix}{m:02d}m {s:02d}s"


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
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
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
    # =========================================================================
    # PERINGATAN / ATURAN TETAP (DO NOT MODIFY - LOCKED LOGIC):
    # Rumus perhitungan GAP Dual Cycle (Selesai ➔ Mulai):
    # - DISC ➔ LOAD: START_TS_LOAD - END_TS_DISC
    # - LOAD ➔ DISC: START_TS_DISC - END_TS_LOAD
    # Jika terjadi overlap (keduanya negatif), gunakan nilai mutlak overlap riil
    # min(|gap_forward|, |gap_backward|) persis seperti DUAL_GAP_MENIT di layer2_dual.
    # =========================================================================
    gap_forward = (merged["START_TS_LOAD"] - merged["END_TS_DISC"]).dt.total_seconds() / 60.0
    gap_backward = (merged["START_TS_DISC"] - merged["END_TS_LOAD"]).dt.total_seconds() / 60.0
    overlap_gap = np.minimum(gap_forward.abs(), gap_backward.abs())

    merged["URUTAN"] = np.where(disc_first, "DISC ➔ LOAD", "LOAD ➔ DISC")
    raw_gap = np.where(disc_first, gap_forward, gap_backward)
    if "DUAL_GAP_MENIT_DISC" in merged.columns and merged["DUAL_GAP_MENIT_DISC"].notna().any():
        fallback_overlap = merged["DUAL_GAP_MENIT_DISC"].fillna(overlap_gap)
    else:
        fallback_overlap = overlap_gap
    merged["GAP_MENIT"] = np.where(raw_gap >= 0.0, raw_gap, fallback_overlap).round(1)

    merged["WAKTU_DISC"] = (
        merged["START_TS_DISC"].dt.strftime("%d/%m/%y %H:%M:%S") + " - " + merged["END_TS_DISC"].dt.strftime("%H:%M:%S")
    )
    merged["WAKTU_LOAD"] = (
        merged["START_TS_LOAD"].dt.strftime("%d/%m/%y %H:%M:%S") + " - " + merged["END_TS_LOAD"].dt.strftime("%H:%M:%S")
    )

    # Format ringkasan siklus urutannya disesuaikan dengan kolom urutan:
    # Jika DISC ➔ LOAD: Truk | DISC (Kapal, Crane) | ➔ Gap durasi ➔ | LOAD (Kapal, Crane)
    # Jika LOAD ➔ DISC: Truk | LOAD (Kapal, Crane) | ➔ Gap durasi ➔ | DISC (Kapal, Crane)
    ringkasan_disc_first = (
        merged["TRUK_ID"]
        + " | DISC ("
        + merged["VES_ID_DISC"]
        + ", "
        + merged["CRANE_ID_DISC"]
        + ") | ➔ "
        + merged["GAP_MENIT"].apply(format_duration)
        + " ➔ | LOAD ("
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
        + merged["GAP_MENIT"].apply(format_duration)
        + " ➔ | DISC ("
        + merged["VES_ID_DISC"]
        + ", "
        + merged["CRANE_ID_DISC"]
        + ")"
    )

    merged["RINGKASAN_PASANGAN"] = np.where(disc_first, ringkasan_disc_first, ringkasan_load_first)

    # Identifikasi pasangan transisi cepat/simultan
    is_fast_s = pd.Series(False, index=merged.index)
    if "DUAL_IS_FAST_DISC" in merged.columns and merged["DUAL_IS_FAST_DISC"].notna().any():
        is_fast_s = merged["DUAL_IS_FAST_DISC"].fillna(False).astype(bool)
    elif "DUAL_IS_FAST_LOAD" in merged.columns and merged["DUAL_IS_FAST_LOAD"].notna().any():
        is_fast_s = merged["DUAL_IS_FAST_LOAD"].fillna(False).astype(bool)
    else:
        is_fast_s = merged["GAP_MENIT"] <= 2.0

    merged = merged.sort_values(by=["START_TS_DISC", "TRUK_ID"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": merged["TRUK_ID"],
            "Format Rincian": merged["RINGKASAN_PASANGAN"],
            "Urutan": merged["URUTAN"],
            "Crane DISC": merged["CRANE_ID_DISC"],
            "Mulai DISC": merged["START_TS_DISC"],
            "Selesai DISC": merged["END_TS_DISC"],
            "Crane LOAD": merged["CRANE_ID_LOAD"],
            "Mulai LOAD": merged["START_TS_LOAD"],
            "Selesai LOAD": merged["END_TS_LOAD"],
            "Gap (Menit)": merged["GAP_MENIT"],
            "Anomali": np.where(merged["GAP_MENIT"] < 10.0, "Anomali", "Normal"),
            "IS_FAST": is_fast_s.loc[merged.index].values if hasattr(is_fast_s, 'loc') else is_fast_s,
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
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
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
    ev_non["DURASI_MENIT"] = (ev_non["END_TS"] - ev_non["START_TS"]).dt.total_seconds() / 60.0
    ev_non["DURASI_MENIT"] = np.maximum(0.0, ev_non["DURASI_MENIT"])

    ev_non["WAKTU_MULAI"] = ev_non["START_TS"]
    ev_non["WAKTU_SELESAI"] = ev_non["END_TS"]

    ev_non["RINGKASAN_EVENT"] = (
        ev_non["TRUK_ID"]
        + " | "
        + ev_non["ACTIVITY"]
        + " ("
        + ev_non["VES_ID"]
        + ", "
        + ev_non["CRANE_ID"]
        + ") | Durasi: "
        + ev_non["DURASI_MENIT"].apply(format_duration)
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
            "Status": "Non Dual (Single Cycle)",
        }
    )
    return res


@st.dialog("Rincian Aktivitas Dual-Cycle", width="large")
def _show_dual_cycle_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    # Proteksi modal: hanya bisa ditutup melalui tombol 'X' di pojok kanan atas
    inject_modal_backdrop_protection()

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
    ambang_dual = float(summary.get("ambang_dual", 30.0)) if summary else 30.0

    # Mini KPI Summary Row dengan Kartu Glassmorphism & Icon Help (?)
    mk1, mk2, mk3, mk4 = st.columns(4)
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
            value=format_duration(avg_gap),
            variant="blue",
            tooltip="Rata-rata selisih waktu tunggu antar aktivitas (selisih waktu selesai aktivitas pertama ke waktu mulai aktivitas kedua).",
        )
    with mk4:
        render_kpi_card(
            label="Parameter Dual Batas",
            value=f"≤ {ambang_dual:.0f} mnt",
            variant="blue",
            tooltip=f"Parameter batas toleransi jeda waktu antar aktivitas untuk diklasifikasikan sebagai Dual Cycle ({ambang_dual:.0f} menit).",
            align_tooltip_right=True,
        )

    # Format durasi pada dataframe untuk tampilan tabel
    df_table = df_data.drop(columns=["IS_FAST", "Truk"], errors="ignore").copy()
    if "Gap (Menit)" in df_table.columns:
        max_m = float(df_table["Gap (Menit)"].max() or 0.0)
        df_table["Gap"] = df_table["Gap (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_table = df_table.drop(columns=["Gap (Menit)"])

    cols_order = [
        "Format Rincian",
        "Urutan",
        "Crane DISC",
        "Mulai DISC",
        "Selesai DISC",
        "Crane LOAD",
        "Mulai LOAD",
        "Selesai LOAD",
        "Gap",
        "Anomali",
    ]
    df_table = df_table[[c for c in cols_order if c in df_table.columns]]

    # Optimasi Rendering Tabel:
    # Pandas Styler internal Streamlit memproses tiap sel satu per satu via Python loop.
    # Untuk dataset sangat besar (> 10.000 baris / > 100.000 sel), Styler menyebabkan browser
    # dan server Streamlit freeze / loading sangat lama (puluhan detik).
    # Oleh karena itu:
    # 1. Jika data <= 5.000 baris: gunakan Pandas Styler penuh (background merah halus di seluruh baris).
    # 2. Jika data > 5.000 baris: gunakan rendering Apache Arrow murni (0.05 detik) dengan badge status
    #    berwarna '🔴 Anomali' / 'Normal' pada kolom Anomali agar instan dan responsif.
    use_styler = len(df_table) <= 5000

    if use_styler:
        def _highlight_anomali_rows(data: pd.DataFrame) -> pd.DataFrame:
            style_df = pd.DataFrame("", index=data.index, columns=data.columns)
            if "Anomali" in data.columns:
                is_anom = data["Anomali"].astype(str).str.strip().str.lower() == "anomali"
                style_df.loc[is_anom, :] = "background-color: rgba(239, 68, 68, 0.22); color: #fca5a5;"
            return style_df

        render_df = df_table.style.apply(_highlight_anomali_rows, axis=None)
    else:
        render_df = df_table.copy()
        if "Anomali" in render_df.columns:
            render_df["Anomali"] = render_df["Anomali"].apply(
                lambda v: "🔴 Anomali" if str(v).strip().lower() == "anomali" else "Normal"
            )

    # Dataframe Interaktif dengan Column Config Lengkap
    st.dataframe(
        render_df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Siklus", width="large"),
            "Urutan": st.column_config.TextColumn("Urutan", width="small"),
            "Crane DISC": st.column_config.TextColumn("Crane DISC", width="small"),
            "Mulai DISC": st.column_config.DatetimeColumn("Mulai DISC", format="DD/MM/YY HH:mm:ss", width="small"),
            "Selesai DISC": st.column_config.DatetimeColumn("Selesai DISC", format="DD/MM/YY HH:mm:ss", width="small"),
            "Crane LOAD": st.column_config.TextColumn("Crane LOAD", width="small"),
            "Mulai LOAD": st.column_config.DatetimeColumn("Mulai LOAD", format="DD/MM/YY HH:mm:ss", width="small"),
            "Selesai LOAD": st.column_config.DatetimeColumn("Selesai LOAD", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
            "Anomali": st.column_config.TextColumn("Anomali", width="small"),
        },
    )

    render_html(
        """
        <div style="display: flex; justify-content: flex-end; align-items: center; margin-top: 8px;">
            <div style="display: inline-flex; align-items: center; gap: 7px; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.32); padding: 4px 12px; border-radius: 6px;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #ef4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);"></span>
                <span style="font-size: 0.8rem; color: #fca5a5; font-weight: 500; font-family: 'Plus Jakarta Sans', sans-serif;">
                    Baris Merah: Anomali (Gap &lt; 10m 00s)
                </span>
            </div>
        </div>
        """
    )


@st.dialog("Rincian Aktivitas Non-Dual", width="large")
def _show_non_dual_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    # Proteksi modal: hanya bisa ditutup melalui tombol 'X' di pojok kanan atas
    inject_modal_backdrop_protection()

    df_data = prepare_non_dual_table(events, out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data Non Dual yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_non", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row dengan Kartu Glassmorphism & Icon Help (?)
    total_events = len(df_data)
    total_trucks = df_data["Truk"].nunique()
    total_kapal = 0
    if "Kapal" in df_data.columns:
        v_set = set()
        for v in df_data["Kapal"].dropna().astype(str):
            for part in v.split(","):
                p = part.strip()
                if p and p != "-":
                    v_set.add(p)
        total_kapal = len(v_set)

    avg_dur = df_data["Durasi (Menit)"].mean()
    ambang_dual = float(summary.get("ambang_dual", 30.0)) if summary else 30.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Total Event Non Dual",
            value=f"{format_number(total_events)} evt",
            variant="blue",
            tooltip="Total jumlah aktivitas tunggal (Single Cycle) yang tidak berpasangan sebagai Dual Cycle.",
        )
    with mk2:
        render_kpi_card(
            label="Truk Terlibat",
            value=f"{format_number(total_trucks)} Truk",
            variant="blue",
            tooltip="Jumlah armada truk (CAR_CHE_ID) unik yang tercatat melakukan aktivitas Non-Dual.",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Kapal",
            value=f"{format_number(total_kapal)} Kapal",
            variant="blue",
            tooltip="Total jumlah kapal (VES_ID) unik yang terlayani dalam aktivitas Non-Dual.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Durasi",
            value=format_duration(avg_dur),
            variant="blue",
            tooltip=f"Rata-rata durasi pengerjaan per event Non-Dual (Waktu Selesai dikurangi Waktu Mulai). Batas toleransi Dual Cycle: > {ambang_dual:.0f} menit.",
            align_tooltip_right=True,
        )

    display_df = df_data.drop(columns=["Status", "Jenis", "Truk"], errors="ignore").copy()
    if "Durasi (Menit)" in display_df.columns:
        max_m = float(display_df["Durasi (Menit)"].max() or 0.0)
        display_df["Durasi"] = display_df["Durasi (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        display_df = display_df.drop(columns=["Durasi (Menit)"])

    display_df = display_df.reset_index(drop=True)

    # Dataframe Interaktif
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Aktivitas", width="large"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "Waktu Mulai": st.column_config.DatetimeColumn("Waktu Mulai", format="DD/MM/YY HH:mm:ss", width="small"),
            "Waktu Selesai": st.column_config.DatetimeColumn("Waktu Selesai", format="DD/MM/YY HH:mm:ss", width="small"),
            "Durasi": st.column_config.TextColumn("Durasi", width="small"),
        },
    )




def prepare_fast_transition_dual_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mengambil pasangan Dual Cycle yang melakukan transisi cepat/simultan
    (pergantian langsung muatan di lapangan atau dermaga dengan jeda waktu sangat singkat).
    """
    df_dual = prepare_dual_cycle_table(events, out_df)
    if len(df_dual) == 0:
        return pd.DataFrame()
    if "IS_FAST" in df_dual.columns and df_dual["IS_FAST"].any():
        return df_dual[df_dual["IS_FAST"] == True].reset_index(drop=True)
    return df_dual[df_dual["Gap (Menit)"] <= 2.0].reset_index(drop=True)


# Alias untuk kompatibilitas ke belakang
prepare_issue_gap_zero_table = prepare_fast_transition_dual_table


def prepare_potential_dual_table(
    events: pd.DataFrame, out_df: pd.DataFrame, ambang_dual: float = 30.0, max_gap: float = 180.0
) -> pd.DataFrame:
    """
    Menyusun tabel ritase potensi Dual Cycle yang diambil dari data aktivitas Non-Dual.
    Kriteria: Truk yang sama melakukan aktivitas bergantian (DISC ➔ LOAD atau LOAD ➔ DISC)
    secara berurutan dalam rentang waktu toleransi potensi (ambang_dual < gap <= max_gap).
    Aktivitas dengan gap melebihi batas toleransi max_gap (mis. jeda beda hari / shift terpisah) diabaikan.
    Setiap event Non-Dual hanya dipasangkan satu kali (greedy matching berdasarkan gap terkecil).
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()

    # Batas atas evaluasi potensi diambil langsung dari max_gap (slider Langkah 2)
    effective_max_gap = float(max_gap) if max_gap is not None else max(float(ambang_dual) + 60.0, 180.0)

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

    candidate_pairs = []
    for _, pos in truck_positions.items():
        pos_sorted = sorted(pos, key=lambda p: start[p])
        m = len(pos_sorted)
        for a in range(m - 1):
            i = pos_sorted[a]
            k = pos_sorted[a + 1]
            # Murni mengambil pasangan dari aktivitas Non-Dual dengan aktivitas bergantian
            if activity[i] != activity[k] and status[i] == "Non Dual" and status[k] == "Non Dual":
                # Waktu mulai event kedua dikurangi waktu selesai event pertama
                gap = (start[k] - end[i]) / np.timedelta64(1, "m")
                gap_r = round(gap, 1)
                if gap_r > ambang_dual and gap_r <= effective_max_gap:
                    candidate_pairs.append((i, k, gap_r))

    if not candidate_pairs:
        return pd.DataFrame()

    # Urutkan kandidat pasangan dari gap terkecil (potensi paling prioritas untuk dioptimasi)
    candidate_pairs.sort(key=lambda x: (x[2], x[0], x[1]))
    assigned = set()
    potential_list = []

    for i, k, gap_r in candidate_pairs:
        if i not in assigned and k not in assigned:
            assigned.add(i)
            assigned.add(k)
            truk_id = str(ev.loc[i, "CAR_CHE_ID"]).replace(".0", "")

            act1 = activity[i]
            act2 = activity[k]
            eid1 = ev.loc[i, "EVENT_ID"] if "EVENT_ID" in ev.columns else ev.loc[i, "GROUP_ID"]
            eid2 = ev.loc[k, "EVENT_ID"] if "EVENT_ID" in ev.columns else ev.loc[k, "GROUP_ID"]
            ves1 = ves_map.get(eid1, "-")
            ves2 = ves_map.get(eid2, "-")
            cr1 = str(ev.loc[i, "CRANE_ID"]) if "CRANE_ID" in ev.columns and pd.notna(ev.loc[i, "CRANE_ID"]) else "-"
            cr2 = str(ev.loc[k, "CRANE_ID"]) if "CRANE_ID" in ev.columns and pd.notna(ev.loc[k, "CRANE_ID"]) else "-"
            gap_str = format_duration(gap_r)
            ringkasan = f"{truk_id} | {act1} ({ves1}, {cr1}) ➔ {gap_str} ➔ {act2} ({ves2}, {cr2})"

            if act1 == "DISC":
                crane_disc = cr1
                t_mulai_disc = pd.to_datetime(ev.loc[i, "START_TS"])
                t_selesai_disc = pd.to_datetime(ev.loc[i, "END_TS"])
                crane_load = cr2
                t_mulai_load = pd.to_datetime(ev.loc[k, "START_TS"])
                t_selesai_load = pd.to_datetime(ev.loc[k, "END_TS"])
            else:
                crane_load = cr1
                t_mulai_load = pd.to_datetime(ev.loc[i, "START_TS"])
                t_selesai_load = pd.to_datetime(ev.loc[i, "END_TS"])
                crane_disc = cr2
                t_mulai_disc = pd.to_datetime(ev.loc[k, "START_TS"])
                t_selesai_disc = pd.to_datetime(ev.loc[k, "END_TS"])

            potential_list.append(
                {
                    "Truk": truk_id,
                    "Format Rincian": ringkasan,
                    "Urutan": f"{act1} ➔ {act2}",
                    "Crane DISC": crane_disc,
                    "Mulai DISC": t_mulai_disc,
                    "Selesai DISC": t_selesai_disc,
                    "Crane LOAD": crane_load,
                    "Mulai LOAD": t_mulai_load,
                    "Selesai LOAD": t_selesai_load,
                    "Gap (Menit)": gap_r,
                    "Kelebihan Ambang": round(gap_r - ambang_dual, 1),
                }
            )

    if not potential_list:
        return pd.DataFrame()

    df_res = pd.DataFrame(potential_list)
    return df_res.sort_values(by=["Gap (Menit)", "Truk"]).reset_index(drop=True)


@st.dialog("Rincian Potensi Dual Cycle", width="large")
def _show_issue_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    # Proteksi modal: hanya bisa ditutup melalui tombol 'X' di pojok kanan atas
    inject_modal_backdrop_protection()

    ambang_dual = float(summary.get("ambang_dual", 30.0)) if summary else 30.0
    max_gap_dual = float(
        st.session_state.get(
            "slider_sim_max_gap_dual",
            st.session_state.get(
                "slider_max_gap_potensi_dual",
                summary.get("max_gap_dual", 180.0) if summary else 180.0,
            ),
        )
    )

    df_potensi = prepare_potential_dual_table(events, out_df, ambang_dual=ambang_dual, max_gap=max_gap_dual)

    if len(df_potensi) == 0:
        st.success(f"Tidak ada ritase dengan aktivitas bergantian dalam batas toleransi ({ambang_dual:.0f} mnt < gap ≤ {max_gap_dual:.0f} mnt). Seluruh ritase sudah terkualifikasi sebagai Dual Cycle aktif!")
        if st.button("Tutup", key="btn_close_empty_pot_dual", type="secondary"):
            st.rerun()
        return

    df_display = df_potensi.copy()

    # Hitung Metrik KPI Sesuai Parameter Dual Cycle yang Aktif
    total_potensi = len(df_display)
    truk_potensi = set(df_display["Truk"].tolist()) if total_potensi > 0 else set()
    truk_terdampak = len(truk_potensi)
    avg_gap_potensi = df_display["Gap (Menit)"].mean() if total_potensi > 0 else 0.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Potensi Dual Cycle",
            value=f"{format_number(total_potensi)} Ritase",
            variant="blue",
            tooltip=f"Aktivitas ritase bergantian (DISC/LOAD) dengan jeda waktu antara {ambang_dual:.0f} mnt s/d batas toleransi {max_gap_dual:.0f} mnt.",
        )
    with mk2:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(truk_terdampak)} Truk",
            variant="blue",
            tooltip="Total armada truk unik yang memiliki aktivitas bergantian dalam rentang toleransi potensi.",
        )
    with mk3:
        render_kpi_card(
            label="Rata-rata Gap",
            value=format_duration(avg_gap_potensi),
            variant="blue",
            tooltip=f"Rata-rata jeda waktu tunggu truk pada ritase potensi ({ambang_dual:.0f} mnt < gap ≤ {max_gap_dual:.0f} mnt).",
        )
    with mk4:
        render_kpi_card(
            label="Maksimal Toleransi",
            value=f"≤ {max_gap_dual:.0f} mnt",
            variant="blue",
            tooltip=f"Batas maksimal toleransi jeda waktu untuk evaluasi potensi: {ambang_dual:.0f} mnt < Gap ≤ {max_gap_dual:.0f} mnt.",
            align_tooltip_right=True,
        )

    render_html('<div style="height:8px;"></div>')

    df_pot_table = df_display.drop(columns=["Truk"], errors="ignore").copy()
    if "Gap (Menit)" in df_pot_table.columns:
        max_m = float(df_pot_table["Gap (Menit)"].max() or 0.0)
        df_pot_table["Gap"] = df_pot_table["Gap (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_pot_table = df_pot_table.drop(columns=["Gap (Menit)"])
    if "Kelebihan Ambang" in df_pot_table.columns:
        max_k = float(df_pot_table["Kelebihan Ambang"].max() or 0.0)
        df_pot_table["Kelebihan Ambang"] = df_pot_table["Kelebihan Ambang"].apply(lambda v: f"+{format_duration_sortable(v, max_k)}")

    cols_order = [
        "Format Rincian",
        "Urutan",
        "Crane DISC",
        "Mulai DISC",
        "Selesai DISC",
        "Crane LOAD",
        "Mulai LOAD",
        "Selesai LOAD",
        "Gap",
        "Kelebihan Ambang",
    ]
    df_pot_table = df_pot_table[[c for c in cols_order if c in df_pot_table.columns]]

    # Dataframe Interaktif
    st.dataframe(
        df_pot_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Potensi Siklus", width="large"),
            "Urutan": st.column_config.TextColumn("Urutan", width="small"),
            "Crane DISC": st.column_config.TextColumn("Crane DISC", width="small"),
            "Mulai DISC": st.column_config.DatetimeColumn("Mulai DISC", format="DD/MM/YY HH:mm:ss", width="small"),
            "Selesai DISC": st.column_config.DatetimeColumn("Selesai DISC", format="DD/MM/YY HH:mm:ss", width="small"),
            "Crane LOAD": st.column_config.TextColumn("Crane LOAD", width="small"),
            "Mulai LOAD": st.column_config.DatetimeColumn("Mulai LOAD", format="DD/MM/YY HH:mm:ss", width="small"),
            "Selesai LOAD": st.column_config.DatetimeColumn("Selesai LOAD", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
            "Kelebihan Ambang": st.column_config.TextColumn("Kelebihan Ambang", width="small"),
        },
    )


_show_potential_dual_dialog = _show_issue_dialog


def show_activity_detail_dialog(status: str, events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian aktivitas operasional
    ('Dual Cycle', 'Non Dual', atau 'Potensi Dual Cycle').
    Menyediakan tabel interaktif, format ringkasan truk, filter pencarian,
    serta tombol unduh CSV.
    """
    if status == "Dual Cycle":
        _show_dual_cycle_dialog(events, out_df, summary)
    elif status in ("Issue", "Potensi", "Potensi Dual Cycle"):
        _show_potential_dual_dialog(events, out_df, summary)
    else:
        _show_non_dual_dialog(events, out_df, summary)


def prepare_combo_table(out_df: pd.DataFrame, events: pd.DataFrame = None, ambang_combo: float = 3.0) -> pd.DataFrame:
    """
    Menyusun tabel rincian operasional Combo (basis kontainer 20ft).
    Setiap baris mewakili 1 pasangan Combo (2 kontainer 20ft dalam 1 ritase).
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
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

    # =========================================================================
    # PERINGATAN / ATURAN TETAP (DO NOT MODIFY):
    # Logic perhitungan GAP COMBO bertingkat (if-else fallback):
    # 1. Cek Gap Dermaga (|DISC_LOAD_TS2 - DISC_LOAD_TS1| <= ambang_combo) -> pakai Gap Dermaga
    # 2. Jika Gap Dermaga > ambang_combo, cek Gap Lapangan (|STACK_UNSTACK_TS2 - STACK_UNSTACK_TS1|) -> pakai Gap Lapangan
    # =========================================================================
    gap_dermaga = (r2["TS_G"] - r1["TS_G"]).dt.total_seconds().abs() / 60.0
    gap_lapangan = (r2["TS_H"] - r1["TS_H"]).dt.total_seconds().abs() / 60.0
    gap = pd.Series(np.where(gap_dermaga <= float(ambang_combo), gap_dermaga, gap_lapangan), index=r1.index)

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
        + gap.apply(format_duration)
    )

    res = pd.DataFrame(
        {
            "Truk": truk_id,
            "Format Rincian": ringkasan,
            "Event ID": r1["EVENT_ID"],
            "Aktivitas": act,
            "Kapal": ves_id,
            "Crane": crane_id,
            "DISC_LOAD_TS1": r1["TS_G"],
            "DISC_LOAD_TS2": r2["TS_G"],
            "STACK_UNSTACK_TS1": r1["TS_H"],
            "STACK_UNSTACK_TS2": r2["TS_H"],
            "Gap Combo (Menit)": gap,
        }
    )
    return res.sort_values(by=["Event ID", "Truk"]).reset_index(drop=True)


def prepare_single_table(out_df: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """
    Menyusun tabel rincian operasional Single (basis kontainer 20ft).
    Setiap baris mewakili 1 kontainer 20ft yang diangkut tunggal (1 kontainer per ritase).
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
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

    durasi_mnt = (df_s["TS_H"] - df_s["TS_G"]).dt.total_seconds().abs() / 60.0

    ringkasan = (
        truk_id
        + " | "
        + act
        + " ("
        + ves_id
        + ", "
        + crane_id
        + ")"
    )

    res = pd.DataFrame(
        {
            "Truk": truk_id,
            "Format Rincian": ringkasan,
            "Event ID": df_s["EVENT_ID"],
            "Aktivitas": act,
            "Kapal": ves_id,
            "Crane": crane_id,
            "DISC_LOAD_TS": df_s["TS_G"],
            "STACK_UNSTACK_TS": df_s["TS_H"],
            "Durasi (Menit)": durasi_mnt,
        }
    )
    return res.sort_values(by=["Event ID", "Truk"]).reset_index(drop=True)


def prepare_combo_gap_zero_table(out_df: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """
    Menyusun tabel anomali Combo dengan gap 0.0 menit.
    Dipertahankan untuk kompatibilitas fungsi.
    """
    df_combo = prepare_combo_table(out_df, events)
    if len(df_combo) == 0:
        return pd.DataFrame()
    return df_combo[df_combo["Gap Combo (Menit)"] <= 0.0].reset_index(drop=True)


def prepare_potential_combo_table(
    out_df: pd.DataFrame,
    events: pd.DataFrame = None,
    ambang_combo: float = 3.0,
    max_gap: float = 30.0,
) -> pd.DataFrame:
    """
    Menyusun tabel ritase potensi Combo yang diambil murni dari data Single 20ft:
    Dua kontainer 20ft Single pada truk yang sama dan aktivitas yang sama (DISC-DISC atau LOAD-LOAD),
    namun jeda waktu tunggunya melebihi ambang_combo dan <= max_gap menit.
    Evaluasi jeda waktu dilakukan pada Dermaga (TS_G) maupun Lapangan (TS_H) sesuai Layer 1 Combo.
    Setiap kontainer Single hanya dipasangkan satu kali (greedy matching berdasarkan gap terkecil).
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame()

    effective_max_gap = float(max_gap) if max_gap is not None else max(float(ambang_combo) + 15.0, 30.0)

    # Murni memfilter kontainer 20ft berstatus Single
    df20 = out_df[(out_df["CTR_SIZE"] == 20) & (out_df["CONTAINER_STATUS"] == "Single")].copy()
    if len(df20) < 2:
        return pd.DataFrame()

    df20["TS_G"] = pd.to_datetime(df20["TS_G"])
    df20["TS_H"] = pd.to_datetime(df20["TS_H"])

    candidate_pairs = []
    for (truck, act), group in df20.groupby(["CAR_CHE_ID", "ACTIVITY"]):
        g_sorted = group.sort_values(by=["TS_G", "TS_H"]).reset_index(drop=True)
        m = len(g_sorted)
        for i in range(m - 1):
            r1 = g_sorted.iloc[i]
            r2 = g_sorted.iloc[i + 1]

            gaps_valid = []
            if pd.notna(r1["TS_G"]) and pd.notna(r2["TS_G"]):
                gaps_valid.append(abs((r2["TS_G"] - r1["TS_G"]).total_seconds()) / 60.0)
            if pd.notna(r1["TS_H"]) and pd.notna(r2["TS_H"]):
                gaps_valid.append(abs((r2["TS_H"] - r1["TS_H"]).total_seconds()) / 60.0)

            if not gaps_valid:
                continue

            gap_min = min(gaps_valid)
            gap_r = round(gap_min, 1)

            if gap_r > ambang_combo and gap_r <= effective_max_gap:
                candidate_pairs.append((i, i + 1, gap_r, r1, r2, truck, act))

    if not candidate_pairs:
        return pd.DataFrame()

    # Urutkan dari gap terkecil (potensi paling prioritas untuk dioptimasi)
    candidate_pairs.sort(key=lambda x: (x[2], x[0], x[1]))
    assigned = set()
    potentials = []

    for idx1, idx2, gap_r, r1, r2, truck, act in candidate_pairs:
        eid1 = r1["EVENT_ID"] if "EVENT_ID" in r1 else idx1
        eid2 = r2["EVENT_ID"] if "EVENT_ID" in r2 else idx2

        if eid1 not in assigned and eid2 not in assigned:
            assigned.add(eid1)
            assigned.add(eid2)

            truk_id = str(truck).replace(".0", "")
            ves1 = str(r1.get("VES_ID", "-"))
            ves2 = str(r2.get("VES_ID", "-"))
            cr1 = str(r1.get("CRANE_ID", "-"))
            cr2 = str(r2.get("CRANE_ID", "-"))
            gap_str = format_duration(gap_r)
            ringkasan = f"{truk_id} | {act} ({ves1}, {cr1}) ➔ {gap_str} ➔ {act} ({ves2}, {cr2})"

            potentials.append(
                {
                    "Truk": truk_id,
                    "Format Rincian": ringkasan,
                    "Aktivitas": act,
                    "Kapal 1": ves1,
                    "Crane 1": cr1,
                    "Kapal 2": ves2,
                    "Crane 2": cr2,
                    "DISC_LOAD_TS1": pd.to_datetime(r1.get("TS_G")),
                    "DISC_LOAD_TS2": pd.to_datetime(r2.get("TS_G")),
                    "STACK_UNSTACK_TS1": pd.to_datetime(r1.get("TS_H")),
                    "STACK_UNSTACK_TS2": pd.to_datetime(r2.get("TS_H")),
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
    inject_modal_backdrop_protection()

    ambang_combo = float(summary.get("ambang_combo", 3.0)) if summary else 3.0
    df_data = prepare_combo_table(out_df, events, ambang_combo=ambang_combo)
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
            value=f"{format_number(total_ritase)} Rit",
            variant="blue",
            tooltip="Jumlah pergerakan 2 kontainer dalam 1 truk yang sama.",
        )
    with mk2:
        render_kpi_card(
            label="Total Kontainer",
            value=f"{format_number(total_kontainer)} Box",
            variant="blue",
            tooltip="Jumlah kontainer 20ft yang terangkut secara bersamaan.",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(total_trucks)} Truk",
            variant="blue",
            tooltip="Jumlah truk yang membawa 2 kontainer.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Gap Combo",
            value=format_duration(avg_gap),
            variant="blue",
            tooltip=f"Rata-rata selisih waktu aktivitas 2 kontainer (Batas ambang combo aktif: ≤ {ambang_combo:.0f} menit).",
            align_tooltip_right=True,
        )

    df_combo_table = df_data.drop(columns=["Truk"], errors="ignore").copy()
    if "Gap Combo (Menit)" in df_combo_table.columns:
        max_m = float(df_combo_table["Gap Combo (Menit)"].max() or 0.0)
        df_combo_table["Gap"] = df_combo_table["Gap Combo (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_combo_table = df_combo_table.drop(columns=["Gap Combo (Menit)"])

    st.dataframe(
        df_combo_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Combo", width="large"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "DISC_LOAD_TS1": st.column_config.DatetimeColumn("DISC_LOAD_TS1", format="DD/MM/YY HH:mm:ss", width="small"),
            "DISC_LOAD_TS2": st.column_config.DatetimeColumn("DISC_LOAD_TS2", format="DD/MM/YY HH:mm:ss", width="small"),
            "STACK_UNSTACK_TS1": st.column_config.DatetimeColumn("STACK_UNSTACK_TS1", format="DD/MM/YY HH:mm:ss", width="small"),
            "STACK_UNSTACK_TS2": st.column_config.DatetimeColumn("STACK_UNSTACK_TS2", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
        },
    )


@st.dialog("Rincian Aktivitas Single (Kontainer 20ft)", width="large")
def _show_single_dialog(out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up rincian aktivitas Single (1x 20ft per ritase).
    """
    inject_modal_backdrop_protection()

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
    ambang_combo = float(summary.get("ambang_combo", 3.0)) if summary else 3.0

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
            variant="blue",
            tooltip="Jumlah kontainer 20ft yang diangkut tunggal (1 kontainer per ritase).",
        )
    with mk3:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(total_trucks)} Truk",
            variant="blue",
            tooltip="Jumlah truk yang membawa 1 kontainer.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Durasi Single",
            value=format_duration(avg_durasi),
            variant="blue",
            tooltip="Rata-rata durasi pergerakan aktivitas ritase kontainer Single.",
            align_tooltip_right=True,
        )

    df_single_table = df_data.drop(columns=["Truk"], errors="ignore").copy()
    if "Durasi (Menit)" in df_single_table.columns:
        max_m = float(df_single_table["Durasi (Menit)"].max() or 0.0)
        df_single_table["Durasi"] = df_single_table["Durasi (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_single_table = df_single_table.drop(columns=["Durasi (Menit)"])

    st.dataframe(
        df_single_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Single", width="large"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "DISC_LOAD_TS": st.column_config.DatetimeColumn("DISC_LOAD_TS", format="DD/MM/YY HH:mm:ss", width="small"),
            "STACK_UNSTACK_TS": st.column_config.DatetimeColumn("STACK_UNSTACK_TS", format="DD/MM/YY HH:mm:ss", width="small"),
            "Durasi": st.column_config.TextColumn("Durasi", width="small"),
        },
    )



@st.dialog("Rincian Potensi Combo (Kontainer 20ft)", width="large")
def _show_combo_issue_dialog(out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up rincian potensi Combo tertunda (jeda waktu melebihi ambang batas).
    """
    inject_modal_backdrop_protection()

    ambang_combo = float(summary.get("ambang_combo", 3.0)) if summary else 3.0
    max_gap_combo = float(
        st.session_state.get(
            "slider_sim_max_gap_combo",
            st.session_state.get(
                "slider_max_gap_potensi_combo",
                summary.get("max_gap_combo", 10.0) if summary else 10.0,
            ),
        )
    )

    df_potensi = prepare_potential_combo_table(out_df, events, ambang_combo=ambang_combo, max_gap=max_gap_combo)

    if len(df_potensi) == 0:
        st.success(f"Tidak ada kontainer 20ft dengan aktivitas sama dalam batas toleransi ({ambang_combo:.0f} mnt < gap ≤ {max_gap_combo:.0f} mnt). Seluruh kontainer sudah terkualifikasi Combo!")
        if st.button("Tutup", key="btn_close_empty_pot_combo", type="secondary"):
            st.rerun()
        return

    df_display = df_potensi.copy()

    total_potensi = len(df_display)
    truk_potensi = set(df_display["Truk"].tolist()) if total_potensi > 0 else set()
    truk_terdampak = len(truk_potensi)
    avg_gap_potensi = df_display["Gap (Menit)"].mean() if total_potensi > 0 else 0.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Potensi Combo",
            value=f"{format_number(total_potensi)} Pasang",
            variant="blue",
            tooltip=f"Data pasangan kontainer 20ft Single pada aktivitas sama dengan jeda waktu antara {ambang_combo:.0f} mnt s/d {max_gap_combo:.0f} mnt.",
        )
    with mk2:
        render_kpi_card(
            label="Jumlah Truk",
            value=f"{format_number(truk_terdampak)} Truk",
            variant="blue",
            tooltip="Total armada truk unik yang memiliki potensi Combo tertunda.",
        )
    with mk3:
        render_kpi_card(
            label="Rata-rata Gap Potensi",
            value=format_duration(avg_gap_potensi),
            variant="blue",
            tooltip=f"Rata-rata jeda waktu pasangan kontainer 20ft ({ambang_combo:.0f} mnt < gap ≤ {max_gap_combo:.0f} mnt).",
        )
    with mk4:
        render_kpi_card(
            label="Ambang Batas Combo",
            value=f"≤ {ambang_combo:.0f} mnt",
            variant="blue",
            tooltip=f"Target batas ambang resmi kualifikasi Combo aktif: ≤ {ambang_combo:.0f} menit. Tabel mengevaluasi kontainer Single yang jedanya melebihi ambang batas ini sebagai peluang efisiensi.",
            align_tooltip_right=True,
        )

    render_html('<div style="height:8px;"></div>')

    df_combo_pot_table = df_display.drop(columns=["Truk", "Kelebihan Ambang"], errors="ignore").copy()
    if "Gap (Menit)" in df_combo_pot_table.columns:
        max_m = float(df_combo_pot_table["Gap (Menit)"].max() or 0.0)
        df_combo_pot_table["Gap"] = df_combo_pot_table["Gap (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_combo_pot_table = df_combo_pot_table.drop(columns=["Gap (Menit)"])

    cols_order = [
        "Format Rincian",
        "Aktivitas",
        "DISC_LOAD_TS1",
        "DISC_LOAD_TS2",
        "STACK_UNSTACK_TS1",
        "STACK_UNSTACK_TS2",
        "Gap",
    ]
    df_combo_pot_table = df_combo_pot_table[[c for c in cols_order if c in df_combo_pot_table.columns]]

    st.dataframe(
        df_combo_pot_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Potensi Combo", width="large"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "DISC_LOAD_TS1": st.column_config.DatetimeColumn("DISC_LOAD_TS1", format="DD/MM/YY HH:mm:ss", width="small"),
            "DISC_LOAD_TS2": st.column_config.DatetimeColumn("DISC_LOAD_TS2", format="DD/MM/YY HH:mm:ss", width="small"),
            "STACK_UNSTACK_TS1": st.column_config.DatetimeColumn("STACK_UNSTACK_TS1", format="DD/MM/YY HH:mm:ss", width="small"),
            "STACK_UNSTACK_TS2": st.column_config.DatetimeColumn("STACK_UNSTACK_TS2", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
        },
    )


_show_potential_combo_dialog = _show_combo_issue_dialog


def show_combo_detail_dialog(status: str, out_df: pd.DataFrame, events: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Combo
    ('Combo', 'Single', atau 'Potensi Combo').
    """
    if status == "Combo":
        _show_combo_dialog(out_df, events, summary)
    elif status == "Single":
        _show_single_dialog(out_df, events, summary)
    elif status in ("Issue", "Potensi", "Potensi Combo"):
        _show_combo_issue_dialog(out_df, events, summary)


def prepare_twinlift_table(out_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Menyusun tabel rincian operasional Twinlift dan Bukan Twinlift (basis kontainer 20ft)
    dalam format 1 baris horizontal menyamping (Waktu Dermaga 1 & Waktu Dermaga 2)
    agar selisih Gap dapat diverifikasi langsung secara horizontal.
    [LOCKED LOGIC - DO NOT MODIFY WITHOUT EXPLICIT USER CONFIRMATION]
    
    Mengembalikan (df_twin_table, df_non_twin_table).
    """
    if out_df is None or len(out_df) == 0:
        return pd.DataFrame(), pd.DataFrame()

    # Filter basis kontainer 20ft (satu-satunya ukuran yang eligible Twinlift)
    df20 = out_df[out_df["CTR_SIZE"] == 20].copy()
    if len(df20) == 0:
        return pd.DataFrame(), pd.DataFrame()

    df20["TS_G"] = pd.to_datetime(df20["TS_G"])
    df20["TS_H"] = pd.to_datetime(df20["TS_H"])

    # -------------------------------------------------------------
    # 1. Tabel Twinlift (Murni pasangan 2x 20ft yang terkualifikasi Twinlift)
    # -------------------------------------------------------------
    df_twin_raw = df20[df20["TWINLIFT_STATUS"] == "Twinlift"].copy()
    if len(df_twin_raw) > 0:
        df_twin_sorted = df_twin_raw.sort_values(by=["EVENT_ID", "TS_G"]).reset_index(drop=True)
        r1 = df_twin_sorted.iloc[0::2].reset_index(drop=True)
        r2 = df_twin_sorted.iloc[1::2].reset_index(drop=True)

        truk_id = r1["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
        ves_id = r1["VES_ID"].fillna("-").astype(str)
        crane1_id = r1["CRANE_ID"].fillna("-").astype(str)
        crane2_id = r2["CRANE_ID"].fillna("-").astype(str)
        act = r1["ACTIVITY"].fillna("-").astype(str)
        ctr1 = r1.get("CTR_NO", pd.Series(["-"] * len(r1))).fillna("-").astype(str)
        ctr2 = r2.get("CTR_NO", pd.Series(["-"] * len(r2))).fillna("-").astype(str)
        gap_m = (r2["TS_G"] - r1["TS_G"]).dt.total_seconds().abs() / 60.0

        ringkasan_twin = truk_id + " | " + act + " (" + ves_id + ", " + crane1_id + ") | 2x 20ft"

        df_twin = pd.DataFrame(
            {
                "Truk": truk_id,
                "Format Rincian": ringkasan_twin,
                "Event ID": r1["EVENT_ID"],
                "Aktivitas": act,
                "Kapal": ves_id,
                "Crane 1": crane1_id,
                "No Container 1": ctr1,
                "Waktu Dermaga 1": r1["TS_G"],
                "Crane 2": crane2_id,
                "No Container 2": ctr2,
                "Waktu Dermaga 2": r2["TS_G"],
                "Gap Twinlift (Menit)": gap_m,
                "Status Twinlift": "Twinlift",
            }
        ).sort_values(by=["Waktu Dermaga 1", "Event ID"]).reset_index(drop=True)
    else:
        df_twin = pd.DataFrame()

    # -------------------------------------------------------------
    # 2. Tabel Bukan Twinlift (Pasangan Combo gagal Twinlift + Single 20ft)
    # -------------------------------------------------------------
    df_non_raw = df20[df20["TWINLIFT_STATUS"] != "Twinlift"].copy()
    if len(df_non_raw) > 0:
        records_non = []
        for eid, grp in df_non_raw.groupby("EVENT_ID", sort=False):
            grp_sorted = grp.sort_values(by="TS_G")
            row1 = grp_sorted.iloc[0]
            truk_non = str(row1["CAR_CHE_ID"]).replace(".0", "")
            ves_non = str(row1.get("VES_ID", "-"))
            cr1_non = str(row1.get("CRANE_ID", "-"))
            act_non = str(row1.get("ACTIVITY", "-"))
            ctr1_non = str(row1.get("CTR_NO", "-"))
            ts1 = row1["TS_G"]

            if len(grp_sorted) >= 2:
                row2 = grp_sorted.iloc[1]
                ts2 = row2["TS_G"]
                cr2_non = str(row2.get("CRANE_ID", "-"))
                ctr2_non = str(row2.get("CTR_NO", "-"))
                gap_val = abs((ts2 - ts1).total_seconds()) / 60.0
                crane_summary = cr1_non if cr1_non == cr2_non else f"{cr1_non}/{cr2_non}"
                ringk_non = f"{truk_non} | {act_non} ({ves_non}, {crane_summary}) | 2x 20ft"
                records_non.append(
                    {
                        "Truk": truk_non,
                        "Format Rincian": ringk_non,
                        "Event ID": eid,
                        "Aktivitas": act_non,
                        "Kapal": ves_non,
                        "Crane 1": cr1_non,
                        "No Container 1": ctr1_non,
                        "Waktu Dermaga 1": ts1,
                        "Crane 2": cr2_non,
                        "No Container 2": ctr2_non,
                        "Waktu Dermaga 2": ts2,
                        "Gap Bukan Twinlift (Menit)": gap_val,
                        "Status Twinlift": "Bukan Twinlift",
                        "Jumlah Kontainer": len(grp_sorted),
                    }
                )
            else:
                ringk_non = f"{truk_non} | {act_non} ({ves_non}, {cr1_non}) | 1x 20ft"
                records_non.append(
                    {
                        "Truk": truk_non,
                        "Format Rincian": ringk_non,
                        "Event ID": eid,
                        "Aktivitas": act_non,
                        "Kapal": ves_non,
                        "Crane 1": cr1_non,
                        "No Container 1": ctr1_non,
                        "Waktu Dermaga 1": ts1,
                        "Crane 2": "-",
                        "No Container 2": "-",
                        "Waktu Dermaga 2": pd.NaT,
                        "Gap Bukan Twinlift (Menit)": None,
                        "Status Twinlift": "Bukan Twinlift",
                        "Jumlah Kontainer": 1,
                    }
                )
        df_non = pd.DataFrame(records_non).sort_values(by=["Waktu Dermaga 1", "Event ID"]).reset_index(drop=True)
    else:
        df_non = pd.DataFrame()

    return df_twin, df_non


@st.dialog("Rincian Aktivitas Twinlift (Kontainer 20ft)", width="large")
def _show_twinlift_dialog(out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Twinlift
    saat tombol 'Rincian Twinlift' di bawah donut chart diklik.
    Format 1 baris menyamping per pasangan lift (Waktu Dermaga 1 & Waktu Dermaga 2).
    """
    inject_modal_backdrop_protection()
    df_twin, _ = prepare_twinlift_table(out_df)
    if len(df_twin) == 0:
        st.info("Tidak ada data kontainer 20ft Twinlift yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_twin", type="secondary"):
            st.rerun()
        return

    # Ambil metrik ringkasan dari summary atau hitung presisi dari dataset
    df20_all = out_df[out_df["CTR_SIZE"] == 20] if out_df is not None else pd.DataFrame()
    total_20ft_all = len(df20_all)
    total_pasangan = len(df_twin)
    total_twinlift = total_pasangan * 2
    pct_twinlift = (total_twinlift / total_20ft_all * 100.0) if total_20ft_all > 0 else 0.0

    truk_terlibat = df_twin["Truk"].nunique() if total_twinlift > 0 else 0
    crane_terlibat = df_twin["Crane 1"].nunique() if total_twinlift > 0 else 0
    avg_gap_twin = df_twin["Gap Twinlift (Menit)"].mean() if total_twinlift > 0 else 0.0

    ambang_val = float(summary.get("ambang_twinlift", 1.0)) if summary else 1.0

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Total Twinlift",
            value=f"{format_number(total_twinlift)} Ctr",
            variant="blue",
            tooltip=f"Total kontainer 20ft yang diangkat dengan spreader Twinlift ({format_number(total_pasangan)} pasang lift).",
        )
    with mk2:
        render_kpi_card(
            label="% Twinlift (20ft)",
            value=format_percent(pct_twinlift, 1),
            variant="blue",
            tooltip=f"Rasio kontainer Twinlift terhadap seluruh kontainer 20ft ({format_number(total_twinlift)} dari {format_number(total_20ft_all)} Ctr 20ft).",
        )
    with mk3:
        render_kpi_card(
            label="Truk & Crane",
            value=f"{format_number(truk_terlibat)} Truk / {format_number(crane_terlibat)} QC",
            variant="blue",
            tooltip=f"Jumlah armada truk ({format_number(truk_terlibat)} Truk) dan Quay Crane ({format_number(crane_terlibat)} QC) unik yang terlibat.",
        )
    with mk4:
        render_kpi_card(
            label="Rata-rata Gap",
            value=format_duration(avg_gap_twin),
            variant="blue",
            tooltip=f"Rata-rata selisih waktu lifting 2 kontainer Twinlift pada QC (Batas ambang Twinlift: ≤ {format_decimal(ambang_val, 0)} menit).",
            align_tooltip_right=True,
        )

    cols_to_drop = ["Truk", "Status Twinlift"]
    df_twin_table = df_twin.drop(columns=cols_to_drop, errors="ignore").copy()
    if "Gap Twinlift (Menit)" in df_twin_table.columns:
        max_m = float(df_twin_table["Gap Twinlift (Menit)"].max() or 0.0)
        df_twin_table["Gap"] = df_twin_table["Gap Twinlift (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_twin_table = df_twin_table.drop(columns=["Gap Twinlift (Menit)"])

    st.dataframe(
        df_twin_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Operasional", width="large"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane 1": st.column_config.TextColumn("Crane 1", width="small"),
            "No Container 1": st.column_config.TextColumn("No Container 1", width="small"),
            "Waktu Dermaga 1": st.column_config.DatetimeColumn("Waktu Dermaga 1", format="DD/MM/YY HH:mm:ss", width="small"),
            "Crane 2": st.column_config.TextColumn("Crane 2", width="small"),
            "No Container 2": st.column_config.TextColumn("No Container 2", width="small"),
            "Waktu Dermaga 2": st.column_config.DatetimeColumn("Waktu Dermaga 2", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
        },
    )


@st.dialog("Rincian Aktivitas Bukan Twinlift (Kontainer 20ft)", width="large")
def _show_non_twinlift_dialog(out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Bukan Twinlift (Single Lift 20ft)
    saat tombol 'Rincian Bukan Twinlift' di bawah donut chart diklik.
    Format 1 baris menyamping per ritase/event (Waktu Dermaga 1 & Waktu Dermaga 2).
    """
    inject_modal_backdrop_protection()
    _, df_non = prepare_twinlift_table(out_df)
    if len(df_non) == 0:
        st.info("Tidak ada data kontainer 20ft Bukan Twinlift yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_nontwin", type="secondary"):
            st.rerun()
        return

    df20_all = out_df[out_df["CTR_SIZE"] == 20] if out_df is not None else pd.DataFrame()
    total_20ft_all = len(df20_all)
    df_non_raw = df20_all[df20_all["TWINLIFT_STATUS"] != "Twinlift"] if len(df20_all) > 0 else pd.DataFrame()
    total_non_twin = len(df_non_raw)
    pct_non_twin = (total_non_twin / total_20ft_all * 100.0) if total_20ft_all > 0 else 0.0

    truk_terlibat = df_non["Truk"].nunique() if len(df_non) > 0 else 0
    crane_ids = set(df_non["Crane 1"].dropna().unique()) | set(df_non["Crane 2"].dropna().unique())
    crane_ids.discard("-")
    crane_terlibat = len(crane_ids)
    disc_count = int((df_non_raw["ACTIVITY"] == "DISC").sum()) if len(df_non_raw) > 0 else 0
    load_count = int((df_non_raw["ACTIVITY"] == "LOAD").sum()) if len(df_non_raw) > 0 else 0

    ambang_tw = float(summary.get("ambang_twinlift", 1.0)) if summary else 1.0
    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        render_kpi_card(
            label="Total Bukan Twinlift",
            value=f"{format_number(total_non_twin)} Ctr",
            variant="blue",
            tooltip=f"Total kontainer 20ft yang diangkat secara Single Lift (Batas ambang Twinlift: > {format_decimal(ambang_tw, 0)} menit).",
        )
    with mk2:
        render_kpi_card(
            label="% Bukan Twinlift",
            value=format_percent(pct_non_twin, 1),
            variant="blue",
            tooltip=f"Rasio kontainer Bukan Twinlift terhadap seluruh kontainer 20ft ({format_number(total_non_twin)} dari {format_number(total_20ft_all)} Ctr 20ft).",
        )
    with mk3:
        render_kpi_card(
            label="Truk & Crane",
            value=f"{format_number(truk_terlibat)} Truk / {format_number(crane_terlibat)} QC",
            variant="blue",
            tooltip=f"Jumlah armada truk ({format_number(truk_terlibat)} Truk) dan Quay Crane ({format_number(crane_terlibat)} QC) unik yang terlibat.",
        )
    with mk4:
        render_kpi_card(
            label="Komposisi DISC / LOAD",
            value=f"{format_number(disc_count)} / {format_number(load_count)}",
            variant="blue",
            tooltip=f"Rincian jumlah kontainer Bongkar (DISC: {format_number(disc_count)} Ctr) dan Muat (LOAD: {format_number(load_count)} Ctr) yang berstatus Bukan Twinlift.",
            align_tooltip_right=True,
        )

    cols_to_drop = ["Truk", "Status Twinlift", "Jumlah Kontainer"]
    df_non_twin_table = df_non.drop(columns=cols_to_drop, errors="ignore").copy()
    if "Gap Bukan Twinlift (Menit)" in df_non_twin_table.columns:
        max_m = float(df_non_twin_table["Gap Bukan Twinlift (Menit)"].max() or 0.0)
        df_non_twin_table["Gap"] = df_non_twin_table["Gap Bukan Twinlift (Menit)"].apply(lambda v: format_duration_sortable(v, max_m))
        df_non_twin_table = df_non_twin_table.drop(columns=["Gap Bukan Twinlift (Menit)"])

    st.dataframe(
        df_non_twin_table,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Format Rincian": st.column_config.TextColumn("Ringkasan Operasional", width="large"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane 1": st.column_config.TextColumn("Crane 1", width="small"),
            "No Container 1": st.column_config.TextColumn("No Container 1", width="small"),
            "Waktu Dermaga 1": st.column_config.DatetimeColumn("Waktu Dermaga 1", format="DD/MM/YY HH:mm:ss", width="small"),
            "Crane 2": st.column_config.TextColumn("Crane 2", width="small"),
            "No Container 2": st.column_config.TextColumn("No Container 2", width="small"),
            "Waktu Dermaga 2": st.column_config.DatetimeColumn("Waktu Dermaga 2", format="DD/MM/YY HH:mm:ss", width="small"),
            "Gap": st.column_config.TextColumn("Gap", width="small"),
        },
    )



def show_twinlift_detail_dialog(status: str, out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian operasional Twinlift atau Bukan Twinlift
    saat tombol 'Rincian Twinlift' atau 'Rincian Bukan Twinlift' diklik di bawah chart donut.
    """
    if status == "Twinlift":
        _show_twinlift_dialog(out_df, summary)
    else:
        _show_non_twinlift_dialog(out_df, summary)


def _get_optimized_preview_uri(gif_file: Path) -> str:
    """
    Mengoptimalkan file animasi berukuran besar (> 3 MB) agar dapat di-render
    dengan sangat ringan di tooltip Streamlit tanpa membebani browser atau WebSocket.
    Menghasilkan animasi WebP berukuran kompak (~1.5 MB) yang tetap tajam dan mulus.
    """
    try:
        file_size = gif_file.stat().st_size
        # Jika file sudah cukup kecil (<= 3 MB), gunakan langsung tanpa kompresi
        if file_size <= 3 * 1024 * 1024:
            suffix = gif_file.suffix.lower().lstrip(".")
            mime = "image/gif" if suffix == "gif" else f"image/{suffix}"
            b64 = base64.b64encode(gif_file.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{b64}"

        # Untuk file besar (> 3 MB), buat thumbnail WebP animasi berukuran kompak (lebar ~380px)
        mtime = int(gif_file.stat().st_mtime)
        cache_dir = gif_file.parent / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{gif_file.stem}_{file_size}_{mtime}.webp"

        need_regenerate = not cache_file.exists()

        if need_regenerate:
            # Bersihkan cache lama untuk file ini
            for old_cache in cache_dir.glob(f"{gif_file.stem}_*.webp"):
                try:
                    old_cache.unlink()
                except Exception:
                    pass

            from PIL import Image, ImageFile, ImageSequence
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            im = Image.open(gif_file)
            w, h = im.size
            new_w = min(w, 380)
            new_h = int(h * (new_w / w))

            step = 2 if getattr(im, "n_frames", 1) > 40 else 1
            frames = []
            for i, frame in enumerate(ImageSequence.Iterator(im)):
                if i % step == 0:
                    f = frame.copy().convert("RGBA").resize((new_w, new_h), Image.Resampling.BILINEAR)
                    frames.append(f)

            dur = im.info.get("duration", 50) * step
            if frames:
                frames[0].save(
                    cache_file,
                    save_all=True,
                    append_images=frames[1:],
                    optimize=True,
                    quality=65,
                    duration=dur,
                    loop=0
                )

        if cache_file.exists():
            b64 = base64.b64encode(cache_file.read_bytes()).decode("utf-8")
            return f"data:image/webp;base64,{b64}"

        # Fallback jika pembuatan cache gagal
        suffix = gif_file.suffix.lower().lstrip(".")
        mime = "image/gif" if suffix == "gif" else f"image/{suffix}"
        b64 = base64.b64encode(gif_file.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


@st.cache_data(show_spinner=False)
def _build_parameter_tooltip(param_key: str, file_sig: str) -> str:
    """Helper internal untuk membuat teks markdown tooltip dengan cache performa."""
    targets = {
        "combo": "combo.gif",
        "dual_cycle": "dual_cycle.gif",
        "twinlift": "twinlift.gif",
    }
    target_filename = targets.get(param_key, f"{param_key}.gif")

    gif_candidates = {
        "combo": [
            "gifs/combotruck.gif", "gifs/combotruck.webp", "gifs/combo.gif", "gifs/combo.webp", "gifs/combo_20ft.gif", "gifs/combo-20ft.gif", "gifs/combo.png",
            "combo.gif", "combo.webp",
        ],
        "dual_cycle": [
            "gifs/dual_cycle.gif", "gifs/dual_cycle.webp", "gifs/dualcycle.gif", "gifs/dual-cycle.gif", "gifs/dual_cycle.png",
            "dual_cycle.gif", "dual_cycle.webp",
        ],
        "twinlift": [
            "gifs/twinlift.gif", "gifs/twinlift.webp", "gifs/twin_lift.gif", "gifs/twin-lift.gif", "gifs/twinlift.png",
            "twinlift.gif", "twinlift.webp",
        ],
    }

    # 1. Cek apakah pengguna sudah menaruh file GIF kustom di assets/gifs/ atau assets/
    gif_file = find_asset_file(gif_candidates.get(param_key, []))
    is_custom_file = False
    if gif_file:
        img_uri = _get_optimized_preview_uri(gif_file)
        is_custom_file = bool(img_uri)
    else:
        # Tampilkan bingkai placeholder visual minimalis (menunggu file GIF asli)
        placeholder_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 358 92" width="358" height="92">
          <rect x="2" y="2" width="354" height="88" rx="8" fill="#090e1a" stroke="#38bdf8" stroke-width="1.2" stroke-dasharray="6,4" stroke-opacity="0.5"/>
          <circle cx="179" cy="32" r="13" fill="#1e293b" stroke="#38bdf8" stroke-width="1" stroke-opacity="0.6"/>
          <polygon points="175,27 185,32 175,37" fill="#38bdf8"/>
          <text x="179" y="58" fill="#f1f5f9" font-size="10.5" font-weight="600" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">Placeholder Animasi GIF ({target_filename})</text>
          <text x="179" y="74" fill="#64748b" font-size="8.5" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">Letakkan file {target_filename} di folder assets/gifs/</text>
        </svg>"""
        b64_svg = base64.b64encode(placeholder_svg.encode("utf-8")).decode("utf-8")
        img_uri = f"data:image/svg+xml;base64,{b64_svg}"

    descriptions = {
        "combo": (
            "Selisih waktu konfirmasi 2 kontainer yang diangkut 1 truk."
        ),
        "dual_cycle": (
            "**Aktivitas Dual Cycle**\n\n"
            "Truk melakukan **2 aktivitas dalam 1 ritase** (bongkar lalu langsung muat tanpa jalan kosong). "
            "Parameter ini menentukan batas waktu maksimal pergerakan siklus dari peletakan hingga pengambilan kontainer."
        ),
        "twinlift": (
            "Selisih waktu konfirmasi 2 kontainer yang diangkat dalam 1 crane yang sama."
        ),
    }

    desc = descriptions.get(param_key, "")
    if img_uri:
        caption = f"Animasi Aktivitas {param_key.replace('_', ' ').title()}" if is_custom_file else "Placeholder Animasi"
        return f"{desc}\n\n![{caption}]({img_uri})"
    return desc


def get_parameter_tooltip(param_key: str) -> str:
    """
    Menghasilkan teks Markdown untuk parameter help pada st.number_input.
    Ketika pengguna meng-hover ikon tanda tanya native (?), tooltip akan menampilkan
    penjelasan singkat mengenai aktivitas operasional serta animasi GIF kustom (dengan auto-caching).
    """
    gif_candidates = {
        "combo": [
            "gifs/combotruck.gif", "gifs/combotruck.webp", "gifs/combo.gif", "gifs/combo.webp", "gifs/combo_20ft.gif", "gifs/combo-20ft.gif", "gifs/combo.png",
            "combo.gif", "combo.webp",
        ],
        "dual_cycle": [
            "gifs/dual_cycle.gif", "gifs/dual_cycle.webp", "gifs/dualcycle.gif", "gifs/dual-cycle.gif", "gifs/dual_cycle.png",
            "dual_cycle.gif", "dual_cycle.webp",
        ],
        "twinlift": [
            "gifs/twinlift.gif", "gifs/twinlift.webp", "gifs/twin_lift.gif", "gifs/twin-lift.gif", "gifs/twinlift.png",
            "twinlift.gif", "twinlift.webp",
        ],
    }
    gif_file = find_asset_file(gif_candidates.get(param_key, []))
    file_sig = f"{gif_file.stat().st_size}_{int(gif_file.stat().st_mtime)}" if gif_file else "0"
    return _build_parameter_tooltip(param_key, file_sig)




