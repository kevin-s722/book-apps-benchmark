# calibre-web-automated Repository Assessment

## Model: ChatGPT 5.5 (xhigh)

Repository: `~/Workspace/calibre-web-automated`

Assessment date: 2026-06-17

## Executive Summary

calibre-web-automated is a production-oriented self-hosted Flask application that extends Calibre-Web with automated ingest, conversion, Kobo sync, KOReader progress sync, metadata maintenance, duplicate handling, statistics, and container-first operations. The strongest evidence is in the breadth of implementation subsystems: Flask blueprints are registered centrally in `cps/main.py:58`, the application bootstrap wires configuration, auth, rate limiting, scheduler, and database setup in `cps/__init__.py:117`, background work is centralized through `WorkerThread` in `cps/services/worker.py:56`, and deployment is directly supported by Docker, s6-overlay services, Compose, Kubernetes manifests, and GitHub Actions.

The repository is functionally mature but structurally uneven. The implementation contains several very large orchestration modules, including `cps/admin.py` at 3,115 lines, `cps/web.py` at 2,968 lines, `scripts/cwa_db.py` at 2,540 lines, `cps/cwa_functions.py` at 2,207 lines, `cps/editbooks.py` at 2,063 lines, and `cps/duplicates.py` at 1,782 lines. These modules combine routing, persistence, subprocess control, request handling, UI state, and operational workflows in ways that make behavior harder to reason about despite meaningful local safeguards.

Security is mixed. The codebase has CSRF setup, session cookie controls, password hashing, rate limiting, SSRF defenses for cover downloads, upload MIME checks, HTML sanitization, and parameterized checksum storage. At the same time, it ships a default admin password path, has Kobo auth-token routes parameterized by arbitrary `user_id` without an ownership check in the handler, keeps permissive CSP directives, stores KOReader Basic Auth credentials client-side, and includes shell-form `os.system` calls in `scripts/cover_enforcer.py`.

## Overall Score

Overall Score: 67/100

Overall Grade: C

Confidence: 90/100

## Maturity

Production-ready self-hosted application with monolithic-core risk.

## Repository Statistics

| Metric | Value |
| --- | ---: |
| Total non-git files | 1,169 |
| Implementation source files counted | 182 |
| Minimum implementation inspection required | 37 files |
| Implementation files inspected | 49 files |
| Implementation inspection coverage | 26.9% |
| Test files counted | 28 |
| Test-to-source ratio | 0.15 |
| Unique declared dependency names | 77 |
| Primary languages and assets | Python, JavaScript, HTML/Jinja templates, CSS, Lua, Shell, YAML, SQL/SQLite |
| Build system | setuptools via `pyproject.toml`, requirements files, Docker build |
| CI/CD | GitHub Actions test, Docker build, translation, release-support workflows |
| Containerization | `Dockerfile`, `docker-compose.yml`, `docker-compose.yml.dev`, s6-overlay services, Kubernetes manifests |

Largest implementation modules by line count:

| File | Lines |
| --- | ---: |
| `cps/iso_language_names.py` | 11,358 |
| `cps/admin.py` | 3,115 |
| `cps/web.py` | 2,968 |
| `scripts/cwa_db.py` | 2,540 |
| `cps/cwa_functions.py` | 2,207 |
| `cps/editbooks.py` | 2,063 |
| `cps/duplicates.py` | 1,782 |
| `cps/kobo.py` | 1,581 |
| `cps/helper.py` | 1,554 |
| `scripts/ingest_processor.py` | 1,447 |

Implementation coverage included these representative files and modules: `cps/__init__.py`, `cps/main.py`, `cps/web.py`, `cps/admin.py`, `cps/db.py`, `cps/ub.py`, `cps/usermanagement.py`, `cps/editbooks.py`, `cps/helper.py`, `cps/config_sql.py`, `cps/cwa_functions.py`, `cps/duplicates.py`, `cps/kobo.py`, `cps/kobo_auth.py`, `cps/services/worker.py`, `cps/services/background_scheduler.py`, `cps/tasks/*`, `cps/progress_syncing/*`, `scripts/ingest_processor.py`, `scripts/cover_enforcer.py`, `scripts/cwa_db.py`, and the KOReader Lua plugin files.

