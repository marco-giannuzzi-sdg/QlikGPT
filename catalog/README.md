# Guida al Semantic Catalog

## Dove definire le misure

**Solo** [catalog/measures.json](measures.json) contiene le definizioni dei master item, anche quando nessuna app li utilizza. Ogni misura ha un ID stabile, `expression`, `format`, `title`, `version`, `description` e `requiredFields`.

Le Presentations contengono esclusivamente una lista `catalogMeasures` di ID, non copie delle formule. Un'app senza misura corrispondente nel manifest **non deve riceverla**. Il namespace storico `qlikgpt_shared_*` è stato mantenuto per preservare gli ID Qlik già in uso: nel nostro progetto significa *governata*, non necessariamente usata da più applicazioni.

## Esempio: una misura condivisa

Se in GitHub modifichi `qlikgpt_shared_revenue`, il diff delle definizioni individua che il suo ID è sottoscritto sia da `presentation1.json` sia da `presentation2.json`. Actions distribuisce la nuova formula in entrambe via QIX `SetProperties`, legge la formula nuovamente da Qlik ed esegue un test `qlik app eval`.

## Esempio: una misura ancora inutilizzata

`qlikgpt_shared_average_order` è già nel catalogo. Per usarla domani in Presentation 2:

1. Apri `apps/presentation2.json`.
2. Aggiungi `"qlikgpt_shared_average_order"` al suo array `catalogMeasures`.
3. Esegui commit su `main`.

Il runner crea il nuovo master item in Presentation 2; **il catalogo resta identico**, e Presentation 1 non cambia. Potrai poi creare un nuovo KPI facendo riferimento al medesimo ID in `apps/presentation2-objects.json`.

## Terza o successiva Presentation

Per una nuova app aggiungi:
- `apps/presentation3.json`, con `appKey="presentation3"`, `appName`, `loadScript="scripts/presentation.qvs"`, `catalogMeasures` e `dashboardSource="apps/presentation3-objects.json"`;
- `apps/presentation3-objects.json`, con le definizioni del foglio Qlik e relativi figli `qLibraryId`.

L'orchestratore rileva i manifest `presentationN.json`, crea e inizializza le nuove app, salva i loro App ID in `deployment/app-ids.json` e distribuisce soltanto le misure a cui si sono iscritte. Le nuove app devono poter leggere i QVD e avere gli stessi campi semantici oppure fornire una propria mappatura dati in una futura estensione.

## Controlli

- JSON valido, ID univoci, sottoscrizioni valide, niente misure inline nei KPI/grafici.
- Qlik GetField per `requiredFields`, GetMeasure/SetProperties e readback della definizione.
- QIX `qLibraryId` dei grafici, ipercubi non vuoti e valutazione espressioni.
- Misure non sottoscritte eliminate **solo dopo controllo delle dipendenze**, mai in maniera cieca.
- Su errori nel mezzo di un deployment, rollback compensativo *best effort*, con log espliciti.

Il codice Qlik è aggiornato tramite GitHub Actions, senza dipendenza dal PC dell'autore.

## Standard di formattazione (Italia)

Il catalogo governa **tutte le master measures**, anche quelle non ancora assegnate a un'app. Ogni misura dichiara `formatPreset`, `colorRole` e, facoltativamente, `compactFormatPreset`, senza copiare impostazioni numeriche.

- [formatting.json](formatting.json) contiene i preset QIX con `qType`, `qnDec`, `qUseThou`, `qFmt`, `qDec`, `qThou` e la palette centralizzata.
- `currency_eur_2`: `€ 1.245.678,90`; `integer_0`: `5.000`; `percent_1`: `27,7%`; disponibili anche `percent_2` e `decimal_2`.
- Il `colorRole` viene inserito nel `coloring.baseColor` del master item nativo Qlik. Ogni grafico può deliberatamente sovrascrivere il colore in caso di visualizzazione specifica.
- `compactFormatPreset` è **un contratto di presentazione**, non altera l'aggregazione o il `qNumFormat` canonico della master measure: il KPI può visualizzare milioni mentre una tabella mostra l'importo completo.
- La CI confronta **tutti e sei i campi di `qNumFormat`**, colore, etichetta, descrizione, espressione e tag; anche unicamente modificando un preset si ridistribuiscono tutte le app sottoscritte.
- Resta necessario verificare il rendering nel browser quando si cambia il tema o la visualizzazione nativa Qlik.

## Semantic Catalog 2.0: dimensioni, variabili e impact analysis

- [dimensions.json](dimensions.json) governa tutte le master dimensions. La vecchia copia `apps/presentation1-dimensions.json` è stata rimossa; gli ID Qlik delle cinque dimensioni esistenti restano invariati.
- [variables.json](variables.json) governa solo variabili applicative create con QIX `CreateVariableEx`; **non sovrascrive** le variabili definite dagli script QVS.
- Ogni `apps/presentationN.json` dichiara `catalogMeasures`, `catalogDimensions`, `catalogVariables`. Oggetti non assegnati restano nel catalogo e vengono creati sull'app solo quando ne dichiari l'ID nel manifest.
- **[Matrice di utilizzo e impatto](USAGE.md)**: distingue master item distribuito a un'app da uso diretto in un oggetto visuale (`qLibraryId`). [usage.json](usage.json) offre gli stessi dati in forma strutturata.
- Modifiche alle definizioni o alle sottoscrizioni eseguono un **frontend-only deployment** (nessun reload dei dati); la pipeline legge poi gli oggetti QIX e verifica il salvataggio. Gli oggetti estranei al catalogo non vengono eliminati.
- Per un'analisi puntuale puoi usare `python3 ci/catalog_report.py --impact measure:qlikgpt_shared_revenue` oppure sostituire `measure` con `dimension` o `variable`.
- `ci/catalog_report.py` rigenera `catalog/USAGE.md` e `catalog/usage.json` nel workflow; il bot li committa con `[skip ci]`.
- Il report non significa che una dimensione referenziata tramite campo inline sia collegata come master dimension: evidenzia la migrazione eventuale.

## Utilizzo effettivo dei master item nei grafici e nei filtri

Tutte le visualizzazioni QlikGPT governate devono fare riferimento a misure e dimensioni **effettivamente esistenti come master item nativi** tramite `qLibraryId`. È vietato specificare campi di dimensione o formule di misura inline nelle ipercube delle Presentations: il validator CI controlla i riferimenti prima della distribuzione.

Anche i listbox `apps/presentation1-filters.json` utilizzano `dimensionId` (ID master dimension) e non duplicano più i nomi dei campi. Il deployment QIX assegna `qListObjectDef.qLibraryId` e verifica su Qlik Engine che il filtro abbia valori reali. Le proprietà locali di ordinamento dei grafici possono restare in configurazione, senza sostituire il master item.

Il report [Usage & Impact](USAGE.md) registra grafici **e filtri** che referenziano le dimensioni master; per le Presentation versionate non devono comparire avvisi di dimensioni inline. ETL1 ed ETL2 sono applicazioni di preparazione dati, senza fogli analitici da vincolare a master item.
