# Executive Summary

## Repository: stump
## Model: Claude Opus 4.8 (high)

## Overall Score

Score: 86/100
Grade: A
Confidence: 88/100

Repository Maturity: **Production Ready**

Stump is a self-hosted comics/manga/e-book media server built as a polyglot monorepo: a Rust backend (axum 0.8, SeaORM, async-graphql, apalis job runner) with a layered TypeScript frontend (React 19, TanStack Query, Zustand) spanning web, Tauri desktop, and Expo mobile. The engineering is consistently strong on the Rust side: a defense-in-depth authorization model (`find_for_user` query scoping plus declarative GraphQL guards), idiomatic `thiserror` error layering, DataLoader-based N+1 prevention, parameterized SeaORM queries, and a mature CI/release toolchain (clippy `-D warnings`, schema verification, Codecov, scheduled CVE audits, SHA-pinned distroless Docker builds). The principal weaknesses are a notably thin frontend test layer, a few concrete security gaps in the OIDC flow (no nonce/state/PKCE verification), a hardcoded non-secure session cookie, and isolated production-path `unwrap()` panics. The project is the work of essentially a single primary maintainer, which is the dominant long-term sustainability risk.

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | A | 89 | Clean monorepo with strong layering: core/models/graphql/server separation, trait-based file processors, job orchestration |
| Security | B | 80 | Excellent authz and SQL safety; concrete gaps in OIDC (no nonce/state/PKCE) and insecure cookie default |
| Maintainability | A | 87 | Workspace-pinned deps, consistent patterns, good docs; high TODO density and some god files temper it |
| Modularity | A | 90 | Clear crate/package boundaries, trait abstractions, clean dependency graph, no circular deps |
| Code Quality | A- | 85 | Idiomatic Rust, low lint-suppression count; isolated `unwrap()` panics and frontend `any`/`@ts-expect-error` usage |
| Testing | B | 78 | 453 Rust test assertions across 103 files with real integration tests; frontend coverage is sparse (~2-3%) |
| Documentation | A | 88 | 60-page docs site, thorough rustdoc, CONTRIBUTING, CLI docs, breaking-change guides |
| Performance Design | A- | 85 | Rayon-parallel scanning, DataLoaders, batched inserts respecting bind limits, async image processing |
| Developer Experience | A | 88 | Nix flake, bacon, husky/lint-staged, path-filtered CI, code generation, editorconfig/rustfmt/prettier |
| Long-Term Sustainability | B- | 74 | Modern, well-maintained stack but single-maintainer bus factor and self-declared beta status |

---

# Deep Assessment

## Architecture

### Grade
A

### Score
89

### Evidence
- Clear physical layering: `core/` (filesystem, jobs, OPDS, kobo), `crates/models` (SeaORM entities), `crates/graphql` (resolvers/guards/loaders), `apps/server` (axum HTTP + middleware + routers), with the entry point `StumpCore` in `core/src/lib.rs` cleanly orchestrating config, encryption, JWT secret, journal-mode, scheduler, and watcher initialization.
- `apps/server/src/http_server.rs` composes the app declaratively: router merge, session layer, CORS layer, `TraceLayer`, apalis `Monitor` worker, and graceful shutdown via `Notify`.
- Job system is well-abstracted: `core/src/job/stump_job.rs` defines a unified `StumpJob` enum dispatched through apalis; scanning is decomposed into `LibraryScanTask`/`SeriesScanTask` state machines (`core/src/filesystem/scanner/library_scan_job.rs`).
- Trait-based extensibility for file formats (`FileProcessor` per ZIP/RAR/PDF/EPUB) and for metadata providers (`crates/integrations/metadata/provider.rs`).
- GraphQL is a first-class API layer with generated schema verified in CI (`cargo dump-schema -- --check`), and the TS client consumes generated typed documents (`packages/graphql`).
- Frontend mirrors the layering: `@stump/sdk` (HTTP/GraphQL base) → `@stump/client` (queries/stores) → `@stump/components` → `@stump/browser` (feature shell) consumed by `apps/web`, `apps/desktop`, `apps/expo` with no circular dependencies.

### Assessment
The architecture is coherent and deliberately layered, separating persistence, API, business logic, and transport. Boundaries are enforced through crates rather than convention, and cross-cutting concerns (auth, CORS, tracing, sessions) live in middleware/layers. The author's own TODO comments (e.g., "core-specific initializations should just be in some initialization function") acknowledge that the core/server initialization split is imperfect, and a few orchestration responsibilities leak between `StumpCore` and the server binary. These are minor relative to the overall clarity. The multi-platform frontend strategy is well executed, sharing the bulk of logic via `@stump/browser`.

