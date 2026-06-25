# Executive Summary

## Repository: stump

## Model: ChatGPT 5.5 (xhigh)

## Overall Score

Score: 76/100

Grade: B

Confidence: 88/100

Repository Maturity: Beta / production-usable self-hosted application

## Assessment Method

The assessment followed the requested order: discovery, implementation analysis, evidence consolidation, then scoring. No cross-repository comparison was used, and no changes were made to the assessed repository.

Implementation coverage exceeded the required threshold through repository-wide static inspection of all tracked Rust and TypeScript-family source files, plus detailed reads across the server, core processing, GraphQL, models, SDK, web, mobile, desktop, component, OPDS, Kobo, test, build, CI, and containerization layers. Source-code evidence, not README or directory layout, is the basis for the majority of findings.

## Repository Statistics

| Metric | Value |
| --- | --- |
| Total tracked files | 2,506 |
| Source files inspected by static scan | 2,002 Rust/TypeScript-family files |
| Non-test implementation files | 1,963 |
| Required implementation threshold | 401 files, based on 20% of 2,002 source files |
| Test files | 39 source test files, 64 tracked test-related files including fixtures/data |
| Test-to-source ratio | 39 / 1,963 = 2.0% by source test files versus non-test implementation files |
| Languages present | Rust, TypeScript, TSX/React, JavaScript, CSS, MDX, TOML, YAML, Nix, Kotlin, Swift |
| Dependency count | 413 unique direct dependencies from parsed manifests: 118 Rust, 295 JavaScript/TypeScript |
| Largest module by implementation file count | `packages/browser` with 737 source files |
| Largest implementation file | `packages/graphql/src/client/graphql.ts`, 13,265 LOC generated GraphQL client |
| Other large files | `crates/migrations/src/m20250807_202824_init.rs`, `apps/server/src/routers/opds/v2_0.rs`, `core/src/filesystem/media/format/epub.rs`, `core/src/filesystem/scanner/utils.rs`, `crates/graphql/src/mutation/library.rs` |
| Build system | Cargo workspace, Yarn 1/Lerna workspaces, Vite, Expo, Tauri, Drizzle, SeaORM migrations, Nix flake |
| CI/CD present | Yes: `.github/workflows/ci.yaml`, `cve_check.yml`, binary and Docker release workflows |
| Containerization present | Yes: `docker/Dockerfile` multi-stage build with PDFium, frontend, Rust builder, distroless runtime |

## Scorecard

| Category | Score | Grade | Evidence Anchors |
| --- | ---: | --- | --- |
| Architecture | 82 | B | `core/src/context.rs`, `apps/server/src/http_server.rs`, `crates/graphql/src/schema.rs`, `core/src/filesystem/media/process.rs`, `packages/sdk/src/api.ts` |
| Security | 68 | C | `apps/server/src/middleware/auth.rs`, `apps/server/src/config/oidc.rs`, `apps/server/src/routers/api/v2/oidc.rs`, `core/src/lib.rs`, `apps/server/src/config/session/utils.rs` |
| Maintainability | 75 | B | `Cargo.toml`, `package.json`, `packages/graphql/codegen.ts`, `crates/graphql/src/mutation/library.rs`, `core/src/filesystem/scanner/utils.rs` |
| Modularity | 80 | B | Cargo workspace crates, Yarn workspaces, `FileProcessor`, `JobLifecycle`, `APIBase` controllers, `packages/components` |
| Code Quality | 73 | C | SeaORM entities, GraphQL guards/loaders, raw SQL in `query/media.rs`, startup unwraps, debug artifacts in metadata integration |
| Testing | 63 | C | `core/integration-tests/tests/scanner.rs`, `core/src/api_key.rs`, `packages/sdk/src/__tests__/api.test.ts`, `.github/workflows/ci.yaml` |
| Documentation | 78 | B | `README.md`, `docs/content/docs/developer/contributing.mdx`, `docs/content/docs/guides/access-control/permissions.mdx`, `docs/cli.json` |
| Performance Design | 76 | B | Apalis worker configuration, file processors, download queue, DataLoaders, raw aggregate queries |
| Developer Experience | 80 | B | root scripts, Nix flake, rust toolchain pin, CI, Docker, GraphQL codegen, Storybook-capable component package |
| Long-Term Sustainability | 73 | C | multi-platform surface area, large files, dependency count, security debt, low test density |

