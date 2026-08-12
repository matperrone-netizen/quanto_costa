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


def activity_counts(token, account_id):
    if not account_id:
        return None
    payload = """
      SELECT blob1 AS event, COUNT() AS total
      FROM costovero_activity
      WHERE timestamp > NOW() - INTERVAL '1' DAY
      GROUP BY event
      FORMAT JSON
    """.encode()
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(f"Cloudflare Analytics Engine: {result['errors']}")
    rows = result.get("data") or result.get("result") or []
    counts = {"calculation": 0, "comparison": 0, "share": 0, "checklist": 0}
    for row in rows:
        if row.get("event") in counts:
            counts[row["event"]] = int(row.get("total") or 0)
    return counts


def main():
    token = required("CLOUDFLARE_API_TOKEN")
    zone_id = required("CLOUDFLARE_ZONE_ID")
    password = required("GMAIL_APP_PASSWORD")
    recipient = required("REPORT_EMAIL")
    visits, requests = cloudflare_visits(token, zone_id)
    activities = activity_counts(token, os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip())
    now = datetime.now(ZoneInfo("Europe/Rome"))
    subject = f"Costo Vero — report del {now:%d/%m/%Y}"
    activity_section = "Tracciamento attività non ancora configurato."
    if activities is not None:
        activity_section = f"""Attività anonime nel sito:
- Calcoli: {activities['calculation']}
- Confronti: {activities['comparison']}
- Condivisioni: {activities['share']}
- Checklist copiate: {activities['checklist']}"""
    body = f"""Ciao,

Report Costo Vero — ultime 24 ore circa

Visite Cloudflare: {visits}
Richieste HTTP: {requests}

{activity_section}

Il sito è online su https://costo-vero.it.
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