---

## Security

### Grade
B

### Score
80

### Evidence
Strengths:
- Defense-in-depth authorization: every user-facing query is scoped via `find_for_user` (e.g., `crates/models/src/entity/library.rs`, `series.rs` with age-restriction and library-exclusion subqueries), and GraphQL mutations carry declarative guards (`#[graphql(guard = "PermissionGuard::one(UserPermission::ManageLibrary)")]`). Guards include `ServerOwnerGuard`, `SelfGuard`, `PermissionGuard`, `BookClubRoleGuard` (`crates/graphql/src/guard.rs`).
- Password hashing via bcrypt with configurable cost (`apps/server/src/utils/auth.rs`); JWT access/refresh pair with DB-tracked `jti` revocation (`apps/server/src/config/jwt.rs`); API keys are prefixed and stored as hashes with permission inheritance/custom scoping and expiry checks (`apps/server/src/middleware/auth.rs::validate_api_key`).
- Brute-force protection: account auto-lock after >=9 failed attempts in 24h, login-activity audit trail, session-on-lock invalidation (`apps/server/src/routers/api/v2/auth.rs`).
- Path-traversal mitigation: media is served by DB lookup of an ID scoped to the user, never by raw client path (`apps/server/src/utils/serve_media.rs`).
- SQL injection safe throughout via SeaORM typed column builders; parameterized `.contains()` search.
- OIDC uses `redirect::Policy::none()` (SSRF mitigation) and ID-token audience verification (`apps/server/src/config/oidc.rs`).
- Operational security posture: scheduled `yarn audit` CVE workflow that auto-files issues (`.github/workflows/cve_check.yml`); SHA1-verified PDFium binary in the Dockerfile; distroless final image.

Gaps (concrete):
- OIDC CSRF/nonce/PKCE are effectively disabled: `nonce_verifier` always returns `Ok(())` (`oidc.rs:178`), the `state` parameter is `serde_json::from_str(...).unwrap_or_default()` rather than a verified anti-CSRF token (`oidc.rs::parse_state`), and `grep` finds zero PKCE usage in the server.
- Session cookie is hardcoded `with_secure(false)` and `SameSite::Lax` (`apps/server/src/config/session/utils.rs`), acknowledged via TODO for the Tauri case.
- CORS allows a `*` wildcard mode together with `allow_credentials(true)` when configured (`apps/server/src/config/cors.rs`) - a known footgun if a user sets `*`.
- A self-described "insecure" auto-generated DB encryption key path is left in for setup friction (`core/src/lib.rs::init_encryption`, with an explicit TODO to remove).

### Assessment
The core authorization and data-access security is genuinely strong and consistently applied - this is the repository's most disciplined security area. The weaknesses are real and specific rather than systemic: the OIDC integration omits standard CSRF/nonce/PKCE defenses, and the cookie/CORS defaults favor self-hosted convenience over hardened defaults. None of these are obfuscated; most are annotated with TODOs, indicating awareness. The combination keeps Security at a solid B: excellent in the largest surface (multi-user data access), with a handful of specific protocol-level and configuration-level gaps.

---

## Maintainability

### Grade
A

### Score
87

### Evidence
- Centralized dependency management: nearly all crate dependencies are pinned in the root `Cargo.toml` `[workspace.dependencies]` with alphabetical ordering and explanatory comments, including pinned/forked deps with rationale (e.g., the `zip = "=1.1.3"` downgrade note and the forked `epub-rs`).
- Consistent error handling: `thiserror`-based layered error enums with `#[from]` conversions (`apps/server/src/errors.rs`, `core/src/filesystem/error.rs`, `crates/email/src/error.rs`).
- Strong inline documentation/rustdoc across core modules (`core/src/lib.rs` has runnable doc examples).
- Low lint-suppression footprint: only ~18 `#[allow(...)]` across 457 Rust files; `#![warn(clippy::dbg_macro)]` enforced per crate.
- Tooling for consistency: `.rustfmt.toml`, `.editorconfig`, `prettier.config.js`, `eslint.config.mjs`.

Tempering factors:
- High TODO/FIXME density: ~190 occurrences across Rust (`grep` count), several flagging planned rewrites (rayon→tokio in the scanner, EpubJsReader "consider total re-write").
- Frontend god files: `EpubJsReader.tsx` (~1013 lines, 3 refactor TODOs), `AppLayout.tsx` (~262 lines mixing state/scrollbars/permissions), and a 765-line `useGraphQL.ts`.
- Some feature duplication on the frontend (metadata editors / form schemas across book/series/smart-list contexts).

