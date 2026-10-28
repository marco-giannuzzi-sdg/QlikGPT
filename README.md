# QlikGPT — Git-governed Qlik Cloud BI as Code

QlikGPT governa app Qlik Cloud, ETL/QVD, master items, dashboard, script deployment e lineage tramite GitHub, CI/CD e QIX.

## Modelli semantici

| Modello | Script, ETL e app | Cataloghi | Lineage e impatti |
| --- | --- | --- | --- |
| **[Sales Analytics](semantic-models/sales/README.md)** | [ETL1](semantic-models/sales/scripts/etl1.qvs), [ETL2](semantic-models/sales/scripts/etl2.qvs), [Presentation](semantic-models/sales/scripts/presentation.qvs) e [app JSON](semantic-models/sales/apps/) | [Misure](semantic-models/sales/catalog/measures.json), [Dimensioni](semantic-models/sales/catalog/dimensions.json), [Variabili](semantic-models/sales/catalog/variables.json), [Formati](semantic-models/sales/catalog/formatting.json) | [App Lineage](semantic-models/sales/lineage/APP_LINEAGE.md) e [Semantic Usage](semantic-models/sales/catalog/USAGE.md) |

Tutti gli asset specifici del modello Sales sono in **[semantic-models/sales/](semantic-models/sales/README.md)**, incluso il registro [model.json](semantic-models/sales/model.json), il [design system](semantic-models/sales/design/EXECUTIVE_CLEAN.md) e gli [App ID](semantic-models/sales/deployment/app-ids.json).

La logica riutilizzabile resta globale in [ci/](ci/), i test in [tests/](tests/) e il workflow in [.github/workflows/](.github/workflows/).

```text
QlikGPT/
├── semantic-models/
│   └── sales/
│       ├── model.json
│       ├── scripts/
│       │   ├── etl1.qvs
│       │   ├── etl2.qvs
│       │   └── presentation.qvs
│       ├── apps/
│       ├── catalog/
│       │   ├── measures.json
│       │   ├── dimensions.json
│       │   ├── variables.json
│       │   ├── formatting.json
│       │   ├── USAGE.md
│       │   └── usage.json
│       ├── lineage/
│       │   ├── APP_LINEAGE.md
│       │   └── graph.json
│       ├── design/
│       └── deployment/
│           └── app-ids.json
├── ci/
├── tests/
└── .github/workflows/
```

## App Qlik esistenti — ID preservati

- [01 ETL RAW](https://sdggroup-it.eu.qlikcloud.com/sense/app/932480d2-415d-4535-9267-c699f44c55c6)
- [02 ETL TRANSFORM](https://sdggroup-it.eu.qlikcloud.com/sense/app/70ba9d05-24b7-46ec-8b8c-560e8169c3d1)
- [03 PRESENTATION](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
- [04 PRESENTATION SHARED](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)

## Deployment distinto dal ricaricamento dati

Un push su `main` distribuisce gli script QVS modificati in modalità **`--no-reload`**; la modifica al solo percorso GitHub di un QVS già presente nell'app non richiede nemmeno di riscriverlo in Qlik (controllo preventivo con `GetScript`).

| Operazione GitHub Actions | Effetto |
| --- | --- |
| `deploy-only` | Applica script e frontend semantico, **nessun reload** |
| `reload-app` | Distribuisce lo script e ricarica una sola app |
| `reload-chain` | Distribuisce e ricarica app selezionata e downstream, in ordine di [App Lineage](semantic-models/sales/lineage/APP_LINEAGE.md) |

Per avviare reload espliciti: [GitHub Actions — QlikGPT](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/workflows/deploy-qlik-cloud.yml).

GitHub resta la fonte autorevole delle misure, dimensioni, variabili e dashboard. Le app sottoscrivono i master item tramite `qLibraryId`. I report di lineage e Usage sono derivati dai file versionati (non da telemetria runtime del tenant).

## Architettura evolutiva

[ci/model_registry.py](ci/model_registry.py) individua i `semantic-models/*/model.json` e risolve i file relativi al modello. Gli App ID appartengono al modello corrispondente. Attualmente il workflow di deployment è **configurato su sales** e distribuisce un modello per job; per gestire più modelli in una singola esecuzione servirà estendere l'orchestrazione e isolare i namespace dove necessario.

## Test e sicurezza

```bash
python3 -m unittest discover -s tests -v
python3 ci/catalog_report.py --check
python3 ci/app_lineage.py --check
```

Le credenziali Qlik restano nei GitHub Secrets. Nessun Reverse Sync automatico dai master item Qlik a GitHub. Rollback compensativo best effort: il deploy su più app non è una singola transazione atomica.
