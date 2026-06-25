# Performance Analysis

## Observations

**Bookorbit** is the fastest at every tested size. Throughput improves as library size increases (65 bk/s at 10K, 110 bk/s at 150K). Idle RAM is reasonable (285-524 MB including PostgreSQL) and grows slowly, but Bookorbit is not the outright lightest on RAM - Kavita beats it at 100K and Stump beats it at 10K. It requires running a PostgreSQL sidecar, which adds complexity and ~160 MB of permanent overhead.

**Kavita** is the second fastest and has some surprising efficiency. At 100K it uses only 336 MB idle RAM (lower than Bookorbit at 472 MB) and 542 MB peak. It stays within 7 seconds of Bookorbit at 50K. At 150K idle RAM jumps to ~1 GB. Handles books and comics/manga in a single app.

**Stump** has the lowest RAM footprint at 10K (209 MB idle, 243 MB peak) and is fast at that scale (3:08). Beyond 50K it collapses: 100K takes 1h 51m and idle RAM hits 1.16 GB. Only viable for small libraries.

**Audiobookshelf** shines in RAM efficiency for smaller libraries, using a highly impressive 125 MB idle at 10K. Ingestion speed is moderate initially (5 minutes for 10K) but degrades significantly at extreme scales, taking nearly 5 hours for 150K. A great choice for its audio features if your ebook library size is modest.

**Tome** performs reasonably well at 10K (4:28) and maintains a low 190 MB idle RAM footprint. However, it struggles severely with large datasets: 100K books takes over 6 hours to ingest, and idle RAM climbs to 1.47 GB. Best suited for smaller collections.

**Grimmory** uses significantly more RAM than the others - 2.45 GB peak at 10K, rising to 4.91 GB at 150K (including MariaDB). This is 5-9x more peak RAM than Kavita. Ingestion is slower than Bookorbit and Kavita at all tested sizes, and throughput degrades at scale. On resource-constrained hardware this is a hard blocker. On capable hardware (8+ GB available), resource usage is less of a concern and Grimmory may offer features or a UI that suit some users better - this benchmark does not evaluate that.

**Komga** (JVM) has a hard floor around 1.16 GB RAM even for 10K books. Ingestion of 10K takes 12 minutes (14 bk/s). At 50K it ran for over 1h 51m without finishing. On a resource-constrained machine this rules it out. Komga is widely used for comics/manga and has a mature feature set and active community - if features matter more than ingestion performance and you have enough RAM, it remains a legitimate choice.

**Calibre-Web-Automated** ingestion is not competitive at scale - 1,100 books in 91 minutes for a 10K set. For users who have small libraries or are already invested in Calibre's ecosystem (metadata tools, conversion, format management), it may still make sense. This benchmark only covers ingestion speed.

---

## Recommendations by Use Case

### Low-end hardware (1-2 GB RAM total) - Raspberry Pi, older SBC, NAS with limited RAM

**Bookorbit** for libraries over ~100K, or when ingestion speed is the priority. At 100K and 150K it has lower idle RAM than every other app (472 MB and 524 MB respectively). Throughput scales up with library size so large imports finish faster. It requires a PostgreSQL sidecar, which adds complexity and ~160 MB of footprint - at 10K and 50K that overhead means Bookorbit is marginally heavier than Kavita, so for smaller libraries Kavita is the leaner single-container pick.

**Audiobookshelf** and **Tome** are incredibly light at 10K (125 MB and 190 MB idle respectively), making them excellent single-container choices for very small libraries. Avoid both at 50K+, as their RAM footprints swell rapidly.

**Stump** is also very light at 10K (209 MB) and is a simpler single-container setup. Fine for small, stable libraries that won't grow past ~20K. Avoid it at 100K+ (idle RAM hits 1.16 GB).

**Kavita** is the lightest single-container option for libraries up to ~100K. At 100K it uses only 336 MB idle - less than Bookorbit's 472 MB (which includes PostgreSQL). At 10K and 50K it is also light (315/437 MB), though Bookorbit edges it out slightly there. At 150K Kavita's idle RAM jumps to 1.02 GB, so for libraries that size Bookorbit becomes the better fit on constrained hardware.

Avoid Grimmory (738 MB idle even at 10K) and Komga (1.16 GB floor at 10K).

### Mid-range server (4-8 GB RAM, 4+ cores) - home server, VPS, Synology NAS

**Bookorbit or Kavita** - both work well across all tested scales. Bookorbit is faster; Kavita uses less peak RAM and requires no database sidecar.

