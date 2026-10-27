# QlikGPT — App Lineage

Questa sezione contiene un lineage **tra applicazioni Qlik e artefatti dati QVD**, distinto dal catalogo semantico di misure, dimensioni e variabili.

## Pagine

- **[APP_LINEAGE.md](APP_LINEAGE.md)** — mappa Mermaid e tabelle per applicazione, QVD e impatti.
- **[graph.json](graph.json)** — grafo strutturato riutilizzabile per analisi e strumenti esterni.
- [Semantic Catalog](../catalog/USAGE.md) — misura/dimensione/variabile verso applicazione e visualizzazioni.

## Come vengono scoperte le dipendenze

Il generatore [ci/app_lineage.py](../ci/app_lineage.py) usa direttamente il registry di `ci/deploy.py`, i manifest `apps/presentationN.json`, gli ID registrati in `deployment/app-ids.json` e le istruzioni QVS. Quando un'app fa `STORE` su un URI e un'altra fa `FROM` sullo stesso URI, viene ricostruito un arco upstream → downstream. Se più app dichiarano di scrivere sullo stesso file, il controllo fallisce per evitare lineage ambiguo.

L'elaborazione produce le dipendenze dirette e quelle indirette (transitive), ad esempio ETL1 → ETL2 → entrambe le Presentation. Le nuove Presentation che leggono QVD già presenti verranno aggiunte automaticamente attraverso i manifest.

## Uso nella CI/CD

- `python3 ci/app_lineage.py`: rigenera Markdown e JSON (eseguito in GitHub Actions).
- `python3 ci/app_lineage.py --check`: verifica l'allineamento tra sorgenti e report.
- `python3 ci/app_lineage.py --app etl1`: elenco diretto e indiretto delle applicazioni dipendenti.

I report vengono salvati automaticamente dal bot nella branch `main`, con un commit `[skip ci]`. La sola creazione/aggiornamento del lineage non avvia un reload dati. Una modifica dei QVS è invece gestita dalle politiche di reload già esistenti.

## Limiti attuali

L'analisi è **statica**, non un'esportazione del lineage runtime Qlik Cloud. Percorsi di QVD costruiti tramite variabili, SQL/REST esterni, INCLUDE non censiti e oggetti creati fuori da GitHub richiedono integrazioni successive. La corrispondenza di due URI DataFiles non è sufficiente se app diverse usano spazi di Qlik Cloud isolati. Il grafo evidenzia l'impatto potenziale, non obbliga la sequenza o la schedulazione dei reload.