# Deep Assessment

## Architecture

Grade: B

Score: 82/100

Evidence:

- `Cargo.toml` defines a coherent Rust workspace across `apps/server`, `core`, `crates/*`, integration crates, and Tauri desktop code.
- `package.json` and `lerna.json` define Yarn workspaces for `apps/*`, `docs`, and `packages/*`, with shared browser, SDK, GraphQL, i18n, and component packages.
- `core/src/context.rs` centralizes `Ctx` with configuration, database connection, job storage, watcher state, event channels, and worker state.
- `apps/server/src/http_server.rs` composes Axum routing, session middleware, auth middleware, graceful shutdown, and Apalis background workers.
- `crates/graphql/src/schema.rs`, `crates/graphql/src/data.rs`, and `crates/graphql/src/guard.rs` establish a GraphQL boundary with context injection, DataLoaders, and guard types.
- `core/src/filesystem/media/process.rs` defines the `FileProcessor` and `FileConverter` traits used by ZIP, RAR, EPUB, and PDF implementations.
- `packages/sdk/src/api.ts` and `packages/sdk/src/controllers/*` provide a client-side API layer consumed by web, mobile, and desktop surfaces.

Assessment:

Stump has a clear product architecture: a Rust Axum server, a core domain library for file processing and jobs, SeaORM model crates, an async-graphql API layer, and multiple TypeScript application surfaces. The architecture handles a broad feature set: OPDS v1/v2, Kobo and KoReader integrations, browser UI, Expo mobile, Tauri desktop, background scanning, metadata, uploads, and generated GraphQL clients.

The strongest design choices are the workspace split, the file-processing trait boundary, the job lifecycle abstraction in `core/src/job/mod.rs`, and the generated GraphQL/SDK contract between backend and frontend packages. The main architectural constraints are the high concentration of responsibility in `Ctx`, very large implementation files such as `crates/graphql/src/mutation/library.rs`, `core/src/filesystem/scanner/utils.rs`, and `apps/server/src/routers/opds/v2_0.rs`, and direct database access spread through GraphQL resolvers rather than isolated behind a smaller service layer.

## Security

Grade: C

Score: 68/100

Evidence:

- `apps/server/src/middleware/auth.rs` supports session auth, Bearer auth, API key auth, and OPDS Basic auth, and inserts `AuthContext` into request extensions.
- `core/src/api_key.rs` creates prefixed API keys, validates hashed long tokens, checks expiration, and resolves custom API key permissions against the owning user.
- `apps/server/src/utils/auth.rs` uses bcrypt for password hashing and verification.
- `apps/server/src/routers/api/v2/auth.rs` contains account lockout and session-limit logic for password auth flows.
- `crates/graphql/src/guard.rs` defines `ServerOwnerGuard`, `SelfGuard`, `PermissionGuard`, and optional feature guards, while `crates/models/src/shared/permission_set.rs` models associated permissions.
- `crates/models/src/entity/media.rs`, `library.rs`, `series.rs`, and related model files implement user-scoped `find_for_user` / `apply_for_user` query helpers.
- `apps/server/src/config/oidc.rs` accepts any OIDC nonce in `nonce_verifier`, and `apps/server/src/routers/api/v2/oidc.rs` serializes callback state into the OIDC `state` parameter without a persisted server-side verifier.
- `core/src/lib.rs` stores an encryption key in the database and contains an inline comment identifying that arrangement as insecure.
- `apps/server/src/config/session/utils.rs` configures session cookies with `SameSite::Lax` and `.with_secure(false)`.
- `apps/server/src/middleware/auth.rs` logs `auth_header` and full request headers under debug assertions.
- `crates/graphql/src/query/media.rs` contains raw SQL aggregate queries for disk usage and alphabet counts outside the standard `find_for_user` helper path; the disk usage resolver is guarded for elevated users but its comments identify permission inaccuracy.
- `apps/server/src/routers/api/v2/oidc.rs` can return mobile JWTs in a redirect query string for token-generating OIDC flows.