If comic/manga support matters, Kavita handles both in one app.

### Large library (50K-100K books)

Speed: **Bookorbit** (16:16 at 100K vs Kavita's 18:57).
RAM: **Kavita** (542 MB peak, 336 MB idle vs Bookorbit's 758 MB peak, 472 MB idle at 100K).

Both are strong choices. Pick based on whether speed or lower memory pressure matters more for your setup.

### Very large library (150K+ books, extrapolating)

**Bookorbit** - fastest (22:48 vs Kavita's 26:02) and lower idle RAM at 150K (524 MB vs 1.02 GB). Its throughput scales up with library size; Kavita and Grimmory plateau or degrade.

### Speed priority - initial import time matters most

**Bookorbit** across all sizes. The differences are large enough to matter at scale (Grimmory takes 1h 29m for 150K vs Bookorbit's 22:48).

### Low-power always-on device (idle CPU matters)

All apps have negligible idle CPU (under 2.5%). This does not meaningfully differentiate them at rest.

For idle RAM: **Stump** (small libraries) or **Kavita** (mid-to-large libraries) are the lightest single-container options.

### Comic and manga focus

**Kavita** - solid performance, decent RAM, supports books and comics/manga in one app. **Komga** is well-established in the comic community with a mature UI and active development - if you have sufficient RAM (2+ GB available for the container) and primarily care about the reading/browsing experience over ingestion speed, it is worth evaluating on those merits.

### Setup simplicity (no database sidecar)

**Kavita** or **Stump** - single container, drop-in. Bookorbit and Grimmory both require a separate database container.

### NAS deployment (Synology, QNAP, TrueNAS)

**Stump** for libraries under 20K. **Kavita** for libraries 20K-100K. **Bookorbit** if the speed advantage justifies running a PostgreSQL container alongside.

---

## Hardware Requirements (minimum practical)

Peak RAM required during ingestion (app + DB, rounded up). **Min CPUs** is based on peak CPU observed across all runs (100% = 1 core).

| App | Min CPUs | 10K | 50K | 100K | 150K |
|-----|----------|-----|-----|------|------|
| Stump | 2 | 250 MB | 450 MB | 1.2 GB | - |
| Kavita | 2 | 350 MB | 450 MB | 550 MB | 1.1 GB |
| Bookorbit | 2 | 450 MB | 700 MB | 800 MB | 850 MB |
| Audiobookshelf | 2 | 300 MB | 850 MB | 1.5 GB | 2.2 GB |
| Tome | 2 | 250 MB | 1.2 GB | 1.6 GB | - |
| Komga | 3 | 1.2 GB | 2.6 GB | - | - |
| Grimmory | 4 | 2.5 GB | 3.1 GB | 4.0 GB | 5.0 GB |
| Calibre-Web-Automated | 3 | n/a | - | - | - |

After ingestion, Bookorbit and Kavita release a significant portion of that RAM back - see the Idle RAM table in Raw Numbers for steady-state figures.

---

## Summary

| App       | Fastest ingestion | Lowest idle RAM (total) | Practical ceiling |
|-----------|-------------------|------------------------|-------------------|
| Bookorbit | Yes (all sizes)   | At 50K and 150K        | 150K+ (scales well) |
| Kavita    | Second (close)    | At 10K-100K            | 150K (RAM grows at 150K) |
| Audiobookshelf | No | At 10K only (125 MB) | ~50K (slows down drastically beyond) |
| Tome      | No                | At 10K only (190 MB)   | ~10K (degrades sharply beyond) |
| Stump     | At 10K only       | No                     | ~20K (degrades beyond) |
| Grimmory  | No                | No                     | Resource-heavy; evaluate on features if hardware allows |
| Komga     | No                | No                     | Mature comic/manga app; evaluate on features if RAM allows |

Bookorbit wins on raw ingestion speed at every size. Kavita wins on RAM efficiency at small-to-mid scale and requires no database sidecar. For most users with libraries under 100K books, Kavita is a strong pick on performance grounds; Bookorbit becomes the clearer choice above 100K or when ingestion speed is the priority. Audiobookshelf and Tome are highly efficient for small libraries (~10K) but their speed and RAM footprint degrade sharply beyond that. Grimmory, Komga, and Calibre-Web-Automated may offer features, UIs, or ecosystem integrations that outweigh their performance numbers for the right user - this benchmark cannot speak to that.
