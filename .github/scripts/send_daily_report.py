import json
import os
import smtplib
import ssl
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
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
    counts = {"calculation": 0, "comparison": 0, "share": 0, "checklist": 0, "fuel_calculation": 0, "mortgage_calculation": 0, "child_cost_calculation": 0}
    for row in rows:
        if row.get("event") in counts:
            counts[row["event"]] = int(row.get("total") or 0)
    return counts


def catalog_status():
    catalog_path = Path(__file__).resolve().parents[2] / "offers.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    offers = catalog.get("offers", [])
    today = date.today()
    stale, invalid, checked_dates = [], [], []
    for offer in offers:
        label = offer.get("title") or offer.get("id") or "Offerta senza nome"
        if not offer.get("sourceUrl", "").startswith("https://"):
            invalid.append(label)
        try:
            checked_date = date.fromisoformat(offer.get("checkedAtISO", ""))
            checked_dates.append(checked_date)
            if (today - checked_date).days > 35:
                stale.append(label)
        except ValueError:
            invalid.append(label)
    oldest = min(checked_dates).strftime("%d/%m/%Y") if checked_dates else "non disponibile"
    return {"total": len(offers), "oldest": oldest, "stale": stale, "invalid": invalid}


def main():
    token = required("CLOUDFLARE_API_TOKEN")
    zone_id = required("CLOUDFLARE_ZONE_ID")
    password = required("GMAIL_APP_PASSWORD")
    recipient = required("REPORT_EMAIL")
    warnings = []
    try:
        visits, requests = cloudflare_visits(token, zone_id)
        traffic_section = f"Visite Cloudflare: {visits}\nRichieste HTTP: {requests}"
    except Exception as error:
        traffic_section = "Visite e richieste: dati temporaneamente non disponibili."
        warnings.append(f"Traffico Cloudflare: {type(error).__name__}: {error}")
    try:
        activities = activity_counts(token, os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip())
    except Exception as error:
        activities = None
        warnings.append(f"Attività anonime: {type(error).__name__}: {error}")
    catalog = catalog_status()
    now = datetime.now(ZoneInfo("Europe/Rome"))
    subject = f"Costo Vero — report del {now:%d/%m/%Y}"
    activity_section = "Tracciamento attività non ancora configurato."
    if activities is not None:
        activity_section = f"""Attività anonime nel sito:
- Calcoli: {activities['calculation']}
- Calcoli carburante: {activities['fuel_calculation']}
- Calcoli mutuo: {activities['mortgage_calculation']}
- Piani costo bambino: {activities['child_cost_calculation']}
- Confronti: {activities['comparison']}
- Condivisioni: {activities['share']}
- Checklist copiate: {activities['checklist']}"""
    catalog_section = f"Catalogo offerte: {catalog['total']} offerte · verifica più vecchia: {catalog['oldest']}."
    if catalog["stale"] or catalog["invalid"]:
        needs_review = catalog["stale"] + catalog["invalid"]
        catalog_section = f"ATTENZIONE: catalogo da aggiornare ({len(needs_review)} offerte).\n- " + "\n- ".join(needs_review)
    warning_section = ""
    if warnings:
        warning_section = "\nAvvisi tecnici (il report è arrivato comunque):\n- " + "\n- ".join(warnings) + "\n"
    body = f"""Ciao,

Report Costo Vero — ultime 24 ore circa

{traffic_section}

{activity_section}

{catalog_section}
{warning_section}

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
