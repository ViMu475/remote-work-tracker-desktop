"""Flextime (Gleitzeit) per month: the data behind the trend chart and the flextime lines of the final report.

Every statement carries three numbers (hours): the balance at the start of the month (`vorperiode`), the change
during the month (`aktuell`) and the balance at the end of the month (`gesamt`). They are kept in the list
`state['gleitzeit_verlauf']`, one entry per month, sorted by year and month. The history records of the
months are not touched by this.
"""
from config import Config

MONTH_NAMES = list(Config.MONATS_NUMMERN)
FIELDS = ('vorperiode', 'aktuell', 'gesamt')
_SOURCE_KEYS = {'vorperiode': 'previous', 'aktuell': 'current', 'gesamt': 'total'}
MAX_ABS_HOURS = 10000

# Thresholds of the employee portal (balance at the end of the month, hours): above 40 h yellow, above 60 h red,
# the same below -40 h / -60 h. Hours above 60 are cut off at the end of the month.
YELLOW_LIMIT = 40.0
RED_LIMIT = 60.0
OK, YELLOW_POS, RED_POS, YELLOW_NEG, RED_NEG = 'ok', 'yellow_pos', 'red_pos', 'yellow_neg', 'red_neg'


def status(balance):
    """Traffic light of a month-end balance: ok, yellow_pos, red_pos, yellow_neg, red_neg (None without a number)."""
    if isinstance(balance, bool) or not isinstance(balance, (int, float)) or balance != balance:
        return None
    if balance > RED_LIMIT:
        return RED_POS
    if balance > YELLOW_LIMIT:
        return YELLOW_POS
    if balance < -RED_LIMIT:
        return RED_NEG
    if balance < -YELLOW_LIMIT:
        return YELLOW_NEG
    return OK


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _hours(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return round(value, 2) if abs(value) < MAX_ABS_HOURS else None


def clean_entry(raw):
    """A valid entry of the series from a stored entry, or None."""
    if not isinstance(raw, dict) or not _is_int(raw.get('jahr')) or not _is_int(raw.get('monat')):
        return None
    if not 1 <= raw['monat'] <= 12 or not 1900 <= raw['jahr'] <= 2200:
        return None
    entry = {'jahr': raw['jahr'], 'monat': raw['monat']}
    for field in FIELDS:
        value = _hours(raw.get(field))
        if value is not None:
            entry[field] = value
    return entry if any(f in entry for f in FIELDS) else None


def normalize_series(raw):
    """Valid entries only, one per month (the last wins), sorted by year and month."""
    unique = {}
    for item in raw if isinstance(raw, list) else []:
        entry = clean_entry(item)
        if entry:
            unique[(entry['jahr'], entry['monat'])] = entry
    return [unique[key] for key in sorted(unique)]


def record_flex(state, flex, year=None, month=None):
    """Store the flextime numbers of one statement (`flex`: previous/current/total, as read by the parser).

    `year`/`month` (1-12) default to the ones in `flex`. Returns True when an entry was stored.
    """
    if not isinstance(flex, dict):
        return False
    year = flex.get('year') if year is None else year
    month = flex.get('month') if month is None else month
    entry = clean_entry({'jahr': year, 'monat': month,
                         **{field: flex.get(source) for field, source in _SOURCE_KEYS.items()}})
    if not entry:
        return False
    series = [e for e in normalize_series(state.get('gleitzeit_verlauf')) if (e['jahr'], e['monat']) != (year, month)]
    series.append(entry)
    state['gleitzeit_verlauf'] = normalize_series(series)
    return True


def remove_month(state, year, month_name):
    """Drop the entry of one month (used when the month is deleted from the history)."""
    number = Config.MONATS_NUMMERN.get(month_name)
    before = normalize_series(state.get('gleitzeit_verlauf'))
    after = [e for e in before if (e['jahr'], e['monat']) != (year, number)]
    state['gleitzeit_verlauf'] = after
    return len(after) < len(before)


def series(state):
    """The series for charts and reports, with the month names. Older data that only has the latest balance
    (`gleitzeit_saldo`) is included as one point when its month is not in the series."""
    entries = normalize_series(state.get('gleitzeit_verlauf'))
    saldo = state.get('gleitzeit_saldo')
    if isinstance(saldo, dict):
        entry = clean_entry({'jahr': saldo.get('year'), 'monat': saldo.get('month'),
                             **{field: saldo.get(source) for field, source in _SOURCE_KEYS.items()}})
        if entry and (entry['jahr'], entry['monat']) not in {(e['jahr'], e['monat']) for e in entries}:
            entries = normalize_series(entries + [entry])
    return [dict(e, monat_name=MONTH_NAMES[e['monat'] - 1], status=status(e.get('gesamt'))) for e in entries]


def summarize(entries):
    """Latest balance, lowest and highest month-end balance of a series (values None when there is none)."""
    totals = [e for e in entries if isinstance(e, dict) and isinstance(e.get('gesamt'), (int, float))
              and isinstance(e.get('jahr'), int) and isinstance(e.get('monat'), int) and 1 <= e['monat'] <= 12]
    if not totals:
        return {'latest': None, 'latest_month': None, 'min': None, 'min_month': None, 'max': None, 'max_month': None,
                'status': None, 'months_yellow': 0, 'months_red': 0}

    def label(e):
        return {'jahr': e['jahr'], 'monat': e['monat'], 'monat_name': e.get('monat_name') or MONTH_NAMES[e['monat'] - 1]}
    low = min(totals, key=lambda e: e['gesamt'])
    high = max(totals, key=lambda e: e['gesamt'])
    states = [status(e['gesamt']) for e in totals]
    return {'latest': totals[-1]['gesamt'], 'latest_month': label(totals[-1]),
            'min': low['gesamt'], 'min_month': label(low), 'max': high['gesamt'], 'max_month': label(high),
            'status': states[-1], 'months_yellow': sum(1 for s in states if s in (YELLOW_POS, YELLOW_NEG)),
            'months_red': sum(1 for s in states if s in (RED_POS, RED_NEG))}