Assessment:

Security is deliberate and broad, with meaningful authorization primitives, user-scoped model helpers, hashed API keys, account lockout, scoped API key permissions, route-level middleware, and hidden-library/age-restriction filtering in model helpers. OPDS, Kobo, KoReader, browser, mobile, and desktop authentication paths are all represented in implementation code.

The score is limited by OIDC state and nonce handling, session cookie secure settings, database-stored encryption key material, debug logging of auth headers in development builds, and some raw SQL paths that bypass the usual user-scoped helper pattern. The GraphQL `PermissionGuard` checks explicit permissions directly while `permission_set.rs` supports associated permissions, creating an observable inconsistency between guard enforcement and helper-level permission evaluation.

## Maintainability

Grade: B

Score: 75/100

Evidence:

- Workspace dependency management is centralized in `Cargo.toml`, with comments explaining root dependency governance.
- Root `package.json` provides top-level setup, lint, typecheck, test, web, desktop, Expo, docs, and format scripts.
- `rust-toolchain.toml` pins Rust `1.92.0`; `flake.nix` defines reproducible development shells for default and Android workflows.
- `packages/graphql/codegen.ts` generates typed GraphQL artifacts from backend schema and frontend documents.
- `core/src/config/stump_config.rs` and the `stump-config-gen` macro crate provide typed configuration and generated config handling.
- `crates/models/src/entity/*` uses SeaORM models and helper methods for common query patterns.
- Large files and concentrated logic appear in `crates/graphql/src/mutation/library.rs`, `core/src/filesystem/scanner/utils.rs`, `core/src/filesystem/media/format/epub.rs`, and `apps/server/src/routers/opds/v2_0.rs`.
- Static scans found TODO/FIXME items in implementation paths including `crates/graphql/src/query/media.rs`, `packages/graphql/codegen.ts`, `core/src/lib.rs`, `apps/server/src/config/session/utils.rs`, and `core/src/filesystem/media/process.rs`.
- `packages/sdk/src/controllers/server-api.ts` calls `GET /update`, while `apps/server/src/routers/api/v2/mod.rs` exposes `GET /check-for-update`.

Assessment:

Maintainability is supported by a consistent workspace setup, generated API types, typed configuration, explicit CI gates, and a clear package/crate boundary. The project has enough structure to keep a large feature set navigable, and several subsystems use domain-level abstractions rather than ad hoc scripting.

The score is capped by large implementation modules, several active TODO/FIXME markers, duplicated auth/token logic across SDK/mobile/desktop, and at least one observed API contract drift between the SDK and backend routes. Some comments in implementation and codegen files are informal enough to weaken long-term maintainability signals, even when the surrounding code is functional.

## Modularity

Grade: B

Score: 80/100

Evidence:

- `core/src/filesystem/media/process.rs` separates media operations through `FileProcessor` and `FileConverter`.
- `core/src/job/mod.rs` defines `JobLifecycle`, `WorkingState`, and job output behavior for background processing.
- `crates/graphql/src/schema.rs` composes query, mutation, subscription, and DataLoader dependencies.
- `packages/sdk/src/api.ts` exposes typed API controllers for auth, media, library, series, EPUB, OPDS, and server operations.
- `packages/components/src/*` contains reusable UI primitives with theme and Tailwind integration.
- `apps/expo/db/schema.ts`, `apps/expo/lib/downloadQueue/manager.ts`, and `apps/desktop/src-tauri/src/store/secure_store.rs` isolate platform-specific persistence and token storage concerns.
- Direct SeaORM access is common inside GraphQL resolver modules, especially `crates/graphql/src/query/*` and `crates/graphql/src/mutation/*`.

Assessment:

The repository is modular at the workspace and domain-boundary levels. Rust concerns are split across server, core, models, migrations, GraphQL, integrations, CLI, and macros. TypeScript concerns are split across SDK, generated GraphQL types, client hooks, browser UI, Expo mobile, desktop wrapper, components, i18n, and docs.

