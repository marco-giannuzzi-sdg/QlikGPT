# QlikGPT — Native Qlik Sense SaaS as Code

## Shared Semantic Catalog — two governed Presentation apps

QlikGPT now has a **central, versioned measures catalog** that distributes reusable native Qlik master measures across different Presentation apps.

| Resource | Purpose |
| --- | --- |
| [catalog/measures.json](catalog/measures.json) | Single source of truth: ID, formula, label, number format, version, required fields |
| [apps/presentation1.json](apps/presentation1.json) | Subscribes to shared Revenue and Orders; retains 4 original local measures |
| [apps/presentation2.json](apps/presentation2.json) | Subscribes to shared Revenue and Margin % |
| [apps/presentation2-objects.json](apps/presentation2-objects.json) | Native KPIs linked via `qLibraryId` to the shared metrics |
| [ci/semantic_catalog.py](ci/semantic_catalog.py) | Dependency analysis, QIX create/update, exact formula read-back, numeric evaluation, best-effort compensation |
| [tests/test_semantic_catalog.py](tests/test_semantic_catalog.py) | Offline schema, duplicate-ID and dependency-routing regression tests |

**Live Qlik apps:** [Presentation 1](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb) · [Presentation 2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)

### How to update a globally shared metric

Edit **only** the matching entry in `catalog/measures.json` (e.g., `qlikgpt_shared_revenue`), keep the stable `id`, and commit to `main`. GitHub Actions determines which Presentation manifests reference that ID; it updates only those apps via QIX, reads each persisted definition back, and evaluates the measure expression. No workstation and no data reload for catalog-only edits.