## Scorecard

| Category | Score | Grade |
| --- | ---: | :---: |
| Architecture | 72 | B |
| Security | 66 | C |
| Maintainability | 58 | C |
| Modularity | 61 | C |
| Code Quality | 62 | C |
| Testing | 67 | C |
| Documentation | 78 | B |
| Performance Design | 67 | C |
| Developer Experience | 73 | B |
| Sustainability | 64 | C |

## Deep Assessment

### Architecture

Grade: B

Score: 72/100

Evidence:

- `cps/main.py:58` registers distinct blueprints for CWA features, stock Calibre-Web routes, OPDS, search, tasks, Kobo, OAuth, KOReader sync, and duplicate handling.
- `cps/__init__.py:117` performs centralized app creation, database initialization, config loading, OAuth setup, rate limiter setup, scheduler registration, and request lifecycle hooks.
- `cps/services/worker.py:56` and `cps/services/background_scheduler.py:26` define process-local background execution and scheduling abstractions used by conversion, backup, thumbnail, auto-send, duplicate, and maintenance tasks.
- `scripts/ingest_processor.py:40` implements a dedicated external ingest processor with file locks, Calibre CLI integration, conversion, checksum generation, and follow-up task scheduling.
- `cps/progress_syncing/models.py:152` and `cps/progress_syncing/checksums/manager.py:132` isolate KOReader checksum schema management and checksum storage.
- `cps/__init__.py:245` runs magic shelf visibility and count work on every request, and `cps/__init__.py:340` keeps per-session count caching in the request hook.

Assessment:

The architecture has real subsystem boundaries around blueprints, task classes, progress sync, Kobo sync, background workers, and deployment services. The central app lifecycle is understandable and the data-access layer exposes permission-aware helpers such as `CalibreDB.common_filters()` in `cps/db.py:924`.

The architectural weakness is that the main process, scripts, scheduler, and routes share global state and call across boundaries. Internal scheduling and operational flows use HTTP callbacks to the local app from scripts, for example in `scripts/ingest_processor.py:1034`, `scripts/ingest_processor.py:1166`, and `scripts/ingest_processor.py:1189`. Large modules also combine route handling, database access, subprocess orchestration, and UI preparation, making the architecture serviceable but not cleanly layered.

### Security

Grade: C

Score: 66/100

Evidence:

- Session cookies are configured with HTTPOnly and SameSite controls in `cps/__init__.py:75`, and secure-cookie behavior is adjusted from configured login mode in `cps/__init__.py:130`.
- CSRF is initialized during app creation in `cps/__init__.py:117`, and rate limiting is initialized in `cps/__init__.py:229`.
- Cover URL downloads use `cw_advocate.get()` with redirects disabled and size enforcement in `cps/helper.py:1037`; the address validator blocks private, link-local, loopback, multicast, reserved, and unspecified targets in `cps/cw_advocate/addrvalidator.py:123`.
- Upload validation checks configured MIME and extension rules in `cps/editbooks.py:361`, and HTML cleanup delegates to Bleach in `cps/clean_html.py:25`.
- The default admin account is created with the default password constant in `cps/ub.py:1175` and `cps/constants.py:132`.
- `cps/kobo_auth.py:70` and `cps/kobo_auth.py:112` expose generate/delete token routes by `user_id` under `@user_login_required`, while the handlers query and delete by the route parameter in `cps/kobo_auth.py:83` and `cps/kobo_auth.py:116`.
- The CSP built in `cps/web.py:112` includes `'unsafe-inline'` and `'unsafe-eval'`.
- `scripts/cover_enforcer.py:627` and `scripts/cover_enforcer.py:697` use shell-form `os.system`.
- KOReader sync uses Basic Auth in `cps/progress_syncing/protocols/kosync.py:130`, and the plugin persists the password into settings in `koreader/plugins/cwasync.koplugin/main.lua:501`.

