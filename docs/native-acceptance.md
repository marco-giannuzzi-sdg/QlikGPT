# Sales Intelligence | Native — verifica del 28 ottobre 2026

Creato un nuovo foglio nella prima app Presentation, tramite **Qlik CLI**:
[aprire il foglio Native](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb/sheet/qlikgpt_sales_native/state/analysis).

## Implementazione

- Quattro oggetti KPI nativi, ciascuno collegato alla propria master measure.
- Un grafico lineare nativo in modalità area, ordinato cronologicamente sulla master dimension Anno/Mese.
- Un grafico a barre orizzontali nativo, collegato a Mercato e Fatturato.
- Tre caselle filtro native, con listbox fisiche collegate ad Anno, Mercato e Canale.
- Header, sezioni e footer realizzati con oggetti nativi Testo e immagine.
- Icone decorative statiche SVG come sfondo delle card; nessun dato o grafico è disegnato nell'immagine.
- Colori, angoli arrotondati, ombre e font salvati nelle proprietà locali `components`.

La gerarchia contiene **18 oggetti**, incluso il foglio e le tre listbox interne.
I grafici sono oggetti distinti e modificabili nell'editor Qlik.
Il componente Premium precedente rimane disponibile nel suo foglio.

## Distribuzione e controlli

[PR #6 integrata](https://github.com/marco-giannuzzi-sdg/QlikGPT/pull/6).
[Codice e istruzioni](https://github.com/marco-giannuzzi-sdg/QlikGPT/tree/main/ui/native-overview).

La scrittura avviene con:
`qlik app object set ui/native-overview/sheet.json --app 07dfa926-4895-4fb2-af4c-eac90e9eb2cb`.

Il file contiene GenericObjectEntry con `qProperty` e `qChildren` ricorsivi:
la CLI crea la gerarchia reale, non una proprietà personalizzata contenente JSON.
La successiva lettura `qlik app object properties --full` conferma gli oggetti.

[Pipeline nativa riuscita](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40699542530),
[regressioni statiche](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40699542583).

Controlli eseguiti: cinque test locali/CI su tipi nativi, gerarchia, griglia,
binding al catalogo, proprietà di stile e ordinamento temporale; verifica live
delle righe dei grafici e dei valori dei filtri; confronto di script e master
prima/dopo; verifica dell'invarianza del timestamp di reload.
**Zero reload; nessuna modifica al modello semantico.**

Il browser è stato usato per controllare il rendering in modalità analisi.
Non sono state applicate modifiche agli oggetti dall'editor SaaS.
Non sono state azionate selezioni dal browser.

## Confronto estetico e limiti

Ripresa la composizione Premium con header navy, canvas chiaro, card bianche
arrotondate con icone, area blu e barre teal. Il controllo reale ha portato
a correggere i segnaposto dei testi vuoti, l'intensità delle ombre,
l'ordinamento dei mesi, la densità del layout e la dimensione dei KPI.

La resa è nativa: font, palette dei valori KPI collegati ai master,
assi, riempimento dell'area, barre e filtri compatti hanno differenze rispetto
al componente HTML/SVG Premium. Non è una replica pixel per pixel.
Il foglio non richiede una nuova estensione né l'assegnazione di un tema.

Riferimenti:
[CLI object set](https://qlik.dev/toolkits/qlik-cli/app/app-object-set/),
[CLI full properties](https://qlik.dev/toolkits/qlik-cli/app/app-object-properties/),
[stili ufficiali del renderer Qlik](https://github.com/qlik-oss/nebula.js/blob/main/apis/nucleus/src/utils/style/styling-props.js).
