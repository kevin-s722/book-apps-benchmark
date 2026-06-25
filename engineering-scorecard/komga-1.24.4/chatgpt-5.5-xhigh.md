# Executive Summary
## Repository: komga
## Model: ChatGPT 5.5 (xhigh)

## Overall Score
Score: 81/100  
Grade: B  
Confidence: 88/100

Repository Maturity: Mature Project

---
## Repository Statistics
| Metric | Value |
|---|---:|
| Total repository files inspected by inventory | 1,134 |
| Implementation files counted | 668 |
| Required implementation coverage floor | 134 files |
| Implementation coverage used | Greater than 134 files through direct reads and targeted content scans |
| Test files counted | 100 |
| Test-to-implementation file ratio | 15.0% |
| Backend Kotlin implementation files | 430 |
| Web UI implementation files | 233 |
| Tray implementation files | 5 |
| Flyway migration files | 91 |
| OpenAPI paths / schemas | 130 / 167 |
| Backend dependency declarations | 63 |
| Web UI dependencies / dev dependencies | 27 / 37 |
| Largest backend package by file count | `komga/src/main/kotlin/org/gotson/komga/infrastructure` with 159 Kotlin files |
| Largest implementation files observed | `Opds2Controller.kt` 934 lines, `SeriesController.kt` 878 lines, `KoboController.kt` 842 lines, `OpdsController.kt` 820 lines, `BookController.kt` 770 lines |

Evidence collection covered backend implementation, frontend implementation, tests, Gradle and npm manifests, CI/CD workflows, Docker packaging, generated OpenAPI output, migrations, and documentation. Scoring was performed after the evidence collection and consolidation phases.

---
## Scorecard
| Category | Grade | Score | Summary |
|---|---:|---:|---|
| Architecture | A | 86 | Strong layered Spring/Kotlin monolith with domain lifecycle services, repository interfaces, jOOQ infrastructure, evented task processing, and multiple API interfaces. Large controllers and lifecycle classes limit architectural sharpness. |
| Security | B | 78 | Solid authentication, authorization, API-key, OAuth/OIDC, content restriction, and query scoping controls. Web CSRF/session tradeoffs, URL API keys for Kobo, unsalted SHA-512 API-key storage, and permissive operational configuration reduce the score. |
| Maintainability | B | 74 | Clear package organization, typed models, migrations, and broad backend tests are offset by very large controllers/services and legacy frontend patterns. |
| Modularity | B | 82 | Domain, infrastructure, interface slices, media extraction, tasks, and frontend services are separated well. Some modules still aggregate many responsibilities. |
| Code Quality | B | 80 | Kotlin code is generally idiomatic and strongly typed, with DTO validation and structured persistence. Weaknesses include broad catches, some unsafe/null-heavy edges, repeated frontend error handling, and older Vue 2 Options API style. |
| Testing | B | 84 | Strong backend unit, integration, DAO, API, media, and ArchUnit coverage with multi-OS CI. Frontend tests are sparse and CI does not visibly enforce coverage thresholds. |
| Documentation | B | 76 | README, development guide, privacy notes, error codes, Docker Hub notes, and generated OpenAPI docs provide good operational context. Internal architectural documentation is limited. |
| Performance Design | B | 82 | Uses Lucene, SQLite indexes, jOOQ temp-table batching, read/write data sources, task queues, and streaming downloads. Some page/resource paths materialize byte arrays and PDF rendering is per-request. |
| Developer Experience | B | 81 | Gradle wrapper, version catalog, npm scripts, CI, release automation, Docker packaging, OpenAPI generation, and ktlint support are present. Build complexity and limited web lint/test enforcement lower confidence. |
| Long-Term Sustainability | B | 80 | Mature release flow, migrations, architecture tests, localization, and broad backend coverage support longevity. Large legacy frontend/backend surfaces add ongoing maintenance cost. |

---
# Deep Assessment

## Architecture
## Grade
A

## Score
86/100

