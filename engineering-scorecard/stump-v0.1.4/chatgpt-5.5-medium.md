# Executive Summary

## Repository: stump
## Model: ChatGPT 5.5 (medium)

## Overall Score

Score: 76/100  
Grade: B  
Confidence: 88/100

Repository Maturity:

- Community Project

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | stump |
| Total Files | 2,535 |
| Source Files | 2,025 |
| Test Files | 36 |
| Languages | Rust, TypeScript, TSX, JavaScript, CSS, SQL/MDX/config |
| Dependency Count | 451 declared direct dependencies: 57 Rust workspace dependencies and 394 JavaScript package dependencies |
| Largest Module | `packages/browser` with 748 source files |
| Build System | Cargo workspace plus Yarn workspaces and Lerna |
| CI/CD Present | Yes: GitHub Actions for Rust checks, TypeScript checks, coverage, docs, CVE audit, Docker and release workflows |
| Containerization Present | Yes: `docker/Dockerfile` multi-stage image using Node, Rust, PDFium, and distroless final image |
| Test-to-Source Ratio | 0.018 |

Implementation coverage: inspected 50+ implementation and configuration files across `apps/server`, `core`, `crates/graphql`, `crates/models`, `crates/migrations`, `packages/client`, `packages/sdk`, `packages/browser`, `apps/expo`, tests, CI, Docker, and docs.

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | B | 82 | Clear Rust core/server/GraphQL/model separation plus multi-client packages, with some acknowledged server/core boundary debt. |
| Security | B | 78 | Strong authentication and permission model, OIDC, API keys, JWT secrets, and audit workflows, balanced by beta security caveats and permissive configurable CORS. |
| Maintainability | B | 76 | Typed Rust and TypeScript layers, shared models, and generated GraphQL clients help maintainability, but large modules and many TODO/FIXME markers reduce clarity. |
| Modularity | B | 83 | Cargo crates and Yarn packages provide strong subsystem boundaries across core, GraphQL, models, SDK, clients, and docs. |
| Code Quality | B | 78 | Consistent typed error handling, transactions, loaders, and schema validation, with some production comments indicating rough edges. |
| Testing | C | 62 | CI runs tests and coverage, and there are meaningful unit/integration tests, but only 36 test files for 2,025 source files. |
| Documentation | B | 73 | README, docs app, security notes, and package READMEs exist, with explicit beta status and some docs deferring to external/generated pages. |
| Performance Design | B | 75 | DataLoaders, WAL setup, batching around SQLite limits, background jobs, and thumbnail/media pipelines exist, but cursor pagination and scan concurrency have known constraints. |
| Developer Experience | B | 80 | Good workspace scripts, CI, Docker, Nix, codegen, generated types, linting, and formatting; complexity remains high. |
| Long-Term Sustainability | B | 74 | Coherent architecture and automation support sustainability, while beta status, broad platform surface, sparse tests, and large generated/frontend areas add maintenance load. |

# Deep Assessment

## Architecture

## Grade
B

## Score
82

## Evidence

- `Cargo.toml` defines a Rust workspace spanning `apps/server`, `core`, `crates/*`, app Tauri code, macros, and integrations, with centralized workspace dependencies.
- `package.json` defines Yarn workspaces for `apps/*`, `docs`, and `packages/*`, with Lerna scripts for linting, testing, building, and app-specific commands.
- `apps/server/src/main.rs` delegates CLI parsing, config bootstrap, tracing, and HTTP server startup instead of embedding all startup behavior in one entry point.
- `apps/server/src/http_server.rs` initializes server config, encryption, JWT secrets, WAL, scheduler, library watcher, routers, session layer, CORS, tracing, and background job worker.
- `crates/graphql/src/schema.rs` builds an async-graphql schema and registers multiple DataLoaders plus a query depth limit.
- `core/src/lib.rs` presents `StumpCore` as the server-side entry point around configuration, database, jobs, events, filesystem, OPDS, and Kobo support.
- Contradictory evidence: `apps/server/src/http_server.rs` has an explicit TODO that core-specific initialization and server-specific watcher/scheduler concerns need reorganization.

## Assessment

The repository has a strong multi-layer architecture for a media server: Axum server, reusable Rust core, SeaORM models, GraphQL API, migrations, TypeScript SDK, browser UI, desktop wrapper, mobile app, and docs are distinct subsystems. The architecture is more mature than a simple web app and shows deliberate separation between business logic, transport, persistence, and clients. Its main architectural weakness is boundary friction between `apps/server` and `core`, visible in startup orchestration and comments acknowledging that server-managed concerns still live near core initialization.

## Security

## Grade
B

## Score
78

## Evidence

