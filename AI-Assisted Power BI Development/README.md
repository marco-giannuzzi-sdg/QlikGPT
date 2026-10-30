# AI-Assisted Power BI Development

Progetto dimostrativo per costruire un report Power BI con assistenza AI e versionamento GitHub. Tutti i dati sono sintetici.

## Apertura

1. Aprire **Sales Overview.pbip** in Power BI Desktop.
2. Se il progetto viene spostato o clonato in un altro percorso, impostare il parametro Power Query **DataFolder** sulla cartella locale **data**, con una barra finale. Dal menu **Trasforma dati > Modifica parametri**, modificare DataFolder e applicare.
3. Premere **Aggiorna** per importare i quattro Excel.

Il valore iniziale di DataFolder punta alla copia locale creata su questo computer:

```text
C:/Users/marco/Documents/Codex/2026-10-29/all/outputs/Sales Overview/data/
```

Le definizioni PBIP includono query, colonne, misure e relazioni. La cache locale dei dati non viene versionata: ogni nuova copia richiede il primo aggiornamento. Il report include due pagine interattive: **Sales Overview** e **Products & Margin**, costruite sui mockup approvati. All apertura viene selezionato Products & Margin.

## Dati Excel

Ogni file contiene una tabella Excel nativa con lo stesso nome del file.

| File | Righe | Contenuto |
| --- | ---: | --- |
| data/Vendite.xlsx | 9.559 | Righe d'ordine dal 01/01/2024 al 28/10/2026 |
| data/Prodotti.xlsx | 48 | Prodotti, categorie, marche, prezzi e costi di listino |
| data/Clienti.xlsx | 240 | Clienti dimostrativi, segmenti e territori italiani |
| data/Calendario.xlsx | 1.096 | Tutti i giorni dal 01/01/2024 al 31/12/2026 |

**Granularita Vendite:** una riga rappresenta un prodotto in un ordine; un ordine puo avere piu righe. VenditaID identifica la riga, OrdineID identifica l'ordine. Importi in EUR, IVA esclusa. ImportoNetto = Quantita × PrezzoUnitario × (1 − ScontoPercentuale), arrotondato a due decimali. CostoTotale = Quantita × CostoUnitario. I prezzi e costi delle vendite sono storici; i valori in Prodotti sono di listino.

## Relazioni

| Lato uno | Lato molti | Filtro | Stato |
| --- | --- | --- | --- |
| Prodotti[ProdottoID] | Vendite[ProdottoID] | Prodotti → Vendite | Attiva |
| Clienti[ClienteID] | Vendite[ClienteID] | Clienti → Vendite | Attiva |
| Calendario[Data] | Vendite[DataVendita] | Calendario → Vendite | Attiva |

Schema a stella, senza filtri bidirezionali. Chiavi prodotto e cliente intere; date senza componente oraria. Calendario e marcato come tabella data, con Data univoca e continua. Mesi, anno-mese e giorni della settimana hanno ordinamento numerico. La data/ora automatica e disattivata a livello di modello.

## Sales Overview

Pagina 1920 × 1080 con testata blu notte, fondo chiaro, grafici teal e accenti lime. Tutti i valori sono collegati al modello: nessun KPI e una scritta statica o un immagine del mockup.

- Quattro KPI: Net Revenue, Gross Margin, Orders e Units Sold; confronto anno precedente e margine assoluto.
- Andamento mensile con linea del periodo selezionato e del periodo equivalente dell anno precedente.
- Categorie con barre di fatturato e margine percentuale.
- Top 5 posizioni per fatturato tra le regioni selezionate; eventuali pari merito vengono mantenuti.
- Composizione del fatturato per segmento cliente, con quote e importi.
- Canali con fatturato e conteggio distinto degli ordini.

**Filtri:** periodo, categoria, regione e canale. Periodo iniziale: **01/01/2026–28/10/2026**. Il periodo si puo modificare; i confronti restano sugli stessi giorni dell anno precedente. I controlli dei filtri restano stabili quando si selezionano punti sui grafici.

**Campi aggiunti in Power Query:** Calendario[Month] per asse mese/anno ordinato cronologicamente e Clienti[OverviewGroup] per la barra della composizione clienti. Non occorre modificare gli Excel.

**Realizzazione:** visual nativi di Power BI, senza custom visual, dipendenze da immagini o servizi esterni. I riquadri categorie, segmenti e canali usano matrici native con campi di raggruppamento espliciti. Le barre di fatturato sono separate dal testo degli importi per ottenere formati compatti come EUR 664.6K, indipendenti dalle unita automatiche del client. Etichette dei KPI e interfaccia in inglese; i campi del modello conservano i nomi italiani.

## Misure disponibili

- Fatturato Netto
- Costo Venduto
- Margine
- Margine %
- Quantita Venduta
- Numero Ordini
- Clienti Attivi
- Valore Medio Ordine

Le misure di base sono nella cartella **Indicatori** di Vendite. Il modello contiene 41 misure: 8 di base, 18 per la Sales Overview e 15 per Products & Margin. Due delle nuove misure sono riutilizzabili (Prodotti Venduti e Quota Fatturato Top 5 Prodotti); le altre supportano il layout e le analisi. I campi tecnici e gli importi di riga sono nascosti per favorire l'uso delle misure. Per filtrare per data usare Calendario. Per anno precedente confrontare periodi equivalenti: il 2026 contiene vendite solo fino al 28 ottobre.

## Verifiche eseguite