## Evidence
- `komga/src/main/kotlin/org/gotson/komga/Application.kt` defines the Spring Boot entry point with scheduling enabled and application-level jOOQ flags.
- Domain lifecycle services such as `LibraryLifecycle.kt`, `LibraryContentLifecycle.kt`, `BookLifecycle.kt`, `SeriesLifecycle.kt`, `MetadataAggregator.kt`, `MetadataApplier.kt`, and `FileSystemScanner.kt` hold core library, scan, metadata, thumbnail, read-progress, and filesystem behavior.
- Repository interfaces under `domain/persistence` separate domain services from storage implementations. jOOQ implementations such as `BookDao.kt`, `SeriesDao.kt`, `LibraryDao.kt`, `BookDtoDao.kt`, `SeriesDtoDao.kt`, and `TasksDao.kt` implement persistence and DTO read models.
- `SearchContext.kt`, `BookSearchHelper.kt`, `SeriesSearchHelper.kt`, and `ContentRestrictionsSearchHelper.kt` centralize user/library/content filtering for queries.
- `TaskEmitter.kt`, `TaskProcessor.kt`, `TaskHandler.kt`, and `Task.kt` form an application task pipeline for scanning, metadata refresh, conversion, indexing, and deletion.
- Interface packages implement distinct API surfaces: REST controllers (`BookController.kt`, `SeriesController.kt`, `LibraryController.kt`), OPDS controllers, Kobo sync (`KoboController.kt`), and KOReader sync (`KoreaderSyncController.kt`).
- ArchUnit tests in `DomainDrivenDesignRulesTest.kt` and `SlicesIsolationRulesTest.kt` enforce domain isolation and interface slice isolation.

## Assessment
Komga has a mature layered architecture for a self-hosted media server. The domain layer contains meaningful behavior rather than anemic CRUD wrappers, and persistence is kept behind repository contracts with jOOQ implementations in infrastructure. Query scoping through `SearchContext` and helper classes gives API-level features a consistent path into storage authorization and filtering.

The architecture also handles multiple product interfaces without forcing them through one controller shape: REST, OPDS, Kobo, KOReader, and the web UI each have dedicated interface packages. Background work is modeled explicitly with persisted task records and task handlers, which gives long-running library operations a separate execution path from request handling.

The main architectural constraint is concentration of responsibility in several very large files. `Opds2Controller.kt`, `SeriesController.kt`, `KoboController.kt`, `BookController.kt`, `LibraryContentLifecycle.kt`, and `TaskHandler.kt` are central orchestration points with many branches and collaborators. This does not undermine the overall architecture, but it raises the cost of local reasoning and change isolation.

## Security
## Grade
B

## Score
78/100

## Evidence
- `SecurityConfiguration.kt` defines separate Spring Security filter chains for REST/OPDS/SSE/actuator/oauth, Kobo, and KOReader endpoints.
- REST and OPDS APIs require authentication by default. Actuator endpoints other than health require ADMIN in the security chain.
- `@EnableMethodSecurity(prePostEnabled = true)` is enabled, and controllers use `@PreAuthorize`, including admin controls in `LibraryController.kt`, role-gated download/streaming in `CommonBookController.kt`, and destructive/user management constraints in `UserController.kt`.
- `SearchContext.kt`, `ContentRestrictionChecker.kt`, `BookSearchHelper.kt`, `SeriesSearchHelper.kt`, `BookController.kt`, and `SeriesController.kt` apply per-user library access and content restriction filters.
- Password storage uses `BCryptPasswordEncoder` in `PasswordEncoderConfiguration.kt`.
- API keys are generated in `ApiKeyGenerator.kt`, stored through `KomgaUserLifecycle.kt`, authenticated by `ApiKeyAuthenticationProvider.kt`, and processed by `ApiKeyAuthenticationFilter.kt`, `HeaderApiKeyAuthenticationConverter.kt`, and `UriRegexApiKeyAuthenticationConverter.kt`.
- OAuth/OIDC user handling in `KomgaOAuth2UserServiceConfiguration.kt` checks email presence and optional OIDC email verification before creating users.
- `ClaimController.kt` permits first admin creation only when `countUsers() == 0`.
- `CorsConfiguration.kt` only registers CORS when explicit allowed origins are configured.
- `application.yml` exposes all management endpoints at configuration level and marks shutdown access unrestricted, while the HTTP security chain limits non-health actuator access to ADMIN.
- `http.plugin.ts` configures browser API calls with `withCredentials: true` and `X-Requested-With`.
- `SecurityConfiguration.kt` disables CSRF for session-backed web/API traffic.
- Kobo API keys are extracted from URL paths by `UriRegexApiKeyAuthenticationConverter.kt`; `KoboController.kt` documents this as part of Kobo device behavior.
- `PasswordUpdateDto.kt` validates password presence but does not define password complexity or minimum length.
- The Docker template runs without a non-root `USER` directive and downloads `kepubify` from a latest GitHub release URL during image build.

