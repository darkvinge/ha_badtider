"""Hämtar och tolkar simhallarnas öppettider från pitea.se."""

from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import dataclass, field

import aiohttp

from .const import HALLS, SESSION_TYPES

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=20)

DAYS = ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"]
_DAY = "|".join(DAYS)
DAY_HEADER_RE = re.compile(
    rf"^((?:{_DAY})(?:\s*(?:,|och|-|–)\s*(?:{_DAY}))*)\s*:?\s*(.*)$", re.I
)
TIME_RE = re.compile(
    r"(\d{1,2})(?:[.:](\d{2}))?\s*[-–]\s*(\d{1,2})(?:[.:](\d{2}))?\s+([A-Za-zÅÄÖåäö]+)"
)
_DATE = r"\d{1,2}(?:/\d{1,2}|\s+[a-zåäö]+)"
PERIOD_RE = re.compile(rf"{_DATE}\s*[-–]\s*{_DATE}(?:\s+\d{{4}})?", re.I)
# Rader som betyder att det första veckoschemat på sidan är slut
END_PREFIXES = ("beskrivningar", "öppettider", "köp din")


class BadtiderError(Exception):
    """Fel vid hämtning av badtider."""


class BadtiderConnectionError(BadtiderError):
    """Pitea.se gick inte att nå."""


@dataclass(frozen=True)
class Session:
    """Ett pass i veckoschemat."""

    type: str
    start: str  # "HH:MM"
    end: str  # "HH:MM"
    note: str | None = None


@dataclass
class HallSchedule:
    """Veckoschema för en hall. days[0] är måndag."""

    days: list[list[Session]] = field(default_factory=lambda: [[] for _ in range(7)])
    period: str | None = None


def html_to_lines(page: str) -> list[str]:
    """Gör om sidans innehåll till textrader."""
    start = page.find("readspeaker_button1")
    if start >= 0:
        page = page[start:]
    page = re.sub(r"<(script|style)\b.*?</\1>", "", page, flags=re.S | re.I)
    page = re.sub(r"<br\s*/?>|</(?:p|div|h\d|li|tr)>", "\n", page, flags=re.I)
    page = re.sub(r"<[^>]+>", "", page)
    page = html.unescape(page).replace("\xa0", " ")
    lines = (re.sub(r"\s+", " ", line).strip() for line in page.splitlines())
    return [line for line in lines if line]


def _parse_day_header(line: str) -> tuple[list[int], str] | None:
    """'Lördag och söndag stängt' -> ([5, 6], 'stängt')."""
    match = DAY_HEADER_RE.match(line.lower().rstrip(":").strip())
    if not match:
        return None
    days_part, rest = match.groups()
    idx = [DAYS.index(name) for name in re.findall(_DAY, days_part)]
    if len(idx) == 2 and re.search(r"[-–]", days_part):  # t.ex. måndag-torsdag
        idx = list(range(idx[0], idx[1] + 1))
    return idx, rest


def parse_schedule(page: str) -> HallSchedule:
    """Läser det första veckoschemat på en öppettidssida."""
    schedule = HallSchedule()
    current: list[int] = []
    seen_day = False

    for line in html_to_lines(page):
        header = _parse_day_header(line)
        if header:
            current, line = header
            seen_day = True
            if not line:
                continue
        low = line.lower()
        if not seen_day:
            match = PERIOD_RE.search(line)
            if schedule.period is None and match and not TIME_RE.search(line):
                schedule.period = match.group(0)
            continue
        if low.startswith(END_PREFIXES):
            break
        if low.startswith("*"):
            continue
        for h1, m1, h2, m2, kind in TIME_RE.findall(line):
            if (session_type := SESSION_TYPES.get(kind.lower())) is None:
                continue
            session = Session(
                type=session_type,
                start=f"{int(h1):02d}:{m1 or '00'}",
                end=f"{int(h2):02d}:{m2 or '00'}",
                note=line if "(" in line else None,
            )
            for day in current:
                schedule.days[day].append(session)

    for sessions in schedule.days:
        sessions.sort(key=lambda s: s.start)
    return schedule


async def _async_fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.text()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise BadtiderConnectionError(f"{url}: {err}") from err


async def async_fetch_schedules(
    session: aiohttp.ClientSession,
) -> dict[str, HallSchedule]:
    """Hämtar veckoschemat för alla hallar.

    Hallar som inte går att hämta eller tolka hoppas över. Går ingen hall att
    hämta kastas BadtiderConnectionError.
    """
    pages = await asyncio.gather(
        *(_async_fetch_page(session, url) for url in HALLS.values()),
        return_exceptions=True,
    )
    schedules: dict[str, HallSchedule] = {}
    for hall, page in zip(HALLS, pages):
        if isinstance(page, BaseException):
            _LOGGER.warning("Kunde inte hämta badtider för %s: %s", hall, page)
            continue
        schedule = parse_schedule(page)
        if not any(schedule.days):
            _LOGGER.warning("Hittade inget schema för %s, har sidan ändrats?", hall)
        schedules[hall] = schedule

    if not schedules:
        raise BadtiderConnectionError("Kunde inte hämta någon hall från pitea.se")
    return schedules
