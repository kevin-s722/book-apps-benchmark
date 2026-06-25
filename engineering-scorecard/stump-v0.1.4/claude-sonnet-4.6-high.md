# Executive Summary

## Repository: stump
## Model: Claude Sonnet 4.6 (high)

## Overall Score

Score: 80/100
Grade: B+
Confidence: 88/100

Repository Maturity: Community Project

---

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | stump |
| Total Files | ~2,506 (excluding build artifacts and node_modules) |
| Source Files | ~1,997 (457 .rs + 551 .ts + 989 .tsx) |
| Test Files | ~104 (78 Rust files with tests, 26 TS/TSX test files) |
| Languages | Rust (primary), TypeScript/TSX, Nix, Shell |
| Dependency Count | ~60 Rust workspace deps + ~30 JS dev deps |
| Largest Module | core/ (library scanner, job system, filesystem) |
| Build System | Cargo (Rust) + Yarn/Lerna (JS) |
| CI/CD Present | Yes (GitHub Actions: CI, nightly, CVE check, release) |
| Containerization Present | Yes (multi-stage Dockerfile with distroless final image) |
| Test-to-Source Ratio | ~0.052 (low overall) |

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | A- | 88 | Layered monorepo with clean separation of concerns across Rust crates and JS packages |
| Security | B | 76 | Good auth fundamentals (JWT, API keys, sessions, OIDC); notable gaps in rate limiting and path validation |
| Maintainability | B | 75 | Strong error hierarchy and config system; 183+ TODOs and 325+ `.unwrap()` calls in production paths |
| Modularity | A- | 87 | Exemplary workspace decomposition with intentional crate boundaries and JS package separation |
| Code Quality | B+ | 81 | Idiomatic Rust with thiserror, tracing, sea-orm; some code smells in scanner and filesystem layers |
| Testing | C+ | 62 | 453 Rust tests across 78 files; coverage target set at 10%; integration tests stale (use old Prisma API) |
| Documentation | B | 74 | CONTRIBUTING, SECURITY, CHANGELOG, doc comments on public APIs; inline docs sparse in some modules |
| Performance Design | B+ | 80 | Criterion benchmarks, apalis job queue, tokio async, concurrent scanner; single-threaded job worker is a constraint |
| Developer Experience | B+ | 82 | Cargo aliases, multi-platform builds, Nix flake, VSCode config, crowdin i18n, good CI separation |
| Long-Term Sustainability | B | 76 | Active changelog, automated CVE scanning, semantic versioning, but single maintainer dependency risk |

---

# Deep Assessment

## Architecture

### Grade
A-

### Score
88

### Evidence
The repository employs a well-considered polyglot monorepo strategy. On the Rust side, the workspace is decomposed into purpose-driven crates: `core/` (library scanning, job lifecycle, filesystem, OPDS), `crates/models` (SeaORM entity definitions), `crates/graphql` (async-graphql schema, query, mutation, subscription, data loaders), `crates/migrations` (sea-orm-migration runner), `crates/email`, `crates/tests` (shared test utilities), `crates/integrations/metadata` and `crates/integrations/notification` (pluggable external integrations), and `crates/macros/` (two proc-macro crates: `stump-config-gen` and `filter-gen`). The binary entry point in `apps/server` is kept deliberately thin - it wires HTTP (`axum` + `tower_http`), session management, CORS, and Apalis job workers, delegating all business logic to `core/`.

The `StumpCore` struct (`core/src/lib.rs`) serves as the clean initialization surface: `new()`, `init_config()`, `init_server_config()`, `init_encryption()`, `init_jwt_secrets()`, `init_journal_mode()`, `init_scheduler()`, `init_library_watcher()`. This explicit sequenced initialization is clean architectural practice.

The `Ctx` struct (`core/src/context.rs`) carries the application context (`Arc<StumpConfig>`, `Arc<DatabaseConnection>`, event broadcast channel, `Arc<LibraryWatcher>`, `Arc<ApalisWorkerState>`, `MemoryStorage<StumpJob>`), and `AppState` in `apps/server` is simply a type alias `Arc<Ctx>` - no unnecessary wrapper types.

The job system (`core/src/job/`) uses a trait-based `JobLifecycle` that all job types implement, with a unified `StumpJob` enum (`stump_job.rs`) acting as a serializable dispatch envelope. `run_job()` in `run.rs` provides a generic executor that runs any `JobLifecycle` implementor. This is a textbook strategy pattern implementation.

