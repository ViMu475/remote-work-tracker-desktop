from datetime import datetime
import calendar
from config import Config

def get_quartal_for_month(monat_name: str, jahr: int) -> str:
    """Bestimmt das Quartal für einen gegebenen Monat und Jahr"""
    for quartal, monate in Config.QUARTALS_PLANUNG.items():
        quartal_jahr = int(quartal.split('/')[1])
        if jahr == quartal_jahr and monat_name in monate:
            return quartal
    # Fallback: berechne Quartal dynamisch
    monat_num = Config.MONATS_NUMMERN.get(monat_name, 1)
    q = ((monat_num - 1) // 3) + 1
    return f"Q{q}/{jahr}"

def get_current_month_from_system():
    """Bestimmt aktuellen Monat und Jahr aus Systemdatum"""
    now = datetime.now()
    month_names = list(Config.MONATS_NUMMERN.keys())
    current_month = month_names[now.month - 1]
    current_year = now.year
    return current_month, current_year

def check_time_overlap(datum: str, start_time: str, end_time: str, state: dict, exclude_id: str = None):
    """Prüft ob es Zeitüberlappungen am selben Tag gibt"""

    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    try:
        new_start = time_to_minutes(start_time)
        new_end = time_to_minutes(end_time)
        if new_end < new_start:
            new_end += 24 * 60
    except:
        return "Ungültiges Zeitformat"

    day_entries = state.get('daily_records', {}).get(datum, [])
    if not isinstance(day_entries, list):
        day_entries = [day_entries] if isinstance(day_entries, dict) else []

    for entry in day_entries:
        if not isinstance(entry, dict):
            continue
        if exclude_id and entry.get('id') == exclude_id:
            continue

        try:
            existing_start = time_to_minutes(entry.get('startTime', ''))
            existing_end = time_to_minutes(entry.get('endTime', ''))
            if existing_end < existing_start:
                existing_end += 24 * 60

            if existing_start <= new_start < existing_end or existing_start < new_end <= existing_end or (
                    new_start <= existing_start and new_end >= existing_end) or (
                    existing_start <= new_start and existing_end >= new_end):
                lang = state.get('language', 'de')
                msg = f"Zeitüberlappung erkannt! {entry.get('startTime')}-{entry.get('endTime')} überschneidet sich." if lang == 'de' else f"Time overlap detected! {entry.get('startTime')}-{entry.get('endTime')} overlaps."
                return msg
        except:
            continue

    return None

def is_working_day_valid(datum_string: str, state: dict, allow_historical: bool = False):
    """
    Prüft, ob am Datum gearbeitet werden darf.

    Args:
        datum_string: Datum im Format YYYY-MM-DD
        state: Aktueller Zustand
        allow_historical: Wenn True, werden historische Daten (andere Jahre/Monate) erlaubt
    """
    try:
        date = datetime.strptime(datum_string, '%Y-%m-%d')
    except ValueError:
        return "Ungültiges Datumsformat."

    tag = date.weekday()
    jahr = date.year
    monat = date.month

    month_names_de = list(Config.MONATS_NUMMERN.keys())
    datum_monat_name = month_names_de[monat - 1]

    # Skip year/month validation for historical imports (e.g., PDF import)
    if not allow_historical:
        current_quartal = state.get('current_quartal', 'Q1/2026')
        quartal_monate = Config.QUARTALS_PLANUNG.get(current_quartal, [])

        # Any month up to the current one is allowed, also in earlier years; future months are not.
        aktueller_monat_num = Config.MONATS_NUMMERN[state['aktueller_monat']]
        if (jahr, monat) > (state['aktuelles_jahr'], aktueller_monat_num):
            return (f"Einträge für zukünftige Monate ({datum_monat_name} {jahr}) sind nicht erlaubt. "
                    f"Aktueller Monat: {state['aktueller_monat']} {state['aktuelles_jahr']}")
    else:
        # For historical imports, only reject future dates
        now = datetime.now()
        if date > now:
            return f"Einträge für zukünftige Daten sind nicht erlaubt."

    if datum_string in Config.BAYERN_FEIERTAGE:
        return "Arbeitszeitprotokollierung an einem Feiertag ist nicht zulässig."

    if tag == 6:
        return "Arbeitszeitprotokollierung an Sonntagen ist nicht zulässig."

    if tag == 5:
        return "Arbeitszeitprotokollierung an Samstagen ist nur bei genehmigter Mehrarbeit erlaubt."

    return None

def calculate_net_hours(start_time: str, end_time: str, pause_minutes: float):
    """Berechnet Netto-Arbeitszeit"""

    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)
    pause_hours = pause_minutes / 60

    if end_min < start_min:
        end_min += 24 * 60

    gross_min = end_min - start_min
    gross_hours = gross_min / 60
    net_hours = gross_hours - pause_hours

    statutory_pause = 0
    if gross_hours >= 9:
        statutory_pause = 0.75
    elif gross_hours >= 6:
        statutory_pause = 0.5

    pause_warning_de = None
    pause_warning_en = None
    if statutory_pause > pause_hours:
        pause_warning_de = f"WARNUNG (ArbZG): Pause ({pause_hours:.2f}h) < gesetzl. Minimum ({statutory_pause:.2f}h)!"
        pause_warning_en = f"WARNING (Working Hours Act): Break ({pause_hours:.2f}h) < legal minimum ({statutory_pause:.2f}h)!"

    return {
        'gross': gross_hours,
        'net': net_hours,
        'pause_warning_de': pause_warning_de,
        'pause_warning_en': pause_warning_en,
        'pause_warning': pause_warning_de
    }

def berechne_soll_stunden_monat(jahr: int, monat: int, soll_stunden_pro_tag: float) -> float:
    """Berechnet Soll-Arbeitsstunden für einen Monat"""
    arbeitsstunden = 0.0
    letzter_tag = calendar.monthrange(jahr, monat)[1]

    for tag in range(1, letzter_tag + 1):
        datum_string = f"{jahr}-{monat:02d}-{tag:02d}"
        date = datetime.strptime(datum_string, '%Y-%m-%d')
        wochentag = date.weekday()

        if 0 <= wochentag <= 4 and datum_string not in Config.BAYERN_FEIERTAGE:
            arbeitsstunden += soll_stunden_pro_tag

    return arbeitsstunden
