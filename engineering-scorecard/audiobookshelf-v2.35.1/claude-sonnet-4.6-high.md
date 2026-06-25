# Executive Summary

## Repository: audiobookshelf
## Model: Claude Sonnet 4.6 (high)

## Overall Score

Score: 72/100
Grade: B
Confidence: 87/100

Repository Maturity: Mature Project

---

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | audiobookshelf |
| Total Files | 941 (excluding .git) |
| Source Files | ~350 server JS + 229 client Vue/JS |
| Test Files | 30 server unit tests + 12 Cypress component tests |
| Languages | JavaScript (Node.js), Vue 2 (Nuxt 2), SQL (inline) |
| Dependency Count | 19 production + 4 dev (server); 16 + 4 client |
| Largest Module | LibraryController.js (1497 lines), libraryItemsBookFilters.js (1352 lines) |
| Build System | npm scripts + pkg (for binary packaging) |
| CI/CD Present | Yes (GitHub Actions - unit tests, integration, Docker, CodeQL, component tests) |
| Containerization Present | Yes (multi-stage Dockerfile, docker-compose.yml) |
| Test-to-Source Ratio | ~1:12 (low coverage) |

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | B | 70 | Layered MVC pattern with controllers, models, managers, routers; heavy use of global variables undermines isolation |
| Security | B+ | 76 | JWT + refresh tokens, OIDC, rate limiting, SSRF filter, IDOR tests present; global state and vendored libs are risks |
| Maintainability | C+ | 68 | Many oversized files (1000-1800 LOC), 116 TODOs, mixed code patterns, but strong JSDoc and consistent conventions |
| Modularity | C+ | 66 | Reasonable module separation but controllers are monolithic, 53 files use global variables, boundary leakage via Database singleton |
| Code Quality | B- | 72 | Consistent patterns, good JSDoc, HTML sanitization, query filtering; var/let inconsistency, some dead-code TODOs |
| Testing | D+ | 42 | 30 server unit tests covering critical paths; near-zero E2E coverage; no service-layer unit tests; migration tests are good |
| Documentation | B | 73 | OpenAPI spec (partially built), custom metadata provider spec, JSDoc throughout, devcontainer, PR template |
| Performance Design | B | 74 | LRU API cache, per-user keying, Sequelize lazy-load, FFmpeg streaming, SQLite PRAGMA tuning, profiler utility |
| Developer Experience | B+ | 78 | devcontainer, VSCode config, CI pipelines on PRs, Cypress visual testing, clean npm scripts, integration smoke test |
| Long-Term Sustainability | B- | 69 | GPL-3.0, large community (iOS+Android apps), vendored libs reduce upgrade surface; Nuxt 2 EOL is a liability |

---

# Deep Assessment

## Architecture

### Grade
B

### Score
70

### Evidence
The server follows a layered structure: `server/routers/` (routing), `server/controllers/` (request handling), `server/managers/` (business orchestration), `server/models/` (Sequelize ORM models), `server/scanner/` (file system scanning), `server/providers/` (external metadata), and `server/objects/` (domain value objects). The `ApiRouter` (`server/routers/ApiRouter.js`) wires 38 controllers across ~576 lines and routes to `server/controllers/`. The `Database` singleton (`server/Database.js`, ~999 lines) exposes all Sequelize models through typed getters and acts as the application's data gateway. However, 53 server files import `global.*` variables (`global.ConfigPath`, `global.MetadataPath`, `global.ServerSettings`, `global.ServerSettings`) that are set imperatively during startup in `Server.js` - this creates hidden coupling and makes unit testing difficult. The `LibraryController.js` (1497 lines) and `LibraryItemController.js` (1247 lines) carry too much responsibility. The scanner subsystem (`LibraryScanner.js`, `BookScanner.js`, `LibraryItemScanner.js`) is well-decomposed. There is an experimental React client path registered in `Server.js`, showing forward migration awareness.

### Assessment
The architecture reflects pragmatic evolution rather than upfront design. Controllers mix HTTP handling with some orchestration concerns. The `Database` singleton passes as an application-wide data access object, which is functional but precludes easy testing without real or in-memory SQLite instances. The global variable pattern is the most significant structural weakness. The multi-stage Dockerfile and clear subsystem separation demonstrate maturity for a community project.

---

## Security

### Grade
B+

