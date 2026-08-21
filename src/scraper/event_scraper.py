import sys
import time
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# A few known Pune / startup-adjacent Meetup groups to seed --mode groups with
# if you don't pass --groups yourself. Edit freely as you find more.
DEFAULT_PUNE_GROUPS = [
    "https://www.meetup.com/echai-pune/",
    "https://www.meetup.com/pune-tech-network/",
    "https://www.meetup.com/pune-startups/",
]


def _new_page(context):
    page = context.new_page()
    return page


def _hit_cloudflare(content: str) -> bool:
    return "Just a moment" in content or "challenge-platform" in content


def _safe_attr_or_text(page, selector: str, attr: str) -> tuple[Optional[str], Optional[str]]:
    """Return (attribute_value, inner_text) for the first matching element."""
    try:
        el = page.query_selector(selector)
        if not el:
            return None, None
        attr_val = el.get_attribute(attr)
        text = el.inner_text().strip() or None
        return attr_val, text
    except Exception:
        return None, None


def _safe_text(page, selector: str) -> str | None:
    """Return stripped text of the first matching element, or None."""
    try:
        el = page.query_selector(selector)
        if el:
            text = el.inner_text().strip()
            return text if text else None
    except Exception:
        pass
    return None


def _looks_like_event_url(url: str) -> bool:
    path = url.split("?")[0].rstrip("/")
    return path.split("/")[-1].isdigit()  # path ends in /events/123456789


def _enrich_event(page, link: str) -> dict:
    """Visit an individual event page and pull out details."""
    event_data = {"url": link}
    try:
        page.goto(link, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        event_data["title"] = _safe_text(page, "h1")

        # <time datetime="2026-08-08T11:00:00+05:30"> -- the datetime attr is
        # ISO-8601 and locale-independent, unlike the rendered text
        # ("Saturday, Aug 8 · 11:00 AM to 1:00 PM IST"), so it's what your
        # downstream code should actually parse/sort/filter on.
        iso_dt, display_dt = _safe_attr_or_text(page, "time", "datetime")
        event_data["datetime_iso"] = iso_dt
        event_data["datetime_display"] = display_dt

        event_data["description"] = _safe_text(
            page,
            "div[class*='line-clamp-'], "          # Meetup's current truncated-description block (seen Aug 2026)
            "div[id*='event-details'], "            # older markup, kept as fallback
            "div[data-testid='event-description']"  # older markup, kept as fallback
        )
        event_data["venue"] = _safe_text(
            page, "div[data-testid='venue-name-row'], address"
        )
        event_data["host"] = _safe_text(
            page, "a[href*='/members/'], div[data-testid='host-row']"
        )
        event_data["group_name"] = _safe_text(
            page, "a[data-testid='group-link'], a[href*='/groups/']"
        )

        # No dedicated "speakers" DOM section exists on Meetup event pages --
        # when organizers list speakers at all, it's free text inside the
        # description ("Panel Speakers coming soon...", bios, etc). Real
        # extraction belongs in a separate LLM-parsing layer downstream.
        # For now: raw description passes through as-is, plus a cheap
        # heuristic flag so events that clearly aren't naming any speakers
        # can be deprioritized before that layer exists.
        desc = event_data.get("description") or ""
        event_data["speakers"] = None
        event_data["self_hosted"] = "speaker" not in desc.lower()
    except PlaywrightTimeoutError:
        event_data["error"] = "timeout loading event page"

    return event_data


def scrape_group_events(page, group_url: str, max_events: int) -> list[dict]:
    """Scrape upcoming events for a single known group (channel)."""
    events_url = group_url.rstrip("/") + "/events/"
    results = []

    print(f"[*] Loading {events_url} ...", file=sys.stderr)
    try:
        page.goto(events_url, timeout=30000, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        print(f"[!] Timed out loading {events_url}", file=sys.stderr)
        return results

    page.wait_for_timeout(3000)

    if _hit_cloudflare(page.content()):
        print(f"[!] Cloudflare challenge on {events_url}, skipping.", file=sys.stderr)
        return results

    event_links = page.eval_on_selector_all(
        "a[data-testid='group-events-card']", "els => els.map(e => e.href)"
    )
    if not event_links:
        event_links = page.eval_on_selector_all(
            "a[href*='/events/']", "els => els.map(e => e.href)"
        )
    event_links = list(dict.fromkeys(event_links))
    event_links = [l for l in event_links if _looks_like_event_url(l)][:max_events]

    print(f"[*] {group_url}: found {len(event_links)} event link(s).", file=sys.stderr)

    for link in event_links:
        print(f"[*] Visiting {link}", file=sys.stderr)
        event_data = _enrich_event(page, link)
        event_data.setdefault("group_name", group_url)
        results.append(event_data)
        time.sleep(1.5)

    return results


def scrape_pune_search(page, keywords: str, location: str, max_events: int) -> list[dict]:
    """
    Scrape Meetup's search/discovery results for a location (e.g. Pune) so we
    pull events across many different groups/organizers, not just one channel.

    Meetup's search URL format: https://www.meetup.com/find/?location=<loc>&source=EVENTS&keywords=<kw>
    location uses Meetup's internal codes, e.g. "in--pune". If that 404s or
    returns nothing, pass --location with whatever value works when you check
    the URL manually in a browser and copy it.
    """
    search_url = (
        f"https://www.meetup.com/find/?source=EVENTS&location={location}"
        f"{'&keywords=' + keywords if keywords else ''}"
    )
    results = []

    print(f"[*] Loading {search_url} ...", file=sys.stderr)
    try:
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        print("[!] Search page load timed out.", file=sys.stderr)
        return results

    page.wait_for_timeout(3000)

    if _hit_cloudflare(page.content()):
        print("[!] Hit a Cloudflare challenge page on search. Try --show-browser once.", file=sys.stderr)
        return results

    # Lazy-loaded results: scroll a bit to trigger more cards to mount.
    for _ in range(4):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(800)

    event_links = page.eval_on_selector_all(
        "a[data-testid='search-result'], a[data-event-label='EventCard']",
        "els => els.map(e => e.href)"
    )
    if not event_links:
        print("[!] search-result selector found nothing, falling back to generic href match", file=sys.stderr)
        event_links = page.eval_on_selector_all(
            "a[href*='/events/']", "els => els.map(e => e.href)"
        )
    event_links = list(dict.fromkeys(event_links))
    event_links = [l for l in event_links if _looks_like_event_url(l)][:max_events]

    print(f"[*] Found {len(event_links)} event link(s) across search results.", file=sys.stderr)

    for link in event_links:
        print(f"[*] Visiting {link}", file=sys.stderr)
        event_data = _enrich_event(page, link)
        results.append(event_data)
        time.sleep(1.5)

    return results


def run_search(keywords: str = "", location: str = "in--pune",
                max_events: int = 10, headless: bool = True) -> list[dict]:
    """Importable entrypoint: search-mode scrape, owns its own browser lifecycle."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = _new_page(context)
        try:
            return scrape_pune_search(page, keywords, location, max_events)
        finally:
            browser.close()


def run_groups(groups: list[str] | None = None, max_events: int = 10,
               headless: bool = True) -> list[dict]:
    """Importable entrypoint: groups-mode scrape, owns its own browser lifecycle."""
    groups = groups if groups else DEFAULT_PUNE_GROUPS
    all_events = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = _new_page(context)
        try:
            for group_url in groups:
                all_events.extend(scrape_group_events(page, group_url, max_events))
        finally:
            browser.close()
    return all_events