- `apps/server/src/middleware/auth.rs` authenticates via session cookie, bearer JWT/API key, and OPDS basic auth, then injects `AuthContext`.
- `apps/server/src/middleware/auth.rs` validates API keys through prefixed key hashing, expiry checks, permission checks, and last-used updates.
- `apps/server/src/config/jwt.rs` stores separate access and refresh token secrets, caches them with `OnceLock`, persists refresh token IDs, and validates JWT claims.
- `apps/server/src/routers/api/v2/auth.rs` tracks login activity, locks accounts after repeated failures, supports max-session enforcement, and blocks local login when OIDC-only auth is enabled.
- `crates/graphql/src/data.rs` centralizes permission enforcement, locked-account checks, and server-owner enforcement.
- `crates/graphql/src/guard.rs` provides GraphQL guards for server-owner, self, permission, optional feature, and book-club role checks.
- `apps/server/src/utils/serve_media.rs` enforces `DownloadFile` permission and user-scoped media lookup before serving files.
- `.github/workflows/cve_check.yml` runs scheduled Yarn audit and opens security issues, and `.github/dependabot.yml` covers npm, Cargo, and GitHub Actions.
- `docs/content/docs/apps/desktop/security.mdx` documents token and credential storage using OS secure stores.
- Contradictory evidence: `core/src/lib.rs` labels auto-created database encryption keys as insecure in a TODO, `apps/server/src/config/cors.rs` allows configured wildcard origins with credentials, and desktop docs state debug builds expose a developer console.

## Assessment

Security is a first-class subsystem rather than incidental middleware. The project has layered authentication, persistent refresh-token state, API-key hashing, OIDC support, login activity tracking, locked accounts, user-scoped media queries, and explicit GraphQL guards. The security posture is not enterprise-grade because the repository itself documents beta limitations, insecure transitional encryption behavior, and desktop build security caveats. Overall, the code demonstrates strong practical security design for self-hosted software, with several known risks explicitly acknowledged.

## Maintainability

## Grade
B

## Score
76

## Evidence

- Workspace dependency management in `Cargo.toml` reduces duplicated Rust dependency declarations.
- `crates/models/src/entity/media.rs`, `library.rs`, and `series.rs` provide reusable `find_for_user` query helpers that keep access-control filters close to data models.
- `packages/client/src/hooks/useGraphQL.ts` centralizes React Query integration, GraphQL execution, upload mutations, authentication error handling, and websocket helpers.
- `packages/browser/src/scenes/settings/server/users/create-or-update/schema.ts` uses Zod schemas for UI-side validation against generated GraphQL types.
- `crates/migrations/src/lib.rs` has an ordered migration chain rather than ad hoc schema changes.
- Contradictory evidence: `packages/graphql/src/client/graphql.ts` is a generated 13,265-line file; `crates/migrations/src/m20250807_202824_init.rs` is 4,086 lines; `crates/graphql/src/mutation/library.rs` exceeds 1,100 lines; and `rg` found many TODO/FIXME markers across server, core, SDK, and browser code.

## Assessment

Maintainability is good for a repository of this breadth because shared query helpers, generated types, central SDK/client wrappers, and workspace dependency management reduce drift. The code also has a transparent style: many comments explain tradeoffs and limitations. The maintainability ceiling is reduced by large modules, generated code volume in the tree, and recurring TODO/FIXME markers in active paths such as pagination, CORS configuration, SDK URL handling, socket lifecycle, scan concurrency, and frontend rendering performance.

## Modularity

## Grade
B

## Score
83

## Evidence

- Major directories separate `apps/server`, `apps/web`, `apps/desktop`, `apps/expo`, `core`, `crates`, `packages`, and `docs`.
- Rust crates isolate `graphql`, `models`, `migrations`, `cli`, `email`, integration crates, and macros.
- TypeScript packages isolate browser UI, SDK, GraphQL generated client, shared components, i18n, and client hooks.
- `apps/server/src/routers/mod.rs` composes API, SPA, OPDS, Kobo, and KOReader routers and conditionally mounts optional integrations.
- `crates/graphql/src/schema.rs` composes query, mutation, subscription, and loaders through schema construction rather than one transport file.
- `packages/sdk/src/api.ts` exposes controller groupings for auth, EPUB, library, media, OPDS, series, and server APIs.
- Contradictory evidence: startup in `apps/server/src/http_server.rs` still coordinates core, database, watcher, scheduler, router, and worker lifecycle directly.

## Assessment

The repository is modular at both build-system and source-organization levels. Its crate and package boundaries map to real product seams: persistence models, GraphQL, core filesystem/media logic, SDK, browser UI, mobile app, and desktop app. The modularity is strongest in package layout and reusable model/query abstractions. It is weaker in runtime orchestration where the server startup path remains a dense coordinator of several subsystem lifecycles.