On the JS side, a Yarn/Lerna workspace contains `apps/web`, `apps/desktop` (Tauri), `apps/expo` (React Native), `packages/sdk`, `packages/browser` (shared React UI logic), `packages/components` (headless UI), `packages/graphql` (generated GraphQL types), `packages/i18n` (32 locale files), and `docs/`.

The dual API surface - REST (`/api/v2`) for operations requiring byte streaming and tight HTTP control (media serving, thumbnails, OPDS), plus GraphQL (via `async-graphql`) for data queries and mutations - is a well-reasoned design choice rather than redundancy.

### Assessment
The architecture shows senior-level design thinking. The crate decomposition is intentional and enforces compilation-level boundaries between concerns. The proc-macro approach to config generation (`stump-config-gen`) prevents repetitive boilerplate across the extensive configuration surface. The separation between the core library and the server binary makes the core testable in isolation and theoretically reusable for alternative frontends (e.g., the CLI crate). One notable architectural constraint is the single-worker apalis job executor (`concurrency(1)` in `http_server.rs`) which is acknowledged in a TODO comment as a historical limitation pending experimentation. The GraphQL schema depth limit of 15 is an appropriate protection against runaway query complexity.

---

## Security

### Grade
B

### Score
76

### Evidence
**Authentication:** Three authentication methods are implemented in `apps/server/src/middleware/auth.rs`: bearer JWT, prefixed API keys (via `prefixed-api-key` crate with SHA-2 hashing), and HTTP Basic Auth (restricted to OPDS routes only). Session management uses a custom `StumpSessionStore` backed by SeaORM with configurable TTL (default 3 days).

**API Keys:** The `validate_api_key()` function in `middleware/auth.rs` performs short-token + long-token-hash verification, checks expiry, verifies user permission to use API keys, and supports custom permission scoping (`APIKeyPermissions::Custom`). Last-used timestamp is updated non-fatally.

**JWT:** Secrets are persisted to the database (`server_config` table) and cached in `OnceLock<String>` after first retrieval (`jwt.rs`). Refresh tokens are stored in the database with expiry checks. The system uses standard `jsonwebtoken` crate with HS256.

**Password Hashing:** Uses `bcrypt` with configurable cost (default 12, set via `HASH_COST_KEY` env var). This is appropriate.

**Brute Force Protection:** The `login()` handler in `routers/api/v2/auth.rs` counts failed login attempts in the last 24 hours using the `user_login_activity` table and locks accounts after 9 failures. Account locking deletes all existing sessions.

**Permission Guards:** GraphQL mutations use `PermissionGuard` (`crates/graphql/src/guard.rs`) which checks `user.is_server_owner` or permission set membership. `ServerOwnerGuard` and `BookClubRoleGuard` provide contextual authorization. REST routes use `auth_middleware` as a layer.

**CORS:** Configurable via `allowed_origins` with sensible defaults for Tauri origins. Wildcard (`"*"`) is supported but requires explicit configuration.

**OIDC:** Full OIDC flow implemented (`apps/server/src/config/oidc.rs`, routers). Supports `disable_local_auth` flag to enforce IdP-only authentication.

**CVE Scanning:** Weekly automated `yarn audit` via `.github/workflows/cve_check.yml` creates GitHub issues when vulnerabilities are found.

**Gaps:** No request-level rate limiting is applied to login or API endpoints (rate limiting exists only in the metadata integration client). The `encryption_key` stored in `server_config` is noted as insecure in a TODO comment in `core/src/lib.rs`. Path traversal risks exist in filesystem operations serving media files - paths are taken from the database (populated by the scanner) rather than user input, which reduces risk, but there is no explicit canonicalization or confinement check visible in `common.rs` for `get_saved_thumbnail`. The `expect()` usage (249 calls) in non-test code introduces panic potential, particularly in startup paths. The `simple_crypt` dependency (`Cargo.toml`) for encryption is a non-standard library; no audit trail for it was found.

### Assessment
The authentication and authorization architecture is thoughtfully implemented with multiple auth methods, proper bcrypt password hashing, JWT with refresh rotation, API key scoping, and account lockout. The lack of endpoint-level rate limiting beyond login-attempt counting is a meaningful gap for a self-hosted server exposed to the internet. The acknowledged insecurity of the auto-generated encryption key (`init_encryption()`) is a known design debt. The CVE automation is a proactive security practice uncommon for a solo-developer community project.

