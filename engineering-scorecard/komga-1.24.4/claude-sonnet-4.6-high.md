# Executive Summary

## Repository: komga
## Model: Claude Sonnet 4.6 (high)

## Overall Score

Score: 84/100
Grade: B+
Confidence: 88/100

Repository Maturity: Mature Project

---

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | komga |
| Total Files | 1164 |
| Source Files | 430 Kotlin + 232 TypeScript/Vue |
| Test Files | 97 Kotlin tests + 3 TypeScript spec files |
| Languages | Kotlin (primary), TypeScript, Vue, SQL |
| Dependency Count | ~60 backend, ~35 frontend |
| Largest Module | domain/service (20 services), interfaces/api/rest (22 controllers) |
| Build System | Gradle (Kotlin DSL) + npm |
| CI/CD Present | Yes (GitHub Actions: tests, release, webui build) |
| Containerization Present | Yes (JReleaser Docker, Conveyor for desktop) |
| Test-to-Source Ratio | ~0.23 (97 test Kt / 430 source Kt) |

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | A | 90 | Clean DDD layers with enforced ArchUnit rules; domain isolation mechanically verified |
| Security | B+ | 83 | BCrypt passwords, SHA-512 API key hashing, Spring Security with role-based access; actuator wildcard exposure is a concern |
| Maintainability | A- | 88 | Conventional Commits, typed config, clear lifecycle classes, CHANGELOG with 6300 lines of history |
| Modularity | A- | 87 | Well-separated domain/infrastructure/interfaces layers; repository interfaces decouple domain from jOOQ |
| Code Quality | B+ | 83 | Idiomatic Kotlin, no stdout misuse, custom domain exceptions, ktlint enforced; webui uses Vue 2 Options API remnants in store |
| Testing | B | 77 | 97 SpringBootTest integration tests across all layers; ArchUnit architecture tests; frontend test coverage thin (3 spec files) |
| Documentation | B+ | 82 | OpenAPI via springdoc, ERRORCODES.md, DEVELOPING.md, CHANGELOG.md; inline comments minimal but appropriate |
| Performance Design | B+ | 82 | Read/write DataSource split for SQLite, ETag filter, Lucene full-text search, Caffeine session store, HTTP cache headers |
| Developer Experience | A- | 87 | Cross-platform CI (ubuntu/macos/windows), Dependabot, IntelliJ run configs committed, DEVELOPING.md, Spring profiles for dev |
| Long-Term Sustainability | B+ | 83 | Active conventional commits history, Dependabot, Spring Boot 3.5, JDK 21, well-defined error codes; SQLite single-DB constraint limits scale |

---

# Deep Assessment

## Architecture

### Grade
A

### Score
90

### Evidence
The repository employs a clean Domain-Driven Design (DDD) layered architecture enforced by automated ArchUnit tests. The package structure is: `domain/model`, `domain/persistence` (interfaces), `domain/service` (lifecycle classes), `infrastructure/` (jOOQ implementations, security, search, image processing), `interfaces/api/rest` (controllers), `interfaces/sse`, `interfaces/api/kobo`, `interfaces/api/opds`, and `application/tasks`.

Architecture rules are mechanically enforced via `DomainDrivenDesignRulesTest`, `SlicesIsolationRulesTest`, `CodingRulesTest`, and `NamingConventionTest` in `komga/src/test/kotlin/org/gotson/komga/architecture/`. Specifically:
- `DomainDrivenDesignRulesTest` asserts that `domain.model` classes cannot depend on `infrastructure`, `interfaces`, `domain.persistence`, or `domain.service`
- `SlicesIsolationRulesTest` asserts that interface slices (rest, kobo, opds, kosync, sse) do not depend on each other
- `CodingRulesTest` enforces no stdout access, no generic exceptions, no Joda-Time, no field injection

The `domain/persistence` layer uses Kotlin interfaces (e.g., `BookRepository`, `SeriesRepository`), and implementations live in `infrastructure/jooq/main/` - a textbook repository pattern. Domain events (`DomainEvent` sealed class with 30+ typed events) are published via Spring's `ApplicationEventPublisher`, decoupling lifecycle services from side-effect coordination.