## Assessment
The security model is substantial. Authentication and authorization are applied at framework level, method level, and query level. User library access and content restrictions are represented in both service checks and query helpers, which is important for a multi-user library product. Passwords use BCrypt, OAuth/OIDC flows handle email conditions, and first-user claiming is bounded by repository state.

The main security tradeoffs are in web session protection and token handling. CSRF is disabled while cookie/session and remember-me mechanisms are present. The browser client sends `X-Requested-With`, but server-side CSRF protection is still disabled. Kobo URL API keys are a compatibility-oriented design, but URL tokens can be exposed through logs, browser history, reverse proxies, or referrers. API keys are stored as SHA-512 digests rather than a keyed hash or password-hash style verifier; the generated token entropy makes brute forcing difficult, but the storage design is less defensive than the password path.

Operational configuration also affects the score. Actuator exposure is guarded by the security chain for non-health endpoints, but `management.endpoints.web.exposure.include: "*"` and unrestricted shutdown access in `application.yml` create a configuration surface that depends on the security chain remaining correct. Container hardening evidence is limited because the Docker template has no non-root runtime user and downloads a latest external binary during build.

## Maintainability
## Grade
B

## Score
74/100

## Evidence
- Package boundaries are clear: `domain`, `infrastructure`, `interfaces`, `application`, and `config`.
- Architecture and coding rules in `CodingRulesTest.kt`, `DomainDrivenDesignRulesTest.kt`, `SlicesIsolationRulesTest.kt`, and `NamingConventionTest.kt` provide automated maintainability guardrails.
- Flyway migrations are split across 91 SQL files under `komga/src/main/resources/db/migration`, and jOOQ code generation is wired through `komga/build.gradle.kts`.
- `LibraryContentLifecycle.kt`, `BookLifecycle.kt`, `SeriesLifecycle.kt`, `TaskHandler.kt`, `BookController.kt`, `SeriesController.kt`, `KoboController.kt`, `OpdsController.kt`, and `Opds2Controller.kt` are large orchestration files with many collaborators.
- Frontend global state in `komga-webui/src/store.ts` and persisted UI state in `plugins/persisted-state.ts` aggregate many unrelated flags, dialogs, and feature settings.
- Frontend views such as `BrowseBooks.vue`, `BrowseSeries.vue`, `DashboardView.vue`, and `EpubReader.vue` mix data loading, routing, settings, keyboard handling, dialogs, and rendering in large Options API components.
- Service wrappers such as `KomgaBooksService.ts`, `KomgaSeriesService.ts`, and `KomgaUsersService.ts` repeat similar axios error-handling patterns.

## Assessment
The backend is maintainable at the package and testing level. Domain and infrastructure boundaries are visible, migrations are systematic, repository contracts keep storage details out of domain services, and automated architecture tests reduce structural drift. The codebase also benefits from Kotlin types, jOOQ generated tables, DTO classes, and explicit API models.

Maintainability weakens at the orchestration edges. Several controllers and lifecycle classes are long enough that feature changes may require reading hundreds of lines of branch-heavy code. The task handler centralizes many operational behaviors in one `when` block. This is manageable for an experienced maintainer but increases the chance of incidental coupling.

The web UI lowers the category score. It is feature rich, but Vue 2 Options API components, global plugin/service usage, and large Vuex state modules make local reasoning harder than in the backend. The code remains coherent, but its maintenance cost is noticeably higher than the architecture itself.

## Modularity
## Grade
B

## Score
82/100