---

## Maintainability

### Grade
B

### Score
75

### Evidence
**Error Handling:** The error hierarchy is well-structured: `CoreError` (thiserror, ~20 variants) in `core/src/error.rs`, `APIError` (~20 variants) in `apps/server/src/errors.rs`, `FileError`, `JobError`, etc. All implement `std::error::Error` via thiserror. `From` conversions allow natural propagation through `?`. The `APIError -> APIErrorResponse -> IntoResponse` chain is clean.

**Configuration:** The `StumpConfigGenerator` proc-macro generates `PartialStumpConfig` and builder methods from the `StumpConfig` struct, eliminating manual sync between config field definitions and their partial/environment-loading equivalents. This is sophisticated and maintainability-positive.

**Technical Debt:** 183 `TODO`/`FIXME`/`HACK` markers across 103 Rust files. Notable examples: the single-worker job concurrency limitation acknowledged in `http_server.rs`, the insecure auto-generated encryption key in `core/src/lib.rs`, the `expect()` calls in production paths (249 total). The library scanner has a TODO about switching from rayon to tokio for IO-bound work.

**`.unwrap()` Usage:** 325 `.unwrap()` calls in files with more than 5 each. While many appear in test paths and startup sequences where panic is acceptable, the volume is high enough to warrant concern for edge-case production reliability.

**Logging:** `tracing` is used consistently with structured fields. The `#[tracing::instrument]` attribute appears on 58 functions, selectively applied to high-value paths.

**Migrations:** Sequential timestamped migrations using `sea-orm-migration` with 22 migration files covering the full schema evolution. Migration history provides accurate audit trail of schema changes.

### Assessment
The codebase shows mature error handling and configuration management design. The custom proc-macro for config is an impressive investment in maintainability automation. The technical debt is visible and acknowledged - the volume of TODOs reflects an active, iterating project rather than neglect. The `unwrap()` and `expect()` usage in non-test paths is the primary maintainability risk, as panics in an async Tokio runtime can take down the server rather than returning an error response.

---

## Modularity

### Grade
A-

### Score
87

### Evidence
**Rust Crate Decomposition:** 15 distinct crates in the workspace: `core`, `models`, `graphql`, `migrations`, `tests`, `email`, `cli`, `integrations/metadata`, `integrations/notification`, `macros/stump-config-gen`, `macros/filter-gen`, and the app binaries `apps/server` and `apps/desktop/src-tauri`. Each crate has a clear, single responsibility.

**Entity-Model Separation:** SeaORM entity models live in `crates/models`, while business logic lives in `core`. The GraphQL schema in `crates/graphql` imports models but does not reach into core internals directly. The `AppState` type alias (`Arc<Ctx>`) allows `Ctx` to be used as the core context without the server imposing its own abstraction layer.

**Provider Pattern:** The `MetadataProvider` trait in `crates/integrations/metadata/src/provider.rs` defines a clean async trait interface. Implementations (`Hardcover`, `AniList`) are separate files. The `RateLimiter` wrapper in `rate_limit.rs` is independently testable.

**JS Package Separation:** `packages/sdk` (HTTP client), `packages/browser` (shared React hooks, components, scenes), `packages/components` (design system primitives), `packages/graphql` (generated types), `packages/i18n` (translations). The SDK is usable independently of React. The 32-locale i18n package is cleanly separated.

**Filter/Order Macros:** The `filter-gen` proc-macro generates filter and ordering types from entity annotations (`#[derive(Ordering)]` on SeaORM entity structs), eliminating manual filter struct definitions.

**Weak Spots:** Some cross-crate concern leakage exists - `async-graphql::SimpleObject` is derived on SeaORM entity models in `crates/models`, coupling the persistence layer to the GraphQL surface. The `AuthUser` type in `crates/models/src/entity/user.rs` carries session-relevant behavior (`has_permission()`) which is arguably application logic rather than model behavior.