Assessment:

The repository contains credible defensive work in several areas: session setup, CSRF, rate limiting, upload checks, HTML sanitization, password hashing, and SSRF controls for URL-based cover downloads. Security-sensitive external processes often use list-form subprocess calls, for example `scripts/ingest_processor.py:582`, `scripts/ingest_processor.py:622`, and `scripts/ingest_processor.py:750`.

The remaining risk is not isolated to one place. The default admin bootstrap, permissive CSP, Basic Auth device flow, client-side password persistence, shell-form file operations, and route-parameter-based Kobo token management reduce the category score. Some of these choices may be acceptable for self-hosted deployment, but they are visible security constraints in the implementation.

### Maintainability

Grade: C

Score: 58/100

Evidence:

- The largest workflow modules are very large: `cps/admin.py` has 3,115 lines, `cps/web.py` has 2,968, `scripts/cwa_db.py` has 2,540, `cps/cwa_functions.py` has 2,207, `cps/editbooks.py` has 2,063, and `cps/duplicates.py` has 1,782.
- `cps/admin.py:522` begins the admin view/configuration routing region, and later sections continue through user tables, restrictions, Kobo full-sync, mail settings, LDAP helpers, and other admin concerns.
- `cps/cwa_functions.py:276` handles internal scheduling endpoints, stats, settings, log reading, conversion UI, process control, and status extraction in one module.
- `scripts/cwa_db.py:2212` contains a large dashboard aggregation method that builds many SQL query strings in sequence.
- `cps/duplicates.py:349` selects SQL, hybrid, or Python duplicate detection behavior, while `cps/duplicates.py:769` includes a Python fallback that loads all filtered books into memory.
- Broad exception handling appears in operational paths, including `cps/schedule.py:141`, `cps/cwa_functions.py:1426`, and `scripts/cwa_db.py:2481`.

Assessment:

Maintainability benefits from clear naming in many local functions, a recognizable Flask blueprint structure, and a growing test suite around CWA database behavior, ingest, progress sync, and Docker startup. The code often preserves operational context in logs and has meaningful comments around non-obvious integration behavior.

The primary maintainability cost is the accumulation of large, mixed-responsibility modules and long procedural workflows. Many feature paths require understanding Flask globals, SQLAlchemy sessions, SQLite side databases, Calibre CLI calls, background tasks, and container runtime assumptions together. That makes change impact harder to bound than the directory structure suggests.

### Modularity

Grade: C

Score: 61/100

Evidence:

- Feature-level modules and blueprints exist for web, admin, edit books, search, Kobo, KOReader sync, duplicates, and CWA-specific functions in `cps/main.py:22`.
- Background task classes are separated under `cps/tasks/`, and the shared queue abstraction is in `cps/services/worker.py:56`.
- KOReader checksum storage is factored into `cps/progress_syncing/checksums/manager.py:70`, while schema handling lives in `cps/progress_syncing/models.py:152`.
- The upload path in `cps/editbooks.py:93` delegates actual ingest to sidecar files and the external ingest processor.
- Cross-module globals are pervasive: `calibre_db`, `ub.session`, `config`, `current_user`, and `CWA_DB()` are accessed directly across `cps/db.py`, `cps/duplicates.py`, `cps/cwa_functions.py`, `cps/kobo.py`, and scripts.
- Scripts call internal routes over HTTP for follow-up work, for example `scripts/ingest_processor.py:1034`, `scripts/ingest_processor.py:1166`, and `scripts/ingest_processor.py:1189`.

Assessment:

The repository has recognizable modular units, especially around Flask route grouping, background tasks, progress syncing, and utility helpers. These modules are sufficient to navigate the project and localize some behaviors.

