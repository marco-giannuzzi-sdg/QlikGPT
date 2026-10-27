# Frontend as Code — Qlik Sense native sheets

**Goal:** ChatGPT generates and changes the **native Qlik Sense UI** (sheets, objects, measures and dimensions) without the user touching Qlik's drag-and-drop sheet editor.

**Architecture:** GitHub Actions -> Qlik CLI -> Qlik Associative Engine -> native Qlik Sense app.

- `dashboard-spec.json`: human/AI-readable desired UI (specification only; *not* currently deployed).
- `dimensions.json`: deployable array of Qlik master dimension object definitions.
- `measures.json`: deployable array of Qlik master measure object definitions.
- `objects.json`: deployable array of native Qlik Engine object definitions (sheets with `cells`, KPIs, line/bar charts, filters, etc).

The three deployable files currently contain `[]`, so no fake frontend is claimed as deployed. The deployer checks for nonempty arrays and uses `qlik app build --objects / --measures / --dimensions --no-reload` to update ONLY the Presentation app. This runs on GitHub-hosted infrastructure.

**Important:** Native Qlik visualization configuration is Qlik-specific JSON, not HTML/React. Any object and sheet JSON must be validated on a test app, especially layout `cells`, visualization type, and Qlik's public/private object visibility. The frontend can be developed entirely as code by the assistant, then deployed via CI.

Qlik CLI docs: https://qlik.dev/toolkits/qlik-cli/app/app-build/
