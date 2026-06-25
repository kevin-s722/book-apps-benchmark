# Executive Summary

## Repository: grimmory
## Model: ChatGPT 5.5 (xhigh)

## Overall Score

Score: 82/100  
Grade: B  
Confidence: 88/100

Repository Maturity:

- Production Ready

Grimmory is a large, production-oriented self-hosted library application with a Spring Boot backend, Angular frontend, Flyway-managed relational schema, background task system, metadata pipeline, built-in readers, Kobo and KOReader integrations, OPDS and Komga-compatible APIs, CI workflows, Docker image build, Helm chart, and compose-based deployment. The strongest signals are the breadth of implementation, active test coverage, build and release automation, and concrete operational design.

The score is limited by several large service and component hotspots, a few security-sensitive authorization inconsistencies in bulk book mutation paths, permissive default CORS behavior, and reliance on very new platform versions and native-library integrations. These are not structural failures, but they lower confidence relative to a smaller, more uniformly bounded production codebase.

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | grimmory |
| Repository Path | `~/Workspace/grimmory` |
| Total Files | 3,365 excluding `.git` |
| Source Files | 1,721 implementation Java, TypeScript, HTML, and SCSS files |
| Test Files | 576 test files: 199 backend JUnit tests, 376 frontend specs, 1 Playwright spec |
| Source LOC | 236,416 implementation LOC in counted Java, TypeScript, HTML, and SCSS files |
| Test LOC | 113,252 test LOC in counted test files |
| Languages | Java, TypeScript, HTML, SCSS, SQL, YAML, shell, Kotlin Gradle DSL |
| Dependency Count | 116 direct dependency declarations: 47 backend Gradle, 63 frontend package, 6 release tooling |
| Largest Module | `backend/src/main/java/org/booklore/model` with 393 Java files; largest frontend feature folders are settings, book, readers, and stats |
| Build System | pnpm workspace, Angular CLI, Vitest, Playwright, Gradle Kotlin DSL, Spring Boot plugin, Justfiles |
| CI/CD Present | Yes: 13 GitHub Actions workflows including tests, lint thresholds, CodeQL, migration check, packaging smoke test, releases |
| Containerization Present | Yes: multi-stage `Dockerfile`, compose files, Helm chart, Podman quadlet files |
| Test-to-Source Ratio | 0.33 by file count |
| Database Migrations | 140 Flyway SQL migrations under `backend/src/main/resources/db/migration` |

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | B | 84 | Strong full-stack architecture with clear backend/frontend layering, background tasks, metadata pipelines, and deployment packaging, offset by large core classes and broad service responsibilities. |
| Security | C | 73 | Deep authentication and protocol coverage with JWT, OIDC, API filters, WebSocket checks, and access aspects, offset by concrete authorization gaps in bulk book mutation flows and permissive defaults. |
| Maintainability | B | 79 | Good test volume, typed build configuration, mappers, DTOs, and domain helpers, limited by several very large services/components and high model/service package density. |
| Modularity | B | 83 | Good registry/factory patterns for processors, metadata writers, parsers, and tasks, with some coupling pressure from shared model entities and large orchestration services. |
| Code Quality | B | 80 | Generally defensive, transaction-aware, and modern code, with high complexity hotspots, some duplicated concepts, and mixed exception/logging idioms. |
| Testing | B | 86 | Broad backend and frontend unit coverage plus CI test execution, migration checks, and one browser smoke spec; end-to-end workflow breadth and enforced coverage gates are limited. |
| Documentation | B | 77 | Solid repository, development, release, security, API, deployment, and Playwright harness documentation, but implementation-level architecture guidance is uneven. |
| Performance Design | B | 84 | Strong attention to database, virtual threads, caching, file scanning, debounce, streaming, and frontend virtualized rendering, with residual risk from large in-memory workflows. |
| Developer Experience | A | 88 | Strong local and CI workflows through Justfiles, package scripts, Gradle tasks, pinned Actions, Docker, Helm, OpenAPI export, and dependency automation. |
| Long-Term Sustainability | B | 81 | Production-capable project structure with migrations, release automation, and test breadth, balanced by bleeding-edge platform choices and sizable complexity hotspots. |

# Deep Assessment

## Architecture

## Grade

B

## Score

84/100

## Evidence