The main modularity weakness is not the top-level layout, but intra-module size and resolver coupling. GraphQL modules frequently own validation, authorization calls, database queries, mutation side effects, and job dispatch in one place. The scanner and OPDS implementations are also large enough that local reasoning requires careful reading across long files.

## Code Quality

Grade: C

Score: 73/100

Evidence:

- Rust code uses typed error enums, async/await, SeaORM entities, transactions, typed permissions, and domain-specific models.
- TypeScript code uses typed SDK controllers, generated GraphQL documents, React Query-style hooks, Zustand stores, Zod schemas, and component primitives.
- `crates/graphql/src/query/media.rs` contains raw SQL via `Statement::from_sql_and_values` for aggregate and CTE-heavy operations.
- `core/src/context.rs` uses `expect("Failed to connect to database")` in startup context creation.
- `core/src/config/stump_config.rs` uses direct `unwrap()` calls while creating config/cache directories.
- `crates/graphql/src/loader/library.rs` and `crates/graphql/src/filter/series.rs` contain `unimplemented!()` paths.
- `crates/integrations/metadata/src/providers/hardcover.rs` includes a `dbg!(&graphql_query)` call in provider implementation code.
- `packages/sdk/src/api.ts` recreates the Axios instance in the `serviceURL` setter without reattaching the request interceptor that adds auth/custom headers.

Assessment:

The codebase has a solid typed foundation and many local patterns are coherent: SeaORM entity helpers, GraphQL guards, generated clients, file processor traits, and UI schema validation. The implementation is generally more mature than a prototype because it encodes real authorization, background job, media parsing, and multi-platform concerns.

The code-quality score is limited by raw SQL complexity, large files, implementation TODOs, remaining panic-style paths in startup/config code, an implementation debug macro in the Hardcover metadata provider, and SDK lifecycle behavior that can drop interceptors when the service URL changes. These are not isolated style issues; they appear in runtime-relevant implementation code.

## Testing

Grade: C

Score: 63/100

Evidence:

- `core/integration-tests/tests/scanner.rs` tests series-based and collection-based library scans against fixture libraries.
- `core/integration-tests/tests/epub.rs`, `rar.rs`, and `zip.rs` exercise file-format processing against real fixture archives and documents.
- `core/src/api_key.rs` includes unit tests for API key validation, wrong-user permission resolution, inherited permissions, and custom permissions.
- `apps/server/src/middleware/auth.rs`, `apps/server/src/middleware/host.rs`, and `apps/server/src/routers/kobo/sync.rs` contain unit tests for auth context behavior, proxy-header handling, and Kobo sync flows.
- `packages/sdk/src/__tests__/api.test.ts` tests URL formatting, token auth, and interceptor-based authorization behavior.
- `packages/browser/src/scenes/settings/app/apiKeys/__tests__/CreateOrUpdateAPIKeyForm.test.tsx` and similar browser tests focus heavily on schemas and selected components.
- `apps/expo/lib/__tests__/opdsUtils.test.ts` covers OPDS search URL templating and encoding.
- `.github/workflows/ci.yaml` runs `cargo fmt`, `cargo clippy -D warnings`, GraphQL schema checks, `cargo test`, coverage, frontend linting, frontend tests, and docs builds depending on changed paths.
- Source test density is low: 39 source test files for 1,963 non-test implementation files.
- `apps/desktop/src-tauri/src/store/secure_store.rs` has ignored native keyring tests due environment constraints.

Assessment:

The strongest testing evidence is in core media processing, scanning, OPDS/Kobo domain code, permissions helpers, and selected server middleware. The fixture-backed archive tests give meaningful confidence in the file-processing subsystem.

The test surface is thin relative to repository size. Frontend and mobile coverage is mostly schema, utility, and selected component behavior. There is limited evidence of end-to-end browser/mobile/desktop flows, broad GraphQL resolver integration tests, OIDC callback tests, or SDK/backend route-contract tests. CI is strong, but the source test ratio remains low for a codebase with this many runtime surfaces.

