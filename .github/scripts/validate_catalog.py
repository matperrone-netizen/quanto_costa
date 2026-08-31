import json, sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

def validate(path):
    catalog = json.loads(Path(path).read_text(encoding="utf-8")); errors, warnings, seen = [], [], set()
    offers = catalog.get("offers")
    if not isinstance(offers, list) or not offers: return ["offers deve essere una lista non vuota"], warnings
    for index, offer in enumerate(offers, 1):
        label = offer.get("id") or f"riga {index}"
        missing = [x for x in ("id", "title", "type", "payment", "months", "sourceUrl") if offer.get(x) in (None, "")]
        if missing: errors.append(f"{label}: campi mancanti: {', '.join(missing)}")
        if offer.get("id") in seen: errors.append(f"{label}: id duplicato")
        seen.add(offer.get("id"))
        if offer.get("type") not in ("rental", "finance"): errors.append(f"{label}: type deve essere rental o finance")
        for field in ("payment", "downPayment", "contractKm"):
            value = offer.get(field, 0)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0: errors.append(f"{label}: {field} deve essere un numero non negativo")
        if not isinstance(offer.get("months"), int) or isinstance(offer.get("months"), bool) or offer.get("months", 0) <= 0: errors.append(f"{label}: months deve essere un intero positivo")
        source = urlparse(str(offer.get("sourceUrl", "")))
        if source.scheme != "https" or not source.netloc: errors.append(f"{label}: sourceUrl deve essere un URL HTTPS valido")
    try:
        if date.fromisoformat(catalog.get("updatedAt")) > date.today(): warnings.append("updatedAt è nel futuro")
    except (TypeError, ValueError): errors.append("updatedAt deve essere una data ISO YYYY-MM-DD")
    return errors, warnings

if __name__ == "__main__":
    errors, warnings = validate(sys.argv[1] if len(sys.argv) > 1 else "offers.json")
    for item in warnings: print(f"AVVISO: {item}")
    for item in errors: print(f"ERRORE: {item}")
    print(f"Validazione completata: {len(errors)} errori, {len(warnings)} avvisi.")
    raise SystemExit(1 if errors else 0)