Task queue architecture (`application/tasks/`) uses a SQLite-backed durable task queue with `TaskProcessor`, `TaskEmitter`, and `TaskHandler` as separate concerns. A separate tasks database (`tasksDb`) is used to isolate task state from main data, with Flyway managing both databases independently.

### Assessment
Architecture quality is exceptional for a community media server project. The combination of DDD layers, repository pattern, event-driven coordination, and automated ArchUnit enforcement demonstrates deliberate architectural intent that most open-source projects lack. The `SlicesIsolationRulesTest` preventing interface slices from cross-depending is particularly sophisticated. One mild concern is that `BookController` directly accesses multiple repositories (`bookDtoRepository`, `thumbnailBookRepository`, `readListRepository`) alongside lifecycle services, which dilutes the controller-as-thin-HTTP-adapter principle.

---

## Security

### Grade
B+

### Score
83

### Evidence
Password encoding uses BCryptPasswordEncoder (`PasswordEncoderConfiguration.kt`). API keys are stored as SHA-512 hashes using `TokenEncoder { rawPassword -> Sha512DigestUtils.shaHex(rawPassword) }`. API key generation uses UUID v4 (`ApiKeyGenerator`). Session management uses Caffeine-backed Spring Session with proper session invalidation on role changes (`KomgaUserLifecycle.updateUser` calls `expireSessions` when roles differ).

Spring Security is configured with multiple filter chains: main REST chain, dedicated Kobo chain (URI regex API key extraction from `/kobo/{token}`), and KOReader chain (header-based API key). The Kobo chain is notably sessionless by deliberate design (commented-out session config with an explanation of Kobo device JSON parsing issues).

Content restrictions are enforced at the repository layer via `SearchContext` carrying `ContentRestrictions`, and `KomgaUser.isContentAllowed()` provides fine-grained age/label-based access control. `ContentRestrictionChecker.checkContentRestriction()` is called in controller methods.

CSRF is disabled (`it.disable()`), which is acceptable for a REST API consumed by single-page applications and native clients, but worth noting. CORS is configurable and conditional on `komga.cors.allowed-origins` being set.

Security concern: `management.endpoints.web.exposure.include: "*"` in `application.yml` exposes all actuator endpoints, mitigated only by requiring `ADMIN` role for non-health endpoints. The shutdown endpoint has `access: unrestricted` in the YAML comment area (line 82) though the actual config requires review - the YAML shows `endpoint.shutdown.access: unrestricted` which is a risk if actuator is on the same port as the API. The FileSystemController is restricted to ADMIN role, which is correct for the directory listing capability.

Remember-me key is auto-generated via `RandomStringUtils.secure().nextAlphanumeric(32)` and persisted to the database, which is correct behavior.

### Assessment
Security posture is solid for a self-hosted single-user/family-tier application. BCrypt for passwords, SHA-512 for API key storage, Spring Security with multiple filter chains, and per-user content restrictions are all well-implemented. The actuator wildcard exposure pattern combined with the `shutdown: unrestricted` configuration is the most significant concern, as it could allow DoS in environments where the actuator port is not separately firewalled. The CSRF disable is a reasonable trade-off for an API-first application. No hardcoded credentials or secrets were found in any source file.

---

## Maintainability

### Grade
A-

### Score
88

### Evidence
The project follows Conventional Commits enforced by `conventionalcommit.json` with automated versioning via `svu`. The 6360-line CHANGELOG.md demonstrates continuous maintenance since at least 2020, with well-categorized entries. Flyway manages 86 SQL migrations and 5 Kotlin migrations covering both the main database and the tasks database, enabling reproducible schema evolution since 2020.

Typed configuration via `KomgaProperties` (annotated with `@ConfigurationProperties`, `@Validated`) prevents raw `process.env` access patterns. `KomgaSettingsProvider` provides runtime-mutable settings with database persistence. Error codes are documented in `ERRORCODES.md` with 39 codes, including properly deprecated entries.

Domain exceptions are purpose-built (`CodedException`, `MediaNotReadyException`, `MediaUnsupportedException`, `DirectoryNotFoundException`, etc.) instead of raw strings or generic exceptions, and `CodingRulesTest` enforces this via ArchUnit. Lifecycle services (e.g., `BookLifecycle`, `SeriesLifecycle`, `LibraryContentLifecycle`) use the `measureTime` Kotlin function for timing without scattered boilerplate.

