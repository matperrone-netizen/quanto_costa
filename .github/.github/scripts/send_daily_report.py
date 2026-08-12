import json
import os
import smtplib
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Secret mancante: {name}")
    return value


def cloudflare_visits(token, zone_id):
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=23, minutes=55)
    query = """
      query($zoneTag: string, $start: Time, $end: Time) {
        viewer {
          zones(filter: { zoneTag: $zoneTag }) {
            httpRequestsAdaptiveGroups(
              limit: 1
              filter: { datetime_geq: $start, datetime_leq: $end }
            ) { count sum { visits edgeResponseBytes } }
          }
        }
      }
    """
    payload = json.dumps({"query": query, "variables": {
        "zoneTag": zone_id, "start": start.isoformat(), "end": end.isoformat()
    }}).encode()
    request = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(f"Cloudflare GraphQL: {result['errors']}")
    groups = result["data"]["viewer"]["zones"][0]["httpRequestsAdaptiveGroups"]
    if not groups:
        return 0, 0
    stats = groups[0]
    return int(stats.get("sum", {}).get("visits") or 0), int(stats.get("count") or 0)


def main():
    token = required("CLOUDFLARE_API_TOKEN")
    zone_id = required("CLOUDFLARE_ZONE_ID")
    password = required("GMAIL_APP_PASSWORD")
    recipient = required("REPORT_EMAIL")
    visits, requests = cloudflare_visits(token, zone_id)
    now = datetime.now(ZoneInfo("Europe/Rome"))
    subject = f"Costo Vero — report del {now:%d/%m/%Y}"
    body = f"""Ciao,

Report Costo Vero — ultime 24 ore circa

Visite Cloudflare: {visits}
Richieste HTTP: {requests}

Il sito è online su https://costo-vero.it.

Nota: questo primo report usa metriche aggregate Cloudflare. I conteggi di calcoli, confronti e condivisioni arriveranno nel report dopo l'attivazione del tracciamento anonimo dedicato.
"""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = recipient
    message["To"] = recipient
    message.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(recipient, password)
        server.send_message(message)


if __name__ == "__main__":
    main()
