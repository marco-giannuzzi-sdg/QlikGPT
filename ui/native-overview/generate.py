"""Generate a real Qlik GenericObjectEntry tree, including physical sheet children."""
from __future__ import annotations
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEET = "qlikgpt_sales_native"
PREFIX = "qlikgpt_native_"
COLS, ROWS = 24, 40
C = {"canvas": "#F2F2F2", "navy": "#142840", "blue": "#3365D5",
     "teal": "#16A39A", "muted": "#718096", "border": "#E5EBF3"}
MEASURES = ["qlikgpt_shared_revenue", "qlikgpt_shared_orders",
            "qlikgpt_shared_margin", "qlikgpt_shared_margin_pct"]
FILTERS = [("year", "Anno", "qlikgpt_d_year"), ("market", "Mercato", "qlikgpt_d_market"),
           ("channel", "Canale", "qlikgpt_d_channel")]

def color(hex_value, alpha=1):
    return {"index": -1, "color": hex_value, "alpha": alpha}

def font(size, hex_value, bold=False):
    return {"fontFamily": "Arial", "fontSize": str(size) + "px",
            "fontStyle": ["bold"] if bold else [], "color": color(hex_value)}

def general(background="#FFFFFF", decorated=True, title_size=16, title_color=None):
    # Exact renderer keys: nebula.js/apis/nucleus/src/utils/style/styling-props.js
    return {"key": "general", "bgColor": {"useExpression": False, "color": color(background)},
        "borderWidth": "1px" if decorated else "0px",
        "borderColor": color(C["border"]), "borderRadius": "16px" if decorated else "0px",
        "shadow": {"boxShadow": "0px 4px 15px 0px" if decorated else "none",
                   "boxShadowColor": color("rgba(36,59,86,0.07)")},
        "title": {"main": font(title_size, title_color or C["navy"], True),
                  "subTitle": font(12, C["muted"]), "footer": font(10, C["muted"])}}

def entry(properties, children=None):
    tree = {"qProperty": properties}
    if children:
        tree["qChildren"] = children
    return tree

def common(ident, typ, title, style):
    return {"qInfo": {"qId": PREFIX + ident, "qType": typ}, "qExtendsId": "",
            "visualization": typ, "title": title, "showTitles": True,
            "showDetails": False, "disableNavMenu": True, "components": [style]}

def text(ident, title, subtitle="", background=None, size=16):
    style = general(background or C["canvas"], False, size)
    props = common(ident, "text-image", title, style)
    props.update({"subtitle": subtitle, "markdown": "\u200b", "images": [], "responsive": False})
    return entry(props)

def cube(measures, dimension=None):
    return {"qStateName": "$",
        "qDimensions": [{"qLibraryId": dimension, "qNullSuppression": True}] if dimension else [],
        "qMeasures": [{"qLibraryId": mid, "qDef": {"qDef": ""}} for mid in measures],
        "qInitialDataFetch": [{"qTop": 0, "qLeft": 0,
                              "qWidth": len(measures) + bool(dimension), "qHeight": 100 if dimension else 1}],
        "qSuppressMissing": True, "qSuppressZero": False}

def icon_image(index):
    shapes = [
        '<path d="M16 5a7 7 0 1 0 0 14M4 10h10M4 14h9"/>',
        '<rect x="5" y="6" width="14" height="15" rx="2"/><path d="M9 6V3h6v3M9 11h6M9 15h6"/>',
        '<path d="M4 19V5M4 19h17M8 15l4-5 4 2 5-7"/>',
        '<path d="M6 19L18 5"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/>']
    ink, fill = ("#3865C5", "#EEF3FF") if index < 2 else ("#14958D", "#E8F7F4")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="76">'
           '<rect x="20" y="18" width="40" height="40" rx="11" fill="' + fill + '"/>'
           '<g transform="translate(28 26)" fill="none" stroke="' + ink +
           '" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + shapes[index] + '</g></svg>')
    return {"mode": "expression", "expressionUrl": "data:image/svg+xml;base64," +
            base64.b64encode(svg.encode()).decode(), "sizing": "originalSize", "position": "top-right"}