The webui uses Vuex store (`store.ts`) with a large flat state structure that represents a maintainability trade-off: while Vuex is appropriate for Vue 2, the `store.ts` file contains extensive untyped state (collections, libraries, books, dialogs, announcements) in a single flat module, making it harder to navigate than a modular store.

### Assessment
Maintainability is strong. The combination of conventional commits, typed configuration, ArchUnit enforcement, error code documentation, and Flyway-managed schema evolution sets a high bar. The main detractor is the Vue 2 frontend with a large flat Vuex store and minimal frontend test coverage, which creates a maintainability gap between backend and frontend quality. The backend maintainability is genuinely excellent.

---

## Modularity

### Grade
A-

### Score
87

### Evidence
Domain persistence is defined as interfaces in `domain/persistence/` (23 interface files) and implemented in `infrastructure/jooq/main/` (25+ DAO files). This means the domain layer has zero direct JOOQ dependency, testable in isolation via mock implementations. The architecture test `SlicesIsolationRulesTest` mechanically prevents the `rest`, `kobo`, `opds`, `kosync`, and `sse` controller packages from depending on each other.

Media container handling is pluggable: `DivinaExtractor` is a list of extractors injected into `BookAnalyzer`, allowing different archive format handlers (ZIP, RAR, RAR5) without modifying the analyzer. Similarly, `SidecarBookConsumer` and `SidecarSeriesConsumer` are injected lists for pluggable sidecar processing.

The `komga-tray` module is a separate Gradle subproject for the desktop tray application, cleanly separating the server from the UI wrapper. The webui is a separate npm project built and embedded at compile time.

The separation of two SQLite databases (main + tasks) with separate Flyway migrations, separate JOOQ code generation, and separate DSLContext instances (`dslContextRO`, `sqliteDataSourceRW`) shows thoughtful data separation at the infrastructure level.

One cross-layer concern: `BookDtoDao` in `infrastructure/jooq/main/` directly imports DTO classes from `interfaces/api/rest/dto/` (e.g., `BookDto`, `BookMetadataDto`). This means the infrastructure layer has a dependency on the interface DTO layer, which is a slight layering violation.

### Assessment
Modularity is strong. The repository pattern cleanly separates domain from persistence, the pluggable extractor/consumer pattern allows format extension without core changes, and the multi-module Gradle structure separates concerns at build level. The one notable issue is the `BookDtoDao` importing interface-layer DTOs directly, bypassing the usual domain-only dependency in the infrastructure layer - this is a pragmatic efficiency decision that avoids a mapping layer but introduces cross-layer coupling.

---

## Code Quality

### Grade
B+

### Score
83

### Evidence
Kotlin is used idiomatically: data classes for domain models (`Book`, `KomgaUser`, `DomainEvent.*`), sealed classes for polymorphic structures (`SearchCondition.Book`, `SearchCondition.Series`, `DomainEvent`), `sealed class` for event types, extension functions in `LanguageUtils.kt` and `language/` package. The `@delegate:Transient` annotation on `Book.path` and `KomgaUser.isAdmin` shows attention to serialization concerns.

No stdout/stderr misuse was found (confirmed by the `CodingRulesTest` ArchUnit rule and grep verification). Logging uses `io.github.oshai:kotlin-logging-jvm` throughout, with structured log entries in lifecycle services. Custom validation annotations (`NullOrBlankOrISBN`, `NullOrBlankOrBCP47`, `BCP47`, `NullOrNotBlank`) extend Jakarta validation cleanly.

The `SearchCondition` DSL uses `@JsonTypeInfo(use = JsonTypeInfo.Id.DEDUCTION)` for polymorphic deserialization, supporting a rich query model without inheritance complexity. `BookSearch` and `SeriesSearch` wrap conditions cleanly.

The webui service files (e.g., `komga-books.service.ts`) use verbose try-catch blocks with manual error message concatenation rather than a centralized Axios interceptor. The Vue 2 store in `store.ts` uses untyped Vuex state with string-based getters/mutations, which is standard for Vue 2 Vuex but notably less safe than Vue 3 alternatives.