- Backend entry point `backend/src/main/java/org/booklore/BookloreApplication.java` uses Spring Boot with scheduling and typed configuration properties.
- `backend/build.gradle.kts` targets Java 25, Spring Boot 4.1.0, Hibernate ORM 7.4.1, Flyway, OpenAPI export, Jacoco, dependency locking, and frontend asset integration into the backend jar.
- Backend package structure includes controllers, services, repositories, entities, mappers, security filters, task abstractions, file processors, metadata providers, and Kobo/KOReader/OPDS/Komga integrations.
- `backend/src/main/resources/application.yaml` configures virtual threads, Hikari pool sizing, compression, multipart limits, Hibernate batching, query timeouts, and `open-in-view: false`.
- The library subsystem spans `LibraryService`, `LibraryProcessingService`, `LibraryWatchService`, `LibraryFileEventProcessor`, `BookFileTransactionalHandler`, and `BookFilePersistenceService`, showing explicit architecture for scanning, event debouncing, file recovery, and transactional persistence.
- The metadata subsystem uses `MetadataExtractorFactory`, `MetadataWriterFactory`, provider parsers such as `GoogleParser`, `MetadataRefreshService`, `BookMetadataService`, and `BookMetadataUpdater`.
- The frontend uses Angular standalone routing in `frontend/src/app/app.routes.ts`, lazy route imports, route guards, shared services, TanStack Angular Query services, and feature folders for books, readers, settings, stats, metadata, and device integrations.
- `Dockerfile` builds frontend and backend in separate stages, copies the Angular build into the backend jar resources, installs runtime tools, exposes a healthcheck, and runs a slim Java runtime image.
- Architecture hotspots include `AppBookService.java` at 1,293 lines, `EpubMetadataWriter.java` at 1,237 lines, `cbx-reader.component.ts` at 2,335 lines, and `pdf-reader.component.ts` at 1,719 lines.

## Assessment

The architecture is substantially above average for a self-hosted library system. It has a real backend domain model, explicit persistence layer, protocol adapters, background task abstraction, file-system event processing, metadata extraction and writing, frontend route-level separation, deployment packaging, and CI integration. The backend and frontend are not merely structured by framework convention; they contain domain-specific mechanisms for library scanning, metadata refresh, reader state, sync adapters, and cache updates.

The main architectural weakness is concentration of responsibility in several large orchestration classes and reader components. The system is modular in important areas, but some central flows still combine authorization, persistence, metadata transformation, cache enrichment, file mutation, and external integration logic in classes that are hard to reason about end to end. This reduces architectural clarity without invalidating the overall design.

## Security

## Grade

C

## Score

73/100

## Evidence

- `backend/src/main/java/org/booklore/config/security/SecurityConfig.java` defines multiple ordered `SecurityFilterChain`s for OPDS, Komga, KOReader, Kobo, query-token media/download endpoints, WebSockets, API JWT authentication, and static resources.
- `JwtUtils.java` uses Nimbus JWT with HS256, enforces a minimum 32-byte secret, issuer validation, required claims, expiration checks, access tokens, and refresh tokens.
- `JwtAuthenticationFilter.java` and `QueryParameterJwtFilter.java` authenticate bearer and query-token flows against repository-backed users.
- `OidcAuthService.java` and `OidcTokenValidator.java` validate OIDC state, nonce, redirect URI, issuer, audience, `azp`, expiration, issued-at time, `at_hash`, and logout token semantics.
- `AuthRateLimitService.java` implements Caffeine-backed login and refresh rate limiting by IP and username.
- `WebSocketAuthInterceptor.java` requires bearer authentication for CONNECT, limits SUBSCRIBE destinations, rejects SEND frames, and blocks destination traversal strings.
- `BookAccessAspect.java` and `LibraryAccessAspect.java` provide cross-cutting access checks for annotated book and library operations, including admin bypass behavior and content restriction application.
- `BookController.java` annotates many book-specific endpoints with `@CheckBookAccess`, but bulk endpoints such as `/shelves`, `/progress`, `/status`, `/reset-progress`, `/personal-rating`, and `/reset-personal-rating` do not have equivalent controller-level book access annotations.
- `BookUpdateService.validateBooksAndGetExistingProgress()` validates only that requested book IDs exist through `bookRepository.countByIdIn(bookIds)` and then checks the current user's progress records; it does not validate library assignment or content restrictions for bulk status and rating operations.
- `BookUpdateService.assignShelvesToBooks()` validates shelf ownership but loads books through `bookQueryService.findAllWithMetadataByIds(bookIds)` without an equivalent book access check in the inspected code path.
- `ReadingProgressService.updateReadProgress()` loads a book by ID and creates or updates current-user progress without an explicit library/content access check in the inspected service path; `resetProgress()` follows the same existence-plus-progress pattern through `validateBooksAndGetExistingProgress()`.
- `SecurityConfig.corsConfigurationSource()` defaults `app.cors.allowed-origins` to `*`, sets wildcard allowed origin patterns, and enables credentials.
- `KoreaderService.validatePassword()` compares an MD5-derived KOReader password value; this is protocol-compatible behavior but weak as a credential storage and verification scheme.
- `frontend/src/app/shared/service/auth.service.ts` stores access and refresh tokens in `localStorage`.
- `BookMetadataUpdater` includes a thumbnail URL guard against localhost, loopback, and site-local addresses before fetching covers.

