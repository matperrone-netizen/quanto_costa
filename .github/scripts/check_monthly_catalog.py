import html
import json
import os
import re
import smtplib
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "catalog-monthly-report.md"


def compact_text(raw):
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).lower()


def variants(number):
    number = int(number or 0)
    if not number:
        return []
    return {str(number), f"{number:,}".replace(",", "."), f"{number:,}".replace(",", " ")}


def contains_any(text, values):
    return any(value in text for value in values)


def fetch_text(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; CostoVeroCatalogMonitor/1.0; +https://costo-vero.it/chi-siamo)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.status, compact_text(response.read().decode("utf-8", errors="replace"))


def inspect_offer(offer):
    result = {"id": offer.get("id", "senza-id"), "title": offer.get("title", "Offerta senza nome")}
    try:
        status, text = fetch_text(offer["sourceUrl"])
        result["http"] = status
    except urllib.error.HTTPError as error:
        result.update(state="errore", detail=f"Fonte non raggiungibile: HTTP {error.code}.")
        return result
    except (urllib.error.URLError, TimeoutError, KeyError) as error:
        result.update(state="errore", detail=f"Fonte non raggiungibile: {type(error).__name__}.")
        return result

    checks = {
        "rata": contains_any(text, variants(offer.get("payment"))),
        "durata": contains_any(text, variants(offer.get("months"))),
        "anticipo": offer.get("downPayment", 0) == 0 or contains_any(text, variants(offer.get("downPayment"))),
        "km": contains_any(text, variants(offer.get("contractKm"))),
    }
    missing = [name for name, found in checks.items() if not found]
    if not missing:
        result.update(state="coerente", detail="Rata, durata, anticipo e km ancora visibili nella fonte.")
    else:
        result.update(state="da_rivedere", detail="Non trovati nella pagina: " + ", ".join(missing) + ".")
    return result


def write_report(results, catalog_date):
    review = [item for item in results if item["state"] != "coerente"]
    lines = [
        f"# Controllo mensile catalogo — {date.today():%d/%m/%Y}", "",
        f"Catalogo dichiarato aggiornato al: **{catalog_date or 'non indicato'}**.",
        f"Offerte controllate: **{len(results)}** · coerenti: **{len(results) - len(review)}** · da rivedere: **{len(review)}**.", "",
        "> Il controllo cerca nella fonte i valori già registrati. Non aggiorna né pubblica automaticamente prezzi.", "",
        "## Offerte da rivedere", "",
    ]
    if review:
        lines.extend(f"- **{item['title']}** — {item['detail']}" for item in review)
    else:
        lines.append("- Nessuna anomalia rilevata.")
    lines.extend(["", "## Tutti i controlli", ""])
    lines.extend(f"- {item['title']}: **{item['state']}** — {item['detail']}" for item in results)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review


def send_mail(review, issue_url):
    recipient = os.environ.get("REPORT_EMAIL", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not recipient or not password:
        raise RuntimeError("GMAIL_APP_PASSWORD o REPORT_EMAIL mancante")
    status = "tutto coerente" if not review else f"{len(review)} offerte da rivedere"
    body = f"""Ciao,

il controllo mensile del catalogo Costo Vero è terminato: {status}.

Apri il riepilogo su GitHub:
{issue_url or 'Issue non disponibile; consulta gli artifact del workflow.'}

Il controllo non modifica automaticamente le offerte: serve la revisione prima della pubblicazione.
"""
    message = EmailMessage()
    message["Subject"] = f"Costo Vero — controllo catalogo {datetime.now(ZoneInfo('Europe/Rome')):%d/%m/%Y}"
    message["From"] = recipient
    message["To"] = recipient
    message.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(recipient, password)
        server.send_message(message)


def main():
    catalog = json.loads((ROOT / "offers.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(inspect_offer, catalog.get("offers", [])))
    review = write_report(results, catalog.get("updatedAt"))
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"review_count={len(review)}\n")
    print(REPORT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