- [CI run #40](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40496905086) verified changing the shared Revenue formula in **both** Presentations.
- [CI run #42](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40497167350) verified updating **only Presentation 2** for a measure to which Presentation 1 is not subscribed.
- Existing app-specific measures and objects remain intact. Removing a metric from a JSON file does not automatically delete a Qlik master item.
- This is governed **CI synchronization**, not a live cross-app Qlik metadata link. Qlik apps own their master items independently.
- An app's chart must use a master measure's `qLibraryId` for that chart to inherit changes; inline expressions do not.
- The compensation/rollback is **best effort**, not a guaranteed distributed transaction. For production add a staging/promotion process and approval before changing published apps.

[Detailed catalog instructions](catalog/README.md)

---


This PoC separates **three Qlik Cloud applications** following the classic Qlik extract/transform/presentation architecture, and supports a **PC-free GitHub Actions CI/CD** workflow, including a path for **native Qlik frontend development via JSON**.

## Architecture

```text
ChatGPT / GitHub (source)
  |
  v GitHub Actions (hosted runner: no local PC)
  |
  +-- QlikGPT - 01 ETL RAW
  |     scripts/etl1.qvs
  |     5000 synthetic orders -> DataFiles/QlikGPT/01_RAW/RawOrders.qvd
  |
  +-- QlikGPT - 02 ETL TRANSFORM
  |     scripts/etl2.qvs
  |     RawOrders.qvd -> DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd
  |
  +-- QlikGPT - 03 PRESENTATION
        scripts/presentation.qvs
        Sales_Clean.qvd -> FactSales / Calendar
        frontend/*.json -> native Qlik sheets, measures, dimensions, charts
```

All three apps **must live in the same space** (personal space by default). The first single-app PoC is not used or modified.

## PC-free GitHub Actions deployment (recommended)

Workflow: [`.github/workflows/deploy-qlik-cloud.yml`](.github/workflows/deploy-qlik-cloud.yml)

The Actions workflow:
1. Runs on a **GitHub-hosted Ubuntu runner** (no user's workstation involved).
2. Installs Qlik CLI v3.4.0 and authenticates against Qlik Cloud.
3. Creates the 3 apps once; stores their App IDs in [`deployment/app-ids.json`](deployment/app-ids.json) and commits that file back to the repository.
4. Deploys and reloads `scripts/etl1.qvs`, `scripts/etl2.qvs`, and `scripts/presentation.qvs`, in order.
5. Applies `frontend/dimensions.json`, `frontend/measures.json` and `frontend/objects.json` to the Presentation app when these arrays are populated.
6. Evaluates `Count(OrderID)` to check the Presentation app can be queried.

### One-time GitHub configuration (browser only, **no PC scripts**)

Open this repository -> **Settings -> Secrets and variables -> Actions**.

1. **Repository secret:** `QLIK_API_KEY` — the existing personal development API key. Never commit or paste it into chat.
2. **Repository variable:** `QLIK_CICD_ENABLED` = `true` (set this only when the tenant and token are ready).
3. **Optional variable:** `QLIK_SPACE_ID` = the Qlik shared development space UUID; leave unset to use the current user's personal space.

Then go to **Actions -> Deploy QlikGPT to Qlik Cloud -> Run workflow**. Subsequent commits on `main` that change `scripts/`, `frontend/` or `ci/` deploy automatically, while changes solely to documentation or `deployment/app-ids.json` do not trigger a new deployment.

**Permissions:** the repository must allow GitHub Actions to write repository contents so it can save the generated App IDs. On first execution, this workflow **creates three apps in your Qlik Cloud tenant** and reloads them. If the user cannot enable repo settings, an organization administrator must approve access.

**Security:** using long-lived user API keys in CI is a PoC convenience only. Prefer an approved Qlik OAuth machine-to-machine identity for enterprise production. Consider making this repository private; never put corporate confidential data or API keys in Git.

**First run not yet verified:** repository code is present, but creating apps and applying the scripts requires configuring the GitHub secret and running the workflow. Inspect the GitHub Actions run logs if any CLI/space-permission issue occurs.

## Frontend as Code — native Qlik Sense sheets and filter panes

The user's workstation and the Qlik sheet editor are **not used**. GitHub Actions deploys all three ETL apps, then handles the native Presentation UI in two phases:

1. `qlik app build --dimensions frontend/dimensions.json --measures frontend/measures.json --objects frontend/objects.json --no-reload` applies versioned master items and sheet properties.
2. `ci/deploy_filters.py` uses **Qlik Associative Engine's QIX WebSocket API** to materialize real native Qlik sheet children from `frontend/objects.json` (4 KPI, 2 charts and 1 filter pane), then attaches the 3 listbox children from `frontend/filters.json` (SalesYear, Market, Channel). This extra step is essential because an embedded `qChildren` JSON array alone is not proof of an actual QIX parent/child relationship.
3. The deployment saves the app, verifies the QIX hierarchy (7 sheet children, 3 nested listboxes), round-trips the app via `qlik app unbuild` and checks the expected 20 object IDs, then validates `Count(OrderID)=5000`.

**Verified:** GitHub Actions runs #28 (first native object creation) and #29 (idempotent re-deployment) completed successfully. These checks prove Engine objects are present and persistent. They do not replace visual QA in the Qlik browser for appearance, cell sizing and styling.

- [GitHub Actions success #29](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40491366744)
- [Presentation app](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
- [QIX frontend deployer](ci/deploy_filters.py)

Native object IDs are stable. Reruns update existing objects, so subsequent AI-generated changes are idempotent without duplicate graphs or filters.

## Local Windows CMD path (legacy, optional)

`create-apps.cmd`, `deploy-all.cmd`, and `run-pipeline.cmd` remain for local recovery or troubleshooting. The recommended GitHub Actions path does **not** call them or require a local computer.

## Useful references

- [Qlik CLI app build](https://qlik.dev/toolkits/qlik-cli/app/app-build/)
- [Qlik CLI context create](https://qlik.dev/toolkits/qlik-cli/context/context-create/)
- [Qlik Engine objects, sheets, visuals](https://qlik.dev/toolkits/qlik-api/guides/app-sheet-list-objects/)
- [Qlik Cloud version control and DTAP](https://qlik.dev/manage/oem/product-development/dtap-environments/)
