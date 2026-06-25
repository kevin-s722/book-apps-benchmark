# Executive Summary

## Repository: komga
## Model: Claude Opus 4.8 (high)

## Overall Score

Score: 88/100
Grade: A
Confidence: 90/100

Repository Maturity: **Mature Project** (production-grade, professionally engineered open-source media server)

Komga is a self-hosted media server for comics, mangas, and ebooks, implemented as a Kotlin/Spring Boot backend (~35,000 LOC of Kotlin), a Vue 2/TypeScript frontend (~33,000 LOC), and a thin Compose-based desktop tray wrapper (`komga-tray`). The backend is built on a textbook hexagonal/Domain-Driven-Design layering (`domain` / `application` / `infrastructure` / `interfaces`) with that layering mechanically enforced by ArchUnit tests. The codebase exhibits unusually disciplined engineering for an open-source project: type-safe jOOQ data access generated from Flyway migrations, a WAL-aware read/write datasource split for SQLite, Lucene full-text indexing, multiple distinct Spring Security filter chains, and a broad backend test suite. The most material gap is frontend test coverage and an aging Vue 2 UI stack.

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | A | 90 | Hexagonal/DDD layering enforced by ArchUnit; clean ports/adapters via domain persistence interfaces + jOOQ DAOs |
| Security | B+ | 84 | Multi-chain Spring Security, BCrypt, OAuth2/OIDC, per-user content scoping; no brute-force throttling, sparse security headers |
| Maintainability | A | 88 | Zero TODO/FIXME, consistent idioms, small focused services, ktlint-enforced style |
| Modularity | A | 89 | Strict slice isolation, ports-and-adapters, swappable interface adapters (REST/OPDS/Kobo/KOReader) |
| Code Quality | A- | 87 | Idiomatic Kotlin, immutable data classes, structured error codes; a few 700-900 LOC controllers |
| Testing | B+ | 83 | ~92 backend test files (unit/DAO/web-layer/ArchUnit) with jimfs + JMH benchmarks; frontend nearly untested |
| Documentation | B+ | 84 | DEVELOPING.md, ERRORCODES.md, generated OpenAPI spec, KDoc on key services; no architecture overview doc |
| Performance Design | A | 90 | RW/RO datasource split, Lucene async commit, Caffeine caching, layered Spring Boot jar, JMH benchmarks |
| Developer Experience | A- | 86 | Reproducible Gradle build, Spring profiles, IntelliJ run configs, multi-OS CI; complex codegen pipeline |
| Long-Term Sustainability | B+ | 84 | Modern dependency stack, conventional commits + automated releases; Vue 2 EOL and single-maintainer bus factor |

---

# Deep Assessment

## Architecture

### Grade: A
### Score: 90

### Evidence
- Clean hexagonal/DDD package structure under `komga/src/main/kotlin/org/gotson/komga`: `domain/model` (66 model files), `domain/persistence` (repository ports), `domain/service` (21 lifecycle/business services), `application` (tasks/scheduler/events), `infrastructure` (jooq, security, search, mediacontainer, datasource), and `interfaces` (api/rest, api/opds/v1+v2, api/kobo, api/kosync, sse, mvc).
- Ports-and-adapters realized concretely: `domain/persistence/BookRepository.kt` etc. are interfaces; implementations live in `infrastructure/jooq/main/*Dao.kt` (e.g., `BookDtoDao.kt`, `ReferentialDao.kt`). Domain never imports jOOQ.
- The layering is **mechanically enforced**, not aspirational: `komga/src/test/kotlin/org/gotson/komga/architecture/DomainDrivenDesignRulesTest.kt` forbids `..domain..model..` from depending on `..infrastructure..`, `..interfaces..`, `..domain.persistence..`, or `..domain.service..`. `SlicesIsolationRulesTest.kt` enforces that interface adapters (REST/OPDS/Kobo) do not depend on each other.
- `domain/service/SeriesLifecycle.kt` shows orchestration via injected ports + `TransactionTemplate` + `ApplicationEventPublisher` (event-driven domain events such as `DomainEvent.SeriesAdded`).
- Task orchestration decoupled through `application/tasks/TaskHandler.kt` + `TaskEmitter` with priority levels and a dedicated tasks database.

