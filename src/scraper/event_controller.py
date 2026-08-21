import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .event_scraper import run_search, run_groups, DEFAULT_PUNE_GROUPS

router = APIRouter()

CACHE_TTL_SECONDS = 15 * 60  # events don't change minute to minute; tune as you like
_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_get(key: str) -> Optional[list[dict]]:
    hit = _cache.get(key)
    if not hit:
        return None
    ts, data = hit
    if time.time() - ts > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return data


def _cache_set(key: str, data: list[dict]) -> None:
    _cache[key] = (time.time(), data)


class Event(BaseModel):
    url: str
    title: Optional[str] = None
    datetime_iso: Optional[str] = None       # machine-parseable, e.g. "2026-08-08T11:00:00+05:30"
    datetime_display: Optional[str] = None   # human string as Meetup renders it, for display only
    description: Optional[str] = None
    venue: Optional[str] = None
    host: Optional[str] = None
    group_name: Optional[str] = None
    speakers: Optional[list[str]] = None  # populated by the future LLM extraction layer, null for now
    self_hosted: Optional[bool] = None    # heuristic: "speaker" not found in description text
    error: Optional[str] = None


class EventsResponse(BaseModel):
    count: int
    cached: bool
    events: list[Event]


class GroupsRequest(BaseModel):
    groups: list[str] = DEFAULT_PUNE_GROUPS
    max_events: int = 10


@router.get("/pune", response_model=EventsResponse)
async def get_pune_events(
    location: str = Query("in--pune", description="Meetup location code"),
    keywords: str = Query("", description="Optional keyword filter, e.g. 'startup'"),
    max_events: int = Query(10, ge=1, le=50),
    refresh: bool = Query(False, description="Bypass cache and force a fresh scrape"),
):
    """Events across all Meetup groups/organizers in Pune (search mode)."""
    cache_key = f"search:{location}:{keywords}:{max_events}"

    if not refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return EventsResponse(count=len(cached), cached=True, events=cached)

    try:
        events = await run_in_threadpool(
            run_search, keywords=keywords, location=location, max_events=max_events
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")

    if not events:
        raise HTTPException(status_code=502, detail="No events scraped -- Meetup may be blocking the request (Cloudflare) or the location code is wrong")

    _cache_set(cache_key, events)
    return EventsResponse(count=len(events), cached=False, events=events)


@router.post("/groups", response_model=EventsResponse)
async def get_group_events(body: GroupsRequest, refresh: bool = Query(False)):
    """Events from a specific list of Meetup groups/channels you curate yourself."""
    cache_key = f"groups:{','.join(sorted(body.groups))}:{body.max_events}"

    if not refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return EventsResponse(count=len(cached), cached=True, events=cached)

    try:
        events = await run_in_threadpool(
            run_groups, groups=body.groups, max_events=body.max_events
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")

    if not events:
        raise HTTPException(status_code=502, detail="No events scraped -- check group URLs or Cloudflare block")

    _cache_set(cache_key, events)
    return EventsResponse(count=len(events), cached=False, events=events)