The modularity score is limited because many modules are not independent in practice. They share live globals, use request-context objects inside data-layer helpers, instantiate `CWA_DB()` directly, and rely on scripts reaching back into the web app. The result is module separation by file more than by stable contract.

### Code Quality

Grade: C

Score: 62/100

Evidence:

- Filename handling is centralized through `get_valid_filename_shared()` in `cps/utils/filename_sanitizer.py:27`, and the main helper falls back safely in `cps/helper.py:242`.
- Uploaded files are saved through a temporary `.uploading` path before rename in `cps/editbooks.py:412`, and ingest uses a robust lock with stale lock detection in `scripts/ingest_processor.py:40`.
- `scripts/ingest_processor.py:582`, `scripts/ingest_processor.py:622`, `scripts/ingest_processor.py:663`, and `scripts/ingest_processor.py:750` use list-form subprocess calls.
- `cps/progress_syncing/checksums/manager.py:77` and `cps/progress_syncing/checksums/manager.py:102` use parameterized SQL for checksum lookup and insertion.
- `scripts/cwa_db.py:91` normalizes user IDs before inserting them into SQL fragments, but `scripts/cwa_db.py:2224` builds date filters with f-strings and then embeds them into multiple query strings.
- `scripts/cover_enforcer.py:627` and `scripts/cover_enforcer.py:697` use shell-form `os.system`.
- `cps/web.py:1467` uses `text(sort_param + " " + order)` after whitelist-style route parameter handling in the same function, rather than a structured order expression.

Assessment:

Code quality is competent in many operational paths. The implementation shows care around file readiness, atomic upload staging, checksums, retries around database locks, and subprocess invocation. The code also contains useful domain-specific safeguards for Calibre libraries, network shares, Kobo devices, and large files.

The quality is uneven because defensive patterns are inconsistent. Some areas use structured SQL and list-form subprocesses, while others use string-built SQL or shell-form commands. The code also mixes print logging, Flask logging, broad exception handling, and direct global session access across high-traffic and operational paths.

### Testing

Grade: C

Score: 67/100

Evidence:

- The repository contains 28 Python test/config files against 182 implementation files, for a test-to-source ratio of 0.15.
- `pytest.ini:3` defines test discovery and strict markers, and `pytest.ini:19` separates smoke, unit, integration, Docker integration, Docker E2E, network, Calibre, and slow tests.
- Shared fixtures create temporary Calibre/CWA structures in `tests/conftest.py:260`, mock Calibre tools in `tests/conftest.py:396`, and skip Docker or Calibre-dependent tests when prerequisites are unavailable in `tests/conftest.py:440`.
- Docker integration fixtures create a test compose override, wait for readiness, check bind mounts, and clean up in `tests/conftest.py:533`.
- Unit coverage includes CWA database creation and settings behavior in `tests/unit/test_cwa_db.py:24`.
- Integration coverage exercises real ingest through a container in `tests/integration/test_ingest_pipeline.py:35`.
- Docker startup smoke tests verify web accessibility, default auth, volumes, app DB creation, and basic health in `tests/docker/test_container_startup.py:21`.
- GitHub Actions runs smoke and unit tests with coverage on all pushes in `.github/workflows/tests.yml:74` and Docker integration tests on main/dev or manual dispatch in `.github/workflows/tests.yml:162`.
- The E2E job currently only starts the stack and checks `/health`, with browser-test commands commented out in `.github/workflows/tests.yml:252`.

Assessment:

The test suite is meaningful for a self-hosted integration-heavy project. It covers database initialization, settings, ingest, progress sync, Docker startup, and environment-specific behavior. The fixtures show attention to real deployment constraints, including Docker-in-Docker and bind-mount visibility.

The score is capped because the test ratio is modest relative to the amount of implementation code and because several complex workflows are primarily covered through broad integration tests or not fully exercised by active E2E tests. Evidence is insufficient to state current passing rate or measured coverage percentage because tests were inspected but not executed.