### Assessment
The codebase is highly maintainable on the Rust side: dependency hygiene is exemplary, error handling is uniform, and lint discipline is strong. The frontend is maintainable in aggregate but carries a few complexity hotspots and duplicated form/metadata logic that would slow change in those areas. The pervasive TODO comments are mostly honest design notes rather than rot, but their density signals an actively-in-flux codebase. Overall this lands at a high A- to A.

---

## Modularity

### Grade
A

### Score
90

### Evidence
- Cargo workspace cleanly partitions concerns: `core`, `apps/server`, `apps/desktop/src-tauri`, and `crates/*` (cli, email, graphql, integrations, macros, migrations, models, tests). Models, GraphQL API, and core logic are separate crates with directional dependencies.
- Trait-driven seams: `FileProcessor` per archive format, metadata `provider.rs` trait, job `JobLifecycle` trait, GraphQL `Guard`/`Loader` traits.
- Proc-macro crates isolate code generation (`crates/macros/filter-gen`, `stump-config-gen`) keeping the DSL generation out of business logic.
- Shared test infrastructure crate (`crates/tests`) provides in-memory SQLite DB + fake-data fixtures reused by unit/integration tests.
- Frontend dependency graph is clean and acyclic: `sdk → client → components/browser → apps`; types generated once in `@stump/graphql` and reused everywhere.

### Assessment
Modularity is a standout. The crate boundaries are meaningful and enforced by the compiler, abstractions are introduced where they earn their keep (file formats, metadata providers, jobs, guards), and there is no evidence of cross-module reaching into internals. The one modularity caveat is on the frontend, where the Expo app re-implements some store/util patterns rather than sharing them with `@stump/browser`, and a couple of features are duplicated rather than extracted. These are localized and do not undermine the otherwise excellent separation.

---

## Code Quality

### Grade
A-

### Score
85

### Evidence
- Idiomatic Rust: pervasive `Result`-based error propagation, `thiserror` enums, builder patterns, `apply_if` conditional query composition, and only 4 `unsafe` blocks total - all justified (`libc::setlocale` for RAR locale; Windows `GetLogicalDriveStringsW` drive enumeration).
- Comprehensive unit tests embedded with code (e.g., 18 auth-context/permission tests and OPDS response tests in `apps/server/src/middleware/auth.rs`; credential-decoding edge cases in `utils/auth.rs`; JWT round-trip tests in `config/jwt.rs`).
- Input validation where it matters: `ImageProcessorOptions::validate` rejects out-of-range quality/scale/dimensions (`core/src/filesystem/image/process.rs`); graceful degradation patterns (`zip.rs` `enclosed_name().unwrap_or_else(...)` with a warning).

Detractors (concrete):
- Production-path panics: `core/src/filesystem/archive.rs:16` (`File::create(destination).unwrap()`) and `:32` (`strip_prefix(...).unwrap()`) inside `zip_dir`, which returns `ZipResult<()>` and should use `?` - reachable via RAR→ZIP conversion.
- ~404 raw `.unwrap()` and ~227 `.expect(...)` in non-test Rust; most are in infallible/init contexts but the count is non-trivial.
- Frontend type-safety holes: ~45 browser files using `any`, 10+ `@ts-expect-error`, and untyped WebSocket message casting in the SDK.

### Assessment
Code quality is high and consistent in Rust, with strong test density and disciplined error handling, undercut only by a small number of genuine panic sites and a moderate raw-unwrap count. The frontend is generally clean and strictly configured (`strict`, `noUncheckedIndexedAccess`, `noUnusedLocals`) but has more type-safety escape hatches than the backend. The net is a clear A-: excellent backend craftsmanship with a few specific, locatable blemishes.

---

## Testing

### Grade
B

### Score
78

### Evidence
- Rust testing is substantial: 453 `#[test]`/`#[tokio::test]` assertions across 103 files; real integration tests exercising archive formats and the scanner (`core/integration-tests/tests/{scanner,rar,epub,zip}.rs`).
- Shared in-memory SQLite test harness (`crates/tests/src/db.rs`) and fake-data fixtures enable DB-backed unit tests (used by JWT, auth, entity age-restriction tests).
- Security-relevant logic is tested: permission enforcement, server-owner checks, OPDS auth responses, credential decoding, JWT round-trips, account-lock paths.
- CI enforces `cargo test` plus Codecov coverage gating on Rust changes (`.github/workflows/ci.yaml`).

