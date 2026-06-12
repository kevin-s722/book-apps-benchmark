#!/usr/bin/env python3
"""
Generates a single self-contained cross-app comparison HTML report.

Auto-discovers all *_loadtest directories under the results/ folder.
For each book-count tab (10K, 50K, ...) the page shows:
  - Summary stats table
  - Bar charts per key metric
  - Time-series overlays (CPU, RAM, PIDs) with elapsed seconds on X axis

Usage:
    python3 generate_comparison.py
    python3 generate_comparison.py --output /path/to/output.html

Output: results/comparison.html by default.
"""

import argparse
import csv
import json
import math
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR.parent / "results"
CHARTJS_DEFAULT_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"

BOOK_COUNT_TOKEN_RE = re.compile(r"^(\d+)([KkMm]?)$")
TITLE_STRICT_RE = re.compile(
    r"<title>\s*Benchmark:\s+(.+?)\s+(v[0-9A-Za-z.\-]+)\s*-\s*(\d+[KkMm]?)\s+books\s*</title>",
    re.IGNORECASE,
)
TITLE_GENERIC_RE = re.compile(
    r"<title>\s*Benchmark:\s+(.+?)\s*-\s*(\d+[KkMm]?)\s+books\s*</title>",
    re.IGNORECASE,
)
VERSION_TOKEN_RE = re.compile(r"\b(v[0-9A-Za-z.\-]+)\b", re.IGNORECASE)


def canonical_app_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())

# Book counts to skip (not enough apps for cross-app comparison)
SKIP_COUNTS = {"250K"}

# Apps to exclude entirely from charts/line data
SKIP_APPS = {"Calibre-Web-Automated"}

# Callout notes shown per tab explaining excluded apps
TAB_NOTES: dict[str, str] = {
    "10K": (
        '<span style="color:#bc8cff;font-weight:600">Calibre-Web-Automated v4.0.6</span> excluded from charts. '
        "The test was manually stopped after approximately 91&nbsp;minutes with only ~1,100 of 10,000 books processed "
        "(~12&nbsp;books/min). At that rate, full completion would have taken approximately <strong>~14&nbsp;hours</strong>. "
        "No further tests were run for it."
    ),
}


# Stable color palette per app (matched by lowercase app-name prefix)
APP_COLOR_MAP = {
    "audiobookshelf": "#f472b6",
    "bookorbit": "#58a6ff",
    "calibre": "#bc8cff",
    "grimmory": "#3fb950",
    "kavita": "#f0883e",
    "komga": "#d29922",
    "stump": "#f85149",
    "tome": "#8b5cf6",
}
FALLBACK_COLORS = ["#79c0ff", "#56d364", "#e3b341", "#ff7b72", "#d2a8ff", "#ffa657", "#8b949e"]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_time_to_seconds(s: str) -> float | None:
    s = s.strip()
    if s in ("N/A", "n/a", ""):
        return None
    try:
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(s)
    except ValueError:
        return None


def parse_ram_to_mb(s: str) -> float | None:
    s = s.strip()
    if s in ("N/A", "n/a", ""):
        return None
    try:
        if s.endswith("GB"):
            return float(s[:-2].strip()) * 1024
        if s.endswith("MB"):
            return float(s[:-2].strip())
        return float(s)
    except ValueError:
        return None


