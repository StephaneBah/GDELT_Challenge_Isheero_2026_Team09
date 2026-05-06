import argparse
import csv
import html
import re
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_INPUT = "copy_events_benin_2025_labeled.csv"
DEFAULT_FLAGGED = "copy_events_benin_2025_labeled_url_flagged.csv"
DEFAULT_FILTERED = "copy_events_benin_2025_labeled_url_filtered.csv"

# URL keywords flagged as likely Nigeria-related (user request)
SUSPECT_KEYWORDS = ["naira", "naija", "nigeria"]
SUSPECT_HOST_PARTS = ["ng.com"]
SUSPECT_TLD = ".ng"

# Article text signals (normalized to ASCII)
CITY_MARKERS = ["benin city", "city of benin", "benin-city", "edo state"]
REPUBLIC_MARKERS = ["republic of benin", "benin republic", "republique du benin"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Flag suspect URLs and remove rows whose articles do not mention Benin."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--flagged", default=DEFAULT_FLAGGED, help="Flagged output CSV")
    parser.add_argument("--filtered", default=DEFAULT_FILTERED, help="Filtered output CSV")
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Also fetch non-suspect URLs (slow)"
    )
    return parser.parse_args()


def normalize_text(text):
    # Remove accents so "benin" matches "benin" and "benin"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.lower()


def is_suspect_url(url):
    if not url:
        return False
    u = url.lower()
    if any(k in u for k in SUSPECT_KEYWORDS):
        return True
    host = urlparse(u).netloc
    if not host:
        return False
    if host.endswith(SUSPECT_TLD) or (".ng." in host):
        return True
    if any(part in host for part in SUSPECT_HOST_PARTS):
        return True
    # Optional catch for ng in path (conservative)
    if "/ng/" in u:
        return True
    return False


def fetch_text(url, timeout=12, max_bytes=2_000_000):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text" not in content_type and "html" not in content_type:
                return None
            raw = resp.read(max_bytes).decode("utf-8", errors="ignore")
    except Exception:
        return None

    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    text = html.unescape(raw)
    text = re.sub(r"\s+", " ", text).strip()
    return normalize_text(text)


def main():
    args = parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError("No rows loaded.")

    url_cache = {}
    benin_missing_urls = set()
    benin_city_urls = set()
    suspect_count = 0
    checked_count = 0

    for r in rows:
        url = (r.get("SOURCEURL") or "").strip()
        suspect = is_suspect_url(url)
        r["SuspectUrl"] = "True" if suspect else "False"

        if not url or (not suspect and not args.check_all):
            r["BeninMentioned"] = ""
            r["BeninCityMentioned"] = ""
            r["BeninRepublicMentioned"] = ""
            r["RemoveReason"] = ""
            continue

        suspect_count += 1
        if url not in url_cache:
            url_cache[url] = fetch_text(url)
            checked_count += 1

        text = url_cache[url]
        if text is None:
            r["BeninMentioned"] = "Unknown"
            r["BeninCityMentioned"] = "Unknown"
            r["BeninRepublicMentioned"] = "Unknown"
            r["RemoveReason"] = "Unknown"
            continue

        has_benin = "benin" in text
        has_city = any(m in text for m in CITY_MARKERS) or re.search(r"\bbenin\s+city\b", text)
        has_republic = any(m in text for m in REPUBLIC_MARKERS)

        r["BeninMentioned"] = "True" if has_benin else "False"
        r["BeninCityMentioned"] = "True" if has_city else "False"
        r["BeninRepublicMentioned"] = "True" if has_republic else "False"
        r["RemoveReason"] = ""

        # Rule 1: remove if Benin is not mentioned at all
        if not has_benin:
            benin_missing_urls.add(url)
            r["RemoveReason"] = "Benin not mentioned"
            continue

        # Rule 2: remove if Benin City is mentioned without Benin Republic
        if has_city and not has_republic:
            benin_city_urls.add(url)
            r["RemoveReason"] = "Benin City (Nigeria)"

    removed_urls = benin_missing_urls | benin_city_urls
    filtered_rows = [
        r for r in rows
        if (r.get("SOURCEURL") or "").strip() not in removed_urls
    ]

    fieldnames = list(rows[0].keys())
    for col in ("SuspectUrl", "BeninMentioned", "BeninCityMentioned", "BeninRepublicMentioned", "RemoveReason"):
        if col not in fieldnames:
            fieldnames.append(col)

    with open(args.flagged, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(args.filtered, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    print("URL quality check done")
    print(f"- Suspect URLs flagged: {suspect_count}")
    print(f"- Unique suspect URLs fetched: {checked_count}")
    print(f"- URLs removed (Benin not mentioned): {len(benin_missing_urls)}")
    print(f"- URLs removed (Benin City only): {len(benin_city_urls)}")
    print(f"- Rows before: {len(rows)}")
    print(f"- Rows after : {len(filtered_rows)}")
    print(f"- Output (flagged): {args.flagged}")
    print(f"- Output (filtered): {args.filtered}")


if __name__ == "__main__":
    main()
