"""History helpers and the quarterly final report.

The same rules are implemented on every platform (Kotlin `FinalReport`, JavaScript in the
Capacitor and React apps), so a result looks the same everywhere:

* a month is "over quota" when its remote hours exceed its remote limit (compared on 2 decimals);
* the history is sorted by year and month;
* the final report groups the months by quarter and rates each quarter by the share of the
  quarter's remote limit that was used: <= 90 % good, <= 100 % tight, above 100 % exceeded.
"""
from config import Config
from services.calculation import get_quartal_for_month
from services.flex_service import status as flex_status
from services.flex_service import summarize as flex_summary

GOOD = 'good'
TIGHT = 'tight'
EXCEEDED = 'exceeded'
TIGHT_FROM = 0.9
MIN_MONTHS_FOR_COMPLETE_QUARTER = 3


def _num(month, key):
    try:
        return float(month.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def is_over_quota(month):
    return round(_num(month, 'ist_remote_stunden_laufend'), 2) > round(_num(month, 'max_remote_stunden'), 2)


def _sort_key(month):
    try:
        year = int(month.get('jahr') or 0)
    except (TypeError, ValueError):
        year = 0
    monat = month.get('monat')
    return (year, Config.MONATS_NUMMERN.get(monat, 0) if isinstance(monat, str) else 0)


def sort_history(history, newest_first=False):
    return sorted(history or [], key=_sort_key, reverse=newest_first)


def normalize_history(history):
    """History without duplicates (the last entry of a month wins), always sorted by year and month."""
    unique = {}
    for m in history or []:
        if not isinstance(m, dict):
            continue
        key = (m.get('jahr'), m.get('monat'))
        try:
            hash(key)
        except TypeError:           # a list/dict as year or month name
            key = (repr(key[0]), repr(key[1]))
        unique[key] = m
    return sort_history(list(unique.values()))


def rate(remote, limit):
    if round(remote, 2) > round(limit, 2):
        return EXCEEDED
    if limit > 0 and remote > TIGHT_FROM * limit:
        return TIGHT
    return GOOD


def _quote(remote, soll):
    return remote / soll * 100 if soll > 0 else 0.0


def _month_row(m, flex=None):
    """One month of the report. `flex`: the flextime entry of that month (flex_service) or None."""
    remote, limit, soll = _num(m, 'ist_remote_stunden_laufend'), _num(m, 'max_remote_stunden'), _num(m, 'soll_stunden_gesamt')
    flex = flex or {}
    return {
        'monat': m.get('monat'), 'jahr': m.get('jahr'), 'quote': _num(m, 'individuelle_quote'),
        'remote': remote, 'max_remote': limit, 'soll': soll, 'gesamt': _num(m, 'ist_arbeitszeit_laufend'),
        'actual_quote': _quote(remote, soll), 'over': is_over_quota(m),
        'flex_total': flex.get('gesamt'), 'flex_change': flex.get('aktuell'), 'flex_status': flex_status(flex.get('gesamt')),
    }


def _quartal_label(m):
    return m.get('quartal') or get_quartal_for_month(m.get('monat'), m.get('jahr'))


def _quartal_key(label):
    try:
        q, year = label.split('/')
        return int(year), int(q.lstrip('Q'))
    except (ValueError, AttributeError):
        return (0, 0)


def _flex_lookup(flex_series):
    return {(e['jahr'], e['monat']): e for e in flex_series or [] if isinstance(e, dict) and 'jahr' in e and 'monat' in e}


def _quarter_flex(rows):
    """(balance at the end of the quarter, change during the quarter) from the months that have flextime data."""
    totals = [r['flex_total'] for r in rows if r['flex_total'] is not None]
    changes = [r['flex_change'] for r in rows if r['flex_change'] is not None]
    return (totals[-1] if totals else None), (round(sum(changes), 2) if changes else None)


def build_final_report(history, flex_series=None):
    """The quarterly report. `flex_series` (flex_service.series) adds the flextime per month and quarter and
    the whole series for the trend chart; without it the flextime values are None / empty."""
    seen = set()
    groups = {}
    flex_by_month = _flex_lookup(flex_series)
    for m in sort_history(history):
        ident = (m.get('monat'), m.get('jahr'))
        if ident in seen:
            continue
        seen.add(ident)
        number = Config.MONATS_NUMMERN.get(m.get('monat')) if isinstance(m.get('monat'), str) else None
        groups.setdefault(_quartal_label(m), []).append(_month_row(m, flex_by_month.get((m.get('jahr'), number))))

    quarters = []
    for label in sorted(groups, key=_quartal_key):
        rows = groups[label]
        remote = sum(r['remote'] for r in rows)
        limit = sum(r['max_remote'] for r in rows)
        soll = sum(r['soll'] for r in rows)
        flex_end, flex_change = _quarter_flex(rows)
        quarters.append({
            'quartal': label, 'months': rows, 'flex_end': flex_end, 'flex_change': flex_change,
            'flex_status': flex_status(flex_end),
            'month_count': len(rows), 'complete': len(rows) >= MIN_MONTHS_FOR_COMPLETE_QUARTER,
            'remote': remote, 'max_remote': limit, 'soll': soll, 'gesamt': sum(r['gesamt'] for r in rows),
            'actual_quote': _quote(remote, soll), 'months_over': sum(1 for r in rows if r['over']),
            'usage': remote / limit if limit > 0 else 0.0, 'rating': rate(remote, limit),
        })

    remote = sum(q['remote'] for q in quarters)
    limit = sum(q['max_remote'] for q in quarters)
    soll = sum(q['soll'] for q in quarters)
    overall = {
        'months': sum(q['month_count'] for q in quarters), 'months_over': sum(q['months_over'] for q in quarters),
        'quarters': len(quarters), 'quarters_exceeded': sum(1 for q in quarters if q['rating'] == EXCEEDED),
        'remote': remote, 'max_remote': limit, 'soll': soll, 'actual_quote': _quote(remote, soll),
        'rating': rate(remote, limit) if quarters else None,
    }
    flex = [e for e in flex_series or [] if isinstance(e, dict)]
    return {'quarters': quarters, 'overall': overall, 'flex': {'series': flex, 'summary': flex_summary(flex)}}
