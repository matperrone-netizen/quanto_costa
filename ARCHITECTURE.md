# Architettura delle future pagine SEO

Il sito è statico: i contenuti essenziali sono presenti nell'HTML inviato al crawler e i calcolatori aggiungono solo l'interazione nel browser. Le nuove pagine non richiedono un CMS.

## Convenzione URL

Per un nuovo verticale, creare un file HTML dentro la relativa cartella usando il nome finale della pagina:

- `auto/quanto-costa-mantenere-auto.html` → `/auto/quanto-costa-mantenere-auto`
- `casa/quanto-mutuo-posso-permettermi.html` → `/casa/quanto-mutuo-posso-permettermi`
- `famiglia/quanto-costa-un-figlio.html` → `/famiglia/quanto-costa-un-figlio`

Ogni pagina pubblica deve avere un solo `h1`, meta description, canonical assoluta, `robots` con `index,follow`, Open Graph e HTML semantico. Se una categoria avrà una pagina hub, usare `categoria/index.html` e canonical `https://costo-vero.it/categoria/`.

`update-sitemap.ps1` include automaticamente tutte le pagine HTML pubbliche, anche nelle sottocartelle, escludendo soltanto `404.html`. `site-check.ps1` deve restare parte della pubblicazione per intercettare metadata, canonical e link non validi.
