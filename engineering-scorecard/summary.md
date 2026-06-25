# Engineering Scorecard - Repository Assessment Summary

**7 apps** assessed across **6 model configurations**, grouped into two providers:

- **ChatGPT:** ChatGPT 5.4 xhigh, ChatGPT 5.5 medium, ChatGPT 5.5 xhigh
- **Claude:** Claude Opus 4.6 high, Claude Opus 4.8 high, Claude Sonnet 4.6 high

Each model independently scored every repository on a 0-100 scale across 10 engineering categories. Naming convention: model files use `<brand>-<model>-<version>-<effort>` (e.g. `chatgpt-5.5-xhigh`, `claude-opus-4.8-high`); tables below use the compact column headers **ChatGPT 5.4x**, **ChatGPT 5.5m**, **ChatGPT 5.5x**, **Opus 4.6**, **Opus 4.8**, **Sonnet 4.6**.

Assessment was performed against the following image tags (~2 weeks prior to scoring):

| App | Image |
|---|---|
| bookorbit | `ghcr.io/bookorbit/bookorbit:v1.10.0` |
| komga | `ghcr.io/gotson/komga:1.24.4` |
| grimmory | `ghcr.io/grimmory-tools/grimmory:v3.2.0` |
| stump | `ghcr.io/aaronleopold/stump:v0.1.4` |
| kavita | `ghcr.io/kareadita/kavita:v0.9.0.2` |
| audiobookshelf | `ghcr.io/advplyr/audiobookshelf:v2.35.1` |
| calibre-web-automated | `ghcr.io/crocodilestick/calibre-web-automated:v4.0.6` |

An interactive version of these tables and charts is available in [comparison.html](comparison.html).

---

## Overall Scores

Ranked by the mean overall score across all six model configurations.

| Rank | App | Image Tag | Stack | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **bookorbit** | `v1.10.0` | NestJS + Vue 3 | 82 (B) | 84 (B) | 81 (B) | 82 (A) | **90 (A)** | 87 (A-) | **84.3** |
| 2 | **komga** | `1.24.4` | Kotlin + Spring + Vue 2 | 80 (B) | 82 (B) | 81 (B) | 80 (A-) | 88 (A) | 84 (B+) | **82.5** |
| 3 | **grimmory** | `v3.2.0` | Java 25 + Spring Boot 4 + Angular 21 | 78 (B) | 81 (B) | 82 (B) | 78 (B+) | 84 (A-) | 83 (B+) | **81.0** |
| 4 | **stump** | `v0.1.4` | Rust + React | 72 (C) | 76 (B) | 76 (B) | 72 (B) | 86 (A) | 80 (B+) | **77.0** |
| 5 | **kavita** | `v0.9.0.2` | C#/.NET 10 + Angular | 65 (C) | 78 (B) | 77 (B) | 65 (C+) | 84 (A-) | 82 (B+) | **75.2** |
| 6 | **audiobookshelf** | `v2.35.1` | Node.js + Nuxt 2 | 62 (D) | 75 (B) | 74 (B) | 62 (C+) | 76 (B) | 72 (B) | **70.2** |
| 7 | **calibre-web-automated** | `v4.0.6` | Python / Flask | 52 (D) | 74 (B) | 72 (C) | 52 (C) | 68 (C) | 52 (C) | **61.7** |

---

## Category Rankings (Avg Score)

Apps ranked #1-#7 per category by mean score across all six model configurations.

