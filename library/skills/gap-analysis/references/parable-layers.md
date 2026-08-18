# Parable Pipeline Layers

What to search for in each layer during the GATHER phase. Use Glob and Grep for discovery, targeted Read (with offset/limit) for details.

## Layer 1-2: Gold/MVO Base Events

Owner: Data Cold Start (upstream dependency for TTS)

| Search target | Glob pattern | What it means |
|---|---|---|
| Gold event tables | `services/dbt/dbt/models/staging/*` | Base event models |
| Identity resolution | Grep for `person_uuid`, `employee_snapshot` | Person dimension |
| MVO contracts | `services/dbt/dbt/contracts/*gold*` or `*mvo*` | Data contracts |

## Layer 3: Classification Context Projections

Owner: TTS squad

| Search target | Glob/Grep | What it means |
|---|---|---|
| Context models | `services/dbt/dbt/models/context/**/*.sql` | dbt SQL models that project source events into classifier-ready format |
| Context contracts | `services/dbt/dbt/contracts/*classification_context*` | ODCS data contracts |
| Context yml | `services/dbt/dbt/models/context/**/*.yml` | dbt model definitions with column tests |
| Catalog wiring | Grep for `classification_context` in `services/query-layer/` | Query layer registration |

Per-source models to check: Google Calendar, Google Email, Slack, Jira, Salesforce CRM. Each should have a `.sql` and `.yml` file.

## Layer 4-5: Classification Service