## Evidence
- Domain repository interfaces such as `BookRepository.kt`, `SeriesRepository.kt`, `LibraryRepository.kt`, and `KomgaUserRepository.kt` are implemented by infrastructure DAOs rather than being coupled to controllers.
- `DataSourcesConfiguration.kt`, `KomgaJooqConfiguration.kt`, and `SplitDslDaoBase.kt` isolate database setup, read/write DSL selection, and transaction-aware data source concerns.
- Media processing is split into focused infrastructure components such as `BookAnalyzer.kt`, `ZipExtractor.kt`, `RarExtractor.kt`, `EpubExtractor.kt`, `PdfExtractor.kt`, `ImageConverter.kt`, `ContentDetector.kt`, and `KepubConverter.kt`.
- API integrations have distinct modules: `KoboController.kt`, `KoboProxy.kt`, `SyncPointLifecycle.kt`, and `KoreaderSyncController.kt`.
- Frontend services are separated under `komga-webui/src/services`, reusable UI components under `components`, shared functions under `functions`, and route-level views under `views`.
- `SlicesIsolationRulesTest.kt` enforces that interface slices do not depend on each other.
- `BookController.kt`, `SeriesController.kt`, `KoboController.kt`, and `EpubReader.vue` still combine multiple workflows inside single files.

## Assessment
Komga has strong module boundaries for a monolithic application. Domain behavior, persistence, API interfaces, background tasks, media parsing, and frontend service wrappers are visibly separated. The design supports several protocols and clients without placing all behavior into one generic API layer.

The modularity score is reduced by aggregation at feature boundaries. Controllers often combine search, metadata, thumbnails, read progress, downloads, and destructive actions. Some domain lifecycle classes combine validation, persistence orchestration, event emission, and task scheduling. These modules are internally organized, but the file-level granularity is coarse.

The frontend is modular at the directory level but less modular within major screens. Reader components and utility functions are reusable, while browse/detail views contain broad workflow logic.

## Code Quality
## Grade
B

## Score
80/100

## Evidence
- Kotlin domain models, value objects, and lifecycle services use typed constructors, data classes, sealed task classes in `Task.kt`, and explicit repository contracts.
- DTO validation appears in files such as `LibraryCreationDto.kt`, `LibraryUpdateDto.kt`, `UserCreationDto.kt`, `UserUpdateDto.kt`, and `PasswordUpdateDto.kt`.
- Query code in `BookSearchHelper.kt`, `SeriesSearchHelper.kt`, `BookDtoDao.kt`, and `SeriesDtoDao.kt` is explicit and uses generated jOOQ tables rather than string SQL in application code.
- `ErrorHandlingControllerAdvice.kt` centralizes validation error conversion for REST responses.
- `TaskHandler.kt`, `BookAnalyzer.kt`, `KoboController.kt`, and frontend service wrappers contain broad exception handling in several places.
- Several frontend components use Vue 2 Options API and object-shaped state rather than stricter component-local typing.
- `ItemBrowser.vue` and `EpubReader.vue` include some hard-coded visual values, while most UI implementation follows the existing Vuetify/Vue 2 conventions.
- `CodingRulesTest.kt` prevents standard-stream access, generic exceptions, Java util logging, JodaTime, and field injection.

## Assessment
Backend code quality is generally high. The Kotlin code is explicit, typed, and organized around domain operations rather than low-level database calls. jOOQ usage is detailed and predictable, and DTO validation gives controllers a clear input contract. Architecture tests demonstrate deliberate codebase hygiene.

The main quality issues are complexity and error-handling consistency. Several functions and classes catch broad exceptions to continue long-running operations. That can be appropriate for scanners and background tasks, but it also obscures failure modes. Some controller paths and frontend services repeat similar handling rather than sharing a narrow abstraction.

The frontend quality is adequate but older. Vue 2, Vuex, class-like plugin globals, and Options API components are consistent with the existing application, but they offer less type-locality and composition than the backend code.

## Testing
## Grade
B

## Score
84/100

