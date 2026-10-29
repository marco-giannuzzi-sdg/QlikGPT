# AI-Assisted Power BI Development

Progetto dimostrativo per costruire un report Power BI con assistenza AI e versionamento GitHub. Tutti i dati sono sintetici.

## Apertura

1. Aprire **AI-Assisted Power BI Development.pbip** in Power BI Desktop.
2. Se il progetto viene spostato o clonato in un altro percorso, impostare il parametro Power Query **DataFolder** sulla cartella locale **data**, con una barra finale. Dal menu **Trasforma dati > Modifica parametri**, modificare DataFolder e applicare.
3. Premere **Aggiorna** per importare i quattro Excel.

Il valore iniziale di DataFolder punta alla copia locale creata su questo computer:

```text
C:/Users/marco/Documents/Codex/2026-10-29/all/outputs/AI-Assisted Power BI Development/data/
```

Le definizioni PBIP includono query, colonne, misure e relazioni. La cache locale dei dati non viene versionata: ogni nuova copia richiede il primo aggiornamento. Il report mantiene la pagina vuota per la successiva fase di mockup.

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

## Misure disponibili

- Fatturato Netto
- Costo Venduto
- Margine
- Margine %
- Quantita Venduta
- Numero Ordini
- Clienti Attivi
- Valore Medio Ordine

Le misure sono nella cartella **Indicatori** di Vendite. I campi tecnici e gli importi di riga sono nascosti per favorire l'uso delle misure. Per filtrare per data usare Calendario. Per anno precedente confrontare periodi equivalenti: il 2026 contiene vendite solo fino al 28 ottobre.

## Verifiche eseguite

- File XLSX riletti dopo l'esportazione: tabelle native, date tipizzate, nessuna formula o cella di errore.
- Chiavi univoche e nessuna vendita senza corrispondenza nelle tre dimensioni.
- Date continue e calendario esteso ad anni completi.
- Coerenza degli importi netti e dei costi delle righe.
- Definizioni deserializzate con il parser Microsoft TMDL: 4 tabelle, 3 relazioni, 8 misure.
- Importazione e calcolo DAX nel motore Power BI Desktop ancora da verificare: l'approvazione automatica dell'ambiente ha negato il controllo dell'app.

Totali attesi dopo Aggiorna: **Fatturato Netto 7.064.517,86 EUR**, **Costo Venduto 4.200.892,86 EUR**, **Quantita Venduta 35.038**, **Numero Ordini 4.780**.