## Code Quality

## Grade
B

## Score
78

## Evidence

- `apps/server/src/errors.rs` defines typed API, auth, server, and entry errors with status-code mapping.
- `core/src/filesystem/scanner/utils.rs` uses explicit database transactions for media creation/update and tag linking.
- `crates/graphql/src/query/media.rs` uses typed filter inputs, pagination validators, SeaORM query builders, user-scoped model helpers, and typed response objects.
- `crates/graphql/src/mutation/library.rs` uses transactions for destructive cleanup and queues typed `StumpJob` variants for long-running analysis and metadata work.
- `crates/graphql/src/loader/media.rs` and `series_count.rs` batch lookup patterns through async-graphql DataLoader implementations.
- `packages/browser/src/scenes/settings/server/users/create-or-update/schema.ts` validates form inputs with typed Zod schemas.
- Contradictory evidence: some production code contains acknowledged rough edges such as `FIXME: Cursor ordering is broken` in `crates/graphql/src/query/media.rs`, `TODO: encode` in `packages/sdk/src/api.ts`, and `FIXME: this is NOT performant` in `packages/browser/src/hooks/useSyncParams.ts`.

## Assessment

The codebase generally uses strong language features and framework primitives well: Rust enums for errors, SeaORM query composition, async job lifecycles, DataLoaders, GraphQL schema typing, React Query wrappers, and Zod validation. Code quality is consistently above average, especially in access-control and data-query paths. The primary quality drag is not style inconsistency, but the number of known incomplete or imperfect areas in production-adjacent modules.

## Testing

## Grade
C

## Score
62

## Evidence

- 36 test files were found for 2,025 source files, giving a test-to-source ratio of 0.018.
- `.github/workflows/ci.yaml` runs `cargo fmt`, `cargo clippy -D warnings`, GraphQL schema verification, `cargo test`, Rust coverage, TypeScript linting, TypeScript tests, and docs build.
- `core/integration-tests/tests` covers EPUB, RAR, ZIP, scanner, and utilities.
- `crates/models/src/entity/media.rs` tests generated SQL for user-scoped media queries and age restrictions.
- `apps/server/src/middleware/auth.rs` tests request context permission and server-owner enforcement.
- `packages/browser/src/scenes/settings/server/users/create-or-update/__tests__/schema.test.ts` covers user form schema validation.
- `packages/sdk/src/controllers/__tests__/utils.test.ts` covers OPDS URL resolution edge cases.
- Contradictory evidence: many large and critical files have no adjacent tests in the inspected sample, and README explicitly lists comprehensive tests as an area needing help.

## Assessment

The project has meaningful tests in the right places for some risky logic: data-access filters, permission helpers, file format handling, scanner integration, UI schemas, SDK URL logic, and reader utilities. CI also treats tests as a standard quality gate. The total volume is thin relative to repository size and product surface area, especially considering server auth, GraphQL mutations, background jobs, desktop/mobile clients, and media-processing complexity.

## Documentation

## Grade
B

## Score
73

## Evidence

- `README.md` states project status, feature set, setup direction, repository structure, contribution areas, license split, and attribution.
- `docs/content/docs/apps/desktop/security.mdx` documents desktop token storage, credential storage, debug-build security implications, macOS remote access restrictions, and signing status.
- `docs/content/docs/apps/web/index.mdx` describes web-app access and deployment context.
- `docs` is its own package with a Vite/TanStack-style docs app and content tree.
- Several package-level READMEs exist under `core`, `docs`, `packages/client`, and `packages/components`.
- Contradictory evidence: `README.md` defers getting-started and developer-guide details elsewhere, while some security and production-readiness notes describe unstable or future-state behavior.

## Assessment

Documentation is solid for a community project. It gives users, contributors, and operators enough context to understand the repository layout, product status, security model, and app surfaces. The docs also candidly document beta status and platform caveats. Documentation quality is not uniformly deep across every internal subsystem, but the repository has a real docs site rather than only a README.

## Performance Design

## Grade
B

## Score
75

## Evidence

- `crates/graphql/src/schema.rs` registers DataLoaders and limits GraphQL query depth to 15.
- `crates/graphql/src/loader/series_count.rs` batches series media counts with grouped SQL.
- `core/src/database.rs` defines a SQLite bind limit and batching helpers to avoid excessive SQL parameters.
- `core/src/lib.rs` initializes WAL journal mode for SQLite.
- `core/src/filesystem/scanner/library_scan_job.rs` breaks scans into discovery and per-series tasks, emits progress and events, and queues downstream thumbnail, analysis, and metadata work.
- `apps/server/src/http_server.rs` runs background jobs through Apalis workers and graceful shutdown.
- `packages/browser/src/components/smartList/createOrUpdate/queryBuilder/SmartListQueryBuilder.tsx` exposes a performance warning for complex smart-list filters.
- Contradictory evidence: background worker concurrency is set to `1` with a TODO to experiment, and `crates/graphql/src/query/media.rs` marks cursor ordering as broken.

