#!/usr/bin/env python3
"""
Generate N minimal valid EPUB 2.0 files for load testing.

Usage:
  python3 generate_books.py <count>

Examples:
  python3 generate_books.py 10000    # creates books/books_10K/
  python3 generate_books.py 50000    # creates books/books_50K/
  python3 generate_books.py 150000   # creates books/books_150K/

Output folder is created at books/books_<N>/ relative to the repo root.
If <count> is a multiple of 1000, the folder uses K notation (e.g. books_10K).
"""
import os
import sys
import time
import zipfile
import random
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

BATCH_SIZE = 500
WORKERS = max(1, multiprocessing.cpu_count() - 1)

GENRES = [
    "Fiction", "Non-Fiction", "Science Fiction", "Fantasy", "Mystery",
    "Thriller", "Romance", "Horror", "Biography", "History", "Science",
    "Philosophy", "Poetry", "Drama", "Adventure", "Classic", "Children",
    "Self-Help", "Business", "Technology",
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Elizabeth", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Elena",
    "Marcus", "Aria", "Finn", "Lyra", "Sebastian", "Zoe", "Oliver", "Chloe",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Moore", "Young", "Hall", "Chen",
    "Nakamura", "Okonkwo", "Petrov", "Silva", "Mueller", "Dubois", "Rossi",
]

TITLE_WORDS = [
    "Shadow", "Light", "Dark", "Lost", "Hidden", "Broken", "Silent",
    "Ancient", "Last", "First", "Final", "Eternal", "Forgotten", "Sacred",
    "Iron", "Golden", "Silver", "Crystal", "Crimson", "Midnight", "Dawn",
    "Storm", "Fire", "Ice", "Wind", "Stone", "Blood", "Soul", "Heart",
    "Edge", "Fall", "Rise", "Path", "Gate", "City", "Kingdom", "Empire",
    "Order", "Chaos", "Truth", "Lies", "Dream", "Nightmare", "Time",
    "Space", "World", "Star", "Moon", "Sun", "Ocean", "Mountain", "Forest",
]

TITLE_NOUNS = [
    "of Destiny", "Chronicles", "Legacy", "Redemption", "Betrayal",
    "Ascension", "Reckoning", "Awakening", "Prophecy", "Covenant",
    "Protocol", "Paradox", "Equation", "Theorem", "Principle",
    "Manifesto", "Archive", "Codex", "Saga", "Anthology",
]


def rand_title(rng):
    return f"The {rng.choice(TITLE_WORDS)} {rng.choice(TITLE_NOUNS)}"


def rand_author(rng):
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def rand_isbn(rng):
    digits = [str(rng.randint(0, 9)) for _ in range(12)]
    s = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(digits))
    check = (10 - s % 10) % 10
    return "978" + "".join(digits[3:]) + str(check)


def make_epub(idx: int, seed: int, out_dir: Path) -> Path:
    rng = random.Random(seed)
    title = rand_title(rng)
    author = rand_author(rng)
    isbn = rand_isbn(rng)
    year = rng.randint(1900, 2025)
    genre = rng.choice(GENRES)
    uid = f"urn:uuid:loadtest-{idx:08d}"

    safe_title = "".join(c if c.isalnum() or c in "- " else "_" for c in title)
    safe_author = "".join(c if c.isalnum() or c in "- " else "_" for c in author)
    stem = f"{idx:08d}_{safe_author}_{safe_title}".replace(" ", "_")[:115]
    filename = stem + ".epub"
    book_dir = out_dir / stem
    book_dir.mkdir(exist_ok=True)
    out_path = book_dir / filename

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="bookid">{uid}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator opf:role="aut">{author}</dc:creator>
    <dc:date>{year}-01-01</dc:date>
    <dc:language>en</dc:language>
    <dc:subject>{genre}</dc:subject>
    <dc:description>A load-test dummy book: {title} by {author}. ISBN: {isbn}.</dc:description>
    <dc:publisher>LoadTest Press</dc:publisher>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="content" href="content.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="content"/>
  </spine>
</package>"""

    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel><text>Chapter 1</text></navLabel>
      <content src="content.html"/>
    </navPoint>
  </navMap>
</ncx>"""

    content_html = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p>By {author}</p>
<p>Published: {year} | Genre: {genre}</p>
<p>This is a load-test dummy EPUB. Book #{idx:,}.</p>
</body>
</html>"""

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        zf.writestr("OEBPS/content.html", content_html)

    return out_path


def generate_batch(args):
    start_idx, end_idx, base_seed, out_dir = args
    out_dir = Path(out_dir)
    generated = 0
    for i in range(start_idx, end_idx):
        make_epub(i, base_seed + i, out_dir)
        generated += 1
    return generated


def count_label(n: int) -> str:
    if n % 1000 == 0:
        return f"{n // 1000}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Generate N minimal valid EPUB 2.0 files for load testing.")
    parser.add_argument("count", type=int, help="Number of books to generate")
    parser.add_argument("--start-idx", type=int, default=0, help="Starting index for books")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory path")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip overwrite confirmation")
    args = parser.parse_args()

    count = args.count
    start_idx = args.start_idx

    if count <= 0:
        print("Error: count must be greater than 0")
        sys.exit(1)

    label = count_label(count)
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        repo_root = Path(__file__).parent.parent
        out_dir = repo_root / "books" / f"books_{label}"

    if out_dir.exists():
        existing = sum(1 for _ in out_dir.rglob("*.epub"))
        if existing > 0 and not args.yes:
            print(f"Directory already exists with {existing:,} EPUBs: {out_dir}")
            answer = input("Overwrite? [y/N] ").strip().lower()
            if answer != "y":
                print("Aborted.")
                sys.exit(0)

    out_dir.mkdir(parents=True, exist_ok=True)

    base_seed = 42
    batches = [
        (i, min(i + BATCH_SIZE, start_idx + count), base_seed, str(out_dir))
        for i in range(start_idx, start_idx + count, BATCH_SIZE)
    ]

    print(f"Generating {count:,} EPUBs -> {out_dir}")
    print(f"Workers: {WORKERS} | Batch size: {BATCH_SIZE} | Batches: {len(batches)}")

    start = time.time()
    total = 0
    last_report = start

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(generate_batch, b): b for b in batches}
        for future in as_completed(futures):
            n = future.result()
            total += n
            now = time.time()
            if now - last_report >= 5:
                elapsed = now - start
                rate = total / elapsed
                eta = (count - total) / rate if rate > 0 else 0
                print(
                    f"  Progress: {total:>8,}/{count:,}  "
                    f"({100*total/count:.1f}%)  "
                    f"{rate:.0f} epub/s  "
                    f"ETA: {eta:.0f}s"
                )
                last_report = now

    elapsed = time.time() - start
    size_bytes = sum(f.stat().st_size for f in out_dir.rglob("*.epub"))
    print(f"\nDone: {total:,} EPUBs in {elapsed:.1f}s ({total/elapsed:.0f} epub/s)")
    print(f"Output: {out_dir}")
    print(f"Total size: {size_bytes / 1024 / 1024:.1f} MB ({size_bytes / total / 1024:.1f} KB avg)")
    print(f"\nIn the app UI, create a library pointing to the mounted books folder:")
    print(f"  Most apps:     /books/books_{label}")
    print(f"  Komga / Stump: /data/books/books_{label}")


if __name__ == "__main__":
    main()
