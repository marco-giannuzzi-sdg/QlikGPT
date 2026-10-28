# QlikGPT — Executive UI Design System V1

Questo livello è **globale e riutilizzabile**: non appartiene soltanto a Sales. Gli script ETL e il Semantic Catalog restano invece locali al proprio modello.

## Asset

- [design-tokens.json](design-tokens.json): palette, contrasto, font, grid, regole dei KPI e colori delle superfici.
- [themes/qlikgpt-executive-v1/theme.json](themes/qlikgpt-executive-v1/theme.json): Qlik custom theme documentato e versionato.
- [themes/qlikgpt-executive-v1/qlikgpt-executive-v1.qext](themes/qlikgpt-executive-v1/qlikgpt-executive-v1.qext): metadati QEXT richiesti per preparare un'estensione tema.
- [ci/ui_template.py](../ci/ui_template.py): libreria per creare e verificare gli oggetti di una nuova Presentation.

I token applicano uno stile **Executive Clean**: fondo chiaro, superfici bianche, header navy, KPI su card delicate, accento teal, filtri compatti, navigazione nativa in alto. L'interfaccia è costruita con oggetti Qlik nativi. Non usiamo CSS che seleziona elementi DOM interni.

## Esperienza di navigazione

La struttura delle Presentation esistenti ora include header QlikGPT e un pulsante **nativo Qlik** per aprire la Presentation complementare. Il pulsante usa `navigation.action = openWebsite` e l'URL dell'altra app nel tenant. Il collegamento è intenzionale: attraversa due app distinte, non finge che siano due sheet dello stesso modello fisico.

In future app multischeda, la stessa classe di pulsante può usare `goToSheetById` e un ID di sheet verificato. Non introduciamo pulsanti verso sheet non esistenti.

## Nuova app già stilizzata — senza cambiare le app attuali

Per preparare un'app Sales con 2 KPI, anteprima non persistente:

```bash
python3 ci/ui_template.py \
  --new-key presentation3 \
  --app-name "QlikGPT - 05 PRODUCT PERFORMANCE" \
  --measures qlikgpt_shared_revenue,qlikgpt_shared_orders
```

Il comando stampa il manifest e il JSON degli oggetti: header, pulsante nativo, griglia 24 colonne e card KPI che referenziano le misure del catalogo tramite `qLibraryId`.

Per **scrivere davvero** i file in `semantic-models/sales/apps/` aggiungere `--write`. Non li pubblichiamo automaticamente. Un commit dei file di una nuova Presentation può attivare il bootstrap dell'app Qlik, che nel codice attuale potrebbe provocare un reload **di quella nuova app**. Per questo la creazione delle app resta un'azione intenzionale e distinta dal semplice aggiornamento estetico.

Per controllare i JSON esistenti senza accedere a Qlik:

```bash
python3 ci/ui_template.py --check
python3 -m unittest discover -s tests -v
```

## Tema custom opzionale Qlik Cloud

Il tema Qlik ufficiale può controllare tipografia, colori dei grafici, alcune superfici e proprietà standard: per usarlo nel tenant occorre comprimere insieme `theme.json` e `qlikgpt-executive-v1.qext`, importarlo come tema e applicarlo all'app. **Il solo commit dei file nel repository non lo installa né lo seleziona in Qlik Cloud**.

La nostra pipeline di default continua a gestire i colori delle card e gli header con proprietà native dei singoli oggetti. Non importiamo il tema nel tenant senza un collaudo visuale, permessi appropriati e selezione esplicita. La verifica QIX di oggetti persistiti non sostituisce la verifica visiva nel browser.

## Governance

- Gli ID Qlik di sheet, KPI e misure già esistenti sono immutati; stili e layout sono modificati senza reload dati.
- Niente misure inline nei KPI, niente CSS hack, niente credenziali nel repository.
- Il formato dei valori resta nel Semantic Catalog del modello (`formatting.json`), distinto dalla palette UI del sistema globale.
- Prima di usare il template in una nuova app, scegliere misure realmente disponibili nel relativo Semantic Catalog e aggiungere i filtri/dimensioni necessari.