## Assessment

The repository has significant security engineering effort. Authentication is not superficial: JWT validation, OIDC validation, rate limiting, WebSocket constraints, specialized device filters, role checks, and cross-cutting access aspects are all present. The code shows awareness of multiple exposed surfaces, including media downloads, device sync protocols, browser WebSockets, metadata fetching, and administrative permissions.

The score is materially reduced by implementation-specific access-control inconsistencies. Several bulk mutation paths for progress, status, personal rating, and shelf assignment operate on book IDs with existence checks and current-user progress or shelf ownership checks, but the inspected service paths do not consistently enforce the same book-library/content access model used by annotated single-book endpoints. Combined with wildcard credentialed CORS by default, query-token media flows, localStorage token persistence, and MD5-based KOReader credentials, the posture is average-to-strong in breadth but not uniformly strong in authorization guarantees.

## Maintainability

## Grade

B

## Score

79/100

## Evidence

- The backend uses explicit controllers, services, repositories, DTOs, mappers, task classes, filters, and configuration packages rather than a single monolithic application layer.
- `backend/src/main/java/org/booklore/model` contains 393 Java files, making it the densest backend package by file count.
- `backend/src/main/java/org/booklore/service` contains 212 Java files, with large orchestration classes including `AppBookService`, `MetadataRefreshService`, `BookMetadataService`, `BookMetadataUpdater`, and `EpubMetadataWriter`.
- The frontend separates feature areas under `frontend/src/app/features`, with large feature folders for settings, book browser, readers, and stats.
- `BookBrowserComponent` delegates selected behavior to helpers and services such as `BookSelectionService`, `BookBrowserQueryParamsService`, `BookBrowserEntityService`, `SortService`, deferred render state, and virtual grid utilities.
- `BookPatchService`, `BookSocketService`, and `book-query-cache.ts` isolate frontend cache mutation and invalidation behavior for book data.
- Flyway migrations are versioned in 140 SQL files, and CI includes a migration check workflow.
- `frontend/playwright/README.md` documents harness-specific testing rules and constraints.
- Naming still carries the older `booklore` Java package and many `BookLore` class names while the runtime product and frontend package are named Grimmory.
- Both `AuthRateLimitService` and `LoginRateLimitService` exist, indicating some conceptual duplication or transition state in authentication rate limiting.

## Assessment

Maintainability is strong overall because the codebase has meaningful separation, typed framework usage, a large amount of test code, explicit migrations, and local abstractions for repeated behaviors. The backend has identifiable domain services, mappers, filters, repositories, task classes, and file-processing helpers. The frontend has feature-level organization and several services that keep data fetching and cache updates out of templates.

The limiting factor is hotspot size and mixed responsibility density. Some classes are large enough to make behavioral changes expensive because each change touches many concerns at once. The model and service packages are also broad, which increases navigation and ownership cost. The old `booklore` naming within the Grimmory repository is not a correctness issue, but it adds cognitive friction.

## Modularity

## Grade

B

## Score

83/100

## Evidence