### Assessment
The workspace modularity is one of the project's strongest attributes. The deliberate investment in proc-macros to enforce DRY across the crate boundary (config generation, filter generation) is evidence of thoughtful long-term modularity planning. The JS package decomposition mirrors the Rust structure with similarly clean boundaries. The `find_for_user()` pattern defined on entity structs (used 205 times across the codebase) provides a consistent, discoverable query scoping interface that enforces the multi-tenancy invariant at the data access layer.

---

## Code Quality

### Grade
B+

### Score
81

### Evidence
**Idiomatic Rust:** The codebase consistently uses Rust idioms: `?` propagation, `Option` chaining, `thiserror`, `serde` derive macros, `async-trait`, `Arc` for shared state. The `JobLifecycle` trait shows appropriate use of associated types for output and task types.

**Type Safety:** The `StumpJob` enum as a tagged serde discriminant ensures all job types serialize/deserialize cleanly. The `CoreJobOutput` enum with per-job output types provides compile-time exhaustiveness. `APIKeyPermissions::Custom/Inherit` enum captures permission inheritance semantics precisely.

**Clippy:** CI enforces `cargo clippy -- -D warnings`, ensuring no warnings are present at merge time.

**Format:** `rustfmt` is enforced in CI and pre-commit hooks (`cargo fmt --check`). ESLint and Prettier are configured for the frontend with pre-commit lint-staged hooks.

**Library Scanner Quality:** `library_scan_job.rs` (886 lines) is the longest single file and shows some complexity. The task decomposition (Init -> WalkSeries -> SeriesTask) is well-structured, but the match arm for `LibraryScanTask::SeriesTask` has deeply nested match arms that reduce readability. The TODO comment about improving progress messages is an honest acknowledgment.

**Code Comments:** The project follows a "explain why, not what" philosophy. Comments are selective and purposeful. No excessive documentation bloat.

**GraphQL Schema:** The 3,558-line `schema.graphql` is auto-generated and checked into the repository, verified in CI via `cargo dump-schema -- --check`. This ensures the schema is always in sync with the implementation.

**Smells:** `expect()` in `write_config_dir()` for directory creation (`std::fs::create_dir(...).unwrap()`) is an unconditional panic on IO failure. The OPDS v2 auth response builder uses `.unwrap_or_else()` for error handling, which is reasonable but reflects defensive coding rather than clean result propagation.

### Assessment
The Rust code quality is consistently good to very good. The strict CI linting (clippy as errors, rustfmt check) enforces a baseline quality floor. The TypeScript code follows modern practices (ESLint, Prettier, strict TypeScript). The main quality concerns are the `unwrap()`/`expect()` usage volume and a handful of long functions in the scanner. The auto-generated, CI-verified GraphQL schema is a strong quality practice that prevents schema drift.

---

## Testing

### Grade
C+

### Score
62

### Evidence
**Rust Tests:** 453 test cases (`#[test]` or `#[tokio::test]`) across 78 files. Tests are co-located with source in `#[cfg(test)] mod tests` blocks and in separate integration test crates.

**Integration Tests (Rust):** `core/integration-tests/` contains format-level tests (`epub.rs`, `zip.rs`, `rar.rs`) and scanner tests. However, `scanner.rs` uses a stale API (`Ctx::mock()`, `PrismaClient`, `LibraryScanMode`) that references the old Prisma ORM layer, not the current SeaORM layer. These tests appear non-functional in the current state of the codebase - a significant gap.

**JWT Tests:** `apps/server/src/config/jwt.rs` has 5 tokio async tests covering missing secret error, access token round trip, refresh token JTI extraction, secret caching, and invalid token handling. These use the real `tests::db::test_database()` in-memory SQLite.

**Auth Tests:** `apps/server/src/middleware/auth.rs` has 9 unit tests covering `AuthContext` permission enforcement scenarios, and `OPDSBasicAuth` response structure.

**Config Tests:** `core/src/config/stump_config.rs` has 2 tests: `test_writing_to_config_dir` (uses tempdir) and `test_simulate_first_boot` (uses `temp_env`). These are thorough for the config subsystem.

**Proc-Macro Tests:** `crates/macros/stump-config-gen/tests/basic_tests.rs` has targeted macro tests.

**Rate Limiter Tests:** `crates/integrations/metadata/src/rate_limit.rs` has 2 unit tests.

**GraphQL Tests:** `crates/graphql/src/tests/` provides only `common.rs` helper utilities; no actual GraphQL query/mutation tests are visible.

