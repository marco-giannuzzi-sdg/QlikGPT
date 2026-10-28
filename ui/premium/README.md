# Premium Sales Intelligence pilot

Source-controlled presentation for app `07dfa926-4895-4fb2-af4c-eac90e9eb2cb`.
Pilot sheet: `qlikgpt_sales_premium`. Existing sheet: `qlikgpt_sales_overview`.

## Architecture

The dashboard is a Qlik Cloud nebula.js visualization, built with the official
Qlik CLI toolchain. All CSS and SVG icons are bundled. It renders only inside
the DOM element supplied by `useElement()`; it does not patch Qlik's shell,
inject global CSS, use a custom app theme, or load runtime CDN assets.

The persistent KPI hypercube references the four existing catalog master
measures. Two session hypercubes reference the existing revenue measure and
month/market master dimensions. Three session list objects reference the year,
market and channel master dimensions. Selections go through supported Engine
methods with Qlik element numbers; there are no inline business formulas.
Change listeners update the charts; teardown removes listeners and destroys
only the session objects owned by this component.

The pilot uses a navy header, a light canvas, white rounded cards, SVG icons,
compact filters, a blue area chart and teal horizontal bars. Values are rendered
from Qlik's formatted KPI text, without invented growth rates or comparisons.

## Build and deployment

`npm test` tests bindings, selection identity, escaping, empty/negative values
and formatting. `npm run build` produces a self-contained supernova extension
through `nebula build` and `nebula sense`.

The dedicated `premium-overview.yml` workflow tests and builds pull requests.
On main, with the existing `QLIK_CICD_ENABLED` opt-in, it uses the existing
GitHub Qlik secret to publish only the `qlikgpt-premium-overview` extension and
create/update the additive pilot sheet. The token is never downloaded to a
developer machine or requested in chat.

The deployment checks the exact application ID, reads all required masters,
verifies Engine chart rows and the persisted measure bindings, and compares
script/master-property snapshots before/after. It never creates an app,
writes a load script/master item, changes the semantic model, or calls a reload.
The older repository deployment workflow remains independent.

## Validation and limits

The original screenshot of the generated premium mockup was not recoverable
from the referenced conversation; the available attachments show previous Qlik
renders. Visual acceptance therefore uses the user's explicit design brief,
not a claimed pixel-for-pixel match.

Live browser acceptance must be recorded after deployment. Browser use is
restricted to opening the analysis view and inspecting its appearance; no Qlik
editor changes or browser-based deployment are part of this workflow.

The initial filters provide single selection and clear; existing multi-selections
from Qlik's selection bar are reflected. The bundled initial data fetch supports
100 chart rows and 1000 list values, sufficient for this pilot's months/markets/
years/channels; larger applications require paging. The UI does not yet expose
multi-select search or a chart data export menu. Native Qlik Cloud image, PDF and
PowerPoint export are not supported for custom visualization extensions; the
persistent KPI hypercube remains available for data inspection/export.

## Rollback

Open the preserved original Overview to return to the previous presentation.
A Git revert restores earlier extension code; rerunning the deployment updates
the same namespaced pilot without deleting sheets, masters, apps or data.
No tenant permissions, CSP settings, OAuth clients or credentials are created.