Gaps:
- Frontend coverage is thin: ~26 TS test files against ~1500 frontend source files; `@stump/client` and `@stump/components` have zero tests; `@stump/browser` ~3.9% of files have tests (mostly form schemas/utilities, not large components or stores).
- No GraphQL resolver integration tests (guard/dataloader behavior is largely unit-tested in isolation).

### Assessment
Backend testing is a genuine strength - the integration tests against real archive fixtures and the shared DB harness give meaningful confidence in the most error-prone subsystem (file scanning/parsing). The frontend, by contrast, is largely unverified beyond schemas and utilities, which is the main drag on this category. With a ~1:15 test-to-source ratio overall and strong Rust-side discipline but weak TS-side coverage, Testing settles at a solid B.

---

## Documentation

### Grade
A

### Score
88

### Evidence
- Dedicated documentation site (fumadocs) with 60 MDX pages spanning installation (Docker/binaries/source), fundamentals (libraries, books, scanner, thumbnails, background-jobs), configuration, features, integrations, breaking-changes, and a developer/contributing guide (`docs/content/docs/...`).
- Repository docs: thorough `README.md` (features, structure, licensing, attribution), `.github/CONTRIBUTING.md`, generated CLI docs (`docs/cli.json`).
- Strong inline rustdoc with runnable examples (`core/src/lib.rs`), and per-function doc comments explaining intent across auth/middleware/jwt.
- Crowdin-based i18n with documented translation workflow.

### Assessment
Documentation is well above typical open-source norms: a maintained docs site, developer onboarding material, breaking-change notes, and high-quality rustdoc. The main shortfall is on the frontend packages, several of which lack package-level READMEs and JSDoc on non-obvious store/hook logic. This is a clear A - the user-facing and contributor-facing documentation is comprehensive and current.

---

## Performance Design

### Grade
A-

### Score
85

### Evidence
- Parallel filesystem scanning using `rayon` (`par_bridge`, `partition_map`) with depth control and globset ignore rules (`core/src/filesystem/scanner/walk.rs`).
- N+1 query prevention via async-graphql DataLoaders across 22 GraphQL files (media/series/reading-session/favorite loaders batch by key).
- Batched DB writes that respect `SQLITE_BIND_LIMIT` during scans (`core/src/filesystem/scanner/library_scan_job.rs`).
- Async image processing offloaded to `spawn_blocking` with oneshot channels (`core/src/filesystem/image/mod.rs`); sample-based hashing to avoid full-file reads for large media (`pdf.rs`).
- SQLite WAL journal-mode initialization for better concurrency; cached JWT secrets via `OnceLock` to avoid repeated DB hits.

Caveats:
- Single-concurrency apalis worker for jobs (`concurrency(1)` in `http_server.rs`), with an author TODO noting historical multi-writer issues - intentional but a throughput ceiling.
- Author TODO to migrate scanner from rayon to tokio for IO-bound work suggests the current model is acknowledged as imperfect.

### Assessment
Performance is clearly designed for, not incidental: parallel scanning, batched inserts, DataLoaders, blocking-pool offload, and caching all reflect deliberate engineering for a media-server workload over SQLite. The single-worker job concurrency is a conscious correctness-over-throughput tradeoff. Overall a strong A-, with the main ceilings being the SQLite single-writer reality and the still-rayon scanner.

---

## Developer Experience

### Grade
A

### Score
88

### Evidence
- Reproducible environments via Nix flake (`flake.nix`/`flake.lock`) and `rust-toolchain.toml` pinning Rust 1.92.
- `bacon.toml` for fast incremental Rust feedback; `.cargo/` config; husky + lint-staged pre-commit (`.husky/pre-commit`).
- Path-filtered CI (`dorny/paths-filter`) runs only relevant jobs (rust/frontend/docs/expo) - fast, targeted feedback.
- CI enforces formatting (`cargo fmt --check`, prettier), linting (`cargo clippy -D warnings`, `yarn lint`), tests, coverage, and GraphQL schema drift.
- Code generation reduces boilerplate: filter/ordering proc-macros, config-gen macros, generated GraphQL TS types; GraphQL LSP plugin in tsconfig.
- Workspace tooling: yarn workspaces + lerna + cargo workspace; `.vscode/` settings; consistent editorconfig/rustfmt/prettier.

### Assessment
The contributor experience is well-considered for a project of this scope: hermetic dev environments, fast and selective CI, strong pre-commit gates, and generation that keeps the API contract in sync across languages. The polyglot setup (Rust + multiple TS platforms) raises the onboarding bar, but the documentation and tooling substantially offset that. A clear A.