The API key generator uses UUID v4 without dashes, which provides 122 bits of entropy - adequate but not as robust as purpose-built token formats.

### Assessment
Backend code quality is high, with idiomatic Kotlin, well-structured custom exceptions, enforced coding conventions via ArchUnit, and zero stdout leakage. The frontend shows age: Vue 2 with Vuex 3, minimal TypeScript strictness in service files, and repetitive error handling patterns. The gap between backend code quality and frontend code quality is noticeable, though the backend is the primary engineering surface for a media server.

---

## Testing

### Grade
B

### Score
77

### Evidence
97 Kotlin test files covering: architecture (4 files with ArchUnit), domain model (8 files), domain service (5 files), infrastructure/jooq (20 files for DAO layer), infrastructure/mediacontainer (10 files for EPUB/PDF/divina/RAR parsers), infrastructure/search (4 files), infrastructure/kobo (2 files), and interfaces/api/rest (18 controller test files) and interfaces/api/kobo + kosync + opds.

Tests use `@SpringBootTest` with full application context (60 test classes use this annotation), indicating heavy integration testing rather than unit testing. `@MockkBean` and `@SpykBean` from `springmockk` are used selectively. Controller tests use `MockMvc` with real Spring Security via `SecurityMockMvcRequestPostProcessors.user()`.

`ApiKeyTest` validates the full API key authentication flow end-to-end. `BookControllerTest` covers pagination, metadata updates, deletion, and thumbnail management. `BookDtoDaoTest` includes parameterized search tests covering complex filter combinations. `DomainDrivenDesignRulesTest`, `SlicesIsolationRulesTest`, `CodingRulesTest`, and `NamingConventionTest` are automated architecture conformance tests that run as part of `./gradlew build`.

Frontend test coverage is very thin: 3 spec files covering `PageLoader`, table of contents logic, and book spreads calculations - none covering components or service layer.

JMH benchmarks exist in the `benchmark` source set (`benchmarkSourceSet`) with `kotlinx.coroutines` and `jmh-core` dependencies, suggesting performance regression monitoring capability.

### Assessment
Test quality on the backend is B-tier: integration test coverage is broad and the ArchUnit architecture tests are a genuine strength uncommon in open-source projects. The heavy reliance on `@SpringBootTest` means tests are slow and brittle to application context changes, and unit test isolation is minimal. The absence of meaningful frontend tests is the main gap. The JMH benchmark infrastructure demonstrates performance consciousness.

---

## Documentation

### Grade
B+

### Score
82

### Evidence
API documentation: SpringDoc OpenAPI is configured via `OpenApiConfiguration.kt` with full tag taxonomy (30+ named tags), and `docs/` contains generated OpenAPI specifications. Individual controller methods use `@Operation(summary = ...)` annotations consistently across `BookController`, `SeriesController`, `UserController`.

Developer documentation: `DEVELOPING.md` covers setup, Spring profiles, Gradle tasks, and frontend/Docker development. `CONTRIBUTING.md` sets issue reporting expectations. `ERRORCODES.md` provides a machine-readable error code registry. `PRIVACY.md` and `DOCKERHUB.md` serve specific audiences.

The 6360-line `CHANGELOG.md` with semantic versioning entries provides a complete operational change history. Architecture decisions are implicit in the ArchUnit test names and comments (e.g., the commented-out Kobo session management code with an explanation of why it was disabled: "Kobo error: Invalid JSON script" from device quirk).

Code comments are sparse but appropriate: non-obvious decisions are explained (the WEBP reader priority selection in `ImageConverter.chooseWebpReader()`, the `KOMGA_TOKEN_PREFIX` handling in `KomgaSyncTokenGenerator`). There is no architecture decision record (ADR) directory.

### Assessment
Documentation is good for a community project. The OpenAPI generation pipeline producing machine-readable specs, combined with the ERRORCODES registry and structured CHANGELOG, provides operational clarity. The lack of ADRs means architectural decisions (e.g., why SQLite over PostgreSQL, why Lucene over database FTS) are undocumented beyond implicit code structure. DEVELOPING.md is comprehensive for contributor onboarding.

---

## Performance Design

### Grade
B+

### Score
82