## Evidence
- 100 test files were counted across backend and frontend test roots.
- Backend architecture tests include `CodingRulesTest.kt`, `DomainDrivenDesignRulesTest.kt`, `SlicesIsolationRulesTest.kt`, and `NamingConventionTest.kt`.
- DAO and repository tests include `BookDaoTest.kt`, `SeriesDaoTest.kt`, `LibraryDaoTest.kt`, `KomgaUserDaoTest.kt`, `TasksDaoTest.kt`, `BookDtoDaoTest.kt`, and `SeriesDtoDaoTest.kt`.
- Domain service tests include `LibraryContentLifecycleTest.kt`, `BookLifecycleTest.kt`, `SeriesLifecycleTest.kt`, `LibraryLifecycleTest.kt`, `MetadataAggregatorTest.kt`, `MetadataApplierTest.kt`, `ReadListMatcherTest.kt`, and `SyncPointLifecycleTest.kt`.
- API tests include `BookControllerTest.kt`, `KoboControllerTest.kt`, `KoreaderSyncControllerTest.kt`, `OpdsControllerTest.kt`, and multiple REST controller tests using Spring Boot and MockMvc.
- Media tests include `ZipExtractorTest.kt`, `RarExtractorTest.kt`, `PdfExtractorTest.kt`, and `KepubConverterTest.kt`.
- Frontend tests are limited to `book-spreads.spec.ts`, `toc.spec.ts`, and `pageLoader.spec.ts`.
- `.github/workflows/tests.yml` builds and tests the backend on Ubuntu, macOS, and Windows, and builds/tests the web UI on Ubuntu.
- `komga/build.gradle.kts` applies Jacoco, but no enforced coverage threshold was observed.

## Assessment
Backend verification is strong. The tests cover architecture rules, domain lifecycle behavior, database persistence, API behavior, media extraction, authentication-related behavior, and integration workflows. `BookControllerTest.kt` exercises library access and content restrictions through MockMvc, and `LibraryContentLifecycleTest.kt` covers realistic scan/update/delete scenarios with mocked scanners and analyzers.

CI coverage is also credible because backend builds run on multiple operating systems. This matters for a media server that handles filesystem paths, archive formats, process execution, and packaging.

The frontend is the clear testing gap. Web tests cover pure utility logic such as spread generation and page loading, but there is little evidence of component, router, store, accessibility, or browser-level reader coverage in the repository. No coverage threshold enforcement was visible in the inspected configuration.

## Documentation
## Grade
B

## Score
76/100

## Evidence
- `README.md` describes the product, major features, installation/documentation links, development link, translation status, and support channels.
- `DEVELOPING.md` documents Java/Node requirements, project organization, Spring profiles, Gradle tasks, frontend development server setup, and Docker build flow.
- `ERRORCODES.md` provides a table of application error codes and descriptions.
- `PRIVACY.md` explains self-hosted data behavior and stored authentication metadata.
- `DOCKERHUB.md` provides Docker Hub usage context and official documentation links.
- `CONTRIBUTING.md` gives issue-reporting and community contribution guidance.
- `komga/docs/openapi.json` contains a generated OpenAPI 3.1 document with 130 paths and 167 schemas.
- `OpenApiConfiguration.kt`, `AuthorsAsQueryParam.kt`, and `PageableAnnotations.kt` show explicit OpenAPI support in source.

## Assessment
The repository has good operational and user-facing documentation. A new contributor can identify the project structure, development profiles, build tasks, frontend/server relationship, Docker packaging path, error code meanings, and API surface. The generated OpenAPI document is a significant documentation asset for API consumers.

The documentation is less comprehensive for internal architecture. The domain boundaries are visible in code and reinforced by ArchUnit tests, but the repository does not contain a detailed architecture narrative, data model guide, task-processing guide, or security model explanation. For this assessment, implementation evidence was sufficient; documentation evidence for internal design was more limited.

## Performance Design
## Grade
B

## Score
82/100