| Category | #1 | #2 | #3 | #4 | #5 | #6 | #7 |
|---|---|---|---|---|---|---|---|
| Architecture | komga 88.3 | bookorbit 86.8 | stump 84.2 | grimmory 82.7 | kavita 80.5 | audiobookshelf 73.0 | calibre 57.0 |
| Security | bookorbit 85.3 | komga 82.2 | grimmory 80.2 | stump 75.0 | kavita 75.0 | audiobookshelf 74.5 | calibre 59.8 |
| Maintainability | komga 82.3 | bookorbit 81.7 | grimmory 78.7 | stump 76.5 | kavita 73.5 | audiobookshelf 66.0 | calibre 52.8 |
| Modularity | komga 85.7 | bookorbit 85.3 | stump 84.3 | grimmory 79.2 | kavita 78.7 | audiobookshelf 69.0 | calibre 59.5 |
| Code Quality | bookorbit 83.7 | komga 83.3 | grimmory 80.7 | stump 78.8 | kavita 75.5 | audiobookshelf 69.7 | calibre 58.8 |
| Testing | bookorbit 84.5 | grimmory 79.5 | komga 78.0 | kavita 65.7 | calibre 64.0 | stump 62.5 | audiobookshelf 52.5 |
| Documentation | grimmory 82.8 | bookorbit 81.3 | komga 78.2 | stump 77.2 | audiobookshelf 75.7 | calibre 74.5 | kavita 70.0 |
| Performance Design | komga 82.7 | bookorbit 81.8 | grimmory 81.2 | stump 79.0 | kavita 77.5 | audiobookshelf 74.5 | calibre 61.5 |
| Developer Experience | bookorbit 87.7 | grimmory 85.2 | komga 82.2 | stump 79.3 | kavita 76.5 | audiobookshelf 73.8 | calibre 67.2 |
| Long-Term Sustainability | bookorbit 84.0 | komga 82.7 | grimmory 81.2 | kavita 75.7 | stump 73.5 | audiobookshelf 68.2 | calibre 59.7 |

---

## Category Scores by App and Model

Each table is sorted by average score (descending). The Avg column is the mean across all six model configurations.

### bookorbit

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Developer Experience | 87 | 88 | 82 | 87 | 92 | 90 | **87.7** |
| 2 | Architecture | 85 | 86 | 84 | 85 | 90 | 91 | **86.8** |
| 3 | Security | 84 | 82 | 81 | 84 | 91 | 90 | **85.3** |
| 4 | Modularity | 86 | 84 | 80 | 86 | 88 | 88 | **85.3** |
| 5 | Testing | 79 | 86 | 84 | 79 | 90 | 89 | **84.5** |
| 6 | Long-Term Sustainability | 85 | 82 | 79 | 85 | 88 | 85 | **84.0** |
| 7 | Code Quality | 84 | 82 | 78 | 84 | 90 | 84 | **83.7** |
| 8 | Performance Design | 76 | 82 | 84 | 76 | 90 | 83 | **81.8** |
| 9 | Maintainability | 80 | 81 | 76 | 80 | 88 | 85 | **81.7** |
| 10 | Documentation | 75 | 86 | 77 | 75 | 87 | 88 | **81.3** |
| - | **Overall** | **82** | **84** | **81** | **82** | **90** | **87** | **84.3** |

### komga

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Architecture | 88 | 88 | 86 | 88 | 90 | 90 | **88.3** |
| 2 | Modularity | 86 | 84 | 82 | 86 | 89 | 87 | **85.7** |
| 3 | Code Quality | 85 | 80 | 80 | 85 | 87 | 83 | **83.3** |
| 4 | Performance Design | 78 | 86 | 82 | 78 | 90 | 82 | **82.7** |
| 5 | Long-Term Sustainability | 84 | 81 | 80 | 84 | 84 | 83 | **82.7** |
| 6 | Maintainability | 82 | 80 | 74 | 82 | 88 | 88 | **82.3** |
| 7 | Security | 83 | 82 | 78 | 83 | 84 | 83 | **82.2** |
| 8 | Developer Experience | 79 | 81 | 81 | 79 | 86 | 87 | **82.2** |
| 9 | Documentation | 74 | 79 | 76 | 74 | 84 | 82 | **78.2** |
| 10 | Testing | 73 | 78 | 84 | 73 | 83 | 77 | **78.0** |
| - | **Overall** | **80** | **82** | **81** | **80** | **88** | **84** | **82.5** |