### Evidence
The most significant performance design is the read/write DataSource split for SQLite: `DataSourcesConfiguration` creates separate `sqliteDataSourceRW` (write pool, size 1) and `sqliteDataSourceRO` (read pool, configurable size) when `shouldSeparateReadFromWrites()` is true. `SplitDslDaoBase` exposes `dslRW` and `dslRO` contexts, and `BookDtoDao` uses `dslRO` for all read operations and `dslRW` for writes - a pattern applied consistently across all DAOs.

ETag caching is implemented via `EtagFilterConfiguration` which installs a `ShallowEtagHeaderFilter` on `/api/*`, `/opds/*`, `/kobo/*`, excluding binary file download paths. Static assets use `CacheControl.maxAge(365, TimeUnit.DAYS)` for CSS/fonts/JS, while HTML and manifest use `noStore`.

Lucene full-text search with multilingual (`MultiLingualAnalyzer`, `MultiLingualNGramAnalyzer`) and async commit (`LuceneAsyncCommitter`) avoids synchronous index commits on every update. Batch operations use a configurable `batchChunkSize` (default 1000) for chunked inserts.

The task queue uses a SQLite-backed durable queue with configurable thread pool size (`taskPoolSize`). The `TempTable` abstraction creates temporary SQLite tables for large IN-clause queries (e.g., Lucene search results fed into book DAO queries), avoiding bind parameter limits.

Image processing: Thumbnailator handles resizing, ImageIO plugin selection prioritizes `nightmonkeys` WebP reader over alternative providers. Thumbnails are stored as blobs in the database.

Session storage uses in-memory Caffeine cache (not Redis), which constrains horizontal scaling but is appropriate for the single-instance deployment model.

### Assessment
Performance design is thoughtfully appropriate for the deployment target (single-instance, local network, SQLite). The read/write pool separation, ETag caching, Lucene async commits, and temp table for large query sets show deliberate optimization thinking. The SQLite choice constrains peak throughput and multi-instance deployment, but is a documented intentional design decision for simplicity. There is no HTTP response compression configuration visible, and pagination is always required but no limit-enforcement is apparent for unpaged queries.

---

## Developer Experience

### Grade
A-

### Score
87

### Evidence
CI runs on all three platforms (ubuntu-latest, macos-latest, windows-latest) via the `tests.yml` workflow with `fail-fast: false`, catching cross-platform regressions. The webui job builds and runs its unit tests separately. Test results are uploaded as artifacts with JUnit report generation via `mikepenz/action-junit-report`.

IntelliJ IDEA run configurations are committed to `.idea/runConfigurations/` covering `bootRun__dev`, `bootRun__dev_noclaim`, `bootRun__dev_localdb_noclaim_oauth2`, and `bootRun__dev_demo_noclaim` - enabling one-click local development without command memorization.

Dependabot monitors npm (weekly), Gradle komga (weekly), Gradle komga-tray (weekly), and GitHub Actions (weekly). Conventional Commits with `conventionalcommit.json` and `svu` enable automated semantic versioning. The release workflow is fully automated: version bump, CHANGELOG generation via JReleaser, GitHub release, Docker push, and MS Store submission in one workflow.

Spring dev profile disables periodic scanning, enables in-memory database, and sets up CORS for the frontend dev server at `localhost:8081`. `DEVELOPING.md` documents all of this. The `noclaim` profile automatically creates default admin/user accounts for fresh starts.

KTLint is integrated (`runKtlintFormatOverMainSourceSet`, `runKtlintCheckOverMainSourceSet`) and code style is persisted in `.idea/codeStyles/`. The `.editorconfig` at root and in webui enforces consistent editor behavior.

### Assessment
Developer experience is excellent. The combination of three-OS CI, committed IDE configs, automated release pipeline, Dependabot, KTLint integration, and clear Spring profiles for local dev represents a mature DevEx posture. The only gaps are the lack of a local Docker compose file for server development and the somewhat manual frontend build integration into the Gradle lifecycle.

---

## Long-Term Sustainability

### Grade
B+

### Score
83

### Evidence
Technology stack: Kotlin with Spring Boot 3.5, JDK 21 (LTS), Flyway for migrations, and jOOQ for type-safe SQL - all actively maintained with long roadmaps. Spring Boot 3.5 targets JDK 21 and represents the current stable LTS combination. Dependabot ensures dependency freshness.