def parse_pct(s: str) -> float | None:
    s = s.strip().rstrip("%")
    if s in ("N/A", "n/a", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def mb_label(mb: float | None) -> str:
    if mb is None:
        return "N/A"
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def pct_label(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v}%"


def seconds_label(s: float | None) -> str:
    if s is None:
        return "N/A"
    t = int(s)
    h, rem = divmod(t, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {sec:02d}s"
    return f"{m}m {sec:02d}s"


def assign_color(app_name: str, used: list[str]) -> str:
    lower = app_name.lower()
    for prefix, color in APP_COLOR_MAP.items():
        if lower.startswith(prefix):
            return color
    for c in FALLBACK_COLORS:
        if c not in used:
            return c
    return "#8b949e"


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_book_count_to_int(token: str) -> int | None:
    m = BOOK_COUNT_TOKEN_RE.match(token.strip())
    if not m:
        return None

    value = int(m.group(1))
    suffix = m.group(2).upper()
    if suffix == "K":
        return value * 1000
    if suffix == "M":
        return value * 1_000_000
    return value


def normalize_book_count(token: str) -> str | None:
    count = parse_book_count_to_int(token)
    if count is None:
        return None
    if count % 1000 == 0:
        return f"{count // 1000}K"
    return str(count)


def book_count_sort_key(token: str) -> int:
    count = parse_book_count_to_int(token)
    return count if count is not None else 10**12


def app_name_from_dir(app_dir_name: str) -> str:
    base = app_dir_name
    if base.endswith("_loadtest"):
        base = base[: -len("_loadtest")]
    return " ".join(part.capitalize() for part in base.replace("-", " ").split("_"))


def parse_title(html: str, app_dir_name: str) -> tuple[str, str, str]:
    """Returns (app_name, version, normalized_book_count) from <title>."""
    strict = TITLE_STRICT_RE.search(html)
    if strict:
        app_name = strict.group(1).strip()
        version = strict.group(2).strip()
        normalized_count = normalize_book_count(strict.group(3))
        return app_name, version, normalized_count or ""

    generic = TITLE_GENERIC_RE.search(html)
    if generic:
        app_and_version = generic.group(1).strip()
        normalized_count = normalize_book_count(generic.group(2))
        version_match = VERSION_TOKEN_RE.search(app_and_version)
        if version_match:
            version = version_match.group(1)
            app_name = app_and_version[:version_match.start()].strip() or app_name_from_dir(app_dir_name)
        else:
            app_name = app_and_version or app_name_from_dir(app_dir_name)
            version = ""
        return app_name, version, normalized_count or ""

    return app_name_from_dir(app_dir_name), "", ""


def parse_html_stats(html: str) -> dict:
    pattern = re.compile(
        r'<div class="lbl">(.*?)</div>.*?<div class="val[^"]*">(.*?)</div>.*?<div class="sub">(.*?)</div>',
        re.DOTALL,
    )
    raw = {m.group(1).strip(): (m.group(2).strip(), m.group(3).strip()) for m in pattern.finditer(html)}

    ingestion_str = raw.get("Ingestion Time", ("N/A", ""))[0]
    ingestion_sec = parse_time_to_seconds(ingestion_str)

    cpu_sub = raw.get("CPU Peak", ("0%", "avg 0%"))[1]
    cpu_avg_m = re.search(r"avg\s+([\d.]+)%", cpu_sub)
    cpu_avg = float(cpu_avg_m.group(1)) if cpu_avg_m else None

    # New reports (with DB tracking) use "RAM Peak (app)"; old reports use "RAM Peak"
    ram_peak_key = "RAM Peak (app)" if "RAM Peak (app)" in raw else "RAM Peak"
    ram_sub = raw.get(ram_peak_key, ("0 MB", "avg 0 MB"))[1]
    ram_avg_m = re.search(r"avg\s+([\d.]+\s*(?:GB|MB))", ram_sub)
    ram_avg_mb = parse_ram_to_mb(ram_avg_m.group(1)) if ram_avg_m else None

    peak_pids_str = raw.get("Peak PIDs", ("0", ""))[0]
    try:
        peak_pids = int(peak_pids_str)
    except ValueError:
        peak_pids = None

    return {
        "ingestion_str": ingestion_str,
        "ingestion_sec": ingestion_sec,
        "cpu_peak_pct": parse_pct(raw.get("CPU Peak", ("N/A", ""))[0]),
        "cpu_avg_pct": cpu_avg,
        "ram_peak_mb": parse_ram_to_mb(raw.get(ram_peak_key, ("N/A", ""))[0]),
        "ram_avg_mb": ram_avg_mb,
        "peak_pids": peak_pids,
        "idle_cpu_pct": parse_pct(raw.get("Idle CPU (avg)", ("N/A", ""))[0]),
        "idle_ram_mb": parse_ram_to_mb(raw.get("Idle RAM (avg)", ("N/A", ""))[0]),
    }


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_csv(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            try:
                db_mem = float(row["db_mem_mb"]) if "db_mem_mb" in row and row["db_mem_mb"] != "" else 0.0
                mem_mb = float(row["mem_mb"])
                rows.append({
                    "unix_ts": float(row["unix_ts"]),
                    "cpu_pct": float(row["cpu_pct"]),
                    "mem_mb": mem_mb,
                    "db_mem_mb": db_mem,
                    "total_mem_mb": mem_mb + db_mem,
                    "pids": int(row["pids"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def to_elapsed(rows: list[dict]) -> list[dict]:
    if not rows:
        return rows
    t0 = rows[0]["unix_ts"]
    for r in rows:
        r["elapsed_s"] = round(r["unix_ts"] - t0, 1)
    return rows


def subsample(rows: list[dict], max_points: int = 300) -> list[dict]:
    if len(rows) <= max_points:
        return rows
    step = math.ceil(len(rows) / max_points)
    return rows[::step]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover(reports_dirs: list[Path]) -> dict[str, list[dict]]:
    """
    Returns { "10K": [run, ...], "50K": [...], ... }
    Scans all provided directories, sorted by book count.
    Only book counts with >= 2 apps are included.
    """
    by_count: dict[str, list[dict]] = {}
    app_colors: dict[str, str] = {}
    used_colors: list[str] = []
    skip_apps_canonical = {canonical_app_key(name) for name in SKIP_APPS}

    seen_runs: set[str] = set()  # deduplicate by (app, book_count, run_dir)

    for reports_dir in reports_dirs:
        if not reports_dir.exists():
            continue
        for app_dir in sorted(reports_dir.iterdir()):
            if not app_dir.is_dir() or not app_dir.name.endswith("_loadtest"):
                continue

            for run_dir in sorted(app_dir.iterdir()):
                if not run_dir.is_dir():
                    continue

                html_path = run_dir / "report.html"
                csv_path = run_dir / "data.csv"
                if not html_path.exists() or not csv_path.exists():
                    continue

                html = html_path.read_text(encoding="utf-8", errors="replace")
                app_name, version, book_count = parse_title(html, app_dir.name)

                if not book_count:
                    print(
                        f"Skipping malformed run (missing/invalid book count in title): {html_path}",
                        file=sys.stderr,
                    )
                    continue

                if book_count in SKIP_COUNTS:
                    continue

                if canonical_app_key(app_name) in skip_apps_canonical:
                    continue

                run_key = f"{app_name}|{book_count}|{run_dir.name}"
                if run_key in seen_runs:
                    continue
                seen_runs.add(run_key)

                stats = parse_html_stats(html)

                if app_name not in app_colors:
                    color = assign_color(app_name, used_colors)
                    app_colors[app_name] = color
                    used_colors.append(color)

                rows = load_csv(csv_path)
                if not rows:
                    print(f"Skipping malformed run (empty/invalid CSV data): {csv_path}", file=sys.stderr)
                    continue

                # Derive RAM stats from CSV for consistency between app-only and total modes
                has_db = any(r["db_mem_mb"] > 0 for r in rows)
                if rows:
                    stats["ram_peak_mb"] = max(r["mem_mb"] for r in rows)
                    stats["ram_avg_mb"] = sum(r["mem_mb"] for r in rows) / len(rows)
                    stats["ram_peak_total_mb"] = max(r["total_mem_mb"] for r in rows)
                    stats["ram_avg_total_mb"] = sum(r["total_mem_mb"] for r in rows) / len(rows)
                else:
                    stats["ram_peak_total_mb"] = stats["ram_peak_mb"]
                    stats["ram_avg_total_mb"] = stats["ram_avg_mb"]
                stats["has_db"] = has_db

                rows = to_elapsed(rows)

                # Compute idle RAM total from post-ingest rows (elapsed_s > ingestion time)
                ingestion_sec = stats.get("ingestion_sec")
                idle_rows = (
                    [r for r in rows if r.get("elapsed_s", 0) > ingestion_sec]
                    if ingestion_sec is not None
                    else []
                )
                if idle_rows:
                    stats["idle_ram_total_mb"] = sum(r["total_mem_mb"] for r in idle_rows) / len(idle_rows)
                else:
                    stats["idle_ram_total_mb"] = stats.get("idle_ram_mb")

                rows = subsample(rows)

                by_count.setdefault(book_count, []).append({
                    "app": app_name,
                    "version": version,
                    "label": f"{app_name} {version}".strip(),
                    "color": app_colors[app_name],
                    "stats": stats,
                    "timeseries": rows,
                })

    filtered = {k: v for k, v in by_count.items() if len(v) >= 2}
    return dict(sorted(filtered.items(), key=lambda item: book_count_sort_key(item[0])))


# ---------------------------------------------------------------------------
# Chart.js download
# ---------------------------------------------------------------------------

def fetch_chartjs(chartjs_url: str) -> str:
    print(f"Downloading Chart.js from {chartjs_url} ...", flush=True)
    try:
        with urllib.request.urlopen(chartjs_url, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Failed to download Chart.js with TLS verification. "
            "Check network/certificate trust, or pass --chartjs-file to use a local copy."
        ) from exc


def load_chartjs_from_file(chartjs_file: Path) -> str:
    if not chartjs_file.exists():
        raise FileNotFoundError(f"Chart.js file not found: {chartjs_file}")
    return chartjs_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_tab_content(book_count: str, runs: list[dict]) -> tuple[str, str]:
    """Returns (tab_html, tab_init_js)."""

    runs = sorted(runs, key=lambda r: r["app"].lower())
    bc = book_count  # e.g. "10K"

    # ---- Winner computation (lower = better); RAM uses total (default checked state) ----
    WIN_KEYS = [
        "ingestion_sec", "cpu_peak_pct", "cpu_avg_pct",
        "ram_peak_total_mb", "ram_avg_total_mb", "idle_cpu_pct", "idle_ram_total_mb", "peak_pids",
    ]
    winners: dict[str, float | None] = {}
    losers: dict[str, float | None] = {}
    for key in WIN_KEYS:
        vals = [r["stats"][key] for r in runs if r["stats"].get(key) is not None]
        winners[key] = min(vals) if vals else None
        losers[key] = max(vals) if len(vals) > 1 else None

    def win_cls(key: str, val: float | None) -> str:
        if val is None:
            return ""
        if winners.get(key) is not None and val == winners[key]:
            return "winner"
        if losers.get(key) is not None and val == losers[key]:
            return "loser"
        return ""

    def td(key: str | None, display: str, raw_val: float | int | None) -> str:
        dv = "" if raw_val is None else str(raw_val)
        cls = win_cls(key, raw_val) if key else ""
        cls_attr = f' class="{cls}"' if cls else ""
        return f'<td{cls_attr} data-val="{dv}">{display}</td>'

    def ram_td(key_total: str, val_app: float | None, val_total: float | None, has_db: bool) -> str:
        """Build a RAM cell with dual app/total values for the DB-RAM checkbox toggle."""
        dv_app = "" if val_app is None else str(round(val_app, 2))
        dv_total = "" if val_total is None else str(round(val_total, 2))
        disp_app = mb_label(val_app)
        disp_total = mb_label(val_total)
        classes = []
        wc = win_cls(key_total, val_total)
        if wc:
            classes.append(wc)
        if not has_db:
            classes.append("no-db-tracked")
        cls_attr = f' class="{" ".join(classes)}"' if classes else ""
        title_attr = ' title="DB container was not tracked for this run"' if not has_db else ""
        return (
            f'<td{cls_attr}{title_attr} data-val="{dv_total}" '
            f'data-val-app="{dv_app}" data-val-total="{dv_total}" '
            f'data-display-app="{disp_app}" data-display-total="{disp_total}">'
            f'{disp_total}</td>'
        )

    # ---- Summary table ----
    th_labels = ["App", "Ingestion Time", "RAM Peak", "Idle RAM", "RAM Avg", "CPU Peak", "CPU Avg",
                 "Idle CPU", "Peak PIDs"]
    headers = "".join(
        f'<th class="sortable" onclick="sortTable(this,\'{bc}\')">{lbl}</th>'
        for lbl in th_labels
    )

    table_rows = []
    for r in runs:
        s = r["stats"]
        c = r["color"]
        has_db = s.get("has_db", False)
        app_td = f'<td data-val="{r["app"]}"><span class="app-badge" style="background:{c}22;color:{c};border-color:{c}44">{r["app"]}</span> <span class="ver">{r["version"]}</span></td>'
        table_rows.append(f"""      <tr>
        {app_td}
        {td("ingestion_sec", s["ingestion_str"], s["ingestion_sec"])}
        {ram_td("ram_peak_total_mb", s.get("ram_peak_mb"), s.get("ram_peak_total_mb"), has_db)}
        {ram_td("idle_ram_total_mb", s.get("idle_ram_mb"), s.get("idle_ram_total_mb"), has_db)}
        {ram_td("ram_avg_total_mb", s.get("ram_avg_mb"), s.get("ram_avg_total_mb"), has_db)}
        {td("cpu_peak_pct", pct_label(s["cpu_peak_pct"]), s["cpu_peak_pct"])}
        {td("cpu_avg_pct", pct_label(s["cpu_avg_pct"]), s["cpu_avg_pct"])}
        {td("idle_cpu_pct", pct_label(s["idle_cpu_pct"]), s["idle_cpu_pct"])}
        {td("peak_pids", str(s["peak_pids"]) if s["peak_pids"] is not None else "N/A", s["peak_pids"])}
      </tr>""")

    # ---- Bar chart data ----
    app_labels = json.dumps([r["app"] for r in runs])
    colors = [r["color"] for r in runs]

    def bar_ds(key, transform=None):
        vals = []
        for r in runs:
            v = r["stats"].get(key)
            if v is None:
                vals.append(None)
            elif transform:
                vals.append(transform(v))
            else:
                vals.append(v)
        return json.dumps({
            "data": vals,
            "backgroundColor": [c + "99" for c in colors],
            "borderColor": colors,
            "borderWidth": 2,
            "borderRadius": 4,
        })

    # Static bar specs (non-RAM)
    bar_specs_static = [
        (f"bar-ingestion-{bc}", "Ingestion Time (minutes) (lower is better)", bar_ds("ingestion_sec", lambda v: round(v / 60, 1))),
        (f"bar-cpu-peak-{bc}", "CPU Peak (%) (lower is better)", bar_ds("cpu_peak_pct")),
        (f"bar-cpu-avg-{bc}", "CPU Avg (%) (lower is better)", bar_ds("cpu_avg_pct")),
        (f"bar-idle-cpu-{bc}", "Idle CPU Avg (%) (lower is better)", bar_ds("idle_cpu_pct")),
    ]
    # RAM Peak bar - two versions for toggle
    ram_bar_id = f"bar-ram-peak-{bc}"
    ram_bar_ds_app = bar_ds("ram_peak_mb", lambda v: round(v / 1024, 2))
    ram_bar_ds_total = bar_ds("ram_peak_total_mb", lambda v: round(v / 1024, 2))
    # Idle RAM bar - two versions for toggle
    idle_ram_bar_id = f"bar-idle-ram-{bc}"
    idle_ram_bar_ds_app = bar_ds("idle_ram_mb", lambda v: round(v / 1024, 2))
    idle_ram_bar_ds_total = bar_ds("idle_ram_total_mb", lambda v: round(v / 1024, 2))

    # Order: Ingestion, RAM Peak, Idle RAM, CPU Peak, CPU Avg, Idle CPU
    bar_html_parts = [
        f'<div class="cb"><h3>{bar_specs_static[0][1]}</h3><canvas id="{bar_specs_static[0][0]}"></canvas></div>\n',
        f'<div class="cb"><h3 id="h3-{ram_bar_id}">RAM Peak - App + DB (GB) (lower is better)</h3><canvas id="{ram_bar_id}"></canvas></div>\n',
        f'<div class="cb"><h3 id="h3-{idle_ram_bar_id}">Idle RAM Avg - App + DB (GB) (lower is better)</h3><canvas id="{idle_ram_bar_id}"></canvas></div>\n',
    ]
    bar_html_parts += [f'<div class="cb"><h3>{title}</h3><canvas id="{cid}"></canvas></div>\n'
                       for cid, title, _ in bar_specs_static[1:]]
    bar_html = "".join(bar_html_parts)

    bar_js_static = "".join(f'  mkBar("{cid}", {app_labels}, [{ds}]);\n'
                             for cid, _, ds in bar_specs_static)

    # ---- Time-series datasets ----
    def line_ds(key):
        datasets = []
        for r in runs:
            col = r["color"]
            points = [{"x": round(row["elapsed_s"] / 60, 3), "y": row[key]} for row in r["timeseries"]]
            datasets.append({
                "label": r["label"],
                "data": points,
                "borderColor": col,
                "backgroundColor": col + "22",
                "borderWidth": 2,
                "pointRadius": 0,
                "tension": 0.3,
                "fill": False,
            })
        return json.dumps(datasets)

    # Static line specs (non-RAM)
    line_specs_static = [
        (f"line-cpu-{bc}", "CPU Usage (%) (lower is better)", "cpu_pct"),
        (f"line-pids-{bc}", "Process / Thread Count (PIDs) (lower is better)", "pids"),
    ]
    # RAM line - two versions for toggle
    ram_line_id = f"line-ram-{bc}"
    line_ds_ram_app = line_ds("mem_mb")
    line_ds_ram_total = line_ds("total_mem_mb")

    line_html_parts = [
        f'<div class="cb wide"><h3 id="h3-{ram_line_id}">RAM Usage - App + DB (MB) (lower is better)</h3><canvas id="{ram_line_id}"></canvas></div>\n'
    ]
    line_html_parts += [f'<div class="cb wide"><h3>{title}</h3><canvas id="{cid}"></canvas></div>\n'
                        for cid, title, _ in line_specs_static]
    line_html = "".join(line_html_parts)

    line_js_static = "".join(f'  mkLine("{cid}", {line_ds(key)});\n'
                              for cid, _, key in line_specs_static)

    # ---- App legend for this tab ----
    legend_items = "".join(
        f'<div class="legend-item"><div class="legend-dot" style="background:{r["color"]}"></div>'
        f'<span>{r["app"]} <span class="ver">{r["version"]}</span></span></div>'
        for r in runs
    )

    tab_html = f"""
<div id="tab-{bc}" class="tab-content" style="display:none">
  <div class="tab-header">
    <span class="tab-summary">{len(runs)} apps compared at <strong>{bc} books</strong></span>
    <div class="app-legend">{legend_items}</div>
  </div>
{'  <div class="note-box"><span class="note-icon">&#9888;&#65039;</span>' + TAB_NOTES[bc] + '</div>' if bc in TAB_NOTES else ''}
  <h2>Summary Stats</h2>
  <p class="table-hint">Click any column header to sort. <span class="no-db-hint">&#8505; Apps marked with <span class="no-db-tag">no DB</span> did not have a DB container tracked.</span></p>
  <div class="table-wrap">
    <table id="table-{bc}">
      <thead><tr>{headers}</tr></thead>
      <tbody>{''.join(table_rows)}</tbody>
    </table>
  </div>

  <h2>Key Metrics</h2>
  <div class="bar-grid">{bar_html}</div>

  <h2>Resource Usage Over Time</h2>
  <div class="line-grid">{line_html}</div>
</div>"""

    tab_init_js = f""""{bc}": function() {{
  ramBarDs["{bc}"] = {{ app: [{ram_bar_ds_app}], total: [{ram_bar_ds_total}] }};
  idleRamBarDs["{bc}"] = {{ app: [{idle_ram_bar_ds_app}], total: [{idle_ram_bar_ds_total}] }};
  ramLineDs["{bc}"] = {{ app: {line_ds_ram_app}, total: {line_ds_ram_total} }};
  var _iDb = document.getElementById("include-db-ram").checked;
{bar_js_static}  mkBar("{ram_bar_id}", {app_labels}, _iDb ? ramBarDs["{bc}"].total : ramBarDs["{bc}"].app);
  mkBar("{idle_ram_bar_id}", {app_labels}, _iDb ? idleRamBarDs["{bc}"].total : idleRamBarDs["{bc}"].app);
{line_js_static}  mkLine("{ram_line_id}", _iDb ? ramLineDs["{bc}"].total : ramLineDs["{bc}"].app);
}}"""

    return tab_html, tab_init_js


def build_html(tabs: dict[str, list[dict]], chartjs_src: str) -> str:
    tab_keys = list(tabs.keys())

    # Tab buttons
    tab_buttons = "".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" data-tab="{bc}" onclick="showTab(\'{bc}\')">'
        f'{bc} books</button>\n'
        for i, bc in enumerate(tab_keys)
    )

    # Tab content + init functions
    all_tab_html_parts = []
    all_init_fn_parts = []
    for bc, runs in tabs.items():
        tab_html, tab_init_js = build_tab_content(bc, runs)
        all_tab_html_parts.append(tab_html)
        all_init_fn_parts.append(tab_init_js)

    all_tab_html = "\n".join(all_tab_html_parts)
    init_fns_obj = ",\n    ".join(all_init_fn_parts)
    first_tab = "100K" if "100K" in tab_keys else (tab_keys[0] if tab_keys else "")

    # ---- RAM growth charts (cross-tab) ----
    # Collect all apps (preserving first-seen order) and their colors
    app_meta: dict[str, str] = {}
    for runs in tabs.values():
        for r in runs:
            if r["app"] not in app_meta:
                app_meta[r["app"]] = r["color"]

    # Lookup: app -> book_count -> stats
    app_data: dict[str, dict[str, dict]] = {}
    for bc, runs in tabs.items():
        for r in runs:
            app_data.setdefault(r["app"], {})[bc] = r["stats"]

    def growth_datasets(key: str) -> str:
        datasets = []
        for app, color in app_meta.items():
            data = []
            for bc in tab_keys:
                v = app_data.get(app, {}).get(bc, {}).get(key)
                data.append(None if v is None else round(v / 1024, 3))
            datasets.append({
                "label": app,
                "data": data,
                "borderColor": color,
                "backgroundColor": color + "33",
                "borderWidth": 2,
                "pointRadius": 5,
                "pointHoverRadius": 7,
                "tension": 0.3,
                "fill": False,
                "spanGaps": False,
            })
        return json.dumps(datasets)

    growth_peak_ds_app = growth_datasets("ram_peak_mb")
    growth_peak_ds_total = growth_datasets("ram_peak_total_mb")
    growth_idle_ds_app = growth_datasets("idle_ram_mb")
    growth_idle_ds_total = growth_datasets("idle_ram_total_mb")
    growth_labels = json.dumps(tab_keys)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Load Test Benchmark - Cross-App Comparison</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0 auto;padding:2rem;max-width:1400px}}
    h1{{color:#58a6ff;font-size:1.6rem;margin:0 0 .25rem}}
    h2{{color:#c9d1d9;font-size:1.05rem;margin:2rem 0 .75rem;border-bottom:1px solid #30363d;padding-bottom:.4rem}}
    .meta{{color:#8b949e;font-size:.85rem;margin-bottom:1.5rem}}
    .tab-bar{{display:flex;gap:.5rem;border-bottom:1px solid #30363d;margin-bottom:2rem;flex-wrap:wrap}}
    .tab-btn{{background:none;border:none;color:#8b949e;font-size:.9rem;padding:.6rem 1.2rem;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;border-radius:4px 4px 0 0;transition:color .15s,background .15s}}
    .tab-btn:hover{{color:#e6edf3;background:#161b22}}
    .tab-btn.active{{color:#58a6ff;border-bottom-color:#58a6ff;font-weight:600}}
    .tab-header{{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;margin-bottom:1.5rem}}
    .tab-summary{{color:#8b949e;font-size:.85rem;padding-top:.1rem}}
    .app-legend{{display:flex;gap:1.25rem;flex-wrap:wrap}}
    .legend-item{{display:flex;align-items:center;gap:.4rem;font-size:.82rem;color:#c9d1d9}}
    .legend-dot{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
    .ver{{color:#6e7681;font-size:.85em}}
    .app-badge{{display:inline-block;padding:.1em .5em;border-radius:4px;border:1px solid;font-weight:700;font-size:.82em}}
    .table-wrap{{overflow-x:auto;margin-bottom:2rem}}
    table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;white-space:nowrap}}
    th,td{{padding:.6rem .9rem;text-align:right;border-bottom:1px solid #21262d;font-size:.82rem}}
    th{{color:#8b949e;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;background:#0d1117}}
    th:first-child,td:first-child{{text-align:left}}
    tr:last-child td{{border-bottom:none}}
    td.winner{{color:#3fb950;font-weight:700}}
    td.loser{{color:#e05c5c;font-weight:700}}
    .table-hint{{font-size:.72rem;color:#6e7681;margin:-.5rem 0 .5rem}}
    .no-db-hint{{display:none}}
    .no-db-hint.visible{{display:inline}}
    .no-db-tag{{display:inline-block;padding:.05em .35em;border-radius:3px;background:#2a2a1a;color:#8b7e50;border:1px solid #6b5e3044;font-size:.9em}}
    td.no-db-tracked[data-mode="total"]::after{{content:" *";color:#6e7681;font-size:.78em;vertical-align:super}}
    .note-box{{background:#161c24;border:1px solid #8b7a4a66;border-left:3px solid #a89060;border-radius:6px;padding:.75rem 1rem;margin:1rem 0 1.5rem;font-size:.83rem;color:#9a8c6e;line-height:1.5}}
    .note-box strong{{color:#b8a87a}}
    .note-icon{{margin-right:.4rem}}
    .db-toggle-wrap{{background:#0d1b2a;border:1px solid #58a6ff44;border-left:3px solid #58a6ff;border-radius:6px;padding:.75rem 1rem;margin:1rem 0 1.5rem;display:flex;align-items:flex-start;gap:.65rem;cursor:pointer}}
    .db-toggle-wrap input[type="checkbox"]{{margin-top:.15rem;accent-color:#58a6ff;flex-shrink:0;width:1rem;height:1rem;cursor:pointer}}
    .db-toggle-body{{display:flex;flex-direction:column;gap:.25rem}}
    .db-toggle-title{{color:#79c0ff;font-weight:600;font-size:.88rem}}
    .db-toggle-hint{{color:#8b949e;font-size:.8rem;line-height:1.45}}
    th.sortable{{cursor:pointer;user-select:none;white-space:nowrap}}
    th.sortable:hover{{color:#e6edf3;background:#1c2128}}
    th.sort-asc::after{{content:" \\2191";color:#58a6ff}}
    th.sort-desc::after{{content:" \\2193";color:#58a6ff}}
    .bar-grid{{display:grid;grid-template-columns:repeat(3, 1fr);gap:1.25rem;margin-bottom:2rem}}
    .line-grid{{display:grid;grid-template-columns:1fr;gap:1.25rem;margin-bottom:2rem}}
    .growth-section{{margin-bottom:2.5rem}}
    .growth-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:1.25rem;margin-bottom:2rem}}
    .cb{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.25rem}}
    .cb h3{{margin:0 0 .75rem;font-size:.88rem;color:#c9d1d9}}
    canvas{{max-height:240px}}
    .cb.wide canvas{{max-height:300px}}
    @media(max-width:700px){{body{{padding:1rem}}.bar-grid{{grid-template-columns:1fr}}.growth-grid{{grid-template-columns:1fr}}.tab-btn{{font-size:.8rem;padding:.5rem .75rem}}}}
  </style>
</head>
<body>
  <h1>Load Test Benchmark - Cross-App Comparison</h1>
  <div class="meta">
    Comparing ingestion performance across apps &nbsp;|&nbsp;
    Times measured from first sample to idle &nbsp;|&nbsp;
    X axis = elapsed minutes from run start
  </div>

  <label class="db-toggle-wrap" for="include-db-ram">
    <input type="checkbox" id="include-db-ram" onchange="setDbRam(this.checked)">
    <div class="db-toggle-body">
     <span class="db-toggle-title">Include Database RAM in memory figures</span>
     <span class="db-toggle-hint">Grimmory (MariaDB) and Bookorbit (PostgreSQL) run external databases whose RAM is tracked separately and added to app RAM above.
       Uncheck if you would deploy with a dedicated database server - actual RAM usage will be significantly lower for those two apps.
       Apps without a tracked database container show app-only RAM in both modes.</span>
    </div>
  </label>

  <div class="growth-section">
    <h2>RAM by Library Size</h2>
    <div class="growth-grid">
      <div class="cb wide">
        <h3 id="h3-growth-peak">RAM Peak - App + DB (GB) (lower is better)</h3>
        <canvas id="growth-peak"></canvas>
      </div>
      <div class="cb wide">
        <h3 id="h3-growth-idle">Idle RAM - App + DB (GB) (lower is better)</h3>
        <canvas id="growth-idle"></canvas>
      </div>
    </div>
  </div>

  <div class="tab-bar">
    {tab_buttons}
  </div>

  {all_tab_html}

  <script>
{chartjs_src}
  </script>
  <script>
(function() {{
  Chart.defaults.color = '#8b949e';

  const chartRegistry = {{}};
  const ramBarDs = {{}};
  const idleRamBarDs = {{}};
  const ramLineDs = {{}};
  const growthDs = {{
    peak: {{ app: {growth_peak_ds_app}, total: {growth_peak_ds_total} }},
    idle: {{ app: {growth_idle_ds_app}, total: {growth_idle_ds_total} }}
  }};

  const BAR_OPTS = {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
     x: {{ ticks: {{ color: '#8b949e', maxRotation: 30 }}, grid: {{ color: '#21262d' }} }},
     y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
    }}
  }};

  const LINE_OPTS = {{
    responsive: true,
    parsing: false,
    animation: false,
    plugins: {{ legend: {{ labels: {{ color: '#c9d1d9', boxWidth: 12 }} }} }},
    scales: {{
     x: {{
       type: 'linear',
       title: {{ display: true, text: 'Elapsed (minutes)', color: '#8b949e' }},
       ticks: {{ color: '#8b949e' }},
       grid: {{ color: '#21262d' }}
     }},
     y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
    }}
  }};

  function mkBar(id, labels, datasets) {{
    chartRegistry[id] = new Chart(document.getElementById(id), {{ type: 'bar', data: {{ labels, datasets }}, options: BAR_OPTS }});
  }}

  function mkLine(id, datasets) {{
    chartRegistry[id] = new Chart(document.getElementById(id), {{ type: 'line', data: {{ datasets }}, options: LINE_OPTS }});
  }}

  const GROWTH_OPTS = {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#c9d1d9', boxWidth: 12 }} }} }},
    scales: {{
     x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
     y: {{
       ticks: {{ color: '#8b949e' }},
       grid: {{ color: '#21262d' }},
       title: {{ display: true, text: 'GB', color: '#8b949e' }}
     }}
    }}
  }};

  function mkGrowth(id, labels, datasets) {{
    chartRegistry[id] = new Chart(document.getElementById(id), {{
      type: 'line',
      data: {{ labels, datasets }},
      options: GROWTH_OPTS
    }});
  }}

  function refreshRamColumn(bc, colIdx) {{
    var table = document.getElementById('table-' + bc);
    if (!table) return;
    var tds = Array.from(table.querySelectorAll('tbody tr')).map(function(tr) {{
     return tr.querySelectorAll('td')[colIdx];
    }});
    tds.forEach(function(td) {{ td.classList.remove('winner', 'loser'); }});
    var vals = tds.map(function(td) {{ return td.dataset.val === '' ? null : parseFloat(td.dataset.val); }});
    var nonNull = vals.filter(function(v) {{ return v !== null; }});
    if (nonNull.length < 2) return;
    var minV = Math.min.apply(null, nonNull);
    var maxV = Math.max.apply(null, nonNull);
    tds.forEach(function(td, i) {{
     if (vals[i] === null) return;
     if (vals[i] === minV) td.classList.add('winner');
     else if (vals[i] === maxV) td.classList.add('loser');
    }});
  }}

  function updateTabRam(bc, include) {{
    var barChart = chartRegistry['bar-ram-peak-' + bc];
    if (barChart && ramBarDs[bc]) {{
     barChart.data.datasets = include ? ramBarDs[bc].total : ramBarDs[bc].app;
     barChart.update();
    }}
    var barTitleEl = document.getElementById('h3-bar-ram-peak-' + bc);
    if (barTitleEl) barTitleEl.textContent = include ? 'RAM Peak - App + DB (GB) (lower is better)' : 'RAM Peak - App only (GB) (lower is better)';
    var idleBarChart = chartRegistry['bar-idle-ram-' + bc];
    if (idleBarChart && idleRamBarDs[bc]) {{
     idleBarChart.data.datasets = include ? idleRamBarDs[bc].total : idleRamBarDs[bc].app;
     idleBarChart.update();
    }}
    var idleBarTitleEl = document.getElementById('h3-bar-idle-ram-' + bc);
    if (idleBarTitleEl) idleBarTitleEl.textContent = include ? 'Idle RAM Avg - App + DB (GB) (lower is better)' : 'Idle RAM Avg - App only (GB) (lower is better)';
    var lineChart = chartRegistry['line-ram-' + bc];
    if (lineChart && ramLineDs[bc]) {{
     lineChart.data.datasets = include ? ramLineDs[bc].total : ramLineDs[bc].app;
     lineChart.update();
    }}
    var lineTitleEl = document.getElementById('h3-line-ram-' + bc);
    if (lineTitleEl) lineTitleEl.textContent = include ? 'RAM Usage - App + DB (MB) (lower is better)' : 'RAM Usage - App only (MB) (lower is better)';
  }}

  window.setDbRam = function(include) {{
    document.querySelectorAll('td[data-val-app]').forEach(function(td) {{
     td.dataset.val = include ? td.dataset.valTotal : td.dataset.valApp;
     td.textContent = include ? td.dataset.displayTotal : td.dataset.displayApp;
     if (td.classList.contains('no-db-tracked')) {{
       td.dataset.mode = include ? 'total' : 'app';
     }}
    }});
    initialized.forEach(function(bc) {{
     updateTabRam(bc, include);
     var table = document.getElementById('table-' + bc);
     if (table) {{
       var firstRow = table.querySelector('tbody tr');
       if (firstRow) {{
         Array.from(firstRow.querySelectorAll('td')).forEach(function(td, idx) {{
           if (td.hasAttribute('data-val-app')) refreshRamColumn(bc, idx);
         }});
       }}
     }}
    }});
    var hint = document.querySelector('.no-db-hint');
    if (hint) hint.classList.toggle('visible', include);

    // Toggle growth charts
    var gPeak = chartRegistry['growth-peak'];
    if (gPeak) {{
      gPeak.data.datasets = include ? growthDs.peak.total : growthDs.peak.app;
      gPeak.update();
    }}
    var gPeakTitle = document.getElementById('h3-growth-peak');
    if (gPeakTitle) gPeakTitle.textContent = include ? 'RAM Peak - App + DB (GB) (lower is better)' : 'RAM Peak - App only (GB) (lower is better)';

    var gIdle = chartRegistry['growth-idle'];
    if (gIdle) {{
      gIdle.data.datasets = include ? growthDs.idle.total : growthDs.idle.app;
      gIdle.update();
    }}
    var gIdleTitle = document.getElementById('h3-growth-idle');
    if (gIdleTitle) gIdleTitle.textContent = include ? 'Idle RAM - App + DB (GB) (lower is better)' : 'Idle RAM - App only (GB) (lower is better)';
  }};

  const tabInits = {{
    {init_fns_obj}
  }};

  const initialized = new Set();

  window.showTab = function(bc) {{
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.getElementById('tab-' + bc).style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-tab="' + bc + '"]').classList.add('active');
    if (!initialized.has(bc)) {{
     tabInits[bc]();
     initialized.add(bc);
     var inclDb = document.getElementById('include-db-ram').checked;
     if (!inclDb) {{
       var table = document.getElementById('table-' + bc);
       if (table) {{
         table.querySelectorAll('td[data-val-app]').forEach(function(td) {{
           td.dataset.val = td.dataset.valApp;
           td.textContent = td.dataset.displayApp;
         }});
         var firstRow = table.querySelector('tbody tr');
         if (firstRow) {{
           Array.from(firstRow.querySelectorAll('td')).forEach(function(td, idx) {{
             if (td.hasAttribute('data-val-app')) refreshRamColumn(bc, idx);
           }});
         }}
       }}
       updateTabRam(bc, false);
     }}
    }}
  }};

  window.sortTable = function(th, bc) {{
    const table = document.getElementById('table-' + bc);
    const ths = Array.from(table.querySelectorAll('thead th'));
    const colIdx = ths.indexOf(th);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const asc = th.dataset.sortDir !== 'asc';
    ths.forEach(h => {{ h.dataset.sortDir = ''; h.classList.remove('sort-asc', 'sort-desc'); }});
    th.dataset.sortDir = asc ? 'asc' : 'desc';
    th.classList.add(asc ? 'sort-asc' : 'sort-desc');
    rows.sort((a, b) => {{
     const aVal = a.querySelectorAll('td')[colIdx].dataset.val;
     const bVal = b.querySelectorAll('td')[colIdx].dataset.val;
     if (aVal === '' && bVal === '') return 0;
     if (aVal === '') return 1;
     if (bVal === '') return -1;
     const aNum = parseFloat(aVal), bNum = parseFloat(bVal);
     if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
     return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }});
    rows.forEach(r => tbody.appendChild(r));
  }};

  showTab('{first_tab}');

  // Initialize RAM growth charts
  (function() {{
    var inclDb = document.getElementById('include-db-ram').checked;
    mkGrowth('growth-peak', {growth_labels}, inclDb ? growthDs.peak.total : growthDs.peak.app);
    mkGrowth('growth-idle', {growth_labels}, inclDb ? growthDs.idle.total : growthDs.idle.app);
  }})();
}})();
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate cross-app load test comparison report")
    parser.add_argument("--output", default=str(RESULTS_DIR / "comparison.html"))
    parser.add_argument(
        "--reports-dir",
        nargs="*",
        help="Directories to scan for runs (default: results/). Pass multiple paths to include others, e.g. --reports-dir ../results ../reference",
    )
    parser.add_argument(
        "--chartjs-url",
        default=CHARTJS_DEFAULT_URL,
        help=f"Chart.js URL to download and inline (default: {CHARTJS_DEFAULT_URL})",
    )
    parser.add_argument(
        "--chartjs-file",
        help="Path to a local Chart.js bundle to inline instead of downloading.",
    )
    args = parser.parse_args()

    scan_dirs = [Path(d) for d in args.reports_dir] if args.reports_dir else [RESULTS_DIR]

    print(f"Discovering runs in: {', '.join(str(d) for d in scan_dirs)} ...")
    tabs = discover(scan_dirs)

    if not tabs:
        print("No comparable runs found (need >= 2 apps at the same book count).", file=sys.stderr)
        sys.exit(1)

    for bc, runs in tabs.items():
        print(f"  {bc}: {len(runs)} apps - {', '.join(r['app'] for r in runs)}")

    try:
        if args.chartjs_file:
            print(f"Loading Chart.js from local file: {args.chartjs_file}")
            chartjs_src = load_chartjs_from_file(Path(args.chartjs_file))
        else:
            chartjs_src = fetch_chartjs(args.chartjs_url)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Generating HTML ...")
    html = build_html(tabs, chartjs_src)

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    size_kb = out.stat().st_size // 1024
    print(f"Done: {out}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