### grimmory

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Developer Experience | 80 | 86 | 88 | 80 | 89 | 88 | **85.2** |
| 2 | Documentation | 80 | 86 | 77 | 80 | 87 | 87 | **82.8** |
| 3 | Architecture | 80 | 82 | 84 | 80 | 87 | 83 | **82.7** |
| 4 | Performance Design | 74 | 82 | 84 | 74 | 90 | 83 | **81.2** |
| 5 | Long-Term Sustainability | 81 | 79 | 81 | 81 | 83 | 82 | **81.2** |
| 6 | Code Quality | 79 | 80 | 80 | 79 | 84 | 82 | **80.7** |
| 7 | Security | 78 | 78 | 73 | 78 | 86 | 88 | **80.2** |
| 8 | Testing | 73 | 83 | 86 | 73 | 85 | 77 | **79.5** |
| 9 | Modularity | 75 | 78 | 83 | 75 | 86 | 78 | **79.2** |
| 10 | Maintainability | 76 | 76 | 79 | 76 | 83 | 82 | **78.7** |
| - | **Overall** | **78** | **81** | **82** | **78** | **84** | **83** | **81.0** |

### stump

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Modularity | 83 | 83 | 80 | 83 | 90 | 87 | **84.3** |
| 2 | Architecture | 82 | 82 | 82 | 82 | 89 | 88 | **84.2** |
| 3 | Developer Experience | 73 | 80 | 80 | 73 | 88 | 82 | **79.3** |
| 4 | Performance Design | 79 | 75 | 76 | 79 | 85 | 80 | **79.0** |
| 5 | Code Quality | 78 | 78 | 73 | 78 | 85 | 81 | **78.8** |
| 6 | Documentation | 75 | 73 | 78 | 75 | 88 | 74 | **77.2** |
| 7 | Maintainability | 73 | 76 | 75 | 73 | 87 | 75 | **76.5** |
| 8 | Security | 74 | 78 | 68 | 74 | 80 | 76 | **75.0** |
| 9 | Long-Term Sustainability | 72 | 74 | 73 | 72 | 74 | 76 | **73.5** |
| 10 | Testing | 55 | 62 | 63 | 55 | 78 | 62 | **62.5** |
| - | **Overall** | **72** | **76** | **76** | **72** | **86** | **80** | **77.0** |

### kavita

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Architecture | 74 | 82 | 82 | 74 | 88 | 83 | **80.5** |
| 2 | Modularity | 72 | 80 | 80 | 72 | 87 | 81 | **78.7** |
| 3 | Performance Design | 67 | 81 | 82 | 67 | 85 | 83 | **77.5** |
| 4 | Developer Experience | 68 | 83 | 75 | 68 | 83 | 82 | **76.5** |
| 5 | Long-Term Sustainability | 67 | 78 | 77 | 67 | 86 | 79 | **75.7** |
| 6 | Code Quality | 68 | 78 | 77 | 68 | 84 | 78 | **75.5** |
| 7 | Security | 67 | 70 | 76 | 67 | 82 | 88 | **75.0** |
| 8 | Maintainability | 66 | 74 | 70 | 66 | 83 | 82 | **73.5** |
| 9 | Documentation | 64 | 70 | 66 | 64 | 80 | 76 | **70.0** |
| 10 | Testing | 45 | 73 | 76 | 45 | 78 | 77 | **65.7** |
| - | **Overall** | **65** | **78** | **77** | **65** | **84** | **82** | **75.2** |

### audiobookshelf

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Documentation | 74 | 79 | 76 | 74 | 78 | 73 | **75.7** |
| 2 | Security | 67 | 77 | 74 | 67 | 86 | 76 | **74.5** |
| 3 | Performance Design | 66 | 80 | 80 | 66 | 81 | 74 | **74.5** |
| 4 | Developer Experience | 65 | 76 | 79 | 65 | 80 | 78 | **73.8** |
| 5 | Architecture | 65 | 78 | 78 | 65 | 82 | 70 | **73.0** |
| 6 | Code Quality | 60 | 75 | 74 | 60 | 77 | 72 | **69.7** |
| 7 | Modularity | 64 | 69 | 73 | 64 | 78 | 66 | **69.0** |
| 8 | Long-Term Sustainability | 58 | 73 | 72 | 58 | 79 | 69 | **68.2** |
| 9 | Maintainability | 58 | 70 | 68 | 58 | 74 | 68 | **66.0** |
| 10 | Testing | 40 | 64 | 61 | 40 | 68 | 42 | **52.5** |
| - | **Overall** | **62** | **75** | **74** | **62** | **76** | **72** | **70.2** |