---

## Long-Term Sustainability

### Grade
B-

### Score
74

### Evidence
- Modern, actively-maintained stack: axum 0.8, SeaORM 1.1, async-graphql 7.2, Rust 1.92, React 19 - dependencies are recent and centrally pinned.
- Migration discipline: 23 timestamped SeaORM migrations with semantic names and type-safe `DeriveIden` definitions, including security and redesign migrations.
- Operational sustainability signals: scheduled CVE audits, nightly/unstable/release CI workflows, distroless reproducible Docker builds.
- Bus-factor risk: the repository history surfaces a single primary author (`git shortlog` shows one dominant contributor for this checkout), and the README explicitly states "I develop and maintain Stump in my free time... there is no guarantee of any timeline," with a beta-status disclaimer.
- Some forked/pinned upstream dependencies (`epub-rs` fork, `zip` downgrade) create maintenance obligations tied to upstream PRs.

### Assessment
Technically the project is well-positioned to endure: the stack is current, schema evolution is handled rigorously, and the CI/release machinery is automated. The dominant risk is organizational rather than technical - a single primary maintainer working in their free time, self-declared beta status, and a couple of forked dependencies that must be tracked. These factors cap sustainability at B-: the engineering would support long life, but the maintenance model concentrates continuity risk in one person.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | High |
| Security Posture | Strong (with specific gaps) |
| Maintainability | High |
| Modularity | High |
| Test Confidence | Moderate-High (backend) / Low (frontend) |
| Documentation Quality | High |
| Production Readiness | Production Ready |
| Enterprise Suitability | Moderate |
| Contributor Friendliness | High |
| Sustainability | Moderate (single-maintainer risk) |

---

# FINAL VERDICT

## Overall Grade
A

## Overall Score
86/100

## Confidence Score
88/100

## Repository Maturity
Production Ready

## Best Attribute
Modularity and the layered, defense-in-depth data-access architecture (crate-enforced boundaries, `find_for_user` scoping, declarative GraphQL guards, trait-based file/metadata abstractions).

## Weakest Attribute
Long-Term Sustainability, driven by single-maintainer bus-factor risk and self-declared beta status; closely followed by thin frontend test coverage.

## Three-Paragraph Assessment

**Engineering quality.** Stump exhibits well-above-average engineering for an open-source self-hosted application. The Rust backend is idiomatic and disciplined: `thiserror`-layered error handling, parameterized SeaORM queries, only four well-justified `unsafe` blocks, a low `#[allow]` count, and embedded plus integration tests that exercise the riskiest subsystem (archive parsing and library scanning) against real fixtures. Security in the largest surface - multi-user data access - is genuinely strong, with consistent query scoping, age restrictions, library exclusions, bcrypt, JWT-with-revocation, hashed prefixed API keys, and brute-force lockout. The countervailing quality issues are specific and locatable: two production-path `unwrap()` panics in `archive.rs`, a moderate raw-unwrap count, OIDC missing nonce/state/PKCE verification, an insecure-by-default session cookie, and a frontend with type-safety escape hatches and a couple of god files.

**Architectural maturity.** The architecture is mature and intentional. Concerns are separated into compiler-enforced crates (models, graphql, core, integrations, macros, cli), abstractions are introduced where they pay for themselves (file-format processors, metadata providers, job lifecycles, GraphQL guards/loaders), and the API contract is generated and CI-verified across the Rust/TypeScript boundary. The multi-platform frontend shares the bulk of its logic through a clean, acyclic package graph. Performance is designed for rather than incidental: rayon-parallel scanning, DataLoader batching, bind-limit-aware bulk inserts, blocking-pool image processing, and SQLite WAL. Acknowledged rough edges (core/server initialization overlap, single-concurrency job worker, rayon-to-tokio migration intent) are documented and do not detract materially from the overall coherence.

**Long-term sustainability.** From a purely technical standpoint, the project is well-equipped to endure - a current dependency stack pinned at the workspace level, rigorous timestamped migrations, automated CVE scanning, and reproducible distroless builds. The principal risk is organizational: the codebase is effectively driven by a single primary maintainer working in their spare time, the README candidly disclaims timeline guarantees and labels the software beta, and a few forked/pinned upstream dependencies impose ongoing maintenance coupling. That concentration of continuity risk in one contributor, rather than any deficiency in the code itself, is what keeps the sustainability outlook moderate even as the rest of the engineering reads as production-ready.