## Documentation

Grade: B

Score: 78/100

Evidence:

- `README.md` describes project purpose, features, beta status, installation entry points, repository structure, and licensing.
- `docs/content/docs/developer/contributing.mdx` documents local setup, required tools, workspace commands, GraphQL codegen, linting, formatting, component library usage, and developer resources.
- `docs/content/docs/guides/access-control/permissions.mdx` documents permission names and their intended user-facing meaning.
- `docs/content/docs/guides/access-control/oidc.mdx`, `docs/content/docs/guides/features/api-keys.mdx`, and installation docs exist in the docs tree.
- `docs/cli.json` and CLI docs indicate generated or maintained command documentation.
- Some implementation docs and comments are helpful, such as `FileProcessor`, `JobLifecycle`, OPDS model docs, and config comments.
- Some implementation comments are informal or mark unresolved design debt, such as `packages/graphql/codegen.ts`, `core/src/lib.rs`, and several TODO/FIXME blocks.

Assessment:

Documentation is above average for an application of this scope. The docs app contains user, admin, integration, mobile, desktop, access-control, and developer material. The README clearly identifies beta status and routes readers to maintained docs instead of duplicating all setup details.

The documentation score is limited by the distance between documented intent and implementation edge cases in OIDC/security and by informal implementation comments in some development-facing files. The public docs are broad, but the deepest operational behavior still requires reading source.

## Performance Design

Grade: B

Score: 76/100

Evidence:

- `core/src/filesystem/media/process.rs` hashes selected file samples rather than entire files for Stump hashes.
- `core/src/filesystem/media/format/pdf.rs`, `zip.rs`, `rar.rs`, and `epub.rs` implement format-specific page counting, page reads, metadata extraction, and content-type analysis.
- `core/src/filesystem/scanner/library_scan_job.rs` and `core/src/filesystem/scanner/utils.rs` batch scanner work and handle large library processing paths.
- `apps/server/src/http_server.rs` runs Apalis worker concurrency at `1`, with comments tying the setting to previous SQLite multi-writer issues.
- `crates/graphql/src/schema.rs` registers DataLoaders to reduce repeated fetches.
- `apps/expo/lib/downloadQueue/manager.ts` limits concurrent downloads with `MAX_CONCURRENT_DOWNLOADS = 2` and tracks resumable downloads.
- `crates/graphql/src/query/media.rs` uses raw SQL aggregate and CTE queries for disk usage, alphabet counts, and on-deck data.
- `crates/graphql/src/query/media.rs` contains comments noting broken cursor ordering and unsupported cursor pagination for `keepReading`.
- `docker/Dockerfile` uses multi-stage builds, cache mounts, checksum validation for PDFium binaries, and a distroless runtime image.

Assessment:

The performance design is intentional: background jobs, chunked scanner work, selected hashing, DataLoaders, mobile download concurrency limits, and Docker build caching all show awareness of scale and runtime cost. File processing is specialized per format instead of forced through one generic path.

The constraints are visible in database-heavy areas. Worker concurrency is serialized for SQLite safety, raw SQL aggregate paths can be expensive, and some pagination behaviors are explicitly incomplete. The design favors correctness and operational predictability over high parallel throughput.

## Developer Experience

Grade: B

Score: 80/100

Evidence:

- Root `package.json` exposes `setup`, `lint`, `check-types`, `test`, `dev:web`, `dev:desktop`, `dev:expo`, `format`, and package-scoped commands.
- `Cargo.toml` centralizes Rust workspace dependencies and membership.
- `rust-toolchain.toml` pins the Rust toolchain, while `flake.nix` provides default and Android development shells.
- `.github/workflows/ci.yaml` gates Rust formatting, clippy, GraphQL schema generation, tests, coverage, frontend linting, frontend tests, and docs builds.
- `.github/workflows/cve_check.yml`, release binary workflows, and Docker release workflows indicate release and security automation.
- `docker/Dockerfile` builds frontend and server artifacts into a deployable runtime image.
- `packages/graphql/codegen.ts` and root setup scripts support generated API types.
- `packages/components` is documented as Storybook-oriented in `docs/content/docs/developer/contributing.mdx`.
- The environment footprint is large: Rust, Node/Yarn 1, Lerna, Expo, Tauri, Android tooling, PDFium, SQLite, Nix, and self-hosted CI runners.