**Frontend Tests:** 26 TS/TSX test files covering SDK API class, form validation schemas, component tests (`TagSelect`, `APIKeyInspector`, `CreateOrUpdateAPIKeyForm`, user restriction forms). These use Jest (not Vitest).

**Coverage Target:** `.github/codecov.yml` sets a project coverage target of only 10%, with patch target at 0%. This is a frank acknowledgment of low coverage rather than a quality target.

**Benchmark:** `core/benches/benchmarks/library_scanner.rs` contains Criterion benchmarks for library scanning at 4 scales (10x10, 100x10, 100x100, 100x1000).

### Assessment
The test infrastructure exists and some subsystems are well-tested (JWT, auth permissions, config, SDK). However, the overall coverage is low by design (10% target), the GraphQL layer has no functional tests, and the integration tests for the scanner reference a superseded ORM layer and appear broken. The Criterion benchmarks are a quality positive for the performance-critical scanning code. The frontend tests are limited to form schema validation and a small number of component tests. For a project handling user data and media libraries, the testing surface is insufficient to catch regressions in the core data flows.

---

## Documentation

### Grade
B

### Score
74

### Evidence
**External Docs:** The project has a dedicated `docs/` application (Fumadocs-based). `README.md` exists at root and in `core/`. `CONTRIBUTING.md` is detailed (7-step process, LLM policy, PR criteria). `SECURITY.md` provides vulnerability disclosure instructions. `CHANGELOG.md` (1,704 lines) maintains a complete history with gitmoji prefixes and issue/commit links.

**Code Documentation:** `StumpCore` in `core/src/lib.rs` has a comprehensive doc comment with example code. `StumpConfig` in `core/src/config/stump_config.rs` has a full doc comment with example. Every config field has a doc comment. `StumpJob` variants have doc comments. `Ctx` has example-bearing doc comments.

**API Documentation:** The 3,558-line GraphQL schema includes type-level doc strings on complex types. The OpenAPI surface (REST) is not documented with a spec file or inline annotations.

**Environment Variables:** All environment variable keys are defined as constants in `env_keys` module with names that match the variable names, but no inline documentation of accepted values or defaults beyond the code itself.

**Inline Comments:** Selective and purposeful. The scanner uses comments to explain non-obvious business logic (collection-based vs. series-based scan modes, the root-directory-as-series edge case). Architecture decision comments appear where needed.

**Crowdin Integration:** `crowdin.yml` enables community-sourced translations for the i18n package's 32 locale files, with a documented workflow.

**Gaps:** The REST API surface has no OpenAPI specification. The data model relationships (SeaORM `Relation` enums are often left empty `{}`) limit automatic documentation of the relational graph. Some modules (`core/src/filesystem/`, `crates/graphql/src/query/`) have no module-level documentation.

### Assessment
Documentation quality is above average for a community project. The changelog discipline, contributing guidelines, and doc-commented public APIs are professional-grade. The absence of an OpenAPI specification for the REST v2 API and the sparseness of module-level documentation in the filesystem and GraphQL query layers are the primary gaps. The crowdin i18n integration is a thoughtful community engagement mechanism.

---

## Performance Design

### Grade
B+

### Score
80

### Evidence
**Async Architecture:** The server is fully async using `tokio` with the multi-thread scheduler. Axum handlers are non-blocking. SeaORM queries are async. The file system scanner uses `tokio::fs` for async IO in critical paths.

**Job Queue:** Apalis `MemoryStorage` with a single concurrent worker processes jobs serially. The TODO in `http_server.rs` acknowledges this as a deliberate conservative choice: "I experienced multi-writer issues but perhaps with SeaORM + WAL we can have parallel scans." WAL mode is initialized in `init_journal_mode()` to enable concurrent reads.

**Scanner Concurrency:** `max_scanner_concurrency` (default 200) controls concurrent file processing within a scan job. `max_thumbnail_concurrency` (default 10) limits thumbnail generation. Both are configurable.

**DataLoaders:** The GraphQL schema uses `async-graphql::dataloader::DataLoader` for 12 loaders (authors, series, media, libraries, reading sessions, etc.), preventing N+1 query problems.

**SQLite WAL:** WAL journal mode enables concurrent readers with single writer, critical for a media server serving many simultaneous clients.