## Assessment

Performance design is deliberate in several important areas: GraphQL batching, query-depth limiting, SQLite WAL, bind-limit batching, background job orchestration, and scan task decomposition. The code is not optimized uniformly. Some choices are explicitly conservative, such as single worker concurrency, and some user-facing query paths have known issues or performance warnings. The repository shows performance awareness but not full performance maturity.

## Developer Experience

## Grade
B

## Score
80

## Evidence

- `package.json` provides setup, lint, type-check, test, clean, and app-specific scripts for server, browser, desktop, web, docs, and Expo workflows.
- `Cargo.toml` centralizes Rust dependencies and workspace membership.
- `.github/workflows/ci.yaml` uses path filters to run relevant Rust, TypeScript, docs, and coverage checks.
- `.github/actions/setup-rust` pins Rust `1.92.0`, installs rustfmt and clippy, and caches Rust dependencies.
- `.github/actions/setup-yarn` pins Node `22.14.0`, installs Yarn, and configures dependency installation.
- `docker/Dockerfile` builds frontend, server, PDFium, and a distroless runtime image.
- `flake.nix` exists for Nix-based environments.
- Contradictory evidence: CI Rust jobs use self-hosted runners, setup spans Cargo, Yarn, Lerna, codegen, Tauri, Expo, Docker, PDFium, and generated GraphQL, making contributor setup inherently complex.

## Assessment

Developer experience is strong for a complex monorepo. The project has consistent scripts, pinned toolchains, CI quality gates, Docker packaging, Nix support, and shared generated types. Complexity is the limiting factor: multiple platforms and build ecosystems mean onboarding and debugging can be heavy even with automation.

## Long-Term Sustainability

## Grade
B

## Score
74

## Evidence

- The repository has clear package boundaries, generated GraphQL types, code-managed migrations, reusable model query helpers, CI, coverage upload, Dependabot, CVE audit, Docker release workflows, and docs.
- `README.md` explicitly states active beta status and no timeline guarantees.
- The codebase supports many surfaces: web, desktop, mobile, OPDS v1.2/v2.0, Kobo, KOReader, media scanning, metadata, email, jobs, smart lists, and book clubs.
- Test coverage exists but is sparse relative to source volume.
- Large generated and high-complexity files include `packages/graphql/src/client/graphql.ts`, migration files, GraphQL mutations, OPDS routers, scanners, and reader components.

## Assessment

The repository has sustainable foundations: typed systems, modular packaging, schema/migration discipline, automation, and documentation. Long-term risk comes from breadth. A beta self-hosted media platform spanning Rust backend logic, multiple TypeScript clients, native desktop/mobile constraints, media processing, and third-party reading protocols needs stronger regression coverage and tighter boundaries to reach mature-project sustainability.

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Strong |
| Security Posture | Strong |
| Maintainability | Good |
| Modularity | Strong |
| Test Confidence | Moderate |
| Documentation Quality | Good |
| Production Readiness | Moderate to Strong |
| Enterprise Suitability | Moderate |
| Contributor Friendliness | Good |
| Sustainability | Good |

# FINAL VERDICT

## Overall Grade
B

## Overall Score
76/100

## Confidence Score
88/100

## Repository Maturity
Community Project

## Best Attribute
Modularity

## Weakest Attribute
Testing

## Three-Paragraph Assessment

Stump is a well-engineered self-hosted media server with a broad and coherent technical foundation. The implementation uses Rust for core/server work, SeaORM for data modeling, async-graphql for API composition, generated GraphQL types for clients, and React/Expo/Tauri surfaces for users. Core implementation evidence shows thoughtful handling of authentication, authorization, migrations, media scanning, background jobs, data loading, and typed client access.

Architecturally, the repository is stronger than average community software. The separation between `core`, `apps/server`, `crates/graphql`, `crates/models`, `crates/migrations`, and TypeScript packages is meaningful and well reflected in code. The main architectural constraints are concentrated in runtime orchestration and large feature modules, where comments identify server/core boundary issues, conservative job concurrency, and incomplete pagination or SDK behavior.

Long-term sustainability is good but not yet mature-project level. The repository has automation, documentation, dependency management, security workflows, and multi-platform packaging, but its beta status, large product surface, sparse tests, and many active TODO/FIXME markers create ongoing maintenance pressure. Against professionally maintained production software, Stump is a strong community project with solid engineering foundations and moderate regression confidence.