### Assessment
This is a mature, deliberately layered architecture that follows hexagonal/DDD principles more rigorously than most professionally maintained software. The separation of domain models, persistence ports, and infrastructure adapters is genuine and continuously verified by ArchUnit in CI. Multiple delivery mechanisms (REST, OPDS v1/v2, Kobo sync, KOReader sync, SSE) are implemented as isolated interface slices over a shared domain, which is a strong indicator of architectural discipline. The event-driven domain layer and clean task abstraction add to the sophistication.

---

## Security

### Grade: B+
### Score: 84

### Evidence
- `infrastructure/security/SecurityConfiguration.kt` defines **four distinct `SecurityFilterChain` beans**: a primary REST/OPDS/SSE chain, a Kobo chain (`/kobo/**`, `ROLE_KOBO_SYNC`), a KOReader chain (`/koreader/**`, `ROLE_KOREADER_SYNC`), each with tailored auth converters (`X-API-Key` header, URI-regex API key, `X-Auth-User` header).
- Method security enabled (`@EnableMethodSecurity(prePostEnabled = true)`); `@PreAuthorize` used across REST controllers (12 occurrences in `BookController.kt` alone).
- Password hashing uses `BCryptPasswordEncoder` (`PasswordEncoderConfiguration.kt`); API keys stored hashed (XXH3 mask + SHA512), per the security review.
- Per-user multi-tenant content scoping in `interfaces/api/ContentRestrictionChecker.kt`: enforces `canAccessLibrary`, age rating, and sharing-label restrictions, throwing `FORBIDDEN`/`NOT_FOUND`. DAO queries are user-scoped (`findAll(... userId ...)` in `BookDtoDao.kt`).
- OAuth2/OIDC login wired conditionally on client registration; remember-me via `TokenBasedRememberMeServices` with a securely generated 32-char key.
- Data access is exclusively type-safe jOOQ (parameterized), with no raw SQL string concatenation found. EPUB/OPF metadata parsed with jsoup (no external-entity expansion). Config externalized; no hardcoded secrets in `application.yml`.
- EPUB resources served with `Content-Security-Policy: script-src 'none'; object-src 'none'`.
- Contradictory/weak evidence: no brute-force/rate-limit on authentication (failed logins logged via `LoginListener` but not throttled); incomplete response security headers (no HSTS, no `X-Content-Type-Options`); `management.endpoint.shutdown.access: unrestricted` in default `application.yml` (mitigated by ADMIN-only actuator matcher); Kobo API key carried in URL path; archive entry names not explicitly validated against zip-slip (entries are read into memory, not extracted to disk, which materially limits impact).

### Assessment
Security is a clear strength relative to typical self-hosted projects: layered filter chains, BCrypt, OAuth2/OIDC, hashed API keys, parameterized data access, and genuine per-user content authorization checked both at the query layer and at controller boundaries. The gaps are real but moderate for the threat model of a self-hosted server: the absence of authentication throttling and several missing hardening headers are the most notable, alongside sync-endpoint auth that relies on API keys in URLs. None of the identified issues are critical injection or auth-bypass flaws; they are hardening shortfalls. The grade reflects a strong posture with a handful of well-bounded weaknesses.

---

## Maintainability

### Grade: A
### Score: 88

