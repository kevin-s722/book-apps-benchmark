# Raw Numbers

### Ingestion Time

| App           | 10K    | 50K     | 100K    | 150K    |
|---------------|--------|---------|---------|---------|
| Bookorbit     | 2:33   | 8:44    | 16:16   | 22:48   |
| Kavita        | 3:37   | 8:51    | 18:57   | 26:02   |
| Stump         | 3:08   | 28:59   | 1h 51m  | -       |
| Grimmory      | 4:51   | 16:41   | 48:50   | 1h 29m  |
| Komga         | 12:04  | 1h 51m* | -       | -       |
| Calibre-Web-Automated | ~91 min (1,100/10K)** | - | - | - |
| Audiobookshelf| 5:00   | 36:43   | 1h 56m  | 4h 49m  |
| Tome          | 4:28   | 1h 12m  | 6h 11m  | -       |


\* Komga 50K was stopped at 1h 51m with unknown books remaining; not run beyond 50K.
\*\* Calibre-Web-Automated processed only 1,100 out of 10,000 books in 91 minutes. Test was stopped. At that rate, 10K alone would take ~14 hours. No further tests were run.

### Throughput (books ingested per second)

| App       | 10K   | 50K   | 100K  | 150K  |
|-----------|-------|-------|-------|-------|
| Bookorbit     | 65    | 95    | 102   | 110   |
| Kavita        | 46    | 94    | 88    | 96    |
| Stump         | 53    | 29    | 15    | -     |
| Grimmory      | 34    | 50    | 34    | 28    |
| Komga         | 14    | ~7    | -     | -     |
| Audiobookshelf| 33    | 23    | 14    | 9     |
| Tome          | 37    | 12    | 4     | -     |

Bookorbit throughput increases with library size (batch efficiency). Stump degrades sharply beyond 10K. Grimmory plateaus around 30-50 bk/s regardless of size.

### Idle RAM - app + DB (steady state after ingestion)

This is what the stack uses while just running - the number that matters for always-on deployments.

| App       | 10K    | 50K    | 100K   | 150K   |
|-----------|--------|--------|--------|--------|
| Stump         | 209 MB | 448 MB | 1.16 GB | -     |
| Bookorbit     | 285 MB | 415 MB | 472 MB | 524 MB |
| Kavita        | 315 MB | 437 MB | 336 MB | 1.02 GB |
| Grimmory      | 738 MB | 1.08 GB | 1.50 GB | 1.94 GB |
| Komga         | 1.16 GB | -     | -      | -      |
| Audiobookshelf| 125 MB | 492 MB | 865 MB | 666 MB |
| Tome          | 190 MB | 749 MB | 1.47 GB | -     |

Kavita's 100K idle RAM (336 MB) is lower than Bookorbit's (472 MB) - at that scale the PostgreSQL sidecar's ~160 MB footprint outweighs Bookorbit's lighter app process. At 10K and 50K the picture reverses: Bookorbit's app is lean enough that the total (285/415 MB) stays below Kavita (315/437 MB). At 150K it reverses again: Bookorbit holds at 524 MB while Kavita jumps to 1.02 GB.

### RAM Peak - app + DB (during ingestion)

| App       | 10K    | 50K    | 100K   | 150K   |
|-----------|--------|--------|--------|--------|
| Stump         | 243 MB | 449 MB | 1.16 GB | -     |
| Kavita        | 319 MB | 448 MB | 542 MB | 1.03 GB |
| Bookorbit     | 438 MB | 675 MB | 758 MB | 827 MB |
| Komga         | 1.17 GB | 2.58 GB | -     | -      |
| Grimmory      | 2.45 GB | 3.08 GB | 3.94 GB | 4.91 GB |
| Audiobookshelf| 292 MB | 807 MB | 1.47 GB | 2.13 GB |
| Tome          | 216 MB | 1.18 GB | 1.51 GB | -     |

Kavita has lower RAM peak than Bookorbit at 10K-100K (the PostgreSQL sidecar adds 120-230 MB during ingestion at those sizes). At 150K the pattern reverses: Bookorbit peaks at 827 MB while Kavita jumps to 1.03 GB. Grimmory peaks near 5 GB at 150K; on a 4 GB machine it would OOM.

### CPU (average during ingestion)

| App       | 10K  | 50K  | 100K | 150K |
|-----------|------|------|------|------|
| Bookorbit     | 26%  | 52%  | 62%  | 65%  |
| Stump         | 28%  | 78%  | 91%  | -    |
| Kavita        | 32%  | 60%  | 74%  | 78%  |
| Grimmory      | 33%  | 31%  | 20%  | 17%  |
| Komga         | 78%  | 95%  | -    | -    |
| Audiobookshelf| 35%  | 75%  | 86%  | 87%  |
| Tome          | 41%  | 93%  | 98%  | -    |

Grimmory's CPU drops at large sizes while taking much longer - it is I/O-bound or not parallelizing effectively. Komga saturates CPU at 78-95% and is still slow.
