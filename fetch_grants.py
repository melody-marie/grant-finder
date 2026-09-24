#!/usr/bin/env python3
"""Pull open/forecasted federal grants from the free, public Grants.gov
search2 API (no key required) and write them to grants.json for the
grant-finder page to read as static data."""
import json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

API = "https://api.grants.gov/v1/api/search2"

# Keyword -> focus-area tag used by the page's filter chips.
SEARCHES = [
    ("LGBTQ",              "lgbtq"),
    ("transgender",        "trans"),
    ("racial justice",     "racial"),
    ("civil rights",       "racial"),
    ("hate crime",         "legal"),
    ("criminal justice reform", "legal"),
    ("victims of crime",   "legal"),
    ("public awareness campaign", "awareness"),
    ("community health equity",   "health"),
]

HEADERS = {"Content-Type": "application/json", "User-Agent": "grant-finder-github-action"}

def post(payload, tries=3):
    body = json.dumps(payload).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request(API, data=body, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == tries - 1:
                print(f"  request failed: {e}", file=sys.stderr)
                return None
            time.sleep(2)

def fmt_date(raw):
    """Grants.gov dates arrive like 'MM/DD/YYYY'."""
    if not raw:
        return "See opportunity"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if not m:
        return raw
    mm, dd, yyyy = m.groups()
    try:
        return datetime(int(yyyy), int(mm), int(dd)).strftime("%b %d, %Y")
    except ValueError:
        return raw

def main():
    seen = {}
    for keyword, focus in SEARCHES:
        payload = {
            "keyword": keyword,
            "oppStatuses": "posted|forecasted",
            "rows": 15,
            "startRecordNum": 0,
        }
        data = post(payload)
        if not data:
            continue
        hits = (data.get("data") or {}).get("oppHits") or data.get("oppHits") or []
        for h in hits:
            opp_id = h.get("id") or h.get("oppId") or h.get("number")
            if not opp_id or opp_id in seen:
                continue
            number = h.get("number") or h.get("oppNumber") or ""
            title = (h.get("title") or "Untitled opportunity").strip()
            agency = (h.get("agencyName") or h.get("agency") or h.get("agencyCode") or "").strip()
            close = fmt_date(h.get("closeDate"))
            open_ = fmt_date(h.get("openDate"))
            url = f"https://www.grants.gov/search-results-detail/{opp_id}"
            seen[opp_id] = {
                "name": title[:140],
                "funder": agency[:100] or "U.S. federal agency",
                "focus": focus,
                "who": ["org"],
                "amount": "See opportunity for award amounts",
                "deadline": close,
                "region": "United States (federal)",
                "blurb": f"Federal opportunity {number}. Posted {open_}.".strip()[:220],
                "url": url,
            }
        time.sleep(1)  # be polite to the public API

    items = list(seen.values())
    out = {
        "items": items,
        "checked": datetime.now(timezone.utc).isoformat(),
        "source": "grants.gov search2 (public, no key required)",
    }
    with open("grants.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(items)} opportunities to grants.json")

if __name__ == "__main__":
    main()
