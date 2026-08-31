# Costovero

Prototipo statico di **Quanto costa veramente?**: un calcolatore italiano che aiuta a confrontare acquisto finanziato e noleggio di un'auto, andando oltre la sola rata mensile.

## Cosa fa oggi

- calcola il costo mensile realistico a partire da rata, durata, anticipo e maxi rata;
- stima carburante/energia dai chilometri annui, alimentazione e segmento dell'auto;
- include i costi ricorrenti principali e separa chiaramente anticipo e maxi rata;
- confronta due proposte, oppure una proposta con una voce del piccolo catalogo statico;
- include contenuti introduttivi e FAQ indicizzabili.

## Struttura

- `index.html` — pagina, form, contenuti SEO e dati strutturati;
- `styles.css` — interfaccia responsive;
- `app.js` — calcoli, confronto e catalogo statico dimostrativo;
- `robots.txt` — istruzioni per i crawler.

Non richiede build, database o dipendenze: basta pubblicare questi file come sito statico.

## Aggiornare le offerte senza database

Il catalogo è nel file `offers.json`, caricato dal browser. È un archivio a cui la ricerca per marca e modello attinge: ogni voce ha un `id`, `brand`, `model`, `aliases` (es. “Peugeot 2008” e “2008”), oltre a rata, durata, versamento iniziale, eventuale maxi rata, km e servizi nelle `conditions`, fonte, URL, data leggibile (`checkedAt`) e data tecnica (`checkedAtISO`). Se esistono sconti o rottamazione, vanno dichiarati esplicitamente nelle condizioni: non devono sembrare disponibili per tutti.

Il flusso MVP è volutamente semplice: una revisione mensile delle fonti autorizzate, aggiornamento di `offers.json`, poi pubblicazione con `publish-seo.ps1`. Il sito resta statico, veloce e senza costi di database.

Prima della pubblicazione, `catalog-check.ps1` controlla automaticamente i campi obbligatori e segnala offerte non verificate da oltre 45 giorni. Per il primo catalogo conviene usare poche offerte complete provenienti da pagine ufficiali o fonti che ne consentono la consultazione, non uno scraping indiscriminato di siti terzi.

`site-check.ps1` verifica inoltre tutte le pagine HTML prima del deploy: title, description, canonical, H1, JSON-LD, corrispondenza con la sitemap e collegamenti interni. `publish-seo.ps1` esegue entrambi i controlli e include automaticamente ogni file HTML, evitando che una nuova guida resti esclusa dalla pubblicazione.

Per eseguire i controlli locali su Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\site-check.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\catalog-check.ps1
```

## Report quotidiano

Il workflow `.github/workflows/daily-report.yml` invia alle 20:00 ora italiana un report delle metriche aggregate Cloudflare. I secret `GMAIL_APP_PASSWORD`, `CLOUDFLARE_ANALYTICS_TOKEN` e `CLOUDFLARE_ZONE_ID` vanno inseriti solo nella sezione GitHub Secrets: non devono mai finire nei file del repository.

La Pages Function `functions/api/activity.js` registra solo quattro eventi anonimi aggregati: calcolo, confronto, condivisione e checklist. Non riceve né salva importi, modello, IP, email o identificativi dell'utente. Per riportarli nell'email, il workflow usa anche il secret `CLOUDFLARE_ACCOUNT_ID` e un token con `Account Analytics: Read`.

## Sviluppi previsti

1. collegare il repository a Cloudflare Pages;
2. acquistare e collegare un dominio breve `.it`;
3. aggiornare mensilmente il catalogo di offerte e le condizioni;
4. aggiungere guide editoriali utili e, dopo la validazione, altri verticali (casa, mutuo, figlio).

Le stime sono orientative e non sostituiscono il preventivo del concessionario o del fornitore.