### Evidence
- **Zero** `TODO`/`FIXME`/`HACK` markers across `komga/src/main/kotlin` (grep count: 0).
- Style enforced repository-wide by ktlint (`org.jlleitschuh.gradle.ktlint` applied to `allprojects` in root `build.gradle.kts`), plus `.editorconfig`.
- Services are small and single-responsibility (`SeriesLifecycle.kt` ~380 LOC with cohesive methods; `ContentRestrictionChecker.kt` ~88 LOC). Domain models are immutable `data class`es (`Media.kt`, `BookMetadata`), favoring `copy()`-based updates.
- Structured, documented error taxonomy in `ERRORCODES.md` (ERR_1000+), with deprecated codes struck through rather than silently removed.
- Conventional Commits enforced (`conventionalcommit.json`, DEVELOPING.md), feeding automated changelog/versioning (jreleaser config in root `build.gradle.kts`).
- Only 27 files use `!!` non-null assertions and 17 use intentional `catch (_: Exception)` (mostly in tolerant parsing paths like `EpubExtractor.isEpub`), indicating disciplined null/error handling.

### Assessment
The codebase is highly maintainable. Consistent Kotlin idioms, immutable models, mechanically enforced formatting, an explicit and versioned error-code catalogue, and a complete absence of debt markers all point to sustained, careful upkeep. Updates flow through small focused services rather than god-objects, and the conventional-commit + automated-release pipeline reduces release friction. The size of a few interface controllers is the only minor drag.

---

## Modularity

### Grade: A
### Score: 89

### Evidence
- Domain depends only on its own ports; adapters are swappable. The same domain is exposed through independent interface slices: `interfaces/api/rest`, `interfaces/api/opds/v1`, `interfaces/api/opds/v2`, `interfaces/api/kobo`, `interfaces/api/kosync`, `interfaces/sse`, `interfaces/mvc`.
- `SlicesIsolationRulesTest.kt` enforces that interface slices do not depend on one another.
- Persistence is a pluggable layer: every `domain/persistence/*Repository` port has a corresponding `infrastructure/jooq/main/*Dao` implementation; jOOQ classes are generated, keeping handwritten code thin.
- Cross-cutting concerns isolated in `infrastructure` (`security`, `search`, `cache`, `image`, `mediacontainer`, `datasource`).
- Multi-module Gradle build (`settings.gradle`: `komga`, `komga-tray`) separates the server from the desktop tray.
- `SplitDslDaoBase.kt` cleanly abstracts the RW/RO DSL selection so DAOs are agnostic to datasource topology.

### Assessment
Modularity is excellent. The ports-and-adapters approach makes both persistence and delivery mechanisms replaceable, and the existence of five+ independent API surfaces over one domain demonstrates the boundaries actually hold under real feature pressure. Module isolation is enforced by automated tests rather than left to convention, which is uncommon and valuable.

---

## Code Quality

### Grade: A-
### Score: 87

### Evidence
- Idiomatic, modern Kotlin: data classes with defaults (`Media.kt`), `when`-based dispatch (`TaskHandler.handleTask`), scope functions, lazy delegates (`Media.profile by lazy`).
- jOOQ DAOs are type-safe with readable sort/condition builders (`BookDtoDao.kt` `sorts` map, `BookSearchHelper(...).toCondition(...)`).
- Centralized validation error handling (`ErrorHandlingControllerAdvice.kt`) translating `ConstraintViolationException`/`MethodArgumentNotValidException` into structured responses.
- Frontend services are typed and consistent (`komga-webui/src/services/komga-books.service.ts`), with DTO types in `src/types`. `tsconfig.json` has `"strict": true`.
- Additional architecture-enforced quality rules in `architecture/CodingRulesTest.kt` (no `System.out`, no generic exceptions, no field injection, no `java.util.logging`) and `NamingConventionTest.kt`.
- Contradictory evidence: several large interface controllers (`Opds2Controller.kt` 934 LOC, `SeriesController.kt` 878, `KoboController.kt` 842, `OpdsController.kt` 820, `BookController.kt` 770) concentrate substantial endpoint logic; the protocol surfaces drive size but they are the heaviest files.