- `BookFileProcessorRegistry` maps `BookFileType` values to specialized processors, and `AbstractFileProcessor` provides common file processing behavior.
- `EpubProcessor`, `AudiobookProcessor`, and other file-specific components specialize metadata extraction, format validation, sidecar handling, and shell book creation.
- `MetadataExtractorFactory` and `MetadataWriterFactory` centralize file-type-specific extraction and writer selection.
- Metadata providers are implemented as separate parsers, including Google, Goodreads, Hardcover, Amazon, ComicVine, LubimyCzytac, and RanobeDB related code paths.
- `TaskService` registers a list of `Task` implementations, tracks running tasks, supports cancellation, and delegates scheduling to `TaskCronService`.
- Security integration is modularized through filters for JWT, query-parameter JWT, Kobo, KOReader, OPDS, Komga, WebSockets, and API chains.
- Frontend data fetching is split across services such as `AppSettingsService`, `BookService`, `BookPatchService`, `BookSocketService`, and feature-specific services.
- Reader internals include isolated storage and state helpers such as `cbx-reader-storage.ts`, `ReaderStateService`, `ReaderLoaderService`, custom font services, and view-manager services.
- Modularity pressure remains in shared entity/model types and in orchestration services that coordinate many modules directly.

## Assessment

The repository uses multiple effective modularity patterns. Registry and factory structures are present where file formats, metadata providers, writers, and tasks vary by type. Protocol-specific auth and sync integrations are separated rather than fully embedded into generic services. On the frontend, data cache behavior and reader state are partly extracted into focused services and helpers.

The main modularity constraint is coupling around central entities and orchestration services. Many workflows converge through large services that coordinate repositories, mappers, notification services, metadata services, sync services, and file helpers. The design is modular by subsystem, but not always modular inside the busiest subsystem boundaries.

## Code Quality

## Grade

B

## Score

80/100

## Evidence

- Backend services use `@Transactional`, repository abstractions, DTOs, mappers, typed enums, and domain-specific API exceptions.
- The library file handling code includes explicit path accessibility checks, unreadable/zero-byte filtering, file stability checks, move detection, pending delete handling, and hash-based recovery.
- Metadata update code includes lock usage, replace modes, sidecar writing, original-file writeback, cover download handling, and post-update path recalculation.
- Frontend services use Angular signals, RxJS, TanStack Query, guards, interceptors, and cache patching rather than only component-local mutable state.
- `AuthService` implements single-flight refresh behavior and stale refresh response protection.
- `GlobalExceptionHandler` normalizes many backend exception types and hides internal details for generic failures.
- `GoogleParser` contains provider-specific rate limiting and relevance filtering, but logs full Google API URLs, which may expose query contents in logs.
- Long methods and classes are common in metadata, reader, and book browser flows.
- Some comments in reader and progress code explain known constraints, while a small amount of legacy or transition language remains.
- The codebase mixes custom `ApiError` exceptions, direct runtime exceptions in some task/test paths, and framework exceptions.

## Assessment

The code quality is professional in many areas. There is clear use of framework features, transaction boundaries, validation, caching abstractions, repository access, and defensive file-system handling. The frontend uses modern Angular patterns and tests around critical services. The backend has many targeted helpers and service classes with explicit domain names.

The code quality score is held below the architecture and testing scores because complexity is often handled inside large classes rather than consistently decomposed into smaller units. The implementation is generally competent, but some provider, metadata, reader, and update paths are dense enough that correctness depends on careful local reasoning.

## Testing

## Grade

B

## Score

86/100

## Evidence

- The repository contains 576 counted test files and 113,252 counted test LOC.
- Backend tests include 199 JUnit test files across repositories, mappers, services, task implementations, metadata extraction, Kobo integration, KOReader behavior, authentication, rate limiting, file upload, and path pattern resolution.
- Frontend tests include 376 Angular/Vitest specs across auth, interceptors, services, readers, layout, themes, book browser helpers, and UI feature logic.
- `frontend/playwright/login-and-books.spec.ts` provides browser smoke coverage for login and opening the all-books browser with mocked routes.
- `backend/build.gradle.kts` configures Jacoco report generation after tests.
- `frontend/vitest.config.ts` includes `src/**/*.spec.ts`; `frontend/vitest-base.config.ts` configures the shared Vitest environment.
- `frontend/playwright.config.ts` configures Chromium, retries in CI, traces, screenshots, video, and a Justfile-powered web server.
- `.github/workflows/test-suite.yml` runs backend tests and frontend tests in CI, uploads reports, and validates failures.
- `.github/workflows/migrations-check.yml` validates changed Flyway migrations against MariaDB.
- `.github/workflows/angular-lint-threshold.yml` runs typecheck, production build, and lint warning thresholds.
- Coverage thresholds are configurable through the frontend coverage setup, but CI test execution does not visibly enforce a global coverage gate in the inspected workflow.
- Browser-level coverage is narrow, with one Playwright spec focused on login and book browser smoke behavior.

