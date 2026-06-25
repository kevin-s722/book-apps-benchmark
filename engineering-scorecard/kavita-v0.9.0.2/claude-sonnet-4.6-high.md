# Executive Summary

## Repository: kavita
## Model: Claude Sonnet 4.6 (high)

## Overall Score

Score: 82/100
Grade: B+
Confidence: 91/100

Repository Maturity: Community Project

---

## Repository Statistics

| Metric | Value |
|----------|----------|
| Repository Name | Kavita |
| Total Files | 3,531 |
| Source Files | 1,533 C# + 793 TypeScript + 291 HTML + 335 SCSS |
| Test Files | 115 C# test files |
| Languages | C# (.NET 10), TypeScript/Angular 21, SCSS, SQL |
| Dependency Count | ~45 NuGet (Services), ~68 npm (frontend) |
| Largest Module | Kavita.Database (481 files, 421 migrations) |
| Build System | MSBuild (.NET SDK), Angular CLI (npm) |
| CI/CD Present | Yes (GitHub Actions: 8 workflows) |
| Containerization Present | Yes (Dockerfile, multi-arch: linux/amd64, arm/v7, arm64) |
| Test-to-Source Ratio | ~0.12 (115 test files / 938 non-test non-migration C# files) |

---

## Scorecard

| Category | Grade | Score | Summary |
|----------|----------|----------|----------|
| Architecture | B+ | 83 | Clean layered architecture with solid separation of concerns; some cross-cutting coupling in manual migrations |
| Security | A- | 88 | Strong multi-auth scheme, rate limiting, access attribute decorators, path traversal protection; weak password requirements and one `.Result` blocking call in StatsService |
| Maintainability | B+ | 82 | Well-structured service layer, Builder pattern for test setup, significant TODO accumulation; some god-service tendencies |
| Modularity | B+ | 81 | Clean project decomposition into API/Database/Models/Services/Server layers; interface-backed service layer; some circular coupling via the Kavita.API shim project |
| Code Quality | B | 78 | Strong async/await discipline, nullable enabled project-wide, C# 10+ patterns used; ExternalMetadataService at 2168 lines and AccountController at 1351 lines indicate incomplete decomposition |
| Testing | B | 77 | Substantive xUnit test suite (28k LOC), SQLite in-memory integration pattern, BenchmarkDotNet harness; zero frontend tests, ProcessSeriesTests entirely stubbed out, MetadataServiceTests at only 38 lines |
| Documentation | B | 76 | XML doc comments on all controllers, OpenAPI spec auto-generated and committed (34k line openapi.json), CONTRIBUTING.md with detailed setup; copilot-instructions.md present but SECURITY.md is minimal |
| Performance Design | B+ | 83 | EasyCaching/HybridCache multi-layer caching, response compression, client-side HTTP cache profiles, Hangfire for background jobs, cancellation token propagation throughout (1470 usages) |
| Developer Experience | B+ | 82 | 8 CI/CD workflows including canary/stable/develop, BenchmarkDotNet project, editorconfig, SonarCloud configured, full OpenAPI/Swagger in dev; manual migration sequence in Startup.cs is difficult to follow |
| Long-Term Sustainability | B | 79 | Active development to .NET 10, multi-arch Docker, GPL-3.0 license, SonarAnalyzer.CSharp included; frontend has zero tests, some deprecated DbSets marked with [Obsolete], growing manual migration chain |

---

# Deep Assessment

## Architecture

### Grade
B+

### Score
83

### Evidence
The codebase follows a clean layered monolith with clear project boundaries: `Kavita.API` contains interface definitions and repository contracts (`ISeriesRepository`, `IUnitOfWork`, all 30+ `I*Repository` interfaces), `Kavita.Database` contains Entity Framework implementations (`DataContext`, `UnitOfWork`, `SeriesRepository`), `Kavita.Models` holds all entities and DTOs, `Kavita.Services` contains business logic, and `Kavita.Server` handles HTTP concerns (controllers, middleware, extensions).

The Unit of Work pattern is implemented in `Kavita.Database/UnitOfWork.cs`, instantiating all 30+ repositories and exposing them via the `IUnitOfWork` interface. Repository implementations (`SeriesRepository.cs` at 1847 lines) are EF-backed and project directly to DTOs using AutoMapper's `ProjectTo<>`. The `Kavita.API` shim project acts as an abstraction boundary - it has no implementation, only interfaces - but all projects reference it, creating a somewhat unusual dependency graph where Models depends on nothing, API depends on Models, Database/Services/Server all depend on API.

Controllers are thin - `ReaderController.cs` at 1090 lines still delegates business logic to services. The `BaseApiController` contains cross-cutting utilities: `CachedFile()`, `IsPathWithinDirectory()`, `UploadToTempAsync()` - a sensible centralization point.

The `Startup.cs` `ExecuteMigrations` method contains a 100-line sequential list of manual migration calls organized by version ranges (v0.7.9 through v0.9.1), revealing a substantial structural debt in migration management that sits outside of EF's migration pipeline.

SignalR integration is clean, with an `IEventHub` interface in `Kavita.API` and the `EventHub` service implementation using `IPresenceTracker` for user tracking and proper library access checks before broadcasting.

### Assessment
Kavita's architecture is a well-structured layered monolith appropriate for its scale and community context. The separation of interface definitions in `Kavita.API` from implementations in `Kavita.Services` and `Kavita.Database` enables testability and clean dependency inversion. The `Kavita.API` shim creating a shared contract layer is a pragmatic choice that avoids circular dependencies. The primary architectural concern is the growing manual migration chain in `Startup.cs` - 40+ versioned migration calls that run at startup - which will become increasingly fragile as the codebase matures.

---

## Security

### Grade
A-

### Score
88

### Evidence
**Authentication:** A sophisticated hybrid authentication policy in `IdentityServiceExtensions.cs` dynamically selects between three authentication schemes - API Key (`AuthKeyAuthenticationHandler`), OIDC cookies, and JWT Bearer - based on request characteristics. The `AuthKeyAuthenticationHandler` uses `HybridCache` with 15-minute TTL for key resolution, preventing database hits on every request.

**Authorization:** Entity-level access control is implemented via custom filter attributes in `EntityAccessAttribute.cs` - `SeriesAccessAttribute`, `ChapterAccessAttribute`, `VolumeAccessAttribute`, `LibraryAccessAttribute`, `ReadingListAccessAttribute`, `PersonAccessAttribute`. These are used as `[SeriesAccess]`, `[ChapterAccess]` decorators on controller actions, enforcing user-scoped access checks through repository calls rather than relying on application-level filtering.

**Rate Limiting:** `AuthenticationRateLimiterPolicy.cs` enforces fixed-window rate limiting (1 request per 10 minutes per host) on authentication endpoints using ASP.NET Core's built-in `IRateLimiterPolicy`. Applied in `Startup.cs` via `AddRateLimiter`.

**Path Traversal Protection:** `BaseApiController.IsPathWithinDirectory()` canonicalizes paths using `Path.GetFullPath()` and validates the resolved path stays within the base directory. Used consistently across `ThemeController`, `UploadController`, `ImageController`, `FontController`, and `CBLController` for all file upload endpoints.

**Password Policy Weakness:** `IdentityServiceExtensions.cs` explicitly disables all password complexity requirements (`RequireNonAlphanumeric = false`, `RequireDigit = false`, `RequireLowercase = false`, `RequireUppercase = false`) with only a 6-character minimum. Account lockout is configured (5 attempts, 10-minute lock).

**Security Logging:** `SecurityEventMiddleware.cs` logs unauthenticated access attempts to a dedicated `security.log` file with IP, method, path, and user agent. Hardcoded log message `"Unauthorized"` avoids localized strings in security logs.

**Credentials in Exception Handling:** `ExceptionMiddleware.cs` includes `ex.StackTrace` in the 500 response body, which exposes internal implementation details to clients.

**Async Anti-Pattern:** `StatsService.cs` uses `.Result` on `GetRolesAsync()`, a potential deadlock risk in ASP.NET Core's async context.

**Code Injection:** All log fields use `.Sanitize()` from `StringExtensions.cs` (removes newlines, non-printable ASCII) before embedding in log messages - consistently applied.

### Assessment
Kavita demonstrates above-average security implementation for a community media server. The entity-level access attribute system is architecturally sound and not easily bypassed. The hybrid auth scheme with caching is well-designed. The primary concerns are: (1) near-zero password complexity requirements creating weak account security by default, (2) stack traces exposed in 500 responses, and (3) a single `.Result` blocking call in `StatsService`. CodeQL analysis is configured in CI on both C# and TypeScript, adding automated security scanning.

---

## Maintainability

### Grade
B+

### Score
82

### Evidence
**Service Sizes:** Several services exceed reasonable single-responsibility bounds. `ExternalMetadataService.cs` at 2168 lines handles external metadata fetching, series matching, cover downloads, smart collection syncing, and Kavita+ API interaction. `ReaderService.cs` at 1051 lines, `StatisticService.cs` at 1886 lines, `SeriesService.cs` at 1022 lines. `ProcessSeries.cs` at 1039 lines is the core library scan processor. `BookService.cs` at 1955 lines handles EPUB parsing, PDF processing, CSS manipulation, and cover extraction.

**Controller Sizes:** `AccountController.cs` at 1351 lines and `ReaderController.cs` at 1090 lines are on the large side but remain delegate-thin - the bulk is endpoint definitions with proper XML doc comments.

**Builder Pattern:** `Kavita.Models/Builders/` provides `SeriesBuilder`, `VolumeBuilder`, `ChapterBuilder`, `LibraryBuilder`, and `AppUserBuilder` for constructing entity graphs in tests. These are used pervasively in test infrastructure via `AbstractDbTest.cs`.

**AutoMapper:** `AutoMapperProfiles.cs` at 420 lines centralizes all entity-to-DTO mappings with explicit property configurations, avoiding magic member mapping.

**Technical Debt Markers:** 60 `TODO`/`FIXME` comments across 39 files, including known issues: "TODO: Why do I have clear temp directory then immediately do it again?" in `CleanupService.cs`, "TODO: Optimize this code" in `DeviceTrackingService.cs`, "TODO: Implement" in `ProcessSeriesTests.cs`.

**Nullable Reference Types:** Enabled across all 12 C# project files, with `#nullable enable/disable` directives used in specific contexts where null contracts are relaxed.

**Cancellation Tokens:** 1470 usages of `CancellationToken` across the codebase indicates consistent async cancellation propagation, though the 2-parameter `ct = default` convention is not uniformly applied.

### Assessment
Kavita's maintainability is above average for a community project of this complexity. The interface-backed service layer, Builder pattern for testing, and consistent DI registration in `ApplicationServiceExtensions.cs` all support long-term maintainability. The primary drag is service class size - `BookService` at 1955 lines and `ExternalMetadataService` at 2168 lines handle too many concerns and resist refactoring. The TODO accumulation signals areas of known debt that have not been addressed.

---

## Modularity

### Grade
B+

### Score
81

### Evidence
**Project Decomposition:** 12 C# projects with clear domain boundaries: `Kavita.Common` (utilities, exceptions, configuration), `Kavita.Models` (entities, DTOs, parsers, builders), `Kavita.API` (interfaces only - repository and service contracts), `Kavita.Database` (EF implementations, migrations, repositories), `Kavita.Services` (business logic services), `Kavita.Server` (ASP.NET Core controllers, middleware, startup).

**Dependency Direction:** `Kavita.Common` has zero project dependencies. `Kavita.Models` depends only on Common. `Kavita.API` depends on Models. `Kavita.Database` and `Kavita.Services` both depend on API (for interfaces). `Kavita.Server` depends on all. This is a clean dependency hierarchy.

**Subdirectory Organization Within Services:** `Kavita.Services/Scanner/` (8 files), `Kavita.Services/Plus/` (8 files + `ScrobbleService/` with 7 files), `Kavita.Services/Reading/` (5 files), `Kavita.Services/ReadingLists/` (5 files), `Kavita.Services/HostedServices/` (2 files). Each grouping has a clear cohesive domain.

**Repository Pattern:** 30+ interface-backed repositories in `Kavita.API/Repositories/` with implementations in `Kavita.Database/Repositories/`. The `UnitOfWork` coordinates them as a single unit, exposed through `IUnitOfWork`.

**Feature Coupling Risk:** `SeriesRepository.cs` at 1847 lines handles 50+ async query methods covering general series queries, filtering/sorting (via `CreateFilteredSearchQueryableV2`), scrobbling DTO projection, CBL import matching, and "want to read" operations. This is a broad surface area for a single repository.

**Database Filter Decomposition:** The `Kavita.Database/Extensions/Filters/` directory separates filtering logic into `SeriesFilter.cs`, `AnnotationFilter.cs`, `PersonFilter.cs`, `ReadingListFilter.cs`, `ActivityFilter.cs` - each implementing filter-specific EF query composition. This is a clean, modular approach to complex query building.

### Assessment
Kavita achieves good modularity at the project boundary level, with the interface-only `Kavita.API` shim being a particularly effective technique for dependency inversion without circular references. Within projects, subdirectory organization is consistent and domain-driven. The primary modularity concern is the fat repository pattern in `SeriesRepository.cs` (1847 lines, 50+ methods) and the aggregate `ExternalMetadataService.cs` (2168 lines), both of which take on multiple distinct responsibilities.

---

## Code Quality

### Grade
B

### Score
78

### Evidence
**Language Version:** All C# projects target `net10.0` with `LangVersion=latestmajor` in `Kavita.Server.csproj`. Modern C# features are actively used: primary constructors (`public class SeriesService(IUnitOfWork unitOfWork, ...) : ISeriesService`), collection expressions (`[LibraryType.Comic, LibraryType.Image]`), pattern matching in switch expressions, `partial` regex source generators (`[GeneratedRegex(...)]`), `required` record properties.

**Async Discipline:** 2388 async method declarations, `CancellationToken` propagated at 1470 points. One confirmed `.Result` blocking call in `StatsService.cs` (on `GetRolesAsync`). `GetAwaiter().GetResult()` used in `Startup.cs` migration runner but within a non-async context (`Task.Run(...).GetAwaiter().GetResult()`).

**Regex Safety:** All regex instances use compiled mode with explicit `TimeSpan.FromMilliseconds(500)` timeout, preventing ReDoS via catastrophic backtracking. Source generators used in `StringExtensions.cs` and `StringHelper.cs`.

**Sanitization:** The `Sanitize()` extension method in `StringExtensions.cs` strips newlines and non-printable ASCII, used for log injection prevention in dynamic log values.

**Dead Code:** `[Obsolete]` decorators on `CollectionTag` DbSet and `SeriesBlacklist` DbSet in `DataContext.cs` indicate migration artifacts retained for compatibility.

**ProcessSeriesTests.cs:** 57 lines, entirely placeholder comments with no actual test implementations despite being in a test project. The core library scanning logic in `ProcessSeries.cs` (1039 lines) has no test coverage from this file.

**Style Enforcement:** `.editorconfig` enforces indent style, charset, and final newlines. `SonarAnalyzer.CSharp` is included as a build dependency in `Kavita.Services.csproj`, running static analysis during builds.

**Comment Quality:** XML doc comments exist on all controllers and most public service methods. `TODO` comments are informational ("TODO: Cache", "TODO: Localize", "TODO: Optimize") rather than markers for broken functionality.

### Assessment
Code quality is generally strong with good use of modern C# language features and consistent async patterns. The primary quality gaps are in test completeness (especially the `ProcessSeriesTests.cs` stub) and a few large service classes that should be decomposed. The regex timeout pattern across all regexes is a notable positive that prevents a common performance vulnerability. The inclusion of SonarAnalyzer in the build toolchain reflects quality investment.

---

## Testing

### Grade
B

### Score
77

### Evidence
**Test Infrastructure:** `AbstractDbTest.cs` in `Kavita.Database.Tests` provides an in-memory SQLite test harness with full EF schema creation, database seeding (roles, settings, themes, fonts, side nav streams), and proper async dispose. Tests derive from this for integration-level service testing with real ORM behavior.

**Test Volume:** 115 C# test files, 28,011 LOC in `Kavita.Services.Tests` alone. Major test files: `ReaderServiceTests.cs` (2877 lines), `ExternalMetadataServiceTests.cs` (3381 lines), `SeriesServiceTests.cs` (1899 lines), `ReadingListServiceTests.cs` (1348 lines), `ReadingProfileServiceTest.cs` (2028 lines), `ScrobblingServiceTests.cs` (1191 lines), `ScannerServiceTests.cs` (1130 lines).

**Testing Framework:** xUnit with `[Theory]`/`[InlineData]` for parameterized tests, NSubstitute for mocking (`Substitute.For<ILogger<...>>()`), `coverlet.collector` for coverage. MockFileSystem (`System.IO.Abstractions.TestingHelpers`) used for filesystem-dependent tests.

**Database Repository Tests:** `Kavita.Database.Tests/Repositories/` contains `SeriesRepositoryTests.cs`, `PersonRepositoryTests.cs`, `GenreRepositoryTests.cs`, `TagRepositoryTests.cs` - testing repository queries against the in-memory SQLite database.

**Benchmark Project:** `Kavita.Benchmark/` with `BenchmarkDotNet` covers `ArchiveServiceBenchmark.cs`, `ParserBenchmarks.cs`, `CleanTitleBenchmark.cs`, `KoreaderHashBenchmark.cs` - indicating attention to performance regression tracking.

**Frontend Tests:** Zero `.spec.ts` files in `UI/Web/src/`. The Angular frontend (793 TypeScript files, 291 HTML templates) has no automated test coverage.

**Test Gaps:** `ProcessSeriesTests.cs` (57 lines) consists entirely of `// TODO: Implement` placeholder comments. `MetadataServiceTests.cs` is 38 lines (not implemented). Integration tests in `Kavita.Integration.Tests` contain only 3 files covering `LicenseServiceTests.cs` and `KavitaPlusApiServiceTests.cs`.

**CI Integration:** Build-and-test workflow runs `dotnet test --filter "Category!=Integration"` on every PR, excluding integration tests (which require live Kavita+ API credentials).

### Assessment
Testing quality is respectable for a community open-source project, with a substantive xUnit suite backed by a reusable SQLite integration harness. The Builder pattern for entity construction makes test setup readable and expressive. Key gaps that lower the score: zero frontend testing, core scanner logic (`ProcessSeries.cs`) not covered by the stub test class, and the integration test suite being minimal (3 files). The BenchmarkDotNet harness shows performance awareness beyond typical community projects.

---

## Documentation

### Grade
B

### Score
76

### Evidence
**API Documentation:** All 499 controller endpoints carry XML `<summary>` doc comments. `Kavita.Server.csproj` generates XML documentation (`<GenerateDocumentationFile>True</GenerateDocumentationFile>`). The 34,025-line `openapi.json` is committed to the repo and auto-generated via `Swashbuckle.AspNetCore.Cli` in CI workflows.

**Swagger UI:** Available in development mode via `app.UseSwagger()` / `app.UseSwaggerUI()`. The OpenAPI spec includes API key security scheme documentation with instructions for obtaining auth keys from user settings.

**Contributing Guide:** `CONTRIBUTING.md` provides complete developer setup (tools, fork/clone, frontend/npm setup, backend IDE setup, database migration commands, deployment), PR guidelines (feature branch naming convention, PR scope), and API reference guidance.

**Copilot Instructions:** `.github/copilot-instructions.md` present, providing AI coding assistant context.

**Security Policy:** `SECURITY.md` is minimal (3 lines) - only stating which versions receive security updates and directing reporters to Discord or GitHub Security Disclosure. No vulnerability disclosure timeline, no severity classification.

**Code Comments:** Comments explain non-obvious behavior rather than restating code. Examples: `// This allows for mocking` in `DataContext.OnEntityTracked`, `// Non-greedy matching of a string where parenthesis are balanced` in `Parser.cs`, remarks on thread-safety invariants in `OidcService.cs`.

**I18N:** `Kavita.Server/I18N/` directory with localization files used by `LocalizationService` for user-facing error messages. Error messages are localization keys (`"permission-denied"`, `"disabled-account"`) rather than hardcoded strings.

**Memory/Architecture Documentation:** No architectural decision records (ADRs) or internal wiki. The CONTRIBUTING guide does not explain the layered architecture or the Kavita.API shim pattern.

### Assessment
Documentation quality is above average for a community project - the XML doc coverage on controllers and auto-generated OpenAPI spec represent serious investment. The CONTRIBUTING.md is genuinely useful. The primary gaps are: no architectural documentation explaining the project structure and layer responsibilities, a minimal SECURITY.md, and no ADRs for significant design decisions (manual migration chain, the Kavita.API shim pattern, the hybrid auth scheme).

---

## Performance Design

### Grade
B+

### Score
83

### Evidence
**Multi-Layer Caching:** `ApplicationServiceExtensions.cs` registers 9 EasyCaching in-memory caches for distinct profiles (Favicon, Publisher, Library, RevokedJwt, LocaleOptions, KavitaPlusExternalSeries, License, LicenseInfo, KavitaPlusMatchSeries, ProviderHealth). `HybridCache` (Microsoft.Extensions.Caching.Hybrid) is used in `AuthKeyAuthenticationHandler.cs` with 15-minute TTL for auth key resolution. MemoryCache with configurable size limit (75 MB default) and LRU compaction is registered in `ApplicationServiceExtensions.cs`.

**HTTP Response Caching:** `BaseApiController.CachedFile()` implements ETag-based conditional requests with `stale-while-revalidate` cache-control. Response cache profiles defined in `Startup.cs`: 1-minute, 5-minute, 10-minute, 1-hour, 6-hour (statistics), 30-day, 4-hour (license). Response compression is enabled via `UseResponseCompression()`.

**Background Jobs:** Hangfire with in-memory storage handles all long-running tasks (library scanning, metadata updates, cleanup, scrobbling, statistics). `TaskScheduler.cs` defines 25+ named recurring/queued job identifiers. Polly retry policies (`AsyncRetryPolicy`) with exponential backoff used in `TaskScheduler`.

**Database Query Design:** `SeriesRepository.cs` uses `AsNoTracking()` on read-only queries, `ProjectTo<>` with AutoMapper for direct DTO projection (avoiding loading full entity graphs), and parameterized queries throughout. The filter system in `Kavita.Database/Extensions/Filters/` builds composable EF LINQ trees.

**Image Processing:** NetVips for high-performance image operations. `ImageService.cs` configures `Cache.MaxFiles = 0` during image dimension calculation to prevent NetVips caching. `RecyclableMemoryStreamManager` (Microsoft.IO.RecyclableMemoryStream) used in `BookService.cs` to reduce large byte array allocations.

**Cancellation:** `CancellationToken` propagated at 1470 points with `HttpContext.RequestAborted` token used in controllers, enabling proper request cancellation for long-running database queries.

**Performance Anti-Pattern:** `ConcurrentDictionary<int, SemaphoreSlim>` in `CacheService.cs` for per-chapter extraction locks is a potential memory leak if chapter IDs accumulate indefinitely without eviction.

### Assessment
Performance design is strong, with thoughtful multi-layer caching, ETag-based HTTP caching, projection-based DB queries, and comprehensive cancellation support. The Hangfire background job system is appropriate for the scale and provides job queuing, deduplication (via `HasAlreadyEnqueuedTask`), and automatic retry. The `RecyclableMemoryStreamManager` usage in the EPUB processing path shows awareness of allocation pressure at scale.

---

## Developer Experience

### Grade
B+

### Score
82

### Evidence
**CI/CD Pipeline:** 8 GitHub Actions workflows covering: `build-and-test.yml` (PR gate - dotnet restore + test), `codeql.yml` (security scanning on develop, scheduled weekly), `pr-check.yml` (PR body validation), `canary-workflow.yml` (canary Docker builds on push to canary), `develop-workflow.yml` (develop Docker builds), `release-workflow.yml` (stable + nightly Docker on release PR merge), `build-ui.yml`, `openapi-gen.yml` (OpenAPI spec generation and commit).

**Local Setup:** CONTRIBUTING.md documents clear 2-step frontend setup (npm install, npm run start) and 2-step backend setup (build + debug in IDE). `copy_runtime.sh` and `build.sh` scripts for local builds. `monorepo-build.sh` for cross-platform release builds.

**Configuration:** `global.json` pins .NET SDK to 10.0 with `allowPrerelease=false` for reproducible builds. `.editorconfig` enforces code style across all file types.

**Development Tooling:** `Kavita.Benchmark/` project for performance profiling. Swagger UI in development mode for API exploration. `appsettings.Development.json` for dev-specific configuration.

**OpenAPI Integration:** The `openapi-gen.yml` workflow auto-generates and commits `openapi.json` to the repository on develop pushes, keeping the API contract documentation current.

**Manual Migration Chain:** `Startup.cs` `ExecuteMigrations` method contains 40+ sequential migration calls across 11 version ranges, executed at startup. This means adding a migration requires editing a 600-line `Startup.cs` file and understanding the migration history - a friction point for new contributors.

**Test Isolation:** `AbstractDbTest.cs` provides self-contained SQLite databases per test run with full seeding, ensuring tests don't interfere with each other or require external database setup.

**Multi-arch Docker:** Release workflow builds `linux/amd64`, `linux/arm/v7`, `linux/arm64` images in a single `docker/build-push-action` step using QEMU.

### Assessment
Developer experience is strong with comprehensive CI/CD, a well-documented contributing guide, and clean local dev setup. The BenchmarkDotNet project and Swagger UI accessibility in dev mode are notable DX investments. The friction point is the manual migration invocation chain in `Startup.cs` - a growing list that new contributors must navigate to understand migration execution order. The zero-test frontend is also a DX gap when modifying UI components.

---

## Long-Term Sustainability

### Grade
B

### Score
79

### Evidence
**Technology Stack Currency:** Targeting `.NET 10.0` (current LTS), Angular 21 (current), Hangfire 1.8.x, AutoMapper 12, SonarAnalyzer.CSharp included. `TieredPGO=true` and `TieredCompilation=true` in `Kavita.Server.csproj` enable profile-guided optimization.

**Database Evolution:** 421 migration files (including designer files) represent 4+ years of schema evolution. Manual migration chain in `Startup.cs` (40+ calls) is a sustainability concern - each version adds 2-5 more entries. Pre-migration DB backup logic in `Program.cs` provides safety nets.

**License:** GPL-3.0 (open source copyleft), appropriate for a community self-hosting application.

**[Obsolete] Decorators:** `CollectionTag` DbSet and `SeriesBlacklist` DbSet marked `[Obsolete]` in `DataContext.cs`, indicating legacy data structures retained for migration compatibility. The `[Obsolete]` decorator instructs developers not to use these but they remain in the codebase.

**Test Coverage Debt:** Zero frontend tests and the ProcessSeries stub tests represent coverage debt that could mask regressions in core library scanning logic.

**SonarCloud Integration:** `.sonarcloud.properties` present but referencing old project paths (`API.Tests` instead of current test project names). May not be actively scanning.

**Multi-Provider Scrobbling:** `AniListScrobbleProviderService.cs`, `MyAnimeListScrobbleProviderService.cs`, `MangabakaScrobbleProviderService.cs`, `HardcoverScrobbleProviderService.cs` registered via keyed DI (`AddKeyedScoped<IScrobbleProviderService, ...>`), following an extensible plugin-like pattern for adding new providers.

**KavitaPlus Coupling:** Multiple services depend on `ILicenseService` and `IKavitaPlusApiService` for premium features. License checks are embedded throughout the codebase. The commercial services are well-isolated behind interfaces.

**Community Signals:** Active commit history (last commits in 2025-2026 range), PR template, issue templates, FUNDING.yml (GitHub Sponsors). The repository is clearly actively maintained.

### Assessment
Kavita demonstrates long-term thinking through its .NET 10 migration, multi-arch container strategy, and keyed DI for extensible scrobbling providers. The primary sustainability risks are: (1) the growing manual migration chain requiring startup-code edits with each version, (2) zero frontend test coverage creating a regression risk surface as Angular upgrades occur (currently at Angular 21, which is very current), and (3) the `.sonarcloud.properties` referencing stale project paths. The project's active community, GPL-3.0 licensing, and comprehensive CI/CD pipeline are strong sustainability signals.

---

# Comparative Snapshot

| Attribute | Rating |
|------------|----------|
| Architecture Sophistication | Above Average |
| Security Posture | Strong |
| Maintainability | Above Average |
| Modularity | Above Average |
| Test Confidence | Moderate |
| Documentation Quality | Above Average |
| Production Readiness | Strong |
| Enterprise Suitability | Moderate |
| Contributor Friendliness | Above Average |
| Sustainability | Above Average |

---

# Final Verdict

## Overall Grade
B+

## Overall Score
82

## Confidence Score
91

## Repository Maturity
Community Project

## Best Attribute
Security

## Weakest Attribute
Testing

## Three-Paragraph Assessment

Kavita is a well-engineered community media server that demonstrates engineering discipline rarely seen at this maturity level. The codebase is organized into a clean 6-project layered architecture with interface-only contract definition in `Kavita.API`, backed by distinct implementation projects for database (`Kavita.Database`), business logic (`Kavita.Services`), and HTTP concerns (`Kavita.Server`). The security implementation is particularly strong: a hybrid auth scheme selecting dynamically between JWT, API Key, and OIDC; entity-level access control enforced through custom ASP.NET filter attributes (`SeriesAccessAttribute`, `ChapterAccessAttribute`); rate limiting on authentication endpoints; path traversal protection on all file upload endpoints; and CodeQL scanning on every PR. The adoption of `.NET 10`, primary constructors, compiled regex with timeout, `CancellationToken` at 1470 call sites, `RecyclableMemoryStreamManager` for EPUB processing, and multi-layer EasyCaching all indicate active engineering investment.

The architectural maturity is solid at the project level but shows internal stress in several large service files. `ExternalMetadataService.cs` at 2168 lines, `BookService.cs` at 1955 lines, and `StatisticService.cs` at 1886 lines each span multiple cohesive responsibilities that would benefit from decomposition. `SeriesRepository.cs` at 1847 lines (50+ async query methods) concentrates too much database surface in a single class. The manual migration invocation chain in `Startup.cs` - 40+ versioned migration calls organized in nested region blocks - is a growing maintenance liability that trades EF migration tooling for a bespoke sequential execution model. The `Kavita.API` shim project serving as an interface-only contract layer is a pragmatic technique that solves the circular dependency problem but creates an unfamiliar project structure for new contributors.

Long-term sustainability is supported by active development, multi-arch Docker builds, SonarAnalyzer in the build chain, and a thriving community. The key sustainability risks are the zero frontend test coverage across 793 TypeScript files and 291 Angular templates, the `ProcessSeriesTests.cs` file containing only stub comments for the most complex business logic in the codebase, and the stale `.sonarcloud.properties` that may indicate SonarCloud analysis is no longer actively reviewing the project. As Kavita continues to grow - adding new metadata providers, scrobbling backends, and reading session tracking - the test coverage debt in both the frontend and the core scanning pipeline will become an increasingly significant regression risk.
