# Ubiquitous Language

## Identity and access

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **User** | An authentication identity in the system, with email and optional name | Account, login |
| **Session** | A time-bounded authenticated context for a User, stored server-side | Token, auth state |
| **MagicLink** | A single-use, time-limited login link sent via email | Login link, auth link |
| **Tenant** | An organization that owns connectors, data, and users | Company, workspace, org, customer |
| **TenantUser** | A User's membership within a specific Tenant, carrying permissions and status | Member, membership |
| **Role** | A named bundle of Permissions assignable to a TenantUser | Access level, privilege set |
| **Permission** | A single capability grant (e.g. "manage_connectors") | Scope, right, entitlement |
| **StaffUserRole** | A platform-wide role for Parable employees (distinct from tenant-scoped Roles) | Admin role, internal role |

## Connector catalog

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **ParableVendor** | A top-level company or product family in the connector catalog (e.g. Atlassian, Google) | Provider, source, integration partner |
| **ParableVendorGrouping** | A hierarchical node under a Vendor -- can be organizational (folder) or a leaf that links to a Connector | Category, connector type |
| **Connector** | A reusable integration definition specifying how to extract data from an external system | Source, integration, adapter |
| **IntegrationClass** | The high-level extraction protocol a Connector uses: API, DATABASE, FILE, STREAMING, META_TOOL, or CUSTOM | Connector type, protocol |
| **ConnectorLifecycleStatus** | The build maturity of a Connector definition, from Draft through Verified | Readiness, build stage |
| **ReleaseStage** | Visibility tier in the catalog: GA, Early Access, Invite Access, Coming Soon | Availability, launch phase |
| **ConnectorPriority** | Tenant-specific importance of a grouping: REQUIRED (blocks insights) or SUGGESTED (improves quality) | Importance, rank |

## Tenant connectors (instances)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **TenantConnector** | A Tenant's configured instance of a Connector, with credentials, config, and operational status | Connection, integration instance |
| **ConnectionStatus** | The computed operational state of a TenantConnector (IDLE, SYNCING, CREDENTIAL_ERROR, etc.) | Connector status, health |
| **Credential** | Authentication material (API token, OAuth tokens, service account key) stored in GCP Secret Manager | Secret, auth config |
| **CredentialMetadata** | The database record that tracks a Credential's type, status, and validation history without storing the secret itself | Credential record |
| **CredentialStatus** | Whether stored credentials are VALID, EXPIRED, INVALID, PENDING, or UNVALIDATED | Auth status |
| **ValidationErrorCode** | The category of a credential validation failure: AUTH_FAILED, INSUFFICIENT_PERMISSIONS, EXPIRED, CONFIG_INVALID, INTERNAL_ERROR | Error type |
| **AuthenticationStrategy** | The chosen auth method for a TenantConnector (e.g. OAuth2, API token, service account) | Auth type, auth method |
| **IngestionConfig** | Connector-specific extraction settings (base URLs, selected streams, filters) separate from auth credentials | Config, connector settings |

## Sync (ingestion)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **SyncJob** | A single execution of data extraction for a TenantConnector | Run, extraction, pull, ingestion run |
| **SyncJobStatus** | Lifecycle state of a SyncJob: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PARTIAL_SUCCESS | Job state |
| **Tap** | A named data stream within a Connector (e.g. "issues", "users", "audit_logs") | Stream, endpoint, table |
| **SyncJobTap** | The execution record for one Tap within a SyncJob | Tap run, stream execution |
| **TapWatermark** | The high-water mark for a Tap, recording the latest successfully synced point for incremental extraction | Cursor, bookmark, checkpoint |
| **SyncMode** | Whether a Tap extracts all records (FULL) or only changes since last watermark (INCREMENTAL) | Load type, extraction mode |
| **SyncPriority** | Queue routing for a SyncJob: CRITICAL, STANDARD, or BACKFILL | Job priority |
| **SyncTriggerType** | What initiated a SyncJob: SCHEDULED, MANUAL, WEBHOOK, RETRY, or BACKFILL | Trigger source |
| **Schedule** | The recurring cadence for automatic syncs: CRON, INTERVAL, or MANUAL | Sync frequency, cadence |

## Transformation (data pipeline)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **TransformationRun** | A single execution of the data transformation pipeline for a TenantConnector, mirroring SyncJob for the transform layer | Transform job, dbt run |
| **TransformationDatasetResult** | The outcome of transforming one Dataset within a TransformationRun, mirroring SyncJobTap | Dataset run, table result |
| **Dataset** | A named data table produced by transformation (e.g. "bronze_ii.okta_audit_logs") | Table, model, asset |
| **DataContractLayer** | The medallion-architecture tier a Dataset belongs to: BRONZE_I, BRONZE_II, SILVER, GOLD, MVO | Layer, tier, zone |
| **Partition** | A date-bounded slice of a Dataset, the unit of idempotent repair in transformation | Chunk, segment |
| **FreshnessClass** | The contracted update cadence for a Dataset: DAILY, WEEKLY, MONTHLY, QUARTERLY | SLA, refresh interval |
| **HealthState** | The projected health of a Dataset: HEALTHY, DEGRADED, FAILED, STALE_BUT_VALID | Quality state |
| **Checkpoint** | A record that a Partition has been successfully processed, allowing future runs to skip it | Marker, completion flag |