def make():
    children, cells = [], []
    def add(tree, col, row, width, height):
        props = tree["qProperty"]
        children.append(tree)
        cells.append({"name": props["qInfo"]["qId"], "type": props["qInfo"]["qType"],
                      "col": col, "row": row, "colspan": width, "rowspan": height,
                      "bounds": {"x": col*100/COLS, "y": row*100/ROWS,
                                 "width": width*100/COLS, "height": height*100/ROWS}})
    add(text("intro", "Executive Overview", "Una visione chiara delle performance di vendita.", size=25), 0, 0, 11, 3)
    for i, (key, label, dimension) in enumerate(FILTERS):
        props = common("filter_" + key, "filterpane", label, general(C["canvas"], decorated=False, title_size=12))
        props["showTitles"] = False
        props["qChildListDef"] = {"qData": {"title": "/title", "id": "/qInfo/qId", "type": "/qInfo/qType"}}
        listing = {"qInfo": {"qId": PREFIX + "list_" + key, "qType": "listbox"},
            "qExtendsId": "", "visualization": "listbox", "title": label, "showTitle": True,
            "searchEnabled": True, "autoConfirm": True,
            "qListObjectDef": {"qLibraryId": dimension, "qStateName": "$",
                "qInitialDataFetch": [{"qTop": 0, "qLeft": 0, "qWidth": 1, "qHeight": 1000}]},
            "layoutOptions": {"dataLayout": "singleColumn", "dense": True},
            "components": [{"key": "theme", "header": {"fontFamily": "Arial", "fontSize": "12px",
                "fontColor": color(C["navy"])}, "content": {"fontFamily": "Arial", "fontSize": "12px"}}]}
        add(entry(props, [entry(listing)]), 12 + i*4, 1, 4, 1)
    add(text("pulse", "BUSINESS PULSE", size=11), 0, 3, 24, 1)
    labels = ["Fatturato", "Ordini", "Margine lordo", "Margine %"]
    notes = ["Valore commerciale", "Volume delle vendite", "Redditività delle vendite", "Margine sul fatturato"]
    for i, (mid, label, note) in enumerate(zip(MEASURES, labels, notes)):
        style = general(title_size=13, title_color=C["muted"])
        style["bgImage"] = icon_image(i)
        props = common("kpi_" + str(i), "kpi", label, style)
        props.update({"qHyperCubeDef": cube([mid]), "textAlign": "center", "layoutBehavior": "fixed",
            "fontSize": "S", "showMeasureTitle": False, "showSecondMeasureTitle": False,
            "footnote": note, "version": "2.5.0", "useLink": False})
        props["qHyperCubeDef"]["qMeasures"][0]["coloring"] = {"baseColor": color(C["navy"])}
        props["qHyperCubeDef"]["qMeasures"][0]["conditionalColoring"] = {
            "useConditionalColoring": False, "useBaseColors": False, "paletteSingleColor": color(C["navy"]),
            "segments": {"limits": [], "paletteColors": [color(C["navy"])]}}
        add(entry(props), i*6, 4, 6, 5)
    add(text("explorer", "PERFORMANCE EXPLORER", size=11), 0, 9, 24, 1)
    for ident, typ, title, subtitle, dimension, ink, col, width in [
        ("trend", "linechart", "Andamento del fatturato", "Evoluzione mensile dei ricavi", "qlikgpt_d_yearmonth", C["blue"], 0, 15),
        ("markets", "barchart", "Performance per mercato", "Confronto dei ricavi per area", "qlikgpt_d_market", C["teal"], 15, 9)]:
        props = common(ident, typ, title, general())
        props.update({"qHyperCubeDef": cube([MEASURES[0]], dimension), "subtitle": subtitle,
            "legend": {"show": False, "showTitle": False},
            "color": {"auto": False, "mode": "primary", "useBaseColors": "off", "paletteColor": color(ink)},
            "dimensionAxis": {"show": "labels", "label": "auto", "dock": "near", "continuousAuto": False},
            "measureAxis": {"show": "labels", "autoMinMax": True, "dock": "near"},
            "gridLine": {"auto": False, "spacing": 2}, "preferContinuousAxis": False,
            "showDisclaimer": False, "version": "1.0.0"})
        if typ == "linechart":
            props["qHyperCubeDef"]["qInterColumnSortOrder"] = [0, 1]
            props["qHyperCubeDef"]["qDimensions"][0]["qDef"] = {
                "autoSort": False, "qSortCriterias": [{"qSortByNumeric": 1, "qSortByAscii": 1}]}
            props.update({"lineType": "area", "nullMode": "gap",
                          "dataPoint": {"show": True, "showLabels": False}})
            props["components"].append({"key": "line", "style": {
                "lineThickness": 3, "dataPointSize": 5, "lineCurve": "linear", "lineType": "solid"}})
        else:
            props.update({"orientation": "horizontal", "barGrouping": {"grouping": "grouped"},
                          "dataPoint": {"showLabels": True, "showSegmentLabels": False},
                          "scrollbar": "none"})
            props["qHyperCubeDef"]["qInterColumnSortOrder"] = [1, 0]
            props["qHyperCubeDef"]["qMeasures"][0]["qSortBy"] = {"qSortByNumeric": -1}
        add(entry(props), col, 10, width, 13)
    add(text("detail", "SALES BREAKDOWN", size=11), 0, 23, 24, 1)
    table = common("market_detail", "table", "Dettaglio vendite", general())
    table.update({"qHyperCubeDef": cube(MEASURES, "qlikgpt_d_market"),
        "subtitle": "Ricavi, volumi e redditività per mercato e canale",
        "totals": {"show": True, "position": "top", "label": "Totale"},
        "scrolling": {"horizontal": True, "keepFirstColumnInView": True},
        "multiline": {"wrapTextInHeaders": False, "wrapTextInCells": False}})
    table["qHyperCubeDef"]["qDimensions"].append({"qLibraryId": "qlikgpt_d_channel", "qNullSuppression": True})
    table["qHyperCubeDef"].update({"qColumnOrder": [0, 1, 2, 3, 4, 5],
        "columnOrder": [0, 1, 2, 3, 4, 5], "columnWidths": [-1, -1, -1, -1, -1, -1]})
    table["qHyperCubeDef"]["qInitialDataFetch"][0]["qWidth"] = 6
    table["qHyperCubeDef"]["qInterColumnSortOrder"] = [2, 0, 1, 3, 4, 5]
    table["qHyperCubeDef"]["qMeasures"][0]["qSortBy"] = {"qSortByNumeric": -1}
    table["components"].append({"key": "theme", "content": {
        "fontSize": 13, "fontColor": color(C["navy"])},
        "header": {"fontSize": 12, "fontColor": color(C["muted"])}})
    add(entry(table), 0, 24, 15, 13)
    donut = common("channels", "piechart", "Mix per canale", general())
    donut.update({"qHyperCubeDef": cube([MEASURES[0]], "qlikgpt_d_channel"),
        "subtitle": "Quota di fatturato per canale di vendita",
        "donut": {"showAsDonut": True}, "dimensionTitle": False,
        "dataPoint": {"auto": False, "labelMode": "share"},
        "legend": {"show": True, "dock": "right", "showTitle": False},
        "color": {"auto": False, "mode": "byExpression", "expressionIsColor": True,
                  "colorExpression": "=If(Channel='Online',RGB(51,101,213),If(Channel='Partner',RGB(22,163,154),RGB(20,40,64)))",
                  "useBaseColors": "off"}})
    donut["qHyperCubeDef"]["qMeasures"][0]["qAttributeExpressions"] = [{
        "id": "colorByExpression",
        "qExpression": "If(Channel='Online',RGB(51,101,213),If(Channel='Partner',RGB(22,163,154),RGB(20,40,64)))"}]
    donut["qHyperCubeDef"]["qInterColumnSortOrder"] = [1, 0]
    donut["qHyperCubeDef"]["qMeasures"][0]["qSortBy"] = {"qSortByNumeric": -1}
    donut["components"].append({"key": "pie", "style": {
        "innerRadius": 0.65, "cornerRadius": 4, "strokeWidth": "small",
        "strokeColor": color("#FFFFFF")}})
    add(entry(donut), 15, 24, 9, 13)
    add(text("footer", "Sales Intelligence · Executive Overview", "Grafici nativi Qlik · Metriche dal catalogo", size=10), 0, 37, 24, 2)
    sheet = {"qInfo": {"qId": SHEET, "qType": "sheet"}, "qExtendsId": "",
        "qMetaDef": {"title": "Sales Intelligence | Native", "description": "Native Qlik CLI premium composition"},
        "title": "Sales Intelligence | Native", "description": "qlikgpt-native-cli-v1",
        "rank": -2, "columns": COLS, "rows": ROWS, "gridMode": "edit",
        "qChildListDef": {"qData": {"title": "/title", "id": "/qInfo/qId", "type": "/qInfo/qType"}},
        "cells": cells, "components": [general(C["canvas"], False)],
        "background": {"color": C["canvas"]}, "backgroundColor": color(C["canvas"]),
        "backgroundMode": "custom"}
    return [entry(sheet, children)]

def write():
    path = Path(__file__).with_name("sheet.json")
    path.write_text(json.dumps(make(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Generated native GenericObjectEntry tree:", path.name)

if __name__ == "__main__":
    write()