Assessment:

Developer experience is strong for a large self-hosted application. The repo provides scripts, CI, codegen, Docker, Nix shells, toolchain pins, docs, and release automation. A new contributor has clear entry points for web, desktop, mobile, server, docs, and GraphQL codegen.

The score is limited by setup complexity and toolchain breadth. Multiple platforms, native dependencies, generated artifacts, self-hosted CI for Rust jobs, and a large direct dependency set raise the cost of local reproduction and dependency maintenance.

## Long-Term Sustainability

Grade: C

Score: 73/100

Evidence:

- The repository supports web, mobile, desktop, server, OPDS, Kobo, KoReader, docs, CLI, metadata integrations, migrations, and generated clients.
- `README.md` explicitly marks the project beta and notes active development before a stable `1.0`.
- `Cargo.toml`, `package.json`, CI workflows, Docker, Nix, and docs show sustained maintenance infrastructure.
- Large implementation files and generated clients increase review and change cost.
- The direct dependency count is high at 413 unique direct dependencies.
- Security debt is visible in OIDC nonce/state handling, session cookie secure settings, and database-stored encryption key material.
- Test density is low relative to implementation size, with limited mobile/desktop and end-to-end coverage evidence.

Assessment:

The project has the infrastructure and architecture of a serious long-running application: workspaces, typed contracts, CI, release automation, Docker, docs, and multi-surface product support. It is not a small or throwaway codebase.

Long-term sustainability is constrained by breadth. The project maintains multiple clients, native mobile/desktop concerns, integrations, file parsers, GraphQL, REST/OPDS, background jobs, and deployment machinery. The codebase can sustain continued development, but its current size, security debt, low test density, and large dependency surface create meaningful maintenance load.

# Comparative Snapshot

No external repository baseline was used.

Best attribute: Architecture. The workspace split, core/server/model/GraphQL separation, file-processing trait boundary, job lifecycle, and shared SDK give the project a coherent shape.

Weakest attribute: Testing. Core file-processing tests are meaningful, but source test density is low and coverage evidence is thinner for frontend, mobile, desktop, OIDC, and end-to-end API-contract behavior.

Most production-like attribute: Developer experience and release infrastructure. CI, Docker, Nix shells, codegen, docs, toolchain pins, and release workflows are present.

Highest-risk attribute: Security. Authorization is broad, but OIDC callback verification, session cookie secure settings, debug auth-header logging, and database-stored encryption key material reduce confidence.

# Final Verdict

Stump is a mature beta-stage self-hosted media server with a strong architecture and substantial implementation depth. The codebase covers Rust backend services, GraphQL, OPDS, Kobo and KoReader integrations, browser UI, Expo mobile, Tauri desktop, docs, Docker deployment, code generation, background jobs, and file-format processing. Its best evidence is in implementation code: model-level user scoping, GraphQL guards, API key controls, media processors, scanner jobs, SDK controllers, platform-specific token storage, and release infrastructure.

The repository is not just scaffolded; it contains real domain behavior and operational tooling. Its architecture and developer experience scores are high because the workspace boundaries and build/release systems are coherent. Documentation is broad, and core tests around scanning, archive processing, auth helpers, OPDS/Kobo, and SDK behavior provide useful confidence in several important subsystems.

The main limits are security edge cases, sparse test density relative to repository size, large implementation files, raw SQL paths, and API-contract drift between the SDK and backend update route. The final score reflects a project that is production-usable for many self-hosted contexts while still carrying beta-stage risk in authentication flows, regression coverage, and long-term maintenance load.

# Limitations

The assessment was static. I did not run the application, execute the test suite, build containers, or validate runtime behavior.

`cargo` was unavailable in the assessment shell, so Rust dependency statistics were derived from Cargo manifest parsing rather than `cargo metadata`.