**PDF Caching:** `pdf_cache_pages: bool` and `pdf_prerender_range: u32` (default 5 pages) enable pre-rendering and disk caching of PDF pages to reduce latency for sequential reading.

**Benchmarks:** Criterion benchmarks for library scanning at 10-100 series with 10-1000 books per series provide regression detection for the most performance-critical operation.

**Retry Logic:** `reqwest-middleware` + `reqwest-retry` are in workspace dependencies for external API calls (metadata providers), providing resilient external requests.

**Gaps:** The single-worker job constraint means a large library scan blocks thumbnail generation and metadata fetches. `MemoryStorage` for the job queue means jobs are lost on restart. No caching layer (Redis, in-memory) is used for hot data like session lookups or library metadata; every request hits SQLite.

### Assessment
The performance design reflects thoughtful tradeoffs for a self-hosted media server. The DataLoader implementation for GraphQL and WAL mode for SQLite are appropriate for the use case. The configurable concurrency limits allow power users to tune for their hardware. The single-worker job constraint is the most impactful performance limitation, acknowledged but unresolved. For the target use case (personal/small-group library server), the current design is adequate; for larger deployments, the in-memory job queue and single worker would be bottlenecks.

---

## Developer Experience

### Grade
B+

### Score
82

### Evidence
**Cargo Aliases:** `.cargo/config.toml` defines named aliases: `integration-tests`, `doc-tests`, `build-server`, `codegen`, `dump-schema`, `migrate`, `rollback`. These significantly reduce command memorization burden.

**Multi-Platform Builds:** The Dockerfile handles `x86_64` and `aarch64` with architecture-conditional PDFium binary download and SHA1 verification. CI runs on `self-hosted` runners (probably ARM + AMD64).

**Nix Flake:** `flake.nix` and `flake.lock` provide reproducible dev environment via Nix, uncommon for a community project and appreciated by Nix users.

**VSCode Config:** `.vscode/settings.json` and `.vscode/extensions.json` provide opinionated editor setup. `.vscode/tasks.json` provides task definitions.

**Husky/lint-staged:** Pre-commit hooks run `prettier --check` on JS/TS/JSON files and `cargo fmt --check` on Rust files, catching formatting issues before they reach CI.

**bacon:** `bacon.toml` is present, enabling `bacon run-server` for hot-reload development workflow for the server.

**CI Separation:** The CI pipeline in `ci.yaml` uses `paths-filter` to only run Rust checks on Rust changes, TypeScript checks on TS changes, and docs checks on docs changes. This keeps CI fast for partial changes.

**i18n:** 32 locale files via Crowdin integration makes the application accessible to a global user base and the process is contributor-friendly.

**Monorepo Tooling:** Lerna with `--stream --parallel` for JS checks and tests provides reasonable multi-package coordination. `yarn workspaces` `nohoist` for the Expo app handles the React Native dependency isolation quirks.

**Gaps:** The initial setup requires multiple manual steps (`docker compose`, `yarn install`, potentially Nix) without a single `make setup` or `just` equivalent. The `patches/` directory with 3 patch files for `react-native-screens`, `expo-router`, and `sf-symbols-typescript` suggests upstream dependency issues that add friction.

### Assessment
The developer experience investment is substantial for an open-source community project. The combination of Cargo aliases, Nix flake, husky hooks, bacon hot-reload, and selective CI makes day-to-day development productive. The VSCode configuration lowers the barrier for new contributors. The main DX friction points are the multi-step onboarding and the patch-package dependencies that indicate some upstream library friction.

---

## Long-Term Sustainability

### Grade
B

### Score
76

### Evidence
**Release Cadence:** The CHANGELOG shows active development with releases at `0.1.4` (2026-05-28) and `0.1.3` (2026-05-16), with features, fixes, and dependency bumps. The project appears actively maintained.

**Versioning:** `workspace.version = "0.1.4"` in `Cargo.toml` and `"version": "0.1.4"` in `package.json` are in sync. Semantic versioning is used. Version `0.1.x` signals explicit pre-1.0 status.

**Dependency Management:** Workspace-level dependency management in `Cargo.toml` centralizes version pinning for all Rust crates. Dependabot (`.github/dependabot.yml`) is configured for automated dependency update PRs. The weekly CVE check workflow creates issues for vulnerable dependencies.

**Database Migration Strategy:** Sequential, timestamped SeaORM migrations with up/down support (22 migrations from init to JWT secrets) provide a clear schema evolution path. The `rollback` cargo alias enables quick rollbacks.