The SQLite database choice provides durability (WAL mode configurable) and simplicity for single-instance deployment but creates a ceiling: no horizontal scaling, no cloud-native deployment to Kubernetes with shared storage, and SQLite's write serialization limits throughput under concurrent library scans. The two-database split (main + tasks) partially mitigates write contention.

The `bestbefore-processor-kotlin` KSP annotation processor (`if (version.toString().endsWith(".0.0"))`) appears to enforce deprecation deadlines - a mature pattern for managing API evolution.

The frontend uses Vue 2 and Vuex 3. Vue 2 reached end-of-life in December 2023. The webui is currently using a framework past its maintenance window, which creates a technical debt burden. The `komga-webui/package.json` shows `vue: ^2.6.14` and the entire webui would require migration to Vue 3 for long-term sustainability.

The multi-interface support (REST API, OPDS v1/v2, Kobo sync, KOReader sync, SSE events) demonstrates the breadth of integrations maintained. The SSE-based real-time update system is a durable design that does not require WebSocket upgrade complexity.

GitHub Sponsor/funding configuration in `.github/FUNDING.yml` suggests the project has sustainable contributor funding.

### Assessment
Long-term sustainability is solid on the backend. The technology stack is current, migrations are well-managed, and the conventional commit + automated release pipeline reduces maintenance friction. The significant sustainability concern is Vue 2 reaching end-of-life: the entire webui technology stack needs migration to Vue 3 (and likely Pinia over Vuex, TypeScript Composition API). This is a known open-source pattern where backend maturity outpaces frontend modernity. The SQLite ceiling is acceptable for the project's stated deployment target but would prevent enterprise adoption.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Very High |
| Security Posture | Strong |
| Maintainability | Very High |
| Modularity | High |
| Test Confidence | Moderate-High |
| Documentation Quality | Good |
| Production Readiness | High |
| Enterprise Suitability | Moderate |
| Contributor Friendliness | Very High |
| Sustainability | Good |

---

# Final Verdict

## Overall Grade
B+

## Overall Score
84

## Confidence Score
88

## Repository Maturity
Mature Project

## Best Attribute
Architecture (mechanically enforced DDD with ArchUnit architecture tests)

## Weakest Attribute
Testing (thin frontend test coverage, heavy SpringBootTest coupling)

## Three-Paragraph Assessment

Komga is an engineering standout in the media server open-source space. The backend demonstrates architectural discipline that exceeds what is typical for community projects: a clean domain-driven design with ArchUnit-enforced rules preventing domain model pollution, repository interfaces decoupling domain from jOOQ persistence, and sealed class event hierarchies enabling decoupled SSE broadcasting and task coordination. The security implementation - BCrypt passwords, SHA-512 API key hashing, multiple Spring Security filter chains for REST/Kobo/KOReader, per-user content restrictions enforced at the query layer - is thorough and professionally implemented. No hardcoded secrets, no stdout misuse, and no generic exception throws were found across 430 Kotlin source files, with all three confirmed by ArchUnit tests that run on every build.

The architectural maturity is reflected in intentional design decisions: two separate SQLite databases (main + tasks) with independent Flyway migrations and JOOQ code generation, read/write connection pool separation, async Lucene commits, temporary tables for large IN-clause queries, and pluggable media format extractors and sidecar consumers. The release pipeline - conventional commits, automated semantic versioning via svu, JReleaser for Docker/GitHub/MS Store release, and three-OS CI - represents a professional delivery process uncommon in single-maintainer projects. The committed IntelliJ run configurations and detailed DEVELOPING.md demonstrate genuine care for contributor experience.

The primary sustainability liability is the Vue 2 frontend. Vue 2 reached end-of-life in December 2023, and the webui's flat Vuex store, minimal TypeScript coverage across 232 TypeScript/Vue files, and 3-file frontend test suite creates mounting technical debt. This is a common pattern in long-running backend-first projects but represents real risk as browser toolchains and library ecosystems diverge from the Vue 2 era. The SQLite single-instance architecture is appropriate for the stated deployment model but prevents enterprise or cloud-native adoption. Within its deployment envelope, Komga represents mature engineering with deliberate trade-offs clearly executed.