### Score
76

### Evidence
Auth is handled via Passport.js with a local username/password strategy (`server/auth/LocalAuthStrategy.js`) using bcrypt (cost factor 8), JWT bearer tokens, and refresh token rotation in `server/auth/TokenManager.js`. The token rotation implementation handles race conditions via a 1-minute grace period on the old `lastRefreshToken` stored in the `sessions` table. OIDC/OpenID Connect support exists in `server/auth/OidcAuthStrategy.js` with callback URL validation via `isValidWebCallbackUrl()`. Rate limiting is applied to all auth routes via `express-rate-limit` (`server/utils/rateLimiterFactory.js`): 40 attempts per 10 minutes by default, configurable via ENV. SSRF protection is provided by the `ssrf-req-filter` package on external HTTP calls, with an opt-out ENV var (`DISABLE_SSRF_REQUEST_FILTER`) and hostname whitelisting. HTML sanitization via `sanitize-html` in `server/utils/htmlSanitizer.js` applies to podcast descriptions and subtitles. Security headers include `Content-Security-Policy: frame-ancestors 'self'` and `Referrer-Policy: no-referrer` via middleware in `Server.js`. IDOR protection is tested in `test/server/controllers/MeController.test.js` (media progress, bookmarks, listening sessions). The `x-powered-by` header is disabled. The `/init` route checks for existing root users before allowing server initialization. Token secret falls back to auto-generated and stored in server settings when `JWT_SECRET_KEY` is not set. The session cookie is `httpOnly` but `secure: false` by default (acknowledged as intentional for non-HTTPS setups). Old JWTs without expiration are still accepted (`ignoreExpiration: true` in JwtStrategy) - manually checked in `jwtAuthCheck()`.

### Assessment
Security posture is solid for a self-hosted community project. The refresh token rotation with grace period handling shows careful implementation. Rate limiting is on all auth endpoints. The SSRF filter is appropriately applied and explicitly disabled with ENV flags plus logging. The main risks are: the session cookie is not `secure` by default (admins using HTTP are fully exposed), vendored library copies in `server/libs/` may diverge from upstream security patches, and API keys authenticated via JWT also pass through `ignoreExpiration: true` which is caught and checked manually. CodeQL runs on every PR/push to master.

---

## Maintainability

### Grade
C+

### Score
68

### Evidence
The codebase has 116 TODO/FIXME/HACK comments across server files. Several have accumulated technical debt markers: "TODO: Old method with no expiration" on `generateAccessToken()` in both `Auth.js` and `TokenManager.js`, `oldPlaybackSessionMap = {}` marked "TODO: Remove after updated mobile versions" in `PlaybackSessionManager.js`, and "TODO: Clients were expecting full author in payload but its unnecessary" in `ApiRouter.js`. The `LibraryController.js` at 1497 lines and `libraryItemsBookFilters.js` at 1352 lines are oversized. `dbMigration.js` in utils/migrations is 1806 lines. JSDoc is consistently used across all controllers and models with typed `@param`, `@returns`, and `@typedef` definitions. The `@this` import pattern in method JSDoc is used to communicate context for methods bound with `.bind()` at routing time - a useful but unconventional pattern. Naming is generally clear and consistent. The migration infrastructure uses Umzug with semantic versioning (v2.15.0 through v2.35.0 observed), with each migration having a corresponding test. Prettier is configured (`.prettierrc`). The codebase uses `var` in some legacy sections alongside `const`/`let` in newer code.

### Assessment
Maintainability is hampered by several large files that have accumulated organically, and by a moderate number of known technical debt markers that have not been addressed. The JSDoc coverage partially compensates by making intent clear. The migration system with per-migration tests is an excellent practice. The binding pattern used in `ApiRouter.js` (routing to `Controller.method.bind(this)` where `this` is the router, not the controller instance) creates non-obvious dependency injection that requires the `@this` JSDoc workaround to communicate.

---

## Modularity

### Grade
C+

### Score
66