**Community Infrastructure:** GitHub issue templates (bug report, feature request), PR template, CODE_OF_CONDUCT, CONTRIBUTING, SECURITY policy, and Discord link (in CONTRIBUTING.md) indicate community building investment.

**Architecture Debt:** The integration tests reference Prisma (the old ORM), suggesting a migration from Prisma to SeaORM occurred but the integration tests were not fully updated. This is a sustainability signal - test suite lagging behind implementation changes.

**Single Maintainer Risk:** The CONTRIBUTING and SECURITY documents reference a single email and Discord. The `git user` in the codebase (`Aaron Leopold`) and the `@stump/monorepo` package author are consistent, indicating single primary maintainer. Community contributions appear welcome but the bus factor is 1.

**Ecosystem Lock-in:** SQLite as the sole database backend (via SeaORM features: `sqlx-sqlite` only) limits scalability and deployment options. The `MemoryStorage` job queue loses jobs on restart. These are acknowledged tradeoffs for a self-hosted personal server.

### Assessment
Stump shows the characteristics of a well-managed community project approaching maturity. Active release cadence, automated security scanning, comprehensive migration history, and community infrastructure suggest sustainable operation. The single maintainer dependency is the primary sustainability risk. The SQLite-only backend is appropriate for the target deployment scale but limits future growth. The stale integration tests are a quality indicator that test maintenance lags feature development, a common pattern in solo-maintainer projects.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | High |
| Security Posture | Moderate-High |
| Maintainability | Moderate |
| Modularity | High |
| Test Confidence | Low-Moderate |
| Documentation Quality | Moderate-High |
| Production Readiness | Moderate (pre-1.0, self-hosted scale) |
| Enterprise Suitability | Low |
| Contributor Friendliness | High |
| Sustainability | Moderate |

---

# Final Verdict

## Overall Grade
B+

## Overall Score
80

## Confidence Score
88

## Repository Maturity
Community Project

## Best Attribute
Modularity

## Weakest Attribute
Testing

## Three-Paragraph Assessment

Stump is an engineering-quality community project that substantially exceeds the typical standards of solo-maintainer self-hosted media server software. The Rust codebase demonstrates genuine expertise: idiomatic error handling via `thiserror`, clean `async`/`await` throughout, proper `Arc`-based shared state, CI-enforced clippy and rustfmt, and a sophisticated proc-macro investment (`stump-config-gen`, `filter-gen`) that reduces boilerplate at a compilation-boundary level. The authentication architecture is comprehensive - bcrypt passwords, JWT with refresh rotation, prefixed API keys with permission scoping, OIDC, account lockout after brute-force attempts, and weekly CVE scanning. The 3,558-line GraphQL schema with DataLoaders, the Criterion performance benchmarks for library scanning, and the SeaORM migration history all reflect engineering maturity that goes beyond typical hobby-project depth.

Architecturally, the workspace design is the project's standout achievement. The decomposition into 15 purposeful crates with enforced compilation boundaries, the clean separation between the `StumpCore` library and the server binary, the unified `StumpJob` dispatch envelope, and the `JobLifecycle` trait pattern collectively form an architecture that scales well across feature complexity. The dual API surface (REST for streaming/OPDS, GraphQL for data) is justified by the use cases each serves. The JS package decomposition mirrors the Rust structure with similarly clean boundaries, and the 32-locale i18n system with Crowdin integration demonstrates investment in community scale. The `find_for_user()` pattern defined on entity structs and used 205 times enforces the multi-tenancy invariant at the data layer without repetition.

The project's primary long-term risks are testing coverage and single-maintainer dependency. The 10% coverage target and apparent non-functional integration tests (scanner tests reference a superseded Prisma ORM layer) mean the test suite cannot reliably catch regressions in the core scanning and job execution paths. The 249 `expect()` calls and 325 `.unwrap()` calls introduce panic potential in production paths that would bring down the Tokio runtime rather than returning graceful error responses. The acknowledged encryption key weakness and absence of endpoint-level rate limiting are security gaps appropriate for a pre-1.0 self-hosted product but would need resolution before enterprise deployment. As a community project targeting personal and small-group library management, Stump is production-ready for its intended scale, with engineering quality that positions it well for continued growth.

---