### calibre-web-automated

| # | Category | ChatGPT 5.4x | ChatGPT 5.5m | ChatGPT 5.5x | Opus 4.6 | Opus 4.8 | Sonnet 4.6 | Avg |
|---|---|---|---|---|---|---|---|---|
| 1 | Documentation | 74 | 78 | 78 | 74 | 78 | 65 | **74.5** |
| 2 | Developer Experience | 63 | 76 | 73 | 63 | 73 | 55 | **67.2** |
| 3 | Testing | 58 | 75 | 67 | 58 | 74 | 52 | **64.0** |
| 4 | Performance Design | 56 | 74 | 67 | 56 | 66 | 50 | **61.5** |
| 5 | Security | 55 | 74 | 66 | 55 | 65 | 44 | **59.8** |
| 6 | Long-Term Sustainability | 55 | 73 | 64 | 55 | 67 | 44 | **59.7** |
| 7 | Modularity | 57 | 70 | 61 | 57 | 72 | 40 | **59.5** |
| 8 | Code Quality | 52 | 73 | 62 | 52 | 64 | 50 | **58.8** |
| 9 | Architecture | 45 | 76 | 72 | 45 | 66 | 38 | **57.0** |
| 10 | Maintainability | 42 | 68 | 58 | 42 | 63 | 44 | **52.8** |
| - | **Overall** | **52** | **74** | **72** | **52** | **68** | **52** | **61.7** |

---

## Key Findings by App

| App | Strongest Category (Avg) | Weakest Category (Avg) | Notable |
|---|---|---|---|
| **bookorbit** | Developer Experience (87.7) | Documentation (81.3) | The only app to clear 80 in every single category; Claude Opus 4.8 is the sole model to award it "Enterprise Grade" maturity (90/A); the lone enforced 80% server coverage gate in CI underpins the top Testing average. |
| **komga** | Architecture (88.3) | Testing (78.0) | ArchUnit-enforced DDD is the highest-rated single attribute in the benchmark; remarkably tight cross-model agreement (overall range 80-88); the Vue 2 frontend is its recurring drag on Maintainability and Sustainability. |
| **grimmory** | Developer Experience (85.2) | Maintainability (78.7) | Best non-bookorbit Testing average (79.5) thanks to TestContainers + Playwright; the permissive default CORS and localStorage tokens are the consistent security caveat; bleeding-edge stack (Java 25, Spring Boot 4, Angular 21) cuts both ways. |
| **stump** | Modularity (84.3) | Testing (62.5) | Rust's crate decomposition earns free structural wins, but the ~2-3% frontend test coverage caps Testing; the widest overall spread of any app (72-86) reflects sharp disagreement on how much its beta status should be penalized. |
| **kavita** | Architecture (80.5) | Testing (65.7) | Clean 14-project .NET layering scores well, but committed-default-secret/stack-trace-leak findings and 415 EF migrations are recurring criticisms; newer models reward its 1,373-test xUnit suite far more than the older ones. |
| **audiobookshelf** | Documentation (75.7) | Testing (52.5) | Lowest Testing average of all apps; untyped JavaScript on a Nuxt 2 (EOL) stack is the single biggest structural risk, depressing Maintainability, Modularity, and Sustainability together. |
| **calibre-web-automated** | Documentation (74.5) | Maintainability (52.8) | Documentation is its only category above 65; 10,000+ lines across a handful of god-files and a hard fork dependency on upstream Calibre-Web are the dominant concerns; the model spread here is the largest in the benchmark for several categories. |

---

## Cross-Model Observations

### Model means (avg of the 7 per-app overall scores)

| Model | Mean overall | Range (spread) |
|---|---|---|
| Claude Opus 4.8 high | **82.3** | 68-90 (22) |
| ChatGPT 5.5 medium | 78.6 | 74-84 (10) |
| ChatGPT 5.5 xhigh | 77.6 | 72-82 (10) |
| Claude Sonnet 4.6 high | 77.1 | 52-87 (35) |
| ChatGPT 5.4 xhigh | 70.1 | 52-82 (30) |
| Claude Opus 4.6 high | 70.1 | 52-82 (30) |

