# Verifica del foglio nativo — revisione 2

Data: 28 ottobre 2026.

[Foglio Sales Intelligence | Native](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb/sheet/qlikgpt_sales_native/state/analysis) nella prima app Presentation.

## Modifiche

- Fascia titolo nativa navy (#142840), testo bianco. Rimosso il blocco di testo che duplicava Sales Intelligence; Executive Overview parte dalla prima riga del canvas.
- Tre filtri nativi compatti, su una riga della griglia, senza cornice esterna, arrotondamenti o ombra.
- Quattro KPI con valore centrato e icone decorative.
- Conservati area chart mensile blu e bar chart per mercato teal.
- Aggiunta tabella nativa con mercato, canale, fatturato, numero ordini, margine lordo e margine percentuale. Totale e dettaglio ordinato per fatturato.
- Aggiunta ciambella nativa con quota di fatturato per canale, colori blu, teal e navy.
- La composizione usa tutte le 40 righe del canvas, con più altezza dedicata al dettaglio.

## Distribuzione e verifiche

Tutte le modifiche persistenti sono state effettuate da GitHub Actions con Qlik CLI 3.4.0:

```
qlik app object set ui/native-overview/app-title.generated.json --app 07dfa926-4895-4fb2-af4c-eac90e9eb2cb
qlik app object set ui/native-overview/sheet.json --app 07dfa926-4895-4fb2-af4c-eac90e9eb2cb
```

Il primo import conserva l'albero completo delle impostazioni esistenti e cambia solamente sheetTitleBgColor, sheetTitleGradientColor e sheetTitleColor. Tema e altre impostazioni vengono verificati invariati.

Il secondo import aggiorna la sola gerarchia gestita qlikgpt_sales_native: 20 oggetti nativi compreso il foglio e le listbox fisiche dei filtri. Il solo oggetto ritirato è il duplicato di intestazione identificato e controllato esplicitamente. Il deploy si ferma in presenza di altri figli non gestiti.

Gli audit leggono gli oggetti via Engine e CLI, verificano dati e collegamenti ai master e riconciliano il fatturato di tabella e ciambella con il KPI. Script, quattro master measures, quattro master dimensions e timestamp dell'ultimo reload risultano invariati. Nessun reload dati richiesto o eseguito.

Verifiche della revisione finale:

- [CI Qlik CLI e audit del foglio](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40709552164).
- [Validazione statica UI e modello semantico](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40709552459).
- [Regressioni dei deploy esistenti](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40709552189).
- Otto test locali sul contratto della gerarchia, griglia senza sovrapposizioni, master esistenti, proprietà native e conservazione delle impostazioni dell'app.
- [PR di implementazione](https://github.com/marco-giannuzzi-sdg/QlikGPT/pull/7), con successive correzioni del renderer sul ramo main.

La verifica visiva nel browser conferma fascia titolo, filtri compatti, KPI centrati,\ntabella completa con 12 righe visibili alla risoluzione verificata e ciambella\ncon palette coerente. Tutte le tre pipeline della revisione finale sono verdi.\n\n## Ambito e limiti

La fascia titolo è una proprietà nativa dell'app: il colore si applica ai titoli di tutti i fogli della prima Presentation app. Gli altri oggetti dei fogli Premium e Overview restano separati.

Tabella, ciambella, KPI, grafici e filtri sono veri oggetti Qlik. Le piccole icone SVG sono solo decorazioni. L'espressione di colore della ciambella è locale al grafico e non cambia formule o dimensioni del catalogo.

La resa tipografica e la formattazione delle percentuali della ciambella restano quelle native di Qlik. Su schermi più piccoli la tabella può usare il proprio scroll.

Il browser autenticato è stato usato esclusivamente per verificare il rendering in modalità analisi, senza modificare oggetti dall'editor SaaS o applicare selezioni.

## Riferimenti Qlik

- [Proprietà native dell'app e della fascia titolo](https://qlik.dev/apis/javascript/sense-client-objects/).
- [Contratto di import Qlik CLI](https://qlik.dev/toolkits/qlik-cli/app/app-object-set/).
- [Proprietà della tabella e metadati delle colonne nel cubo](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/APIs/Content/Sense_ClientAPIs/QlikVisual/qlik-visual-table-properties.htm).
- [Allineamento dei KPI](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/APIs/Content/Sense_ClientAPIs/QlikVisual/qlik-visual-kpi-properties.htm).
- [Proprietà native di ciambella e colori](https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/APIs/Content/Sense_ClientAPIs/QlikVisual/qlik-visual-piechart-properties.htm).
