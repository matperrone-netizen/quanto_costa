import csv, html, json, os, re, smtplib, ssl, subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "catalog-monthly-report.md"
CSV_PATH = ROOT / "catalog-monthly-review.csv"

def parse_number(value):
    digits = re.sub(r"\D", "", value or "")
    return int(digits) if digits else None


def extract_terms(text):
    patterns = {
        "payment": r"rata mensile\s*€?\s*([\d.\s]+?)(?=\s*(?:iva|km/anno))",
        "contractKm": r"km/anno\s*([\d.\s]+?)(?=\s*durata)",
        "months": r"durata\s*(\d+)\s*mesi",
        "downPayment": r"anticipo\s*€?\s*([\d.\s]+?)(?=\s*(?:iva|dimensioni|$))",
    }
    terms = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.I)
        terms[field] = parse_number(match.group(1)) if match else None
    return terms

def fetch_text(url):
    result = subprocess.run(["curl", "--location", "--fail", "--silent", "--show-error", "--compressed",
        "--max-time", "35", "--user-agent", "Mozilla/5.0", url], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    raw = result.stdout.decode("utf-8", errors="replace")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).lower()

def inspect_offer(offer):
    result = {"id": offer.get("id", "senza-id"), "title": offer.get("title", "Offerta senza nome"),
        **{key: offer.get(key, "") for key in ("payment", "months", "downPayment", "contractKm", "sourceUrl")}}
    try:
        text = fetch_text(offer["sourceUrl"])
    except (RuntimeError, TimeoutError, KeyError) as error:
        return result | {"state": "errore", "detail": f"Fonte non raggiungibile: {type(error).__name__}."}
    source_terms = extract_terms(text)
    labels = {"payment": "rata", "months": "durata", "downPayment": "anticipo", "contractKm": "km/anno"}
    unreadable = [labels[key] for key, value in source_terms.items() if value is None]
    if unreadable:
        return result | {"state": "da_rivedere", "detail": "Impossibile leggere dalla sezione condizioni: " + ", ".join(unreadable) + "."}
    changed = [
        f"{labels[key]} {offer.get(key)} → {source_terms[key]}"
        for key in source_terms if int(offer.get(key, 0)) != source_terms[key]
    ]
    if changed:
        return result | {"state": "da_rivedere", "detail": "Valori cambiati nella fonte: " + "; ".join(changed) + "."}
    return result | {"state": "coerente", "detail": "Rata, durata, anticipo e km ancora visibili nella fonte."}

def write_report(results, catalog_date):
    review = [item for item in results if item["state"] != "coerente"]
    lines = [f"# Controllo mensile catalogo — {date.today():%d/%m/%Y}", "",
        f"Catalogo dichiarato aggiornato al: **{catalog_date or 'non indicato'}**.",
        f"Offerte controllate: **{len(results)}** · coerenti: **{len(results)-len(review)}** · da rivedere: **{len(review)}**.", "",
        "> Il controllo cerca nella fonte i valori già registrati. Non aggiorna né pubblica automaticamente prezzi.", "", "## Offerte da rivedere", ""]
    if review:
        lines += [f"- **[{i['title']}]({i['sourceUrl']})** — {i['detail']} Valori registrati: {i['payment']} €/mese, "
            f"{i['months']} mesi, anticipo {i['downPayment']} €, {i['contractKm']} km." for i in review]
    else:
        lines.append("- Nessuna anomalia rilevata.")
    lines += ["", "## Tutti i controlli", ""]
    lines += [f"- [{i['title']}]({i['sourceUrl']}): **{i['state']}** — {i['detail']}" for i in results]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review

def write_csv(results):
    fields = ["id", "title", "payment", "months", "downPayment", "contractKm", "checkedAtISO", "sourceUrl", "esito_controllo", "azione", "note"]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";"); writer.writeheader()
        for item in results:
            writer.writerow({**{key: item.get(key, "") for key in fields}, "checkedAtISO": date.today().isoformat(),
                "esito_controllo": item["state"], "azione": "VERIFICARE" if item["state"] != "coerente" else "NESSUNA", "note": item["detail"]})

def send_mail(review, issue_url):
    recipient, password = os.environ.get("REPORT_EMAIL", "").strip(), os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not recipient or not password: raise RuntimeError("GMAIL_APP_PASSWORD o REPORT_EMAIL mancante")
    status = "tutto coerente" if not review else f"{len(review)} offerte da rivedere"
    message = EmailMessage(); message["Subject"] = f"Costo Vero — controllo catalogo {datetime.now(ZoneInfo('Europe/Rome')):%d/%m/%Y}"
    message["From"] = message["To"] = recipient
    message.set_content(f"Ciao,\n\nil controllo mensile del catalogo Costo Vero è terminato: {status}.\n\nApri il riepilogo su GitHub:\n{issue_url or 'Consulta gli artifact del workflow.'}\n\nIl controllo non modifica automaticamente le offerte: serve la revisione prima della pubblicazione.\n")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(recipient, password); server.send_message(message)

def main():
    catalog = json.loads((ROOT / "offers.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=5) as pool: results = list(pool.map(inspect_offer, catalog.get("offers", [])))
    review = write_report(results, catalog.get("updatedAt")); write_csv(results)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output: output.write(f"review_count={len(review)}\n")
    print(REPORT_PATH.read_text(encoding="utf-8"))

if __name__ == "__main__": main()
