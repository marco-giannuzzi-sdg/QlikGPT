# Verifica del frontend Premium — 28 ottobre 2026

Implementazione nel repository **marco-giannuzzi-sdg/QlikGPT**, distribuita tramite CI.
Il browser è stato usato in modalità analisi per ispezionare il risultato; non sono
state applicate modifiche grafiche dall'editor SaaS.

## Risultato verificato

- Header navy, canvas chiaro e card KPI bianche con angoli arrotondati, ombre e icone.
- Quattro KPI con i valori formattati da Qlik, coincidenti con il foglio precedente.
- Filtri Anno/Mercato/Canale renderizzati con le opzioni dei master item.
- Area chart blu con 12 mesi e confronto per mercato con quattro barre teal.
- Nessuna visualizzazione non valida nel nuovo foglio.
- Foglio originale conservato nella stessa app; nessuna nuova applicazione creata.

## Evidenze CI

[PR integrata #5](https://github.com/marco-giannuzzi-sdg/QlikGPT/pull/5).
La successiva correzione dell'ID temporale e del confronto delle proprietà Engine
è nel commit `1547f5dc22ca29b9613805bafd29016bef3a63f6`.

[Deploy Premium riuscito](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40695257470),
[regressioni e modello semantico](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40695257663),
[pipeline Qlik esistente](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40695257473):
tutte concluse con successo.

La pipeline dedicata conferma:
`SEMANTIC SNAPSHOT UNCHANGED: script, 4 measures, 4 dimensions`;
`DATA RELOADS: 0`.
I sei test JavaScript e i tre nuovi test Python coprono binding al catalogo,
identità delle selezioni, valori vuoti/negativi, escaping e limiti delle scritture.

## Aprire il risultato

[Foglio Sales Intelligence | Premium](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb/sheet/qlikgpt_sales_premium/state/analysis)

## Limiti dichiarati

Il mockup generato originale non era presente tra gli allegati recuperabili:
il confronto è stato eseguito rispetto alla descrizione concordata, senza
affermare una corrispondenza pixel per pixel.

La verifica live è stata visiva e desktop, senza azionare filtri dal browser,
come richiesto. La CI verifica binding e dati Engine; non è stato eseguito un
test end-to-end delle selezioni nel browser autenticato.

I filtri del componente sono a selezione singola; riflettono anche eventuali
selezioni multiple già applicate in Qlik. Fetch iniziale: 100 righe per grafico
e 1000 valori per filtro, adeguati a questa app. Paging e ricerca multiselezione
restano estensioni future. L'esportazione nativa di immagini/PDF/PowerPoint delle
estensioni custom non è supportata da Qlik Cloud.

## Riferimenti tecnici

[Guida ufficiale nebula.js](https://qlik.dev/extend/extensions/nebula-js/quickstart/first-extension/),
[confine di rendering delle estensioni](https://qlik.dev/extend/extensions/extension-guidelines/),
[API Qlik per le estensioni](https://qlik.dev/apis/rest/extensions/),
[limiti di esportazione](https://qlik.dev/extend/extensions/extension-api/).

Codice, istruzioni di build e ripristino:
[ui/premium](https://github.com/marco-giannuzzi-sdg/QlikGPT/tree/main/ui/premium).
