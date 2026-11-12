# ha_badtider
Simtider för Piteås simhallar till Home Assistant

Integrationen läser öppettiderna för **Öjebyn**, **Munksund** och **Hortlax** från
pitea.se och visar var och när det går att simma (passtyperna *Simma* och
*Lunchsim*), idag och imorgon.

# Features
* Status: pågående pass, annars nästa pass idag, annars morgondagens första
* Alla simpass idag, i alla hallar, sorterade på starttid
* Morgondagens första pass (alla hallar som startar samtidigt)
* Tidsstämpelsensor för nästa pass, att använda i automationer
* En kalender per hall, som syns i HA:s kalendervy
* Status räknas om varje minut. Schemat hämtas från pitea.se var tredje timme,
  och det senast hämtade schemat behålls om sidan inte svarar

# Installation
1. HACS → ⋮ → *Custom repositories* → lägg till `https://github.com/darkvinge/ha_badtider`, kategori *Integration*
2. Installera **Badtider Piteå** och starta om Home Assistant
3. *Inställningar → Enheter och tjänster → Lägg till integration* → **Badtider Piteå**

## Sensorer
| Sensor | State | Attribut |
| --- | --- | --- |
| `sensor.badtider_status` | `Nu: Öjebyn 15:00–20:30 Simma`, `Öjebyn 11:00–11:50 Lunchsim` eller `Imorgon: …` | `pagar`, `pagaende`, `nasta` |
| `sensor.badtider_idag` | Dagens pass, kommaseparerade | `pass`, `perioder` |
| `sensor.badtider_imorgon_forsta` | Morgondagens första pass | `forsta`, `pass` (alla imorgon) |
| `sensor.badtider_nasta_pass` | Starttid för nästa pass (timestamp) | `hall`, `typ`, `datum`, `start`, `slut`, `notering`, `text` |

Varje pass i listorna har `hall`, `typ` (`Simma`/`Lunchsim`), `datum`, `start`, `slut` och `notering`.

## Kalendrar
`calendar.badtider_ojebyn`, `calendar.badtider_munksund` och `calendar.badtider_hortlax`
visar simpassen som händelser, till exempel *Simma Öjebyn* 15:00–20:30. Kalendern är
`on` medan ett pass pågår, och attributen visar pågående eller nästa pass.

Veckoschemat upprepas fyra veckor framåt och en vecka bakåt från idag. Längre fram
visas inget, eftersom kommunen kan hinna ändra tiderna.

Ge varje kalender en egen färg under *Kalender* i sidomenyn, via kugghjulet vid
kalenderns namn.

## Kort
Lägg till ett **Markdown**-kort och klistra in följande i kodredigeraren:

```yaml
type: markdown
title: Simning
content: |
  **{{ states('sensor.badtider_status') }}**

  {% for p in state_attr('sensor.badtider_idag', 'pass') or [] %}
  - {{ p.hall }} {{ p.start }}–{{ p.slut }} {{ p.typ }}
  {% else %}
  Ingen simning idag
  {% endfor %}

  **Imorgon:** {{ states('sensor.badtider_imorgon_forsta') }}
```

# Begränsningar
* Bara det ordinarie veckoschemat läses (första schemat på varje halls sida).
  Röda dagar, tillfälliga stängningar och notiser under "Aktuellt" kommer inte med.
* Integrationen läser pitea.se:s HTML. Om sidorna byggs om loggas en varning
  ("Hittade inget schema för …") och hallen får inga pass.

# Utveckling
```sh
python -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

Testerna använder sparade kopior av sidorna i `tests/fixtures/`.
