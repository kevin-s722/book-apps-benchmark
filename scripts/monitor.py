#!/usr/bin/env python3
"""
monitor.py  -  Docker container resource monitor for ingestion benchmarking.

Usage:
  python3 monitor.py <container_name> [options]

Options:
  --label TEXT            Display name for the report (default: container name)
  --books TEXT            Book count label shown in report and live display (e.g. 50K, 100K)
  --db-container TEXT     Optional DB sidecar container to also track RAM (e.g. postgres, mariadb)
  --interval SECS         Sampling interval in seconds (default: 5)
  --idle-threshold PCT    CPU% below which the container is considered idle (default: 5.0)
  --idle-duration SECS    Seconds CPU must stay below threshold to auto-stop (default: 60)
  --idle-window SECS      Seconds to keep recording after ingestion completes for idle baseline (default: 120)
  --min-duration SECS     Minimum recording time before auto-stop can trigger (default: 30)
  --no-autostop           Disable auto-stop; run until Ctrl+C

Examples:
  python3 monitor.py grimmory_loadtest --label "Grimmory v3.1.0" --books 50K --db-container grimmory_mariadb_loadtest
  python3 monitor.py bookorbit_loadtest --label "Bookorbit v1.4.0" --books 150K --db-container bookorbit_db_loadtest
  python3 monitor.py kavita_loadtest --label "Kavita v0.9.0.2" --books 100K --interval 2
  python3 monitor.py komga_loadtest --label "Komga v1.24.4" --books 50K --idle-threshold 3
  python3 monitor.py tome_loadtest --label "Tome v1.3.2" --books 50K

Requires:  pip install rich   (gracefully falls back to plain text if missing)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich import box as rich_box
    RICH = True
except ImportError:
    RICH = False

SCRIPT_DIR = Path(__file__).parent
REPORTS_DIR = SCRIPT_DIR.parent / "results"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Sample:
    __slots__ = ("ts", "cpu", "mem", "pids", "db_mem")

    def __init__(self, ts: float, cpu: float, mem: float, pids: int, db_mem: float = 0.0):
        self.ts     = ts
        self.cpu    = cpu     # percent 0-100
        self.mem    = mem     # megabytes (app container only)
        self.pids   = pids    # process/thread count
        self.db_mem = db_mem  # megabytes (db container, 0 when not tracked)


# ---------------------------------------------------------------------------
# Docker polling
# ---------------------------------------------------------------------------

_UNITS: dict[str, float] = {
    "b":   1 / (1024 ** 2),
    "kb":  1 / 1024,  "kib": 1 / 1024,
    "mb":  1.0,       "mib": 1.0,
    "gb":  1024.0,    "gib": 1024.0,
    "tb":  1024.0 ** 2, "tib": 1024.0 ** 2,
}


def _to_mb(s: str) -> float:
    s = s.strip()
    m = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", s)
    if not m:
        return 0.0
    return float(m.group(1)) * _UNITS.get(m.group(2).lower(), 0.0)


def poll(container: str) -> Optional[Sample]:
    """Run docker stats --no-stream and return a Sample, or None on failure."""
    try:
        r = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", container],
            capture_output=True, text=True, timeout=10,
        )
        line = r.stdout.strip()
        if not line:
            return None
        d = json.loads(line)
        cpu = float(d.get("CPUPerc", "0%").strip().rstrip("%"))
        mem_parts = d.get("MemUsage", "0B / 0B").split("/")
        mem = _to_mb(mem_parts[0])
        pids = int(d.get("PIDs", "0").strip() or "0")
        return Sample(time.time(), cpu, mem, pids)
    except Exception:
        return None


def poll_mem(container: str) -> float:
    """Return RAM usage in MB for a container, or 0.0 on failure. Used for DB sidecar tracking."""
    try:
        r = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", container],
            capture_output=True, text=True, timeout=10,
        )
        line = r.stdout.strip()
        if not line:
            return 0.0
        d = json.loads(line)
        mem_parts = d.get("MemUsage", "0B / 0B").split("/")
        return _to_mb(mem_parts[0])
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _dur(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _fmb(mb: float) -> str:
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


def _stats(vals: list[float]) -> tuple[float, float, float, float]:
    if not vals:
        return 0.0, 0.0, 0.0, 0.0
    return vals[-1], min(vals), max(vals), sum(vals) / len(vals)


# ---------------------------------------------------------------------------
# Rich live table
# ---------------------------------------------------------------------------

def build_table(
    samples: list[Sample],
    container: str,
    label: str,
    books: str,
    status: str,
    countdown: Optional[int],
    db_container: str = "",
) -> "Table":
    elapsed = (samples[-1].ts - samples[0].ts) if len(samples) > 1 else 0.0

    cur_cpu, mn_cpu, mx_cpu, av_cpu         = _stats([s.cpu     for s in samples])
    cur_mem, mn_mem, mx_mem, av_mem         = _stats([s.mem     for s in samples])
    cur_pid, mn_pid, mx_pid, _             = _stats([float(s.pids) for s in samples])

    tracking_db = db_container and any(s.db_mem > 0 for s in samples)
    if tracking_db:
        cur_dbm, mn_dbm, mx_dbm, _ = _stats([s.db_mem for s in samples])

    def _cc(v: float) -> str:
        c = "red" if v > 80 else "yellow" if v > 40 else "green"
        return f"[{c}]{v:.1f}%[/]"

    def _cp(v: float) -> str:
        c = "red" if v > 80 else "yellow" if v > 50 else "green"
        return f"[{c}]{v:.1f}%[/]"

    sc = {"ACTIVE": "green", "IDLE": "yellow", "SETTLING": "blue", "DONE": "cyan", "STARTING": "dim"}.get(status, "white")
    cd = f"  [dim](settling: {countdown}s left)[/]" if status == "SETTLING" and countdown else (
         f"  [dim](auto-stop in {countdown}s)[/]" if countdown else ""
    )

    books_suffix = f"  [yellow]{books} books[/]" if books else ""
    t = Table(
        title=f"[bold cyan]{label}[/]{books_suffix}  [dim]({container})[/]",
        box=rich_box.ROUNDED, expand=True,
    )
    t.add_column("Metric",  style="bold white", min_width=16)
    t.add_column("Current", justify="right",    min_width=13)
    t.add_column("Min",     justify="right",    min_width=13)
    t.add_column("Max",     justify="right",    min_width=13)

    t.add_row("CPU %",     _cc(cur_cpu),  f"{mn_cpu:.1f}%",  f"[red]{mx_cpu:.1f}%[/]")
    t.add_row("RAM (app)", _fmb(cur_mem), _fmb(mn_mem),      f"[red]{_fmb(mx_mem)}[/]")
    if tracking_db:
        t.add_row(
            f"RAM (db/{db_container})",
            _fmb(cur_dbm), _fmb(mn_dbm), f"[red]{_fmb(mx_dbm)}[/]",
        )
        t.add_row(
            "RAM (total)",
            _fmb(cur_mem + cur_dbm), _fmb(mn_mem + mn_dbm), f"[red]{_fmb(mx_mem + mx_dbm)}[/]",
        )
    t.add_row("PIDs",      str(int(cur_pid)), str(int(mn_pid)), str(int(mx_pid)))

    t.add_section()
    t.add_row(
        f"[dim]Elapsed: [bold]{_dur(elapsed)}[/]   Samples: {len(samples)}[/]",
        "",
        f"[{sc}]● {status}[/]{cd}",
        "",
    )
    return t


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_csv(samples: list[Sample], path: Path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_iso", "unix_ts", "cpu_pct", "mem_mb", "pids", "db_mem_mb"])
        for s in samples:
            w.writerow([
                datetime.fromtimestamp(s.ts).isoformat(),
                f"{s.ts:.3f}",
                f"{s.cpu:.3f}",
                f"{s.mem:.3f}",
                s.pids,
                f"{s.db_mem:.3f}",
            ])


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def write_html(
    samples: list[Sample],
    container: str,
    label: str,
    books: str,
    interval: float,
    ingestion_end_idx: Optional[int],
    path: Path,
    db_container: str = "",
) -> None:
    ts_labels   = [datetime.fromtimestamp(s.ts).strftime("%H:%M:%S") for s in samples]
    cpu_data    = [round(s.cpu, 2) for s in samples]
    mem_data    = [round(s.mem, 2) for s in samples]
    pids_data   = [s.pids          for s in samples]

    total_sec  = samples[-1].ts - samples[0].ts if len(samples) > 1 else 0.0
    ingest_sec = (
        samples[ingestion_end_idx].ts - samples[0].ts
        if ingestion_end_idx is not None else total_sec
    )

    cpu_min, cpu_max, cpu_avg   = min(cpu_data), max(cpu_data), sum(cpu_data) / len(cpu_data)
    mem_min, mem_max, mem_avg   = min(mem_data), max(mem_data), sum(mem_data) / len(mem_data)
    pid_max                     = max(pids_data)

    tracking_db = db_container and any(s.db_mem > 0 for s in samples)
    if tracking_db:
        db_mem_data = [round(s.db_mem, 2) for s in samples]
        db_mem_max  = max(db_mem_data)
        db_mem_avg  = sum(db_mem_data) / len(db_mem_data)
        total_mem_data = [round(s.mem + s.db_mem, 2) for s in samples]
    else:
        db_mem_data = total_mem_data = []
        db_mem_max = db_mem_avg = 0.0

    idle_samples = samples[ingestion_end_idx:] if ingestion_end_idx is not None and ingestion_end_idx < len(samples) else []
    if idle_samples:
        idle_cpu_avg      = sum(s.cpu  for s in idle_samples) / len(idle_samples)
        idle_mem_avg      = sum(s.mem  for s in idle_samples) / len(idle_samples)
        idle_pids_avg     = sum(s.pids for s in idle_samples) / len(idle_samples)
        idle_window_sec   = idle_samples[-1].ts - idle_samples[0].ts
    else:
        idle_cpu_avg = idle_mem_avg = idle_pids_avg = idle_window_sec = None

    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    annot_js = "null"
    if ingestion_end_idx is not None:
        annot_js = (
            "{"
            f"type:'line',xMin:{ingestion_end_idx},xMax:{ingestion_end_idx},"
            "borderColor:'rgba(248,113,113,0.9)',borderWidth:2,borderDash:[6,3],"
            "label:{"
            "display:true,content:'Ingestion complete',position:'start',"
            "color:'#f87171',backgroundColor:'rgba(13,17,23,0.85)',padding:4,font:{size:11}"
            "}}"
        )

    L  = json.dumps(ts_labels)
    CD = json.dumps(cpu_data)
    MD = json.dumps(mem_data)
    PD = json.dumps(pids_data)
    DD = json.dumps(db_mem_data) if tracking_db else "[]"
    TD = json.dumps(total_mem_data) if tracking_db else "[]"

    idle_cpu_card = (
        '    <div class="card idle"><div class="lbl">Idle CPU (avg)</div>'
        '<div class="val idle">' + f"{idle_cpu_avg:.1f}%" + "</div>"
        '<div class="sub">avg over ' + f"{int(idle_window_sec)}s post-ingestion</div></div>\n"
    ) if idle_cpu_avg is not None else (
        '    <div class="card"><div class="lbl">Idle CPU (avg)</div>'
        '<div class="val">N/A</div>'
        '<div class="sub">no post-ingestion data</div></div>\n'
    )
    idle_mem_card = (
        '    <div class="card idle"><div class="lbl">Idle RAM (avg)</div>'
        '<div class="val idle">' + _fmb(idle_mem_avg) + "</div>"
        '<div class="sub">avg over ' + f"{int(idle_window_sec)}s post-ingestion</div></div>\n"
    ) if idle_mem_avg is not None else (
        '    <div class="card"><div class="lbl">Idle RAM (avg)</div>'
        '<div class="val">N/A</div>'
        '<div class="sub">no post-ingestion data</div></div>\n'
    )
    idle_table_rows = (
        "      <tr class=\"idle-row\"><td>Idle CPU (avg post-ingest)</td>"
        '<td colspan="3">' + f"{idle_cpu_avg:.1f}%" + "</td></tr>\n"
        "      <tr class=\"idle-row\"><td>Idle RAM (avg post-ingest)</td>"
        '<td colspan="3">' + _fmb(idle_mem_avg) + "</td></tr>\n"
        "      <tr class=\"idle-row\"><td>Idle PIDs (avg post-ingest)</td>"
        '<td colspan="3">' + f"{idle_pids_avg:.0f}" + "</td></tr>\n"
    ) if idle_cpu_avg is not None else (
        "      <tr><td>Idle metrics</td>"
        '<td colspan="3"><em>N/A - no post-ingestion window recorded</em></td></tr>\n'
    )

    books_suffix  = f" - {books} books" if books else ""
    books_meta    = f" &nbsp;|&nbsp;\n    Books: <strong>{books}</strong>" if books else ""
    books_card    = (
        '    <div class="card"><div class="lbl">Books Ingested</div>'
        + '<div class="val">' + books + "</div>"
        + '<div class="sub">library size for this run</div></div>\n'
    ) if books else ""

    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "  <title>Benchmark: " + label + books_suffix + "</title>\n"
        '  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>\n'
        '  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>\n'
        "  <style>\n"
        "    *,*::before,*::after{box-sizing:border-box}\n"
        "    body{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:2rem}\n"
        "    h1{color:#58a6ff;font-size:1.5rem;margin:0 0 .25rem}\n"
        "    .meta{color:#8b949e;font-size:.85rem;margin-bottom:2rem}\n"
        "    code{background:#161b22;padding:.15em .4em;border-radius:4px;font-size:.9em}\n"
        "    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}\n"
        "    .card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem}\n"
        "    .card.idle{border-color:#388bfd44}\n"
        "    .lbl{font-size:.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:.06em}\n"
        "    .val{font-size:1.4rem;font-weight:700;color:#58a6ff;margin:.25rem 0 .1rem}\n"
        "    .val.idle{color:#388bfd}\n"
        "    .sub{font-size:.75rem;color:#6e7681}\n"
        "    .charts{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:2rem}\n"
        "    .cb{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.25rem}\n"
        "    .cb h3{margin:0 0 1rem;font-size:.9rem;color:#c9d1d9}\n"
        "    canvas{max-height:260px}\n"
        "    table{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden}\n"
        "    th,td{padding:.7rem 1rem;text-align:left;border-bottom:1px solid #21262d;font-size:.85rem}\n"
        "    th{color:#8b949e;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;background:#0d1117}\n"
        "    tr.idle-row td{color:#388bfd}\n"
        "    tr:last-child td{border-bottom:none}\n"
        "    @media(max-width:640px){.charts{grid-template-columns:1fr}}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Benchmark: " + label + books_suffix + "</h1>\n"
        '  <div class="meta">\n'
        "    Container: <code>" + container + "</code> &nbsp;|&nbsp;\n"
        "    " + run_ts + " &nbsp;|&nbsp;\n"
        "    " + str(len(samples)) + " samples @ " + str(interval) + "s"
        + books_meta + "\n"
        "  </div>\n"
        '  <div class="cards">\n'
        + books_card
        + '    <div class="card"><div class="lbl">Ingestion Time</div>'
            '<div class="val">' + _dur(ingest_sec) + "</div>"
            '<div class="sub">first sample to idle</div></div>\n'
        '    <div class="card"><div class="lbl">CPU Peak</div>'
            '<div class="val">' + f"{cpu_max:.1f}%" + "</div>"
            '<div class="sub">avg ' + f"{cpu_avg:.1f}%" + " &nbsp; min " + f"{cpu_min:.1f}%" + "</div></div>\n"
        + (
            '    <div class="card"><div class="lbl">RAM Peak (app)</div>'
            '<div class="val">' + _fmb(mem_max) + "</div>"
            '<div class="sub">avg ' + _fmb(mem_avg) + " &nbsp; min " + _fmb(mem_min) + "</div></div>\n"
            '    <div class="card"><div class="lbl">RAM Peak (db)</div>'
            '<div class="val">' + _fmb(db_mem_max) + "</div>"
            '<div class="sub">avg ' + _fmb(db_mem_avg) + " &nbsp; db: " + db_container + "</div></div>\n"
            '    <div class="card"><div class="lbl">RAM Peak (total)</div>'
            '<div class="val">' + _fmb(mem_max + db_mem_max) + "</div>"
            '<div class="sub">app + db combined</div></div>\n'
            if tracking_db else
            '    <div class="card"><div class="lbl">RAM Peak</div>'
            '<div class="val">' + _fmb(mem_max) + "</div>"
            '<div class="sub">avg ' + _fmb(mem_avg) + " &nbsp; min " + _fmb(mem_min) + "</div></div>\n"
        )
        + '    <div class="card"><div class="lbl">Peak PIDs</div>'
            '<div class="val">' + str(pid_max) + "</div>"
            '<div class="sub">max threads/processes</div></div>\n'
        + idle_cpu_card
        + idle_mem_card
        + "  </div>\n\n"
        '  <div class="charts">\n'
        '    <div class="cb"><h3>CPU Usage (%)</h3><canvas id="c1"></canvas></div>\n'
        '    <div class="cb"><h3>RAM Usage (MB)</h3><canvas id="c2"></canvas></div>\n'
        '    <div class="cb"><h3>Process / Thread Count (PIDs)</h3><canvas id="c3"></canvas></div>\n'
        "  </div>\n\n"
        "  <table>\n"
        "    <thead><tr><th>Metric</th><th>Min</th><th>Max</th><th>Avg</th></tr></thead>\n"
        "    <tbody>\n"
        "      <tr><td>CPU %</td>"
            "<td>" + f"{cpu_min:.1f}%" + "</td>"
            "<td>" + f"{cpu_max:.1f}%" + "</td>"
            "<td>" + f"{cpu_avg:.1f}%" + "</td></tr>\n"
        + (
            "      <tr><td>RAM (app)</td>"
            "<td>" + _fmb(mem_min) + "</td>"
            "<td>" + _fmb(mem_max) + "</td>"
            "<td>" + _fmb(mem_avg) + "</td></tr>\n"
            "      <tr><td>RAM (db: " + db_container + ")</td>"
            '<td>-</td>'
            "<td>" + _fmb(db_mem_max) + "</td>"
            "<td>" + _fmb(db_mem_avg) + "</td></tr>\n"
            "      <tr><td><strong>RAM (total)</strong></td>"
            '<td>-</td>'
            "<td><strong>" + _fmb(mem_max + db_mem_max) + "</strong></td>"
            "<td>" + _fmb(mem_avg + db_mem_avg) + "</td></tr>\n"
            if tracking_db else
            "      <tr><td>RAM</td>"
            "<td>" + _fmb(mem_min) + "</td>"
            "<td>" + _fmb(mem_max) + "</td>"
            "<td>" + _fmb(mem_avg) + "</td></tr>\n"
        )
        + "      <tr><td>PIDs</td>"
            '<td colspan="2"></td>'
            "<td>" + str(pid_max) + " peak</td></tr>\n"
        + idle_table_rows
        + "      <tr><td>Ingestion duration</td>"
            '<td colspan="3"><strong>' + _dur(ingest_sec) + "</strong></td></tr>\n"
        "      <tr><td>Total recording</td>"
            '<td colspan="3">' + _dur(total_sec) + "</td></tr>\n"
        "    </tbody>\n"
        "  </table>\n\n"
        "  <script>\n"
        "    const labels = " + L + ";\n"
        "    const annot  = " + annot_js + ";\n"
        "    const annotations = annot ? { ingestionEnd: annot } : {};\n"
        "    const sharedOpts = {\n"
        "      responsive:true, maintainAspectRatio:true, animation:false,\n"
        "      plugins:{ legend:{display:false}, annotation:{annotations} },\n"
        "      scales:{\n"
        "        x:{ ticks:{color:'#6e7681',maxTicksLimit:8,font:{size:11}}, grid:{color:'#21262d'} },\n"
        "        y:{ ticks:{color:'#6e7681',font:{size:11}}, grid:{color:'#21262d'} }\n"
        "      }\n"
        "    };\n"
        "    function mkChart(id, data, color) {\n"
        "      return new Chart(document.getElementById(id), {\n"
        "        type: 'line',\n"
        "        data: { labels, datasets:[{ data, borderColor:color,\n"
        "          backgroundColor:color+'1a', fill:true, tension:0.3,\n"
        "          pointRadius:0, borderWidth:1.5 }] },\n"
        "        options: sharedOpts\n"
        "      });\n"
        "    }\n"
        "    mkChart('c1', " + CD + ", '#58a6ff');\n"
        + (
            "    new Chart(document.getElementById('c2'), {\n"
            "      type:'line',\n"
            "      data:{ labels, datasets:[\n"
            "        { label:'App RAM', data:" + MD + ", borderColor:'#a371f7', backgroundColor:'#a371f71a', fill:true, tension:0.3, pointRadius:0, borderWidth:1.5 },\n"
            "        { label:'DB RAM (" + db_container + ")', data:" + DD + ", borderColor:'#f0883e', backgroundColor:'#f0883e1a', fill:true, tension:0.3, pointRadius:0, borderWidth:1.5 },\n"
            "        { label:'Total RAM', data:" + TD + ", borderColor:'#ff7b72', backgroundColor:'transparent', fill:false, tension:0.3, pointRadius:0, borderWidth:2, borderDash:[4,2] }\n"
            "      ]},\n"
            "      options:{ ...sharedOpts, plugins:{ ...sharedOpts.plugins, legend:{ display:true, labels:{ color:'#8b949e', font:{size:11} } } } }\n"
            "    });\n"
            if tracking_db else
            "    mkChart('c2', " + MD + ", '#a371f7');\n"
        )
        + "    mkChart('c3', " + PD + ", '#3fb950');\n"
        + "  </script>\n"
        "</body>\n"
        "</html>\n"
    )

    path.write_text(html)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor a Docker container during ingestion and generate a benchmark report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 monitor.py grimmory_loadtest --label \"Grimmory v3.1.0\" --books 50K --db-container grimmory_mariadb_loadtest\n"
            "  python3 monitor.py bookorbit_loadtest --label \"Bookorbit v1.4.0\" --books 150K --db-container bookorbit_db_loadtest\n"
            "  python3 monitor.py kavita_loadtest --label \"Kavita v0.9.0.2\" --books 100K --interval 2\n"
            "  python3 monitor.py komga_loadtest --label \"Komga v1.24.4\" --books 50K --idle-threshold 3\n"
            "  python3 monitor.py tome_loadtest --label \"Tome v1.3.2\" --books 50K\n"
            "\n"
            "Requires: pip install rich (gracefully falls back to plain text if missing)\n"
        ),
    )
    parser.add_argument("container",         help="Docker container name to monitor")
    parser.add_argument("--label",           default="",    help="Human-readable label for the report")
    parser.add_argument("--books",           default="",    help="Book count label shown in report and live display (e.g. 50K, 100K)")
    parser.add_argument("--db-container",    default="",    help="Optional DB sidecar container to track RAM (e.g. postgres, mariadb)")
    parser.add_argument("--interval",        type=float, default=5.0,  help="Sampling interval in seconds (default: 5)")
    parser.add_argument("--idle-threshold",  type=float, default=5.0,  help="CPU%% below this = idle (default: 5.0)")
    parser.add_argument("--idle-duration",   type=float, default=60.0, help="Seconds at idle before auto-stop (default: 60)")
    parser.add_argument("--idle-window",     type=float, default=120.0, help="Seconds to record after ingestion completes for idle baseline (default: 120)")
    parser.add_argument("--min-duration",    type=float, default=30.0, help="Min recording time before auto-stop (default: 30)")
    parser.add_argument("--no-autostop",     action="store_true",      help="Disable auto-stop; run until Ctrl+C")
    args = parser.parse_args()

    container     = args.container
    label         = args.label or container
    books         = args.books
    db_container  = args.db_container
    interval      = args.interval
    idle_threshold = args.idle_threshold
    idle_duration  = args.idle_duration
    idle_window    = args.idle_window
    min_duration   = args.min_duration
    autostop       = not args.no_autostop

    # Verify container exists and is running
    check = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container],
        capture_output=True, text=True,
    )
    if check.returncode != 0 or check.stdout.strip() != "true":
        print(f"Error: container '{container}' is not running.")
        print("Run:  docker ps  to see running containers.")
        sys.exit(1)

    if db_container:
        db_check = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", db_container],
            capture_output=True, text=True,
        )
        if db_check.returncode != 0 or db_check.stdout.strip() != "true":
            print(f"Error: db container '{db_container}' is not running.")
            print("Run:  docker ps  to see running containers.")
            sys.exit(1)
        print(f"DB RAM tracking enabled: {db_container}")

    if not RICH:
        print("Tip: run  pip install rich  for a live dashboard display.")

    # Set up output directory
    run_ts  = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    folder_name = f"{run_ts}_{books}" if books else run_ts
    run_dir = REPORTS_DIR / container / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)

    samples: list[Sample]   = []
    ingestion_end_idx: Optional[int] = None
    idle_since:   Optional[float]    = None
    settle_start: Optional[float]    = None
    stop_requested = False

    def _handle_signal(sig, frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    def _status_and_countdown() -> tuple[str, Optional[int]]:
        if not samples:
            return "STARTING", None
        if settle_start is not None:
            remaining = int(idle_window - (time.time() - settle_start))
            return ("SETTLING", max(0, remaining)) if remaining > 0 else ("DONE", None)
        if ingestion_end_idx is not None:
            return "DONE", None
        elapsed = samples[-1].ts - samples[0].ts
        if not autostop or elapsed < min_duration:
            return "ACTIVE", None
        if idle_since is None:
            return "ACTIVE", None
        remaining = int(idle_duration - (time.time() - idle_since))
        return ("IDLE", max(0, remaining)) if remaining > 0 else ("IDLE", 0)

    def _check_autostop() -> bool:
        nonlocal idle_since, ingestion_end_idx, settle_start
        # Phase 2: settling window has elapsed
        if settle_start is not None:
            return (time.time() - settle_start) >= idle_window
        if not autostop or not samples:
            return False
        elapsed = samples[-1].ts - samples[0].ts
        if elapsed < min_duration:
            return False
        last_cpu = samples[-1].cpu
        if last_cpu < idle_threshold:
            if idle_since is None:
                idle_since = time.time()
        else:
            idle_since = None
        # Phase 1: ingestion idle detected - begin settling window
        if idle_since is not None and (time.time() - idle_since) >= idle_duration:
            ingestion_end_idx = len(samples) - 1
            settle_start = time.time()
        return False

    # --- Collection loop ---

    if RICH:
        console = Console()
        books_display = f"  |  Books: [yellow]{books}[/]" if books else ""
        console.print(f"\n[bold cyan]Starting monitor:[/] [yellow]{container}[/]{books_display}")
        console.print(f"[dim]Label: {label}  |  Interval: {interval}s  |  "
                      f"Auto-stop: {'CPU < ' + str(idle_threshold) + '% for ' + str(int(idle_duration)) + 's, then ' + str(int(idle_window)) + 's idle window' if autostop else 'disabled (Ctrl+C to stop)'}[/]")
        console.print(f"[dim]Report will be saved to: {run_dir}[/]")
        console.print(f"[dim]Press Ctrl+C to stop recording at any time.\n[/]")

        with Live(console=console, refresh_per_second=2, screen=False) as live:
            while not stop_requested:
                s = poll(container)
                if s:
                    if db_container:
                        s.db_mem = poll_mem(db_container)
                    samples.append(s)
                if _check_autostop():
                    live.update(build_table(samples, container, label, books, "DONE", None, db_container))
                    time.sleep(0.3)
                    break
                status, countdown = _status_and_countdown()
                if samples:
                    live.update(build_table(samples, container, label, books, status, countdown, db_container))
                time.sleep(interval)
    else:
        print(f"Monitoring {container} ({label})... Ctrl+C to stop.")
        while not stop_requested:
            s = poll(container)
            if s:
                if db_container:
                    s.db_mem = poll_mem(db_container)
                samples.append(s)
                elapsed = s.ts - samples[0].ts if len(samples) > 1 else 0.0
                db_suffix = f"  DB RAM: {_fmb(s.db_mem)}" if db_container else ""
                print(f"[{_dur(elapsed)}]  CPU: {s.cpu:.1f}%  RAM: {_fmb(s.mem)}{db_suffix}")
            if _check_autostop():
                print("\nIngestion complete. Recording idle window...")
                break
            time.sleep(interval)

    # --- Output ---

    if not samples:
        print("No samples collected. Exiting.")
        sys.exit(1)

    if RICH:
        console.print("\n[bold green]Recording stopped.[/] Generating report...")
    else:
        print("\nRecording stopped. Generating report...")

    csv_path  = run_dir / "data.csv"
    html_path = run_dir / "report.html"

    write_csv(samples, csv_path)
    write_html(samples, container, label, books, interval, ingestion_end_idx, html_path, db_container)

    total_sec = samples[-1].ts - samples[0].ts if len(samples) > 1 else 0.0

    print()
    print("=" * 60)
    print(f"  Report : {html_path}")
    print(f"  CSV    : {csv_path}")
    print(f"  Samples: {len(samples)}  ({_dur(total_sec)} recorded)")
    print("=" * 60)
    print(f"\n  Open:  open \"{html_path}\"")
    print()


if __name__ == "__main__":
    main()