### Assessment
Code quality is high and consistent across the backend, reinforced by ArchUnit coding rules that ban common anti-patterns and field injection outright. Kotlin idioms are used well, error handling is centralized, and even the frontend service layer is cleanly typed under strict TypeScript. The principal blemish is a cluster of large protocol controllers; these are cohesive and readable but sit well above the otherwise tight per-file size, holding the category just short of an A.

---

## Testing

### Grade: B+
### Score: 83

### Evidence
- ~92 backend test files spanning architecture (4 ArchUnit suites), domain models (~10), domain services (~13, e.g. `BookLifecycleTest`, `SeriesLifecycleTest`, `MetadataApplierTest`), jOOQ DAOs (~19, e.g. `BookDaoTest`, `SeriesDaoTest`), infrastructure extractors/search/metadata (~22), and REST/OPDS/Kobo/KOReader controllers (~21 via `@SpringBootTest` + `@AutoConfigureMockMvc`).
- Test infrastructure: factory helpers (`domain/model/Utils.kt` `makeBook/makeSeries/...`), jimfs in-memory filesystem (~48 usages) for isolated FS tests, custom `@WithMockCustomUser` security annotation, mockk/springmockk for selective mocking, SQLite test DB driven by Flyway + generated jOOQ.
- JMH benchmark sourceSet (`komga/src/benchmark/...`) with REST benchmarks (`DashboardBenchmark`, `BrowseBenchmark`, `UnsortedBenchmark`) and a `benchmark` Gradle task.
- CI (`.github/workflows/tests.yml`) runs the full backend build/tests on ubuntu, macOS, and Windows (`fail-fast: false`) and publishes JUnit reports; frontend runs `npm run test:unit`.
- Test-to-source ratio (backend Kotlin): 97 test files / 430 main files ≈ 0.22.
- Contradictory evidence: frontend has only ~3 spec files (`toc.spec.ts`, `book-spreads.spec.ts`, `pageLoader.spec.ts`) for ~110 Vue components + ~39 views; jacoco is configured but **not gated** (no coverage thresholds in CI); no E2E/browser tests.

### Assessment
Backend test confidence is strong: meaningful unit tests with edge cases, dedicated DAO tests against a real SQLite engine, full web-layer controller tests with security context, plus architecture tests and performance benchmarks. The test pyramid is, however, lopsided. The Vue 2 frontend is almost entirely untested, there is no end-to-end coverage, and coverage is measured but never enforced. The backend alone would merit an A-range testing grade; the near-absent frontend testing pulls the combined category to B+.

---

## Documentation

### Grade: B+
### Score: 84

### Evidence
- Contributor-facing docs: `DEVELOPING.md` (profiles, Gradle tasks, frontend/backend dev loop, Docker build steps), `CONTRIBUTING.md`, `DOCKERHUB.md`, `PRIVACY.md`, `README.md`.
- `ERRORCODES.md` documents the full error-code taxonomy with deprecated codes retained for traceability.
- Machine-readable API contract: generated `komga/docs/openapi.json` (Springdoc), with Swagger annotations (`@Operation`, `@ApiResponse`) present in controllers (`BookController.kt`).
- KDoc on non-obvious domain logic (`ContentRestrictionChecker.kt`, `EpubExtractor.kt`).
- A large maintained `CHANGELOG.md` (~346 KB) generated from conventional commits.
- Contradictory evidence: no dedicated architecture overview/ADR document in-repo (the DDD structure must be inferred from packages and ArchUnit tests); inline comments are sparse by design.

### Assessment
Documentation is solid and pragmatic. The developer guide is genuinely actionable, the OpenAPI spec gives a precise API contract, and the versioned error-code catalogue is a notably mature touch. The main shortfall for newcomers is the lack of a written architecture narrative; the design is excellent but largely self-documenting through code and tests rather than prose.

---

## Performance Design

### Grade: A
### Score: 90