### Evidence
The server has clear physical separation: controllers, managers, models, providers, scanner, objects, utils. The `Database` singleton is imported directly into controllers (`const Database = require('../Database')`), managers, and even the `Server.js` root - this is a monolithic data access layer without abstraction. 53 files access `global.*` variables, creating hidden dependencies that prevent module-level isolation. The `SocketAuthority` singleton is also imported in 10+ files, creating tight coupling for real-time event dispatch. The `ApiRouter` accepts the full `Server` instance in its constructor and extracts managers, which is a passable DI approach. Controllers are instantiated as singletons and exported as `module.exports = new XController()`. The `providers/` directory cleanly separates external metadata sources. The `scanner/` subsystem decomposes scanning concerns into separate classes (`LibraryScanner`, `BookScanner`, `PodcastScanner`, `AudioFileScanner`, `OpfFileScanner`, etc.). The `utils/queries/` directory groups database query builders by entity type.

### Assessment
The physical module layout is clear and functionally grouped. However, the pervasive use of singletons (`Database`, `SocketAuthority`, `Logger`) imported throughout the codebase means modules are not independently testable without significant mocking. The 53-file global variable dependency is the weakest aspect of modularity. Controller files exceeding 1000 lines suggest individual controllers have not been subdivided as features grew.

---

## Code Quality

### Grade
B-

### Score
72

### Evidence
JSDoc is used pervasively with accurate type annotations via `@typedef`, `@type`, and `@param`. Request type composition using `@typedef` intersections (e.g., `LibraryItemControllerRequest = RequestWithUser & RequestEntityObject`) is a clean pattern in a non-TypeScript codebase. Error handling in controllers consistently returns early with `res.sendStatus()` or `res.status().send()`. Input validation is manual (type checks, `typeof`, array checks) in controllers rather than using a validation library. The `htmlSanitizer.js` uses `sanitize-html` with a strict allowlist. The `rateLimiterFactory.js` is a well-structured factory with ENV configuration and logging. The `profiler.js` utility wraps async functions with histogram recording - useful but appears to be a development/debugging utility not intended for production use. Some inconsistency exists: older code uses `var`, newer uses `const`/`let`. Methods like `cleanUserData()` in `Server.js` mix raw SQL queries with ORM queries. The `escapeRegExp` utility exists and is used in `Auth.js` for safe regex construction. HTML entity decoding in `htmlSanitizer.js` uses a custom `decodeHTMLEntities()` function against a manually maintained `htmlEntities.js` (2235 lines) which is a significant maintenance surface.

### Assessment
Code quality is above average for a community-driven project of this scope. The JSDoc discipline, consistent error response patterns, and sanitization practices indicate quality awareness. The manual HTML entity table and manual input validation without a schema library are the most notable gaps. The profiler utility should be guarded so it is not callable in production builds.

---

## Testing

### Grade
D+

### Score
42

### Evidence
The server test suite has 30 files under `test/server/`. Coverage includes: controller integration tests using real in-memory SQLite via Sequelize (`test/server/controllers/LibraryItemController.test.js`, `test/server/controllers/MeController.test.js`), manager unit tests with stubs (`MigrationManager.test.js`, `ApiCacheManager.test.js`, `BinaryManager.test.js`), per-migration tests (9 migration test files covering v2.15.0 through v2.20.0), provider unit tests (`Audible.test.js`), utility tests (`ffmpegHelpers.test.js`, `fileUtils.test.js`, `scandir.test.js`), and parser tests (`parseNameString.test.js`, `parseNfoMetadata.test.js`, `parseOpfMetadata.test.js`). The IDOR security tests in `MeController.test.js` are particularly thorough - testing media progress, bookmarks, and listening session isolation across users. The test stack is Mocha + Chai + Sinon. The client has 6 Cypress component tests. There are no end-to-end tests. The integration test (`integration-test.yml`) only smoke-tests that the server returns HTTP 200 on the root path. The scanner subsystem, playback session management, podcast manager, and streaming pipeline have no test coverage. The test-to-source ratio is approximately 1:12.

### Assessment
Testing is the weakest dimension of this repository. The existing tests are well-written and cover important security boundaries (IDOR), but overall coverage is critically low for the complexity of the application. Core subsystems with the most complex business logic (library scanning, audio streaming, playback session management, podcast downloading) have zero test coverage. The migration tests are a standout practice. CI runs unit tests on every PR and push.

---

## Documentation

### Grade
B

### Score
73