## Data contracts

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **DataContract** | A versioned schema agreement between an upstream producer and downstream consumer at a specific layer | Schema, SLA, interface |
| **ContractCompatibility** | Whether an upstream schema change breaks downstream consumers: COMPATIBLE, INCOMPATIBLE, or UNKNOWN | Breaking change check |

## Artifacts (file uploads)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Artifact** | A customer-uploaded file (CSV, XLSX, etc.) ingested as a data source | Upload, file, attachment |
| **ArtifactProcessingStatus** | The lifecycle of an uploaded Artifact: PENDING, PROCESSING, READY, FAILED | Upload status |

## Platform internals

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **psgen** | The code generator that reads .graphql schema files and produces SQL DDL, Go ORM, Go REST routes, TypeScript types, and TypeScript SDKs | Codegen, generator |
| **Schema DSL** | The GraphQL-syntax files in platform-schemas/schemas/ used as a schema definition language (no GraphQL runtime exists) | GraphQL, schema |
| **route-impl** | Hand-written Go business logic implementing the interfaces generated by psgen | Handler, controller, endpoint logic |
| **Scaffold** | A file generated once by psgen then owned by developers (route-impl files) | Template, stub |
| **BFF** | The SvelteKit backend-for-frontend layer that proxies API calls and injects auth tokens server-side | Proxy, middleware |
| **Directive** | A GraphQL annotation (@auth, @secret, @requirePermission, etc.) that controls code generation behavior | Annotation, decorator |
| **Scalar** | A named primitive type with per-language mappings and built-in validation (UUID, Email, Permission, etc.) | Custom type, value type |

## Relationships

- A **Tenant** has many **TenantUsers**, each linking a **User** to a **Tenant** with **Permissions**
- A **ParableVendor** has many **ParableVendorGroupings** in a tree; leaf groupings link to exactly one **Connector**
- A **TenantConnector** is a Tenant's instance of a **Connector**, holding a **CredentialMetadata** reference and **IngestionConfig**
- A **SyncJob** belongs to one **TenantConnector** and contains many **SyncJobTaps**, one per **Tap**
- Each **Tap** maintains a **TapWatermark** on its **TenantConnector** for incremental extraction
- A **TransformationRun** belongs to one **TenantConnector** and contains many **TransformationDatasetResults**
- A **Dataset** lives at a specific **DataContractLayer** and has a **FreshnessClass** contract
- **ConnectionStatus** is computed from SyncJob history, CredentialStatus, and config state -- not stored directly by users

## Example dialogue

> **Dev:** "A customer says their connector shows CREDENTIAL_ERROR. Where does that status come from?"
>
> **Domain expert:** "**ConnectionStatus** is computed by `ResolveStatus` in priority order. CREDENTIAL_ERROR means the latest **CredentialValidationResult** on the **CredentialMetadata** has a **ValidationErrorCode** of AUTH_FAILED or EXPIRED -- and nothing higher-priority (like DISABLED or active syncing) overrides it."
>
> **Dev:** "So if I fix the credentials and trigger a sync, the status changes automatically?"
>
> **Domain expert:** "Yes. Once the **Credential** is updated and a new **SyncJob** starts, the **ConnectionStatus** recomputes. While the job runs, the **TenantConnector** shows INITIAL_SYNCING or UPDATE_SYNCING depending on whether `hasEverSynced` is true. When the **SyncJob** completes, it settles to IDLE."
>
> **Dev:** "What about the **TransformationRun** -- does that affect **ConnectionStatus** too?"
>
> **Domain expert:** "Only indirectly. If the **TransformationRun** has **HealthState** DEGRADED across datasets, the status resolves to TRANSFORM_QUALITY_DEGRADED. But that sits below sync-related statuses in priority -- a running **SyncJob** always takes precedence."

## Flagged ambiguities

- **"connector"** is used for three distinct things: the reusable **Connector** definition (catalog entry), the **TenantConnector** instance (customer's configured connection), and sometimes loosely for the **ParableVendorGrouping** (UI display node). Prefer the specific term for the layer you mean.
- **"status"** appears on at least five entities (TenantConnectorStatusEnum, SyncJobStatus, CredentialStatus, TransformationRunStatus, ArtifactProcessingStatus). Always qualify: "ConnectionStatus", "SyncJob status", "Credential status", etc.
- **"sync"** can mean the SyncJob (ingestion extraction) or loosely the entire ingest-then-transform pipeline. In this glossary, **Sync** refers only to the ingestion layer; use **TransformationRun** for the transform layer.
- **"watermark"** has two scopes: the legacy per-connector `lastWatermark` on TenantConnector, and the per-tap **TapWatermark** entity. New code should use per-tap watermarks.