## Evidence
- `DataSourcesConfiguration.kt` configures SQLite data sources with separate read/write behavior, WAL-aware settings, foreign keys, busy timeout, and write pool size control.
- `KomgaJooqConfiguration.kt` defines read/write DSL contexts, and `SplitDslDaoBase.kt` selects read or write DSL based on transaction state.
- Query helpers and DTO DAOs use explicit joins, pagination, content restriction conditions, and batching. `BookDtoDao.kt` and `SeriesDtoDao.kt` batch related metadata, tags, authors, links, and read progress.
- `BookSearchHelper.kt` and `SeriesSearchHelper.kt` apply filters in SQL rather than post-filtering large result sets in memory.
- Flyway migrations include performance indexes, including `V20220715213721__perf_indices.sql`.
- Lucene support appears in `LuceneHelper.kt`, `LuceneEntityIndexLifecycle.kt`, and search lifecycle classes, with a fixed maximum result window.
- `CommonBookController.kt` and `SeriesController.kt` stream downloads and ZIP output with `StreamingResponseBody` and `IOUtils.copyLarge`.
- `TaskProcessor.kt` uses `ThreadPoolTaskExecutor` for background work, and `TasksDao.kt` persists tasks with group ownership rules to avoid conflicting work.
- `PdfExtractor.kt`, `EpubExtractor.kt`, and `ImageConverter.kt` materialize page/resource/image data as byte arrays in several request paths.
- `TaskHandler.kt` catches task exceptions, records failure metrics, and returns without rethrowing, so `TaskProcessor.kt` deletes the task record after the handler returns.

## Assessment
Komga shows deliberate performance design for its data and media workload. Query filtering happens close to the database, DTO fetches batch related data, key read paths are paginated, and Lucene supports search use cases. SQLite is configured with attention to WAL, read/write separation, busy timeout, and foreign keys.

Media delivery is mixed but pragmatic. Large downloads and generated ZIPs stream to the response, which is appropriate for book files and series archives. Page rendering, EPUB resource extraction, PDF rendering, and image conversion often use byte arrays, which is simpler and acceptable for typical page-sized data but creates memory pressure under high concurrent reading or large resources.

Background task processing has useful concurrency and grouping controls. The observed failure path records metrics and logs but removes the task after the handler returns, which limits retry durability for transient failures.

## Developer Experience
## Grade
B

## Score
81/100

## Evidence
- `settings.gradle` defines a Gradle multi-project build for `komga` and `komga-tray`.
- Root `build.gradle.kts`, `komga/build.gradle.kts`, `komga-tray/build.gradle.kts`, and `gradle/libs.versions.toml` centralize Gradle plugins, dependencies, code generation, packaging, release, and version management.
- `komga-webui/package.json` provides `serve`, `build`, `lint`, and `test` scripts.
- `.github/workflows/tests.yml` runs backend build/tests on Ubuntu, macOS, and Windows and web UI install/build/test on Ubuntu.
- `.github/workflows/release.yml` automates release builds, Docker publishing, OpenAPI generation, JReleaser release publishing, Conveyor packaging, and release commits.
- `komga/docker/Dockerfile.tpl` provides multi-architecture container packaging.
- `DEVELOPING.md` documents local profiles, Gradle tasks, frontend development server behavior, and Docker build steps.
- `komga/build.gradle.kts` wires npm install/build tasks into backend resource preparation and OpenAPI generation.
- CI uses npm install/build/test for the web UI, but no web lint step was observed in the test workflow.

## Assessment
The developer experience is strong for a mature full-stack repository. Build, test, release, OpenAPI generation, Docker packaging, and web asset integration are automated through Gradle, npm, GitHub Actions, and JReleaser. Development profiles and common commands are documented.

The tradeoff is toolchain breadth. Contributors need Java, Gradle, Node, npm, Vue CLI, Spring Boot, jOOQ, Flyway, Docker/JReleaser concepts, and media-processing dependencies. The repository handles that complexity reasonably well, but the setup is heavier than a smaller service.

CI gives good baseline confidence, especially for backend portability. The frontend path is thinner because the workflow builds and tests but does not visibly run lint, component tests, or browser tests.

## Long-Term Sustainability
## Grade
B

## Score
80/100

