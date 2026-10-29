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

Le definizioni PBIP includono query, colonne, misure e relazioni. La cache locale dei dati non viene versionata: ogni nuova copia richiede il primo aggiornamento. Il report include la pagina interattiva **Sales Overview**, costruita sul mockup approvato.

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
- Categorie con barre di fatturato e margine percentuale; il margine piu alto tra le categorie selezionate e evidenziato in lime.
- Top 5 posizioni per fatturato tra le regioni selezionate; eventuali pari merito vengono mantenuti.
- Composizione del fatturato per segmento cliente, con quote e importi.
- Canali con fatturato e conteggio distinto degli ordini.

**Filtri:** periodo, categoria, regione e canale. Periodo iniziale: **01/01/2026–28/10/2026**. Il periodo si puo modificare; i confronti restano sugli stessi giorni dell anno precedente. I controlli dei filtri restano stabili quando si selezionano punti sui grafici.

**Campi aggiunti in Power Query:** Calendario[Month] per asse mese/anno ordinato cronologicamente e Clienti[OverviewGroup] per la barra della composizione clienti. Non occorre modificare gli Excel.

**Realizzazione:** visual nativi di Power BI, senza custom visual, dipendenze da immagini o servizi esterni. Il riquadro categorie usa una tabella con barre nei valori per mostrare fatturato e margine insieme. Etichette dei KPI e interfaccia in inglese; i campi del modello conservano i nomi italiani.

## Misure disponibili

- Fatturato Netto
- Costo Venduto
- Margine
- Margine %
- Quantita Venduta
- Numero Ordini
- Clienti Attivi
- Valore Medio Ordine

Le misure di base sono nella cartella **Indicatori** di Vendite. Sono state aggiunte 7 misure riutilizzabili per confronti e quote, oltre a 11 helper nascosti per il layout e la formattazione: 26 misure complessive. I campi tecnici e gli importi di riga sono nascosti per favorire l'uso delle misure. Per filtrare per data usare Calendario. Per anno precedente confrontare periodi equivalenti: il 2026 contiene vendite solo fino al 28 ottobre.

## Verifiche eseguite

- File XLSX riletti dopo l'esportazione: tabelle native, date tipizzate, nessuna formula o cella di errore.
- Chiavi univoche e nessuna vendita senza corrispondenza nelle tre dimensioni.
- Date continue e calendario esteso ad anni completi.
- Coerenza degli importi netti e dei costi delle righe.
- Definizioni deserializzate con il parser Microsoft TMDL: 4 tabelle, 3 relazioni, 26 misure.
- Pagina e 49 elementi PBIR controllati sugli schemi ufficiali Microsoft, sui nomi delle proprieta e sugli enum pubblici. I 20 elementi con query hanno riferimenti a colonne e misure esistenti.
- Dimensioni entro il canvas, identificativi univoci e destinazioni delle interazioni valide.
- Anteprima tecnica del layout controllata per spaziatura e leggibilita; non costituisce uno screenshot di Power BI.
- Apertura, calcolo DAX e rendering nel motore Power BI Desktop da verificare al primo avvio di questa versione. Su richiesta dell utente lo sviluppo e il versionamento avvengono esclusivamente sui file, senza controllare l app.

La copia locale aggiornata e nella cartella **Sales Overview**. Il file di apertura ha il nome univoco **Sales Overview.pbip** per distinguerlo dal precedente progetto vuoto. Aprire questo PBIP e premere **Aggiorna** anche se era gia stato aggiornato il precedente progetto vuoto.

Totali attesi dopo Aggiorna: **Fatturato Netto 7.064.517,86 EUR**, **Costo Venduto 4.200.892,86 EUR**, **Quantita Venduta 35.038**, **Numero Ordini 4.780**.


Per il periodo iniziale dell overview i valori attesi sono: **Fatturato Netto 2.225.634,04 EUR**, **Margine 905.533,75 EUR**, **Margine % 40,6866%**, **Numero Ordini 1.465**, **Quantita Venduta 10.797**. Il fatturato cresce del **12,7437%** rispetto al 01/01/2025–28/10/2025.
