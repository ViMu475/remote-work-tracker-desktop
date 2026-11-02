import datetime
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def resolve_data_file(environ=None, frozen=None, executable=None):
    """Where the state file lives.

    - RW_DATA_FILE overrides everything.
    - In a packaged .exe (PyInstaller) it sits next to the executable, so it
      does not depend on the working directory the program was started from.
    - In development it stays relative to the working directory.
    """
    environ = os.environ if environ is None else environ
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    executable = sys.executable if executable is None else executable

    override = (environ.get('RW_DATA_FILE') or '').strip()
    if override:
        return override
    if frozen:
        return os.path.join(os.path.dirname(os.path.abspath(executable)), 'tracker_state.json')
    return 'tracker_state.json'


HOLIDAY_YEARS = range(2025, 2031)  # 2025 plus the next five years (2026 to 2030)


def easter_sunday(year):
    """Gregorian Easter Sunday (anonymous / Meeus algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(year, month, day + 1)


def bavarian_holidays(year):
    """The 13 public holidays of Bavaria (incl. Mariä Himmelfahrt and Allerheiligen)."""
    easter = easter_sunday(year)
    day = datetime.timedelta
    return {
        datetime.date(year, 1, 1),       # Neujahr
        datetime.date(year, 1, 6),       # Heilige Drei Könige
        easter - day(days=2),            # Karfreitag
        easter + day(days=1),            # Ostermontag
        datetime.date(year, 5, 1),       # Tag der Arbeit
        easter + day(days=39),           # Christi Himmelfahrt
        easter + day(days=50),           # Pfingstmontag
        easter + day(days=60),           # Fronleichnam
        datetime.date(year, 8, 15),      # Mariä Himmelfahrt
        datetime.date(year, 10, 3),      # Tag der Deutschen Einheit
        datetime.date(year, 11, 1),      # Allerheiligen
        datetime.date(year, 12, 25),     # 1. Weihnachtstag
        datetime.date(year, 12, 26),     # 2. Weihnachtstag
    }


class Config:
    # No Flask secret key on purpose: the app uses no sessions, flash messages or
    # signed cookies. If that ever changes, add a random per-installation key then;
    # never a built-in default (it would allow forged cookies).
    DATA_FILE = resolve_data_file()
    VERSION = "1.0.0"
    
    # Gemini Configuration
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    # Constants
    BASIS_QUOTE_PROZENT = 40.0
    MAX_INDIVIDUELLE_QUOTE_PROZENT = 60.0
    MIN_INDIVIDUELLE_QUOTE_PROZENT = 40.0
    QUOTEN_ANPASSUNG_PROZENT = 10.0
    SOLL_STUNDEN_PRO_TAG = 8.0
    
    # Public holidays in Bavaria, generated for HOLIDAY_YEARS (see bavarian_holidays).
    # To cover more years, extend HOLIDAY_YEARS; tests/test_holidays.py checks each year.
    BAYERN_FEIERTAGE = sorted(
        d.isoformat() for year in HOLIDAY_YEARS for d in bavarian_holidays(year))
    
    MONATS_NUMMERN = {
        "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
        "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
    }
    
    # one entry per quarter of every supported year (same range as the holiday table)
    QUARTALS_PLANUNG = {
        f"Q{q}/{year}": months
        for year in HOLIDAY_YEARS
        for q, months in enumerate((
            ["Januar", "Februar", "März"], ["April", "Mai", "Juni"],
            ["Juli", "August", "September"], ["Oktober", "November", "Dezember"]), 1)
    }