### The two duplicated baselines

ChatGPT 5.4 xhigh and Claude Opus 4.6 high produced **numerically identical scores in all 70 cells** (7 apps x 10 categories) and identical overall scores. They differ only in the letter grade assigned to the same number (Claude Opus 4.6 tends to award a higher letter, e.g. 82 = "A" vs ChatGPT 5.4 "B"). These two columns are effectively a single shared baseline carried over from the earlier benchmark run; treat them as one data point, not two independent opinions.

### The newer models lift the field

The two newest configurations - **Claude Opus 4.8 high** (mean 82.3) and **ChatGPT 5.5** (medium 78.6, xhigh 77.6) - score every app higher than the older baselines, and the gap is largest for the mid-tier apps:

- **kavita** moved from 65 (the old baseline) to 84 (Claude Opus 4.8) and 77-78 (ChatGPT 5.5) - a swing that promotes it from "Community Project" to "Mature Project" depending on the grader.
- **stump** moved from 72 to 86 (Claude Opus 4.8), the single largest per-app jump, driven almost entirely by a more generous read of its testing and maintainability.
- **calibre-web-automated** is the clearest fault line: ChatGPT 5.5 medium rates it a 74 ("Production Ready"-adjacent) while Claude Sonnet 4.6 and the baselines hold it at 52. This 22-point gap is the largest single overall disagreement in the benchmark.

### Model personality

- **Claude Opus 4.8 high** is the most generous and the most decisive: highest mean, awards the only 90 (bookorbit) and the only "Enterprise Grade" rating, and rewards modern test infrastructure heavily (kavita testing 78, stump testing 78).
- **ChatGPT 5.5 (medium and xhigh)** are the most calibrated: the narrowest spreads (10 points each) and the most consistent B-range grading. Medium is marginally more generous than xhigh, which is unusual - more reasoning effort here trended slightly stricter.
- **Claude Sonnet 4.6 high** is the widest-variance model (35-point range): optimistic on modern, well-tested stacks (bookorbit 87, kavita 82) but the harshest grader of weak ones (calibre 52, with several sub-45 category scores). It punishes security gaps hardest.
- **The two baselines (ChatGPT 5.4 xhigh / Claude Opus 4.6 high)** are the strictest overall and the most skeptical of testing and maintainability claims in the mid and bottom tier.

---

## Testing: Still the Universal Weak Point

Testing remains the lowest or near-lowest category for most apps. The structural divide is unchanged from the prior run, only the magnitudes shifted as the newer models gave more credit:

- **bookorbit (84.5)** and **grimmory (79.5)** treat tests as first-class; both enforce coverage and run real integration/E2E suites.
- The bottom tier - **audiobookshelf (52.5)**, **stump (62.5)**, **calibre (64.0)**, **kavita (65.7)** - all carry test-to-source ratios well below 0.1. The newer models lifted these averages, but never above the production-ready apps.
- The single largest category disagreement is **kavita Testing**: the baselines score it 45 while every newer model scores it 73-78, a 30+ point gap rooted in whether the 1,373-test backend suite outweighs the complete absence of frontend tests.

## Documentation: Still the Great Equalizer

Documentation continues to show the narrowest spread between apps (70.0 - 82.8). Every project invests in a README, Docker docs, or API annotations regardless of code quality, so the category is a poor proxy for overall engineering quality - calibre (61.7 overall) and audiobookshelf (70.2 overall) sit within a few points of far stronger apps on Documentation alone.

## Security Patterns

- **bookorbit (85.3)** and **komga (82.2)** lead with different profiles: bookorbit shows defense-in-depth (token rotation with theft detection, SSRF/path-traversal hardening, login lockout); komga is architecturally strong but repeatedly flagged for disabled brute-force throttling and sparse security headers.
- **kavita** shows the widest security disagreement: Claude Sonnet 4.6 rates it 88 (crediting the multi-scheme auth) while the baselines sit at 67, weighing the committed default secret and stack-trace leakage more heavily.
- **grimmory's** permissive default CORS with credentials and **stump's** OIDC gaps (no nonce/state/PKCE in some flows) are the recurring runtime-misconfiguration risks cited across models.
