# Central Semantic Catalog — QlikGPT

The authoritative shared metric definitions are in [measures.json](measures.json). Two Presentation application manifests subscribe to them:

| Presentation | Shared measures |
| --- | --- |
| [Presentation 1](../apps/presentation1.json) | `qlikgpt_shared_revenue`, `qlikgpt_shared_orders` |
| [Presentation 2](../apps/presentation2.json) | `qlikgpt_shared_revenue`, `qlikgpt_shared_margin_pct` |

Presentation 1 also preserves its **four local master measures** in `frontend/measures.json`; they are *not* part of the global catalog.

## Change management

Edit the `expression` for `qlikgpt_shared_revenue` and commit to `main`. GitHub Actions detects the changed measure ID, finds subscribed apps, and updates the same native master-measure ID in each. It reads back the expression using QIX `GetMeasure` and checks that the app has required fields; all updates execute on a GitHub-hosted runner, **no workstation required**.

Changes to a measure subscribed only by one Presentation should deploy only to that subscriber. The workflow preserves stable IDs, checks for duplicate IDs, validates references and preflights expressions. Unsubscribing does **not** automatically delete an existing Qlik master measure; deletion needs a separate approved operation.

### Example

```json
{
  "id": "qlikgpt_shared_revenue",
  "title": "Ricavi condivisi",
  "expression": "Sum(Revenue)",
  "requiredFields": ["Revenue"]
}
```

A chart linked through `qLibraryId` inherits changes to its master measure. An inline expression does not. Presentation 2 contains two native KPI objects linked to shared library measures.

The pipeline deliberately uses normalized fields from the common Sales_Clean QVD in both Presentation apps. Different business models will require compatibility checks or per-app translation.

### Limits

- Changes are propagated on a successful **CI deployment**, not instantaneously on Qlik Cloud without GitHub Actions.
- For the PoC, deploy to two editable development apps; published/managed apps have distinct promotion requirements.
- Automatic deletion and universal transactional multi-app deployment are not claimed.
- Never store API keys or client data in the public repository.