## Assessment

Test investment is one of the repository's strongest traits. The codebase has substantial backend and frontend unit coverage, a migration check, CI wiring for test report publication, and targeted tests around complex areas such as metadata extraction, Kobo behavior, auth flows, file upload, path formatting, and cache-related frontend services.

The main limitation is breadth of end-to-end validation. The browser test harness exists and is disciplined, but only one Playwright spec is present. Coverage gates are available in configuration but not clearly enforced as a universal CI requirement in the inspected workflows. The test base is strong for unit and service-level confidence, with less evidence for full-stack workflow confidence.

## Documentation

## Grade

B

## Score

77/100

## Evidence

- Top-level documentation includes `README.md`, `DEVELOPMENT.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, and `SECURITY.md`.
- Backend and frontend development documentation exists in `backend/DEVELOPMENT.md` and `frontend/DEVELOPMENT.md`.
- Domain and integration documentation exists in `docs/Komga-API.md`, `docs/OIDC-Setup-With-PocketID.md`, `docs/forward-auth-with-proxy.md`, and `docs/komga-clean-mode.md`.
- Release process documentation exists in `docs/MAKING-A-RELEASE.md`.
- Playwright harness rules are documented in `frontend/playwright/README.md`.
- Deployment artifacts include compose, Helm chart, and Podman quadlet files, each giving operational context beyond source code.
- OpenAPI export support is present through backend Gradle scripting.
- The repository contains extensive code, but the inspected documentation set is stronger on setup, contribution, release, deployment, and selected integrations than on internal architecture maps.

## Assessment

Documentation is solid for a production-facing open source application. There are clear documents for setup, contribution process, governance, security policy, development, release flow, Playwright harness constraints, and integrations. Deployment formats are also represented directly in the repository.

The documentation grade is not higher because the deepest implementation areas are not accompanied by equally deep architecture documentation. The repository has enough docs for contributors and operators, but complex subsystems such as metadata refresh, library scanning, reader internals, and protocol adapters rely primarily on code and tests for understanding.

## Performance Design

## Grade

B

## Score

84/100

## Evidence

- `application.yaml` enables virtual threads and keeps Tomcat thread counts low, aligning request handling with the Java runtime model.
- Hikari pool configuration is intentionally small, with comments around virtual-thread burst handling.
- JPA configuration disables open-in-view, fails on pagination over collection fetches, and sets batch and fetch sizes to reduce N+1 behavior and excessive round trips.
- Compression and multipart limits are configured at the backend level.
- Library scanning uses file filters, zero-byte checks, unreadable-file handling, folder audiobook detection, file stability checks, event debouncing, pending delete grace periods, and hash-based move detection.
- `TaskExecutorConfig` sizes task execution, uses a bounded queue, propagates security context, and uses virtual-thread scheduling for scheduled tasks.
- Metadata providers include rate limiting in provider code such as `GoogleParser`.
- Frontend book browsing uses virtual grid utilities, deferred render state, TanStack Query caching, and cache patch helpers to reduce full reload pressure.
- Reader components manage blob URLs, local/session preferences, dynamic loading, and format-specific progress.
- Some flows still perform large list operations or in-memory filtering in application services, and very large reader components create performance reasoning complexity.

## Assessment

Performance design is deliberate and visible across backend, frontend, and deployment. The backend shows awareness of database round trips, batching, connection limits, request threads, scheduled work, file-system load, and long-running tasks. The frontend shows awareness of virtualized browsing, cache updates, deferred rendering, and format-specific reader behavior.

The remaining uncertainty is in large workflows where performance depends on the interaction between repositories, in-memory enrichment, file scans, and metadata processing. The code contains performance controls, but the largest operations are complex enough that their behavior is workload-sensitive.

## Developer Experience

## Grade

A

## Score

88/100

## Evidence

- Root, backend, and frontend Justfiles provide common entrypoints for check, test, build, dev, database, image, and OpenAPI workflows.
- Frontend `package.json` includes build, production build, dev, watch, test, coverage, e2e, typecheck, ESLint, and stylelint scripts.
- Backend `build.gradle.kts` includes Java toolchain setup, dependency management, Jacoco, OpenAPI export, frontend asset integration, and dependency locking.
- `.github/workflows/ci-validate.yml` composes migration checks, reusable test suite, Helm chart linting, and Docker packaging smoke tests.
- `.github/workflows/test-suite.yml` runs backend and frontend test suites and uploads reports.
- `.github/workflows/codeql.yml` runs CodeQL for Actions, Java/Kotlin, and JavaScript/TypeScript, with scheduled execution.
- GitHub Actions are pinned to commit SHAs in the inspected workflows.
- `.github/dependabot.yml` groups and schedules dependency updates for Gradle, npm, and Actions.
- Container and deployment support includes `Dockerfile`, `deploy/compose/docker-compose.yml`, `dev.docker-compose.yml`, Helm chart files, and Podman quadlet files.
- Frontend Playwright harness rules are documented and port-safe.

## Assessment

Developer experience is excellent. The repository gives developers and CI systems repeatable entrypoints for building, testing, linting, checking migrations, validating charts, exporting OpenAPI, and building container images. The workflow design is broad enough to catch regressions across backend, frontend, database migrations, packaging, and deployment templates.

This is the highest-scoring category because the repository has the practical tooling expected from a production-maintained project. The only meaningful limit is the inherent complexity of the system: many technologies, runtime tools, native dependencies, and environment variants are involved.

## Long-Term Sustainability

## Grade

B

## Score

81/100

## Evidence

- The repository combines backend, frontend, database migrations, release tooling, deployment artifacts, documentation, and CI automation in a single coherent codebase.
- Flyway migrations are versioned and checked in CI when migration files change.
- Dependabot is configured for Gradle, npm, and GitHub Actions.
- Release workflows and `docs/MAKING-A-RELEASE.md` indicate an operational release process.
- Tests cover many of the highest-risk code paths, including metadata, readers, auth, mappers, repositories, file upload, and device sync.
- The Dockerfile and deployment templates support production packaging across CPU architectures.
- The backend targets Java 25 with preview features enabled, and the frontend targets Angular 21 with several very recent dependency versions.
- Native and external tool dependencies include PDFium-related packages, epub libraries, ffprobe, kepubify, and libarchive.
- Large core classes and broad model/service packages increase future change cost.
- Security policy and governance documentation exist, but the inspected `SECURITY.md` is general-purpose rather than deeply tied to concrete support windows in code.

## Assessment

The repository has the foundations of a sustainable production project: migrations, CI, tests, release workflows, deployment templates, documentation, dependency automation, and broad implementation coverage. These are strong indicators that the project can continue to evolve without depending entirely on local knowledge.

Sustainability is moderated by complexity and platform risk. The codebase sits on very current Java, Spring, Angular, and TypeScript versions, uses native runtime components, and contains large domain hotspots. The project is production-capable, but its long-term maintenance burden is non-trivial.

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Strong |
| Security Posture | Moderate |
| Maintainability | Strong |
| Modularity | Strong |
| Test Confidence | Strong |
| Documentation Quality | Moderate-Strong |
| Production Readiness | Strong |
| Enterprise Suitability | Moderate-Strong |
| Contributor Friendliness | Strong |
| Sustainability | Strong |

# Final Verdict

## Overall Grade

B

## Overall Score

82/100

## Confidence Score

88/100

## Repository Maturity

Production Ready

## Best Attribute

Developer Experience

## Weakest Attribute

Security

## Three-Paragraph Assessment

1. Engineering quality: Grimmory is a well-engineered production application with substantial implementation depth. The backend handles complex library, metadata, reader, device sync, task, and file-system workflows, while the frontend uses modern Angular patterns, caching services, route guards, and a large test base. The repository also has unusually strong build, CI, container, and deployment support for a self-hosted application.

2. Architectural maturity: The architecture is mature enough to support real production use. It separates many subsystems correctly and uses factories, registries, service layers, repository layers, task abstractions, migration workflows, and frontend feature modules. The maturity is reduced by several large classes and high-responsibility services that make some central flows harder to audit and evolve.

3. Long-term sustainability: The project has strong sustainability assets: extensive tests, versioned migrations, dependency automation, pinned CI workflows, release documentation, Docker and Helm support, and a coherent full-stack build. The long-term risk profile is shaped by fast-moving platform versions, native dependencies, large reader and metadata components, and security-sensitive access-control paths that require careful ongoing attention.

Assessment caveat: this run performed code, test, build, CI/CD, and containerization inspection plus repository statistics collection. It did not execute the full local build or test suite.
