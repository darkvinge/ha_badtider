"""Konstanter för Badtider Piteå."""

DOMAIN = "ha_badtider"

_BASE = "https://www.pitea.se/invanare/fritid-kultur/pitea-simhallar"
HALLS = {
    "Öjebyn": f"{_BASE}/ojeby-simhall/oppettider-ojeby-simhall/",
    "Munksund": f"{_BASE}/munksunds-simhall/munksund-simhall/",
    "Hortlax": f"{_BASE}/hortlax-simhall/oppettider-hortlax-simhall/",
}

# Passtyper som räknas som simning, nyckel = text på sidan i gemener
SESSION_TYPES = {"simma": "Simma", "lunchsim": "Lunchsim"}

TIME_ZONE = "Europe/Stockholm"