Owner: TTS squad (Joseph's area)

| Search target | Glob/Grep | What it means |
|---|---|---|
| Classification service | `services/classification/**/*` | Python classification executor |
| Classification Go handlers | `services/web-admin-api/internal/route-impl/classification/**/*` | Go control plane for job lifecycle |
| Classification DB types | `platform-schemas/schemas/web-db/classification*.graphql` | DB schema for classification tables |
| Classification API types | `platform-schemas/schemas/web-admin-api/classification/**/*` | Admin API schema |
| Classification enums | `platform-schemas/schemas/enums/classification*.graphql` | Job status, taxonomy status enums |
| Classification results contract | `services/dbt/dbt/models/classification/*.yml` | artifact_classification_results definition |
| Classification migrations | Grep for `classification` in `services/web-db/migrations/sql/` | DB migrations |
| Classification spec | `docs/internal/specs/*classification*` | Service specification |
| Prefect flows | `services/classification/deployments/` | Prefect deployment config |
| CI/CD | `.github/workflows/*classification*` | Deployment workflows |

## Layer 6: Time Attribution

Owner: TTS squad (Daniel's area)

| Search target | Glob/Grep | What it means |
|---|---|---|
| Attribution model | `services/dbt/dbt/models/time_attribution/**/*` | dbt SQL model + yml definition |
| Attribution contracts | `services/dbt/dbt/contracts/*time_attribution*` | ODCS data contracts |
| Duration macros | `services/dbt/dbt/macros/time_attribution/**/*` | Duration strategy SQL macros |
| Event extraction | Grep for `extracted_*_events` in `services/dbt/` | Per-source event expansion models |
| time_spend_daily SQL | `services/dbt/dbt/models/time_spend_daily/*.sql` | THE FINAL FACT TABLE -- check if it exists |
| time_spend_daily yml | `services/dbt/dbt/models/time_spend_daily/*.yml` | Contract definition (may exist without SQL) |
| Attribution spec | `docs/internal/specs/*time-attribution*` or `*time_attribution*` | Spec document |

## Serving: Query Layer

Owner: Platform / Andrew's area

| Search target | Glob/Grep | What it means |
|---|---|---|
| Query layer service | `services/query-layer/` | DataFusion service |
| Flight SQL client | Grep for `flight-sql` or `FlightSQL` in `apps/web-app/src/` | Web-app client for DataFusion |
| Catalog entries | Grep for `time_spend` or `classification` in `services/query-layer/` | Table registration in catalogue |
| Contract publisher | Grep for `contract_bridge` or `contract_publisher` in PRs | Mechanism to register dbt contracts in catalogue |

## Serving: web-api

| Search target | Glob/Grep | What it means |
|---|---|---|
| Mock handlers | `services/web-api/internal/route-impl/time-spend/*` | UNSTABLE mock endpoints |
| Schema-defined routes | `platform-schemas/schemas/web-api/early-access/previews/time-spend/` | psgen-generated routes |
| Query layer integration | Grep for `query-layer` or `tts` in `apps/web-app/src/lib/server/` | BFF proxy to DataFusion |

## Serving: Frontend

| Search target | Glob/Grep | What it means |
|---|---|---|
| Time spend domain | `apps/web-app/src/lib/domains/time-spend/` or Grep `time-spend` in `apps/web-app/src/lib/domains/` | Dedicated domain directory |
| Release panel | `apps/web-app/src/lib/domains/early-access/release-panels/*TimeSpend*` | Early access release panel |
| Routes | Grep for `time-spend` in `apps/web-app/src/routes/` | SvelteKit route files |
| Design system components | Grep for `DonutChart` in `apps/packages/design-system/` | Chart components |

## Cross-Layer Schema Compatibility Checks

When both the producer (dbt/Delta) and consumer (frontend queries) exist, diff their column schemas.

| Consumer file | What to extract | Producer to compare against |
|---|---|---|
| `apps/web-app/src/lib/server/query-layer/tts/queries.ts` | Column names in SQL strings (SELECT, WHERE, GROUP BY) | Delta log schema at the GCS path from catalogue, or dbt `.yml` contract |

**Delta log schema inspection:**

```bash
gcloud storage cat gs://<bucket>/<path>/_delta_log/00000000000000000000.json \
  | python3 -c "
import sys, json
for line in sys.stdin:
    obj = json.loads(line)
    if 'metaData' in obj:
        schema = json.loads(obj['metaData']['schemaString'])
        for f in schema['fields']:
            print(f['name'])
"
```

Flag any column referenced by the consumer that does not appear in the producer schema. Also grep consumer files for "not yet", "will be added", TODO comments that document known schema gaps.

## Admin Configuration (M4, usually not M1)

| Search target | Glob/Grep | What it means |
|---|---|---|
| DB tables | `platform-schemas/schemas/web-db/time-spend.graphql` | POV-548 config tables |
| DB enums | `platform-schemas/schemas/enums/time-spend.graphql` | Taxonomy/run status enums |
| Admin API schema | `platform-schemas/schemas/web-admin-api/time-spend/**/*` | Admin CRUD endpoints |
| Admin handlers | `services/web-admin-api/internal/route-impl/timespend/**/*` | Go route implementations |
| Admin permissions | Grep for `timespend` in `platform-schemas/permissions/permissions.yml` | Permission entries |
| Admin UI | Grep for `admin` in time-spend frontend files | Admin modals/pages |
| Migrations | Grep for `time_spend` in `services/web-db/migrations/sql/` | DB migrations |

## Data / Backfill

| Search target | Glob/Grep | What it means |
|---|---|---|
| Seed data | `services/dbt/dbt/seeds/` | dbt seed files |
| Backfill scripts | Grep for `backfill` in `*-flows/` and `services/` | Data loading scripts |
| Fixture data | Grep for `fixture` or `mock.*data` in time-spend files | Test/demo data |

## Known Large Files (always chunk, never full-read)

These files commonly exceed the 10K token Read limit. Always use Grep to find the relevant section first, then Read with offset and limit (200 lines max).

- `docs/internal/specs/0017-team-time-spend-architecture.mdx` (~540 lines)
- `docs/internal/specs/0017-team-time-spend-frontend.mdx` (~400 lines)
- `docs/internal/specs/classification-service-draft.mdx` (~350 lines)
- `docs/internal/edr/0017-team-time-spend-architecture.mdx` (~300 lines)
- `services/web-db/migrations/sql/*.up.sql` (variable, some over 200 lines)
- `platform-schemas/schemas/web-db/*.graphql` (100-400 lines)
- PR diffs for large PRs (use `gh pr view --json files` to list files first, then fetch specific files)