### Documentation

Grade: B

Score: 78/100

Evidence:

- `README.md` is present as the project readme, and `pyproject.toml:73` designates it as the package readme.
- Versioned changelogs exist under `changelogs/`, including V2, V3, and V4 directories.
- `cps/progress_syncing/README.md` documents checksum behavior, schema, KOReader partial MD5, and KOSync endpoints.
- `tests/README.md`, `tests/DOCKER_VOLUMES.md`, and `tests/TEST_OPTIMIZATION.md` document test modes, Docker volume behavior, and test optimization.
- `kubernetes/README.md` and Kubernetes manifests document an optional Kubernetes deployment path.
- Inline docstrings are common in test fixtures and domain modules, for example `tests/conftest.py:533`, `cps/progress_syncing/models.py:152`, and `cps/progress_syncing/checksums/manager.py:132`.

Assessment:

Documentation is above average for a self-hosted application. There are user-facing docs, deployment examples, changelogs, test guidance, and subsystem notes for progress sync. The tests also contain useful operational documentation for Docker execution and integration constraints.

The documentation score is not higher because much of the core architecture remains implicit in implementation code. The largest modules do not have matching design-level documentation that explains boundaries, ownership of side databases, or the interplay between Flask routes, s6 services, Calibre CLI processes, and internal HTTP callbacks.

### Performance Design

Grade: C

Score: 67/100

Evidence:

- Worker execution is serialized through `WorkerThread` in `cps/services/worker.py:112`, which avoids abrupt daemon termination for file and database safety.
- APScheduler integration routes scheduled work into the worker in `cps/services/background_scheduler.py:56`.
- The KOReader checksum schema creates lookup indexes in `cps/progress_syncing/models.py:247` and `cps/progress_syncing/models.py:270`.
- KOReader partial MD5 intentionally samples file chunks rather than hashing entire files in `cps/progress_syncing/checksums/koreader.py:35`.
- Duplicate notifications use cache-first behavior and avoid triggering scans on every status call in `cps/duplicates.py:1007`.
- The duplicate Python fallback loads all filtered books with `.all()` in `cps/duplicates.py:795` and warns only past 50,000 books in `cps/duplicates.py:798`.
- The global request hook queries magic shelf visibility and count data on authenticated requests in `cps/__init__.py:269` through `cps/__init__.py:356`.
- Kobo sync reconnects the Calibre DB at the beginning of sync in `cps/kobo.py:182` and calls `len(books.all())` in `cps/kobo.py:278`.
- Cover downloads enforce size limits while streaming in `cps/helper.py:1051`.

Assessment:

The codebase has several performance-aware designs: checksumming uses partial reads and indexes, duplicate status uses caching, file watchers fall back to polling when needed, and background work is separated from request handling. These are meaningful choices for a library automation app with large files and slow external tools.

The performance profile is constrained by global request work, `.all()` materialization in duplicate and Kobo flows, SQLite side databases, and a single in-process worker model. The design is adequate for typical self-hosted use, but heavy libraries and simultaneous workflows can hit visible bottlenecks.

### Developer Experience

Grade: B

Score: 73/100

Evidence:

- `pyproject.toml:1` defines setuptools build metadata and package metadata, with Python support declared in `pyproject.toml:29`.
- `requirements-dev.txt:4` includes pytest, pytest-flask, pytest-cov, pytest-mock, pytest-timeout, pytest-xdist, testcontainers, factory-boy, faker, ruff, black, and isort.
- `pytest.ini:3` centralizes test discovery, markers, and coverage configuration.
- `.github/workflows/tests.yml:74` runs fast tests with coverage on every push and PR, and `.github/workflows/tests.yml:162` runs Docker integration tests for main/dev or manual runs.
- `Dockerfile:20` defines a multi-stage build with Python, Calibre, kepubify, and runtime packages, and `Dockerfile:299` defines a container healthcheck.
- `docker-compose.yml:1` provides a runnable self-hosted service definition with config, ingest, library, and plugin volumes.
- `tests/conftest.py:533` provides a real Docker test fixture with configurable test image, test port, UID/GID, readiness checks, and bind-mount fallback.
- Dependency declarations are split between `pyproject.toml` and requirements files, with duplicate/conflicting entries in `requirements.txt:11` and `requirements.txt:31` for `requests`, and `requirements.txt:20` and `requirements.txt:33` for `urllib3`. No lockfile was present in the inspected dependency manifests.

