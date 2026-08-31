import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
PROPERTY = os.environ.get("SEARCH_CONSOLE_PROPERTY", "sc-domain:costo-vero.it")


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Secret mancante: {name}")
    return value


def access_token():
    try:
        info = json.loads(required("GOOGLE_SEARCH_CONSOLE_CREDENTIALS"))
    except json.JSONDecodeError as error:
        raise RuntimeError("GOOGLE_SEARCH_CONSOLE_CREDENTIALS non contiene JSON valido") from error
    credentials = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
    credentials.refresh(Request())
    return credentials.token


def query(token, start, end, dimensions=None, limit=10):
    site = urllib.parse.quote(PROPERTY, safe="")
    payload = {"startDate": start.isoformat(), "endDate": end.isoformat(), "type": "web"}
    if dimensions:
        payload.update({"dimensions": dimensions, "rowLimit": limit})
    request = urllib.request.Request(
        f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response).get("rows", [])


def totals(rows):
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    row = rows[0]
    return {key: float(row.get(key, 0)) for key in ("clicks", "impressions", "ctr", "position")}


def change(current, previous, key):
    old, new = previous[key], current[key]
    if not old:
        return "nuovo" if new else "0%"
    return f"{((new-old)/old)*100:+.1f}%".replace(".", ",")


def decimal(value, digits=1):
    return f"{value:.{digits}f}".replace(".", ",")


def format_rows(rows, kind):
    if not rows:
        return "- Nessun dato disponibile nel periodo."
    lines = []
    for row in rows:
        label = row.get("keys", ["-"])[0]
        if kind == "page":
            label = label.replace("https://costo-vero.it", "") or "/"
        lines.append(
            f"- {label} — {int(row.get('clicks', 0))} clic · {int(row.get('impressions', 0))} impression · "
            f"CTR {decimal(row.get('ctr', 0)*100)}% · posizione {decimal(row.get('position', 0))}"
        )
    return "\n".join(lines)


def main():
    token = access_token()
    # Search Console dichiara normalmente i dati completi con alcuni giorni di ritardo.
    current_end = date.today() - timedelta(days=3)
    current_start = current_end - timedelta(days=27)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=27)
    current = totals(query(token, current_start, current_end))
    previous = totals(query(token, previous_start, previous_end))
    queries = query(token, current_start, current_end, ["query"], 10)
    pages = query(token, current_start, current_end, ["page"], 10)

    recipient = required("REPORT_EMAIL")
    password = required("GMAIL_APP_PASSWORD")
    now = datetime.now(ZoneInfo("Europe/Rome"))
    body = f"""Ciao,

Report SEO settimanale Costo Vero
Periodo: {current_start:%d/%m/%Y}–{current_end:%d/%m/%Y}, confrontato con i 28 giorni precedenti.

RISULTATO GENERALE
- Clic: {int(current['clicks'])} ({change(current, previous, 'clicks')})
- Impression: {int(current['impressions'])} ({change(current, previous, 'impressions')})
- CTR: {decimal(current['ctr']*100)}% (prima {decimal(previous['ctr']*100)}%)
- Posizione media: {decimal(current['position'])} (prima {decimal(previous['position'])})

QUERY PRINCIPALI
{format_rows(queries, 'query')}

PAGINE PRINCIPALI
{format_rows(pages, 'page')}

Come leggerlo: più impression indicano maggiore visibilità; CTR e posizione aiutano a capire quali pagine migliorare. Search Console può omettere query rare o anonimizzate.

Sito: https://costo-vero.it
"""
    message = EmailMessage()
    message["Subject"] = f"Costo Vero — report SEO del {now:%d/%m/%Y}"
    message["From"] = message["To"] = recipient
    message.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(recipient, password)
        server.send_message(message)


if __name__ == "__main__":
    main()
