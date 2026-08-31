import json
import os
import re
import smtplib
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
PROPERTY = os.environ.get("SEARCH_CONSOLE_PROPERTY", "sc-domain:costo-vero.it")
USER_AGENT = "Mozilla/5.0 (compatible; CostoVeroSEOMonitor/1.0; +https://costo-vero.it)"


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Secret mancante: {name}")
    return value


def access_token():
    raw = os.environ.get("GOOGLE_SEARCH_CONSOLE_CREDENTIALS", "").strip()
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("GOOGLE_SEARCH_CONSOLE_CREDENTIALS non contiene JSON valido") from error
    credentials = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
    credentials.refresh(Request())
    return credentials.token


def inspect_public_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except Exception as error:
        return f"{url} — non raggiungibile ({type(error).__name__})"
    if status != 200:
        return f"{url} — HTTP {status}"
    canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', body, re.I)
    if not canonical:
        canonical = re.search(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', body, re.I)
    if not canonical:
        return f"{url} — canonical mancante"
    expected = url.rstrip("/") or "https://costo-vero.it"
    if canonical.group(1).rstrip("/") != expected:
        return f"{url} — canonical diverso: {canonical.group(1)}"
    if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', body, re.I):
        return f"{url} — noindex inatteso"
    return None


def technical_health():
    sitemap_request = urllib.request.Request("https://costo-vero.it/sitemap.xml", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(sitemap_request, timeout=20) as response:
        root = ET.fromstring(response.read())
    urls = [node.text for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        errors = [error for error in pool.map(inspect_public_page, urls) if error]
    return len(urls), errors


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
    checked_urls, technical_errors = technical_health()
    if token:
        current = totals(query(token, current_start, current_end))
        previous = totals(query(token, previous_start, previous_end))
        queries = query(token, current_start, current_end, ["query"], 10)
        pages = query(token, current_start, current_end, ["page"], 10)
        search_section = f"""RISULTATO SEARCH CONSOLE
- Clic: {int(current['clicks'])} ({change(current, previous, 'clicks')})
- Impression: {int(current['impressions'])} ({change(current, previous, 'impressions')})
- CTR: {decimal(current['ctr']*100)}% (prima {decimal(previous['ctr']*100)}%)
- Posizione media: {decimal(current['position'])} (prima {decimal(previous['position'])})

QUERY PRINCIPALI
{format_rows(queries, 'query')}

PAGINE PRINCIPALI
{format_rows(pages, 'page')}"""
    else:
        search_section = "SEARCH CONSOLE\n- Collegamento non ancora configurato: il controllo tecnico è comunque attivo."
    health_section = f"CONTROLLO TECNICO\n- URL sitemap controllati: {checked_urls}\n- Errori: {len(technical_errors)}"
    if technical_errors:
        health_section += "\n- " + "\n- ".join(technical_errors[:20])

    recipient = required("REPORT_EMAIL")
    password = required("GMAIL_APP_PASSWORD")
    now = datetime.now(ZoneInfo("Europe/Rome"))
    body = f"""Ciao,

Report SEO settimanale Costo Vero
Periodo: {current_start:%d/%m/%Y}–{current_end:%d/%m/%Y}, confrontato con i 28 giorni precedenti.

{health_section}

{search_section}

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
