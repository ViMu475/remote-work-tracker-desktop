"""Month records of the history and the quarter summary.

Used by "Monat abschließen" (`/month/switch`) and by the batch import of time statements, so a month
that enters the history this way has exactly the same shape and numbers as a month that was closed by hand.
"""
import math

from config import Config
from services.calculation import berechne_soll_stunden_monat, get_quartal_for_month

MIN_MONTHS_FOR_QUARTER_SUMMARY = 3


def safe_number(value, default=0.0):
    """float(value) for numbers and numeric strings; `default` for anything else (None, bool, NaN, text)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def month_prefix(month_name, year):
    return f"{year}-{Config.MONATS_NUMMERN[month_name]:02d}-"


def month_entry_totals(state, month_name, year):
    """(remote hours, net hours) of all entries of one month in the daily records."""
    prefix = month_prefix(month_name, year)
    remote = netto = 0.0
    for date_key, entries in (state.get('daily_records') or {}).items():
        if not isinstance(date_key, str) or not date_key.startswith(prefix) or not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                remote += safe_number(entry.get('remoteStundenHeute'))
                netto += safe_number(entry.get('totalStundenHeute'))
    return remote, netto


def month_has_entries(state, month_name, year):
    prefix = month_prefix(month_name, year)
    return any(isinstance(k, str) and k.startswith(prefix) and v for k, v in (state.get('daily_records') or {}).items())


def build_month_record(state, month_name, year, quote=None):
    """The history record of one month, computed from its daily records.

    `quote` is the remote quota in percent that applied to that month; None means the current quota of the state.
    """
    remote, netto = month_entry_totals(state, month_name, year)
    soll = berechne_soll_stunden_monat(year, Config.MONATS_NUMMERN[month_name], state['soll_stunden_pro_tag'])
    quote = state['individuelle_quote_prozent'] if quote is None else quote
    return {
        'monat': month_name,
        'jahr': year,
        'soll_stunden_gesamt': soll,
        'ist_remote_stunden_laufend': remote,
        'ist_arbeitszeit_laufend': netto,
        'max_remote_stunden': soll * (quote / 100.0),
        'individuelle_quote': quote,
        'tatsaechliche_remote_quote': (remote / soll * 100) if soll > 0 else 0,
        'quartal': get_quartal_for_month(month_name, year),
    }


def update_quarter_summary(history, quartal):
    """Write the quarter totals into every month of `quartal` once it has 3 months.

    Returns the totals (with the months of the quarter), or None when the quarter is not complete yet.
    Only the summary fields are written: the quota of the user is never touched here.
    """
    months = [m for m in history if isinstance(m, dict) and m.get('quartal') == quartal]
    if len(months) < MIN_MONTHS_FOR_QUARTER_SUMMARY:
        return None

    def total(key):   # a damaged history entry counts as 0 instead of breaking the month close
        return sum(safe_number(m.get(key)) for m in months)

    monthly_quotes = [safe_number(m.get('tatsaechliche_remote_quote')) for m in months]
    summary = {
        'months': months,
        'gesamt_soll': total('soll_stunden_gesamt'),
        'gesamt_ist_remote': total('ist_remote_stunden_laufend'),
        'gesamt_ist_arbeitszeit': total('ist_arbeitszeit_laufend'),
        'quartal_quote': sum(monthly_quotes) / len(monthly_quotes) if monthly_quotes else 0,
    }
    for m in months:
        m['quartal_quote'] = summary['quartal_quote']
        m['quartal_remote'] = summary['gesamt_ist_remote']
        m['quartal_gesamt'] = summary['gesamt_ist_arbeitszeit']
        m['quartal_soll'] = summary['gesamt_soll']
    return summary
