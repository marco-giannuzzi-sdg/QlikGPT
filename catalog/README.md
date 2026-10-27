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