### Evidence
- WAL-aware **read/write datasource split** (`infrastructure/datasource/DataSourcesConfiguration.kt`): a single-connection write pool plus a multi-connection read pool, only activated when journal mode is WAL and the DB is file-based; `SplitDslDaoBase.kt` routes RO queries to the read pool unless inside a writable transaction. This directly addresses SQLite's single-writer constraint.
- Configurable SQLite PRAGMAs, busy timeout, FK enforcement, and HikariCP pool sizing keyed to available processors.
- Lucene full-text search with async index commit (`infrastructure/search/LuceneAsyncCommitter.kt`, `SearchIndexLifecycle.kt`) to keep writes off the request path.
- Caffeine caching (`spring-session-caffeine`, `caffeine` dependency).
- Layered Spring Boot jar extraction in `komga/docker/Dockerfile.tpl` (`-Djarmode=tools ... extract --layers`) for efficient image layer caching; multi-arch (amd64/arm64/arm/v7) builds.
- Batched DB operations (`batchChunkSize` property injected into `BookDtoDao`); pagination throughout DTO DAOs.
- JMH benchmark suite targets the hottest read paths (dashboard, browse) — evidence performance is actively measured.

### Assessment
Performance is engineered deliberately, not accidentally. The WAL-aware RW/RO datasource separation is a sophisticated, problem-specific optimization rarely seen in projects of this kind, and asynchronous Lucene commits, Caffeine caching, batching, and JMH benchmarking together show a team that treats latency as a first-class concern. The layered container build further reflects operational performance awareness.

---

## Developer Experience

### Grade: A-
### Score: 86

### Evidence
- Reproducible Gradle (Kotlin DSL) build with wrapper pinned (`8.14.3`), version catalog (`gradle/libs.versions.toml`), and a fully automated codegen pipeline: Flyway migrations -> SQLite -> jOOQ generation -> compile.
- Rich Spring profiles for local dev (`dev`, `localdb`, `noclaim`) documented in `DEVELOPING.md`, plus committed IntelliJ run configurations.
- Frontend dev server with backend proxying (`npm run serve`), `.nvmrc` pinning Node.
- ktlint formatting tasks, jacoco reports, OpenAPI generation task, and JMH `benchmark` task all wired into Gradle.
- CI matrix validates builds on three operating systems.
- Contradictory evidence: the build is intricate (jOOQ/Flyway codegen ordering, multiple source sets including `flyway` and `benchmark`, Thymeleaf injection step), raising onboarding complexity and first-build cost.

### Assessment
Developer experience is well above average for a project of this scope. The build is reproducible and self-bootstrapping, profiles make local iteration straightforward, and tooling (lint, coverage, OpenAPI, benchmarks, multi-OS CI) is comprehensive. The cost is build sophistication: the codegen and source-set wiring is powerful but non-trivial to fully understand, which slightly tempers the grade.

---

## Long-Term Sustainability

### Grade: B+
### Score: 84

### Evidence
- Modern, current dependency stack: Spring Boot 3.5.14, Kotlin 2.2.0, jOOQ 3.19.32, Lucene 9.9.1, SQLite JDBC 3.50.2.0, PDFBox 3.0.5 (per `build.gradle.kts` / `libs.versions.toml`); automated dependency-update tooling (`com.github.ben-manes.versions`, Dependabot-style commits visible in git log).
- 85 Flyway SQL migrations (+5 Kotlin migrations) demonstrate sustained, controlled schema evolution.
- Automated releases and changelog via jreleaser + conventional commits reduce maintainer burden and improve traceability.
- Architecture-enforcing tests act as long-lived guardrails against design erosion.
- Contradictory evidence: the frontend is on **Vue 2** (`"vue": "^2.6.14"`), which has reached end-of-life, implying an eventual migration cost; the project is effectively driven by a single primary author (copyright "Gauthier Roebroeck"), a bus-factor risk; chart.js pinned to 2.x is also dated.