Assessment:

Developer experience is solid for contributors comfortable with Python, Docker, and Calibre tooling. The repository has explicit test modes, CI, coverage upload, Docker image builds, Compose, Kubernetes examples, and specialized fixtures for integration work.

The weaker evidence is dependency hygiene and reproducibility. Dependency versions are declared but not locked, and some requirements are duplicated with different constraints. The E2E workflow is also a healthcheck placeholder rather than active browser or full workflow automation.

### Sustainability

Grade: C

Score: 64/100

Evidence:

- The project declares production/stable status and GPL licensing in `pyproject.toml:11`.
- CI covers fast tests and Docker integration paths in `.github/workflows/tests.yml:74` and `.github/workflows/tests.yml:162`.
- Deployment assets include a Dockerfile, Compose file, s6-overlay service tree, and Kubernetes manifests.
- Runtime services include initialization, ingest watching, metadata change detection, checksum backfill, process recovery, and Calibre binary setup under `root/etc/s6-overlay/s6-rc.d/`.
- The codebase carries large monolithic modules and direct globals across core flows, as shown by `cps/admin.py`, `cps/web.py`, `scripts/cwa_db.py`, `cps/cwa_functions.py`, and `cps/editbooks.py`.
- Dependency breadth is high, with 77 unique declared dependency names across production, optional, and development manifests.

Assessment:

The project has enough operational maturity to sustain active self-hosted use. It has release artifacts, changelogs, container support, CI, tests, and several domain-specific hardening measures for Calibre, Kobo, KOReader, and network-share deployments.

Long-term sustainability is limited by complexity concentration. The system has many workflows, external tools, side databases, internal callbacks, and global app state, while the largest modules remain broad and tightly connected. This increases the cost of feature evolution and regression analysis.

## Comparative Snapshot

No cross-repository comparison was performed. This snapshot characterizes only `~/Workspace/calibre-web-automated`.

| Dimension | Repository-local characterization |
| --- | --- |
| Production readiness | Functional and deployable for self-hosted use |
| Operational surface | Large: web app, Calibre CLI, s6 services, ingest watcher, metadata detector, Docker, Kubernetes |
| Implementation shape | Feature-rich Flask app with large monolithic core modules |
| Strongest areas | Deployment support, domain functionality, integration handling, documentation, practical tests |
| Weakest areas | Maintainability, boundary clarity, inconsistent security patterns, dependency reproducibility |

## Final Verdict

calibre-web-automated is a capable and mature self-hosted automation app with substantial real-world functionality. Its core strengths are the breadth of Calibre/Kobo/KOReader workflows, pragmatic handling of file and database operations, and deployment support that includes Docker, Compose, s6-overlay services, Kubernetes manifests, and CI-backed tests.

The implementation is not lightweight or cleanly layered. Several critical modules act as large orchestration surfaces, and many paths rely on shared Flask globals, SQLite side databases, direct SQL strings, Calibre subprocesses, and local HTTP callbacks. Security and quality controls exist, but they are inconsistent across modules, with notable weak spots around default credentials, token-route ownership checks, permissive CSP, Basic Auth device flows, client-side credential storage, and shell-form commands.

The assessed maturity is production-ready for the repository's self-hosted target context, not enterprise-grade. The overall score is 67/100 because the project demonstrates practical product maturity and operational depth while carrying significant maintainability, modularity, security, and sustainability constraints in its implementation structure.