## Evidence
- The repository contains mature release automation in `.github/workflows/release.yml`, JReleaser configuration in Gradle, Docker templates, and generated OpenAPI artifacts.
- Database evolution is explicit through 91 Flyway migrations and jOOQ generated code.
- Backend architecture rules preserve domain and interface boundaries.
- README badges, translation status, `CONTRIBUTING.md`, `PRIVACY.md`, and community links indicate an established open-source project process.
- Tests cover core backend behavior, media handling, API behavior, database access, and architecture constraints.
- Frontend dependencies show legacy stack choices: Vue 2.6, Vuex 3, Vue Router 3, Vuetify 2, Vue CLI, TypeScript 4.9, Jest 27.
- Large backend controllers and lifecycle classes remain central change hotspots.
- SQLite is the main storage engine, which fits the self-hosted deployment model but constrains multi-node and high-concurrency enterprise-style deployment shapes.

## Assessment
Komga has strong sustainability signals for its intended self-hosted product domain. Releases, Docker images, migrations, API documentation, localization, and tests are all part of the repository. Architectural guardrails reduce the chance of uncontrolled coupling over time.

The strongest long-term risk is accumulated surface area. The project supports comics, manga, EPUBs, PDFs, OPDS, Kobo, KOReader, imports, metadata, duplicate detection, multiple readers, users, and restrictions. That breadth is backed by real implementation and tests, but it leaves many central code paths large and behavior-heavy.

The frontend stack is the clearest aging component. Vue 2 and related tooling remain functional, but their presence affects future dependency posture and contributor familiarity. This does not negate current maturity, but it keeps the sustainability score below the architecture and testing scores.

---
# Comparative Snapshot

This snapshot is standalone for the Komga repository only. No cross-repository comparison was performed.

| Dimension | Standalone Rating | Evidence Basis |
|---|---|---|
| Architecture Sophistication | Strong | Domain lifecycle services, repository interfaces, jOOQ infrastructure, multiple API surfaces, task pipeline |
| Security Posture | Strong with tradeoffs | Spring Security chains, method roles, query scoping, content restrictions, CSRF disabled, URL API keys |
| Maintainability | Moderate-Strong | Clear package structure and tests, but large controllers/services and legacy frontend components |
| Modularity | Strong | Domain/infrastructure/interface separation, media modules, API integrations, frontend service/component separation |
| Test Confidence | Strong backend, limited frontend | 100 test files, ArchUnit, MockMvc, DAO/media tests, only 3 web unit test files |
| Documentation Quality | Good | README, DEVELOPING, ERRORCODES, PRIVACY, Docker notes, generated OpenAPI |
| Production Readiness | Strong | Release automation, Docker packaging, migrations, CI, authentication and permissions |
| Enterprise Suitability | Moderate | Single-node self-hosted architecture, SQLite storage, session-based web model, limited container hardening evidence |
| Contributor Friendliness | Good | Development guide, Gradle/npm scripts, CI, version catalog, but broad toolchain |
| Sustainability | Strong with legacy UI risk | Release/test/migration discipline plus Vue 2/Vue CLI/Jest legacy surface |

---
# Final Verdict

Overall Grade: B  
Overall Score: 81/100  
Confidence: 88/100  
Repository Maturity: Mature Project

Best Attribute: Architecture  
Weakest Attribute: Maintainability

Komga is a mature, production-capable self-hosted media server with a strong Kotlin/Spring backend architecture. The codebase has meaningful domain services, repository contracts, jOOQ-backed persistence, explicit task processing, multiple API surfaces, strong query scoping, and broad backend test coverage. Its architecture is not merely directory organization; core business workflows such as scanning, metadata aggregation, read progress, content restrictions, media extraction, and device sync are represented in implementation code.

The main limiting factor is operational and feature complexity concentrated in large files. Major controllers and lifecycle classes are large enough to make localized changes harder, and the frontend carries an older Vue 2/Vuex/Vuetify/Vue CLI stack with large Options API views. These are maintainability costs rather than signs of architectural immaturity.

Security, performance, and developer experience are all above average for this repository type. Authentication, authorization, content restriction scoping, release automation, migrations, Docker packaging, OpenAPI generation, and CI are well represented. The principal constraints are CSRF/session tradeoffs, Kobo URL-token compatibility, API-key storage design, limited frontend testing, and legacy UI tooling. Evidence was insufficient to assess real-world production incident history, external vulnerability scan results, or hosted deployment operations.