- File XLSX riletti dopo l'esportazione: tabelle native, date tipizzate, nessuna formula o cella di errore.
- Chiavi univoche e nessuna vendita senza corrispondenza nelle tre dimensioni.
- Date continue e calendario esteso ad anni completi.
- Coerenza degli importi netti e dei costi delle righe.
- Definizioni deserializzate con il parser Microsoft TMDL: 4 tabelle, 3 relazioni, 41 misure.
- Pagina e 49 elementi PBIR controllati sugli schemi ufficiali Microsoft, sui nomi delle proprieta e sugli enum pubblici. I 20 elementi con query hanno riferimenti a colonne e misure esistenti.
- Dimensioni entro il canvas, identificativi univoci e destinazioni delle interazioni valide.
- Anteprima tecnica del layout controllata per spaziatura e leggibilita; non costituisce uno screenshot di Power BI.
- Apertura, calcolo DAX e rendering nel motore Power BI Desktop da verificare al primo avvio di questa versione. Su richiesta dell utente lo sviluppo e il versionamento avvengono esclusivamente sui file, senza controllare l app.

La copia locale aggiornata e nella cartella **Sales Overview**. Il file di apertura ha il nome univoco **Sales Overview.pbip** per distinguerlo dal precedente progetto vuoto. Aprire questo PBIP e premere **Aggiorna** anche se era gia stato aggiornato il precedente progetto vuoto.

Totali attesi dopo Aggiorna: **Fatturato Netto 7.064.517,86 EUR**, **Costo Venduto 4.200.892,86 EUR**, **Quantita Venduta 35.038**, **Numero Ordini 4.780**.


Per il periodo iniziale dell overview i valori attesi sono: **Fatturato Netto 2.225.634,04 EUR**, **Margine 905.533,75 EUR**, **Margine % 40,6866%**, **Numero Ordini 1.465**, **Quantita Venduta 10.797**. Il fatturato cresce del **12,7437%** rispetto al 01/01/2025–28/10/2025.


## Revisione stile v2

- Riempimenti e contorni delle 11 forme con selettore nativo `id: default`: testata e card fatturato blu notte, riquadri bianchi e linea lime.
- Dimensioni dei testi statici espresse in pixel, con altezze maggiorate per evitare tagli e scrollbar nei titoli.
- Matrici native al posto dei tre TableEx. Il client October 2026 aveva segnalato un errore di tooltip in `TableExInteractionManager.getGroupingTooltipInfo`; i tooltip dei riquadri sono disattivati.
- Larghezza fissa di ogni colonna e righe compatte, con spazio verificato per tre elementi.
- Zoom dei grafici disattivato e spazio tra titolo e area dati esplicito.
- Filtri data ad alto contrasto; intervallo iniziale letto da `general.filter` senza estremi duplicati come stringhe.
- Modello semantico, Excel e misure di business invariati.

Per applicare questa revisione, chiudere il report attualmente aperto **senza salvare** e riaprire **lo stesso Sales Overview.pbip**. Aggiornare i dati se richiesto. Non salvare la vecchia sessione sopra le definizioni aggiornate. La revisione e stata controllata sui file e su una composizione tecnica; il rendering nativo aggiornato va verificato in Power BI.


## Products & Margin

Secondo foglio con la stessa palette, tipografia e correzioni di stile della Sales Overview.

- Quattro KPI: Gross Profit, Active Products, Gross Margin, Top 5 Revenue Share.
- Mappa nativa dei prodotti: X = fatturato netto; Y = margine percentuale; dimensione = quantita venduta; colore = categoria. Tutti i prodotti con vendite sono rappresentati. Nomi e dettagli sono disponibili nei tooltip, per evitare sovrapposizioni tra le etichette.
- Linee di riferimento dinamiche: fatturato medio per prodotto attivo e margine ponderato del portafoglio selezionato.
- Top 5 prodotti per margine assoluto, con indicazione della percentuale di margine.
- Dettaglio dei Top 5 per fatturato: prodotto, categoria, fatturato, margine assoluto, margine percentuale e unita vendute. Matrice nativa con sei colonne a larghezza esplicita e tooltip disattivati.
- Confronto del margine percentuale delle categorie, con margine assoluto nelle etichette.

**Filtri:** periodo, categoria, marca e canale. Periodo, categoria e canale sono sincronizzati con la prima pagina; marca rimane specifica di Products & Margin. Le classifiche risolvono gli eventuali pari merito usando ProdottoID e includono al massimo cinque prodotti. Il margine ponderato e il rapporto tra i totali, non la media delle percentuali dei prodotti.

**Controlli:** parser Microsoft TMDL; schemi e proprieta PBIR; riferimenti di colonne e misure; selettori delle forme; ingombri dei testi; sei colonne e cinque righe della matrice; collegamenti e sincronizzazione delle due pagine. I valori iniziali sono stati ricalcolati indipendentemente dagli Excel esportati.

Valori attesi per 01/01/2026–28/10/2026: margine lordo **905.533,75 EUR**, prodotti attivi **48**, margine **40,6866%**, quota fatturato Top 5 **42,9505%**, fatturato medio per prodotto **46.367,38 EUR**. Notebook Premium guida il margine assoluto con **92.071,71 EUR**.

La pagina Products & Margin e selezionata in apertura. Per caricare le nuove definizioni, chiudere la sessione precedente senza salvare, riaprire **Sales Overview.pbip** e premere **Aggiorna**. Il progetto e stato modificato esclusivamente tramite file e GitHub; l esecuzione DAX e la resa nativa di questa nuova pagina rimangono da verificare in Power BI dopo la riapertura.
