# QlikGPT - Qlik Sense SaaS PoC

Code-first Qlik Cloud PoC using three **separate QVS source scripts**.

## Architecture

| File | Layer | Responsibility |
| --- | --- | --- |
| `scripts/etl1.qvs` | ETL1 / RAW | Generates 5,000 synthetic orders |
| `scripts/etl2.qvs` | ETL2 / STAGING | Validates fields and computes Revenue, Cost |
| `scripts/presentation.qvs` | PRESENTATION | Creates Sales + Calendar tables; Margin |

Pipeline: **ETL1 → ETL2 → PRESENTATION**.

This version runs all three layers in one Qlik application reload, using in-memory RESIDENT loads. It does **not** create three Qlik apps or QVD files. That can be added later as a separate multi-app ETL deployment.

## Build locally from Windows CMD

Requirements: Windows CMD, Qlik CLI authenticated to a development tenant, permission to edit the target app. No Python or database required.

1. Clone or download this repository.
2. Ensure `qlik.exe` is in this directory or accessible through PATH.
3. Build a single QVS file from the **three separate sources**:

```cmd
build.cmd
```

4. Deploy to a known, development-only app after setting the ID in your *local* CMD session:

```cmd
set QLIK_APP_ID=<your-development-app-id>
build.cmd deploy
```

The deployment calls `qlik app build --app <id> --script dist\load.qvs`, which overwrites the target app's **load script**, runs a reload, and saves it. It does not yet generate sheets or charts.

Verify separately:

```cmd
qlik.exe app eval "Count(OrderID)" --app <your-development-app-id>
```

Expected count: **5000**. Financial results vary between reloads because of `Rand()`.

## Security and version control

- This repository contains only synthetic demo data and no credentials.
- Keep API keys in local Qlik CLI authentication settings, not in GitHub.
- Never commit a CLI context or `.env` file containing tokens.
- Keep production app identifiers out of public repositories.
- Commits to GitHub **do not** automatically deploy to Qlik Cloud. `build.cmd deploy` is an explicit action.

## Next iteration

Create Git-versioned master measures, sheets and visual objects in JSON, then deploy them via Qlik CLI. For reusable QVS includes in Qlik Cloud, explore `$(Must_Include=lib://DataFiles/file.qvs)` once the files are uploaded to a suitable space.