### Evidence
An OpenAPI 3.0 spec exists in `docs/` with a bundled `openapi.json` and individual YAML files per controller. Only 6 controller YAML files exist out of 21+ controllers, indicating partial coverage. The `docs/README.md` documents the toolchain (`redocly-cli`, `vacuum`, `wiretap`) and commands for bundling, linting, and generating HTML docs. The `custom-metadata-provider-specification.yaml` provides a complete OpenAPI spec for the plugin provider interface. JSDoc is comprehensive across all server-side files. The `readme.md` documents features, mobile apps, and community links but lacks setup instructions (these appear on the external docs site). A devcontainer configuration enables zero-setup development. The `migrations/changelog.md` and `migrations/readme.md` exist for the migration system. A PR template is defined at `.github/pull_request_template.md`. Issue templates for bugs and features exist.

### Assessment
Documentation quality is good for a community project. The OpenAPI spec is partially implemented and uses tooling that enforces spec quality. JSDoc coverage throughout the server codebase significantly reduces onboarding friction. The gap is that the OpenAPI spec covers only ~30% of endpoints and there is no inline API documentation for the remaining routes. External documentation (audiobookshelf.org) supplements what is in the repo.

---

## Performance Design

### Grade
B

### Score
74

### Evidence
An LRU-based API cache (`ApiCacheManager.js`) caches GET responses to `/libraries/*` routes with a 10MB size limit and 30-minute TTL for personalized shelf responses. The cache is per-user (keyed by `username + url`) and invalidated via Sequelize lifecycle hooks on `afterCreate`, `afterUpdate`, `afterDestroy`, and `afterBulkCreate/Update/Destroy`. High-churn models (session, mediaProgress, playbackSession, device) only clear user-progress cache slices rather than flushing the entire cache, avoiding unnecessary invalidations. SQLite is configured with WAL mode via `PRAGMA journal_mode = WAL` and cache size tuning in `Database.js`. The `stats` query in the `libraryItemsBookFilters.js` module uses parametrized Sequelize queries with `Sequelize.literal()` for SQLite-specific JSON functions. FFmpeg is used for audio transcoding and streaming (`Stream.js`, `ffmpegHelpers.js`) with HLS segmentation for efficient delivery. The `profiler.js` wraps database queries with histogram recording for performance monitoring. The `lru-cache` library is also used for user and API key lookups (`UserCache`, `ApiKeyCache` in respective model files). A `p-throttle` package is imported for rate-limiting external API calls. The watcher uses debouncing (`pendingDelay: 10000`) before triggering scans on file changes.

### Assessment
Performance design is well-considered for a self-hosted application at this scale. The API cache with model-hook-based invalidation is a practical pattern. The per-user cache key prevents data leakage between users. The LRU caches on user and API key lookups reduce database round-trips on hot paths. The main risk is that SQLite WAL mode under heavy concurrent write load (e.g., many simultaneous podcast downloads) may create lock contention, but this is an SQLite architectural limitation rather than a design flaw.

---

## Developer Experience

### Grade
B+

### Score
78

### Evidence
A `.devcontainer/` directory with `devcontainer.json`, a `Dockerfile`, and a `post-create.sh` script enables zero-config development via VS Code dev containers. `.vscode/settings.json`, `extensions.json`, `launch.json`, and `tasks.json` provide IDE configuration for ESLint and debugging. CI pipelines run on every PR and push: unit tests (`unit-tests.yml`), integration smoke test (`integration-test.yml`), Docker build (`docker-build.yml`), CodeQL security scan (`codeql.yml`), OpenAPI lint (`lint-openapi.yml`), and Cypress component tests (`component-tests.yml`). The `npm run coverage` script via nyc enables local coverage reports. Docker Compose (`docker-compose.yml`) enables single-command local deployment. The build system supports cross-compilation to Linux binary via `pkg` and cross-platform Docker via `docker buildx`. An i18n integration workflow (`i18n-integration.yml`) manages translations. The `.editorconfig` standardizes editor settings. The Cypress tests can be run visually via `npm run test-visually`.

### Assessment
Developer experience is strong. The devcontainer provides a smooth onboarding path. The CI suite is comprehensive for a community project, covering testing, security scanning, and API spec linting. The integration test is minimal (HTTP 200 smoke check) but validates the full build pipeline. The VSCode task and launch configurations reduce setup friction for first-time contributors.

---

## Long-Term Sustainability

### Grade
B-

### Score
69

