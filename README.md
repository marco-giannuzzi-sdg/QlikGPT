# QlikGPT - Qlik Sense SaaS three-app QVD PoC

This project automatically creates **three separate Qlik Cloud analytics applications** and deploys their respective Qlik load scripts from GitHub source files, with QVD handoffs.

## Design

```text
App 1: QlikGPT - 01 ETL RAW
    scripts/etl1.qvs
    AUTOGENERATE 5000 orders
        |
        v STORE
    lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd
        |
        v LOAD FROM QVD
App 2: QlikGPT - 02 ETL TRANSFORM
    scripts/etl2.qvs
    Clean rows, calculate Revenue/Cost
        |
        v STORE
    lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd
        |
        v LOAD FROM QVD
App 3: QlikGPT - 03 PRESENTATION
    scripts/presentation.qvs
    FactSales + Calendar associative model
```

All three applications **must be in the same Qlik Cloud space** because `lib://DataFiles/...` without an explicit space name refers to the current space. By default, the scripts create them in the authenticated user's personal space.

### Files

| File | What it does |
| --- | --- |
| `scripts/etl1.qvs` | ETL1: generates synthetic RAW orders, stores RAW QVD |
| `scripts/etl2.qvs` | ETL2: loads RAW QVD, applies transformations, stores clean QVD |
| `scripts/presentation.qvs` | Presentation: loads clean QVD into FactSales and Calendar |
| `create-apps.cmd` | Creates the three Qlik apps and saves their real App IDs locally |
| `deploy-all.cmd` | Deploys the appropriate QVS to each app, reloads in dependency order |
| `run-pipeline.cmd` | **One-command setup**: creates apps (if absent) and deploys all scripts |
| `build.cmd` | Compatibility alias for `run-pipeline.cmd` |
| `.local/app-ids.cmd` | Auto-generated, git-ignored state file holding App IDs |

## Requirements

- Windows CMD (not PowerShell required)
- Qlik CLI (`qlik.exe`) in the repository folder or on PATH
- A working Qlik CLI login/context (`qlik.exe user me`)
- Permission to create and edit apps, reload, and write QVDs to the target space
- Internet access to the Qlik Cloud tenant

## Quick start from Windows CMD

1. Clone the repository (or download the repository ZIP and extract it).
2. Open CMD **inside the repository folder**.
3. If `qlik.exe` is not available via PATH, copy it into the repository folder (it is ignored by Git).
4. Confirm authentication: `qlik.exe user me`.
5. Run:

```cmd
run-pipeline.cmd
```

This runs the three actions end-to-end. Qlik CLI reads each **local QVS source file automatically** using the `--script` option; there is **no manual copy/paste** into the Qlik editor.

### Optional separate commands

```cmd
create-apps.cmd
deploy-all.cmd
```

### Shared space instead of personal space (optional)

Only *before the first creation*, set your target shared space ID in the CMD session:

```cmd
set QLIK_SPACE_ID=your-shared-space-uuid
run-pipeline.cmd
```

All three applications are created in that same space. This requires appropriate edit and data-file permissions. Do not change space after IDs are generated without migrating all three apps and their QVD files.

## Re-running

- App IDs are written locally to `.local/app-ids.cmd` **immediately after each successfully-created app**.
- Later executions reuse the same apps: no duplicate apps are created as long as that local state file is retained.
- Subsequent `deploy-all.cmd` runs overwrite the **load script** of each saved app, then reload sequentially.
- If a step fails, the pipeline stops and does not execute downstream steps.
- Randomized demo sales data is regenerated on each ETL1 reload, so sales KPI values are not deterministic.

## Data model and validation

ETL1: 5,000 rows in `RawOrders` and the RAW QVD.

ETL2: rows passing basic validation; columns such as OrderID, OrderDate, Market, ProductCategory, Channel, CustomerID, Quantity, UnitPrice, Revenue, Cost.

Presentation: `FactSales` and `Calendar` related only by `OrderDate`; supports Revenue, Cost, Margin, MarginPct and time/group breakdowns.

```cmd
REM Verify using the generated Presentation App ID:
call .local\app-ids.cmd
qlik.exe app eval "Count(OrderID)" --app "%QLIK_PRESENTATION_APP_ID%"
```

Expected: `5000` rows.

## Security notes

- This is a PoC with **synthetic** data only.
- The GitHub repository may be public. Never add tenant credentials, source-system secrets or client data.
- CLI authentication stays on the local workstation.
- The local App IDs file is deliberately excluded from source control.
- The previously created single PoC application is **not touched** by this new pipeline.
- GitHub commits do **not** automatically deploy to Qlik Cloud; running the CMD launcher performs deployment.

## Next iteration

Generate master measures, dimensions, JSON visualization objects and sheets as versioned code for the Presentation application. Add a safer staging/production promotion process, tests, schedules and possibly GitHub Actions on an approved runner.

Official reference:
- https://qlik.dev/toolkits/qlik-cli/app/app-create/
- https://qlik.dev/toolkits/qlik-cli/app/app-build/
- https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Spaces/manage-data-files-spaces.htm
