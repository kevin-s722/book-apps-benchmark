# Running Your Own Benchmark


### Prerequisites

- Docker Desktop (or Docker Engine)
- Python 3.10+
- Internet access (unless you provide a local Chart.js file with `--chartjs-file`)
- ~40 MB free disk space per 10K EPUBs (the generated EPUBs are ~1.8 KB each)

### Quick smoke test

Before long benchmark runs, validate the environment and scripts:

```bash
cd scripts
./smoke_test.sh
```

### Step 1 - Set up Docker

Each app has a `docker-compose.yml` in `docker/<app>/`. Configure any required credentials or first-run setup yourself - default dev-mode settings were used in the reference runs.

Book volumes are pre-configured with `../../books` as the host source. The container-side mount point varies per app - check the "Library path in container" column in the Apps Tested table above for the path to use when creating a library in each app's UI.

### Step 2 - Generate test books

```bash
cd scripts

# Generate 10,000 EPUBs
python3 generate_books.py 10000
# Output: books/books_10K/  (~40 MB)

# Generate more counts as needed
python3 generate_books.py 50000
python3 generate_books.py 100000
python3 generate_books.py 150000
```

Generation is parallel and typically takes a few minutes per count on modern hardware.

### Step 3 - Run a benchmark (repeat for each app and book count)

Keep things fair: **stop all other app containers before starting the one you are testing.**

**Main terminal:**

```bash
# Example: benchmark Kavita with 10K books

# 0. Stop only benchmark stacks (safe: does not touch unrelated containers)
for app in bookorbit grimmory kavita komga stump calibre-web-automated tome audiobookshelf; do
  docker compose -f "docker/$app/docker-compose.yml" down -v --remove-orphans 2>/dev/null || true
done

# 1. Start only the app under test (run from repo root)
cd docker/kavita
docker compose up -d
cd ../..

# 2. Log in to the app, then create a new library pointing to /books/books_10K
#    Do NOT save/confirm the library yet.
```

**Separate terminal - start the monitor BEFORE triggering the scan:**

```bash
cd scripts
python3 monitor.py kavita_loadtest \
  --label "Kavita v0.9.0.2" \
  --books 10K
```

**Back in the main terminal:**

```bash
# 4. Save/confirm the library in the app UI to trigger the scan.
#    The monitor samples approximately every 5 seconds and stops
#    automatically once idle. Run with --help to see all stop criteria.

# 5. After the monitor finishes it writes:
#      results/kavita_loadtest/<timestamp>_10K/data.csv
#      results/kavita_loadtest/<timestamp>_10K/report.html

# 6. Delete the library in the app, then stop the containers (from repo root)
docker compose -f docker/kavita/docker-compose.yml down -v
```

Repeat steps 0-6 for each book count (10K, 50K, 100K, 150K) and for each app.

### Monitor commands for all apps

```bash
cd scripts

# Grimmory (has DB container)
python3 monitor.py grimmory_loadtest \
  --label "Grimmory v3.1.0" --books 10K \
  --db-container grimmory_mariadb_loadtest

# Kavita
python3 monitor.py kavita_loadtest \
  --label "Kavita v0.9.0.2" --books 10K

# Komga
python3 monitor.py komga_loadtest \
  --label "Komga v1.24.4" --books 10K

# Stump
python3 monitor.py stump_loadtest \
  --label "Stump v0.1.3" --books 10K

# Calibre-Web-Automated
python3 monitor.py calibre_web_automated_loadtest \
  --label "Calibre-Web-Automated v4.0.6" --books 10K

# Bookorbit (has DB container)
python3 monitor.py bookorbit_loadtest \
  --label "Bookorbit v1.4.0" --books 10K \
  --db-container bookorbit_db_loadtest

# Tome
python3 monitor.py tome_loadtest \
  --label "Tome v1.3.2" --books 10K

# Audiobookshelf
python3 monitor.py audiobookshelf_loadtest \
  --label "Audiobookshelf v2.35.1" --books 10K
```

### Step 4 - Generate the comparison dashboard

Once you have results from multiple apps or counts:

```bash
cd scripts
python3 generate_comparison.py
# Output: results/comparison.html
```

Open `results/comparison.html` in a browser to see the cross-app comparison.

> To include the pre-run `reference/` data alongside your own runs, pass both dirs:
> `python3 generate_comparison.py --reports-dir ../results ../reference`

> If your Python environment cannot validate HTTPS certificates, do not disable TLS verification. Instead:
> 1) fix trust roots (for macOS python.org installs, run `Install Certificates.command`), or
> 2) pass a local Chart.js bundle:
> `python3 generate_comparison.py --reports-dir ../results ../reference --chartjs-file ./chart.umd.min.js`

> Note: Calibre-Web-Automated is always excluded from the comparison dashboard due to insufficient data. See the reference results section for details.

## Monitor script reference

Run `python3 monitor.py --help` for the full option list. Key options:

```
python3 monitor.py <container_name> [options]

Options:
  --label TEXT              Human-readable label for the run (e.g. "Kavita 0.9")
  --books TEXT              Book count label (e.g. 10K, 50K) used in the output path
  --db-container TEXT       Additional container to track for DB RAM usage
  --interval SECS           Sampling interval in seconds (default: 5)
  --idle-threshold PCT      CPU% below which the container is considered idle (default: 5.0)
  --idle-duration SECS      Seconds CPU must stay below threshold before auto-stop (default: 60)
  --idle-window SECS        Seconds recorded after ingestion completes (default: 120)
  --min-duration SECS       Minimum run time before auto-stop can trigger (default: 30)
  --no-autostop             Disable auto-stop; run until Ctrl+C
```