### Evidence
The project is GPL-3.0 licensed and has active development (version 2.35.1, with migrations as recent as v2.35.0). The companion mobile apps (iOS and Android) are maintained in a separate repository. The client uses Nuxt 2 which reached end-of-life in December 2024, presenting a framework migration risk. The server uses Express 4 with no immediate EOL concern. Node.js 20 LTS is targeted. Dependencies include `axios ^0.27.2` which is quite old (current is 1.x). The `openid-client ^5.6.1` is a v5 pin while v6 released as a breaking change. The `sequelize ^6.35.2` is current. Approximately 35 third-party libraries are vendored directly into `server/libs/` (bcryptjs, fsExtra, dateAndTime, jsonwebtoken, etc.) - this eliminates supply-chain update friction but means security patches require manual vendor updates. The database migration system with versioning and Umzug ensures upgrade paths are maintained. The `migrations/changelog.md` documents migration intent. The codebase tracks data model changes through versioned migrations back to v2.15.0.

### Assessment
Long-term sustainability is moderate. The community engagement (iOS/Android apps, Discord, demo server) indicates ecosystem investment. The Nuxt 2 EOL is the most pressing technical debt for the client layer - migration to Nuxt 3 or another modern framework will require significant effort. Vendoring all libraries into `server/libs/` is an unusual choice that trades supply-chain risk for upgrade control; it requires discipline to keep patches applied. The active migration trail and semantic versioning demonstrate commitment to upgrade paths for existing deployments.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Moderate |
| Security Posture | Good |
| Maintainability | Moderate |
| Modularity | Moderate |
| Test Confidence | Low |
| Documentation Quality | Good |
| Production Readiness | Good |
| Enterprise Suitability | Low-Moderate |
| Contributor Friendliness | Good |
| Sustainability | Moderate |

---

# Final Verdict

## Overall Grade
B

## Overall Score
72

## Confidence Score
87

## Repository Maturity
Mature Project

## Best Attribute
Developer Experience

## Weakest Attribute
Testing

## Three-Paragraph Assessment

Audiobookshelf is a functionally rich, actively maintained self-hosted media server that demonstrates strong engineering discipline in its security model, documentation, and operational tooling. The authentication subsystem is particularly well-engineered: refresh token rotation with race condition handling, OIDC support with callback URL validation, per-IP rate limiting, and SSRF protection on all external HTTP calls reflect deliberate security thinking uncommon in community projects of this size. The presence of IDOR-specific integration tests for the `MeController` and `LibraryItemController`, using real in-memory SQLite instances, shows the team understands multi-user data isolation as a first-class concern. The multi-stage Dockerfile, devcontainer setup, and comprehensive CI pipeline (unit tests, CodeQL, component tests, OpenAPI linting, integration smoke test) indicate a project that has matured its delivery infrastructure.

Architecturally, the codebase follows a clear MVC layering with explicit subsystem separation (scanner, providers, managers, models), but this is undermined by pervasive use of Node.js `global.*` variables for configuration and runtime state, imported singletons (`Database`, `SocketAuthority`, `Logger`) throughout the module graph, and several controllers that have grown beyond 1000-1500 lines without subdivision. The `LibraryController.js` at 1497 lines and `libraryItemsBookFilters.js` at 1352 lines are god-file candidates. The Sequelize-based data layer is sound with typed model definitions, migration infrastructure via Umzug, and appropriate use of parameterized queries; however, the `Database` singleton accessed directly from controllers and managers removes the option for repository-pattern abstraction. The binding pattern in `ApiRouter.js` - routing to `Controller.method.bind(this)` where `this` becomes the router - is a non-obvious DI pattern that works but requires the `@this` JSDoc annotation to remain comprehensible.

The most significant long-term risk is the combination of low test coverage and the Nuxt 2 EOL. With approximately 30 server test files covering a subset of the application's business logic and near-zero coverage of the scanner subsystem, audio streaming pipeline, and podcast management, any refactoring of core functionality carries regression risk. The Nuxt 2 framework reached end-of-life in December 2024; the client's 42 Vue pages and 184 components will require migration to a supported framework. The vendor-copy pattern in `server/libs/` (35+ libraries vendored) is sustainable only with active patch discipline. For a self-hosted community project targeting technically capable users, these risks are manageable, but they represent concrete work that must be undertaken to maintain quality as the feature set grows.
