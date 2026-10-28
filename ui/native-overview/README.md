# Native Sales Intelligence via Qlik CLI

Additive native sheet `qlikgpt_sales_native` in Presentation app
`07dfa926-4895-4fb2-af4c-eac90e9eb2cb`.

The generator creates a proper GenericObjectEntry tree: every node has
`qProperty`, and physical child nodes live under `qChildren`. Four KPI objects,
a line/area chart, a horizontal bar chart, a market detail table, a channel donut,
three filter panes and their listboxes
are separate Qlik native objects. Section/footer text uses native
text-image objects. Small decorative icons are inline SVG background assets;
all figures, scales, selections and tooltips are rendered by native Qlik charts.

Chart styling is local to object `components`: `key: general`, `bgColor`,
`borderWidth`, `borderColor`, `borderRadius`, `shadow` and title fonts.
The renderer key contract was checked against Qlik's official nebula.js
[`styling-props.js`](https://github.com/qlik-oss/nebula.js/blob/main/apis/nucleus/src/utils/style/styling-props.js).
No custom extension, theme assignment, shell CSS or semantic formula is deployed.

## Build and deploy

Generate with `python ui/native-overview/generate.py`, then import with:

```
qlik app object set ui/native-overview/sheet.json --app 07dfa926-4895-4fb2-af4c-eac90e9eb2cb
```

[Official CLI contract](https://qlik.dev/toolkits/qlik-cli/app/app-object-set/)
accepts GenericObjectEntry, recursively creating the sheet's native children.

The dedicated workflow tests and generates an artifact on PRs; on main it
authenticates with the existing GitHub secret and runs the CLI import.
All persistent object writes go through Qlik CLI. QIX calls in the audit
are read-only or create transient inspection lists. The audit checks native
hierarchy/types, master bindings, Engine rows/filter values, local component
styles, unchanged script/masters and unchanged reload timestamp. It also reads
the full property tree back through CLI.

The native title band is styled through the existing appprops object with
`sheetTitleBgColor` / `sheetTitleGradientColor` set to navy and
`sheetTitleColor` set to white. This setting applies to all sheet title bands
in this Presentation app. The CLI preserves every unrelated app property,
including the selected theme, and all existing appprops children. The duplicate
managed text header is explicitly retired; Executive Overview starts at row zero.
KPI values are centered and filter panes use one grid row without outer decoration.

The table reuses market, channel and the four master measures; the donut reuses channel
and revenue. Its blue, teal and navy slice colors are chart-local styling expressions;
master measures and dimensions remain unchanged. Engine readback reconciles the revenue sum of both breakdowns to
the revenue KPI, without rewriting expressions or reloading data.

The Premium extension sheet and older Overview remain separate. This generator
does not modify the application model or create a new application. A collision
with an unmanaged sheet/child ID stops deployment.

Native chart internals and responsive layout are Qlik-controlled: this recreates
the composition with editable native objects, with minor typography, spacing,
area opacity and bar geometry differences from the custom nebula canvas.