### Assessment
Sustainability is good. The backend is built on a current, well-supported stack with disciplined schema migration and automated release machinery, and the enforced architecture should resist decay over time. The headwinds are the EOL Vue 2 frontend (a known future cost) and concentration of stewardship in a single maintainer. These are manageable but real long-horizon risks, placing the category solidly at B+ rather than A.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Excellent |
| Security Posture | Strong |
| Maintainability | Excellent |
| Modularity | Excellent |
| Test Confidence | Strong (backend) / Weak (frontend) |
| Documentation Quality | Strong |
| Production Readiness | Production Ready |
| Enterprise Suitability | Strong (self-hosted), Moderate (multi-tenant SaaS) |
| Contributor Friendliness | Strong |
| Sustainability | Strong with caveats (Vue 2 EOL, bus factor) |

---

# FINAL VERDICT

## Overall Grade: A
## Overall Score: 88/100
## Confidence Score: 90/100
## Repository Maturity: Mature Project

## Best Attribute
Architecture and Performance Design (tie at 90): a rigorously enforced hexagonal/DDD structure combined with problem-specific performance engineering (WAL-aware RW/RO SQLite datasource split, async Lucene commits, JMH benchmarking).

## Weakest Attribute
Testing (83), dragged down by near-absent frontend test coverage and un-gated coverage, despite a strong backend suite. Sustainability and Security (84) are the next constraints, owing to the EOL Vue 2 frontend / single-maintainer bus factor and missing auth-throttling/hardening headers respectively.

## Three-Paragraph Assessment

**Engineering quality.** Komga reflects a level of engineering discipline well beyond the typical self-hosted media server. The backend uses idiomatic, immutable Kotlin; data access is uniformly type-safe via jOOQ generated from Flyway migrations; validation and error handling are centralized; and the entire repository is held to a consistent style by ktlint and to behavioral coding rules (no field injection, no generic exceptions, no `System.out`) by ArchUnit. There are zero debt markers in the main source, a versioned error-code taxonomy, and a broad backend test suite (~92 files) covering domain logic, DAOs against a real SQLite engine, and the web layer with full security context. The clearest quality gaps are a handful of very large protocol controllers and a frontend that, while cleanly typed under strict TypeScript, is almost entirely untested.

**Architectural maturity.** The system is a faithful hexagonal/Domain-Driven-Design implementation in which the boundaries are not merely documented but mechanically enforced in CI: domain models cannot reference infrastructure or interfaces, and interface slices cannot reference one another. That discipline has held up under genuine feature pressure, as evidenced by five-plus independent delivery surfaces (REST, OPDS v1/v2, Kobo sync, KOReader sync, SSE) layered over a single shared domain through swappable persistence ports. Performance is treated as a design concern rather than an afterthought, most strikingly in the WAL-aware read/write datasource separation that accommodates SQLite's single-writer model, supported by asynchronous Lucene indexing, Caffeine caching, batching, and a JMH benchmark suite. Security is multi-layered (distinct filter chains per protocol, BCrypt, OAuth2/OIDC, hashed API keys) with genuine per-user content authorization, though it stops short of brute-force protection and full response-header hardening.

**Long-term sustainability.** The project is positioned to age well: it rides a current, actively patched dependency stack (Spring Boot 3.5, Kotlin 2.2, jOOQ 3.19, Lucene 9.9), evolves its schema through 85+ controlled Flyway migrations, and automates releases and changelogs from conventional commits, all reinforced by architecture tests that resist design erosion. The principal long-horizon risks are external to the core engineering: the Vue 2 frontend has reached end-of-life and will eventually require migration, and stewardship is concentrated in a single primary maintainer, creating bus-factor exposure. Weighed against professionally maintained production software, Komga lands in the upper tier - a mature, production-ready, sustainably engineered project whose few weaknesses are bounded and well understood.
