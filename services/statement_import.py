"""Batch import of time statements: review every statement, then import the correct months.

Flow (see `routes/api.py`, `/pdf/batch/analyze` and `/pdf/batch/import`):

1. `review_statement` checks ONE parsed statement and returns a report with `errors` and `warnings`.
   `review_batch` adds the checks across statements (the same month twice).
2. `annotate_with_state` adds what only the saved state knows (month already in the history, entries of
   the same days that were typed in by hand).
3. `apply_batch` imports the months the user confirmed. A month is imported completely or not at all:
   an error rejects the whole month and writes nothing. A month that is already over goes into the
   history (sorted by year and month) and its days stay in the daily records; the month that is still
   open only gets its daily records. The quota of the user is never changed.

Issues are `{'code': ..., 'date': ..., 'detail': ...}`; the codes are translated in the browser.
"""
from datetime import datetime

from config import Config
from services.calculation import (
    assign_statement_breaks,
    calculate_net_hours,
    check_time_overlap,
    is_working_day_valid,
    parse_hhmm,
)
from services.final_report import normalize_history
from services.flex_service import record_flex
from services.history_service import (
    build_month_record,
    month_prefix,
    safe_number,
    update_quarter_summary,
)

MAX_NET_HOURS_PER_DAY = 10.0       # Working Hours Act: more than 10 h is a warning, not an error
MAX_SESSIONS_PER_MONTH = 2000
MONTH_NAMES = list(Config.MONATS_NUMMERN.keys())
RELIABLE_PERIOD_SOURCES = ('header', 'filename')

# Errors reject the month, warnings need the confirmation of the user.
ERRORS = ('not_pdf', 'file_too_large', 'parse_failed', 'period_unknown', 'period_multi_month', 'no_sessions', 'too_many_sessions',
          'future_month', 'future_date', 'invalid_date', 'date_outside_month', 'invalid_time',
          'end_not_after_start', 'overlap', 'duplicate_month', 'overlaps_existing', 'invalid_quote')
WARNINGS = ('period_from_filename', 'non_working_day', 'long_day', 'replaces_history', 'has_manual_entries')


def clean_flex_balance(raw):
    """Flextime balance from a statement, validated: only known numeric fields are kept."""
    if not isinstance(raw, dict):
        return None
    out = {}
    for key in ('previous', 'current', 'total'):
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) < 10000:
            out[key] = round(float(value), 2)
    if not out:
        return None
    for key in ('year', 'month'):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            out[key] = value
    return out


def _issue(code, date=None, detail=None):
    issue = {'code': code}
    if date is not None:
        issue['date'] = date
    if detail is not None:
        issue['detail'] = detail
    return issue


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _status(errors, warnings):
    return 'error' if errors else ('warning' if warnings else 'ok')


def _group_by_day(sessions):
    days = {}
    for s in sessions:
        days.setdefault(s['date'], []).append(s)
    return days


def _day_net_hours(day_sessions):
    """Net hours per session of one day, with the break the time system deducts (as in the single import)."""
    pauses = assign_statement_breaks([(s['start_time'], s['end_time']) for s in day_sessions])
    return pauses, [calculate_net_hours(s['start_time'], s['end_time'], p)['net']
                    for s, p in zip(day_sessions, pauses)]


def review_sessions(year, month, sessions, today=None):
    """Check the sessions of one month. Returns (errors, warnings, summary)."""
    today = today or datetime.now()
    errors, warnings = [], []

    if not (_is_int(year) and _is_int(month) and 1990 <= year <= 2100 and 1 <= month <= 12):
        return [_issue('period_unknown')], [], {}
    if (year, month) > (today.year, today.month):
        errors.append(_issue('future_month', detail=f'{year}-{month:02d}'))
    if not isinstance(sessions, list) or not sessions:
        return errors + [_issue('no_sessions')], [], {}
    if len(sessions) > MAX_SESSIONS_PER_MONTH:
        return errors + [_issue('too_many_sessions', detail=str(len(sessions)))], [], {}

    valid = []
    for s in sessions:
        if not isinstance(s, dict):
            errors.append(_issue('invalid_date'))
            continue
        date, start, end = s.get('date'), s.get('start_time'), s.get('end_time')
        try:
            day = datetime.strptime(date, '%Y-%m-%d')
            if day.strftime('%Y-%m-%d') != date:
                raise ValueError(date)
        except (ValueError, TypeError):
            errors.append(_issue('invalid_date', detail=str(date)))
            continue
        if (day.year, day.month) != (year, month):
            errors.append(_issue('date_outside_month', date=date))
            continue
        if day > today:
            errors.append(_issue('future_date', date=date))
            continue
        try:
            start_min, end_min = parse_hhmm(start), parse_hhmm(end)
        except ValueError:
            errors.append(_issue('invalid_time', date=date, detail=f'{start} - {end}'))
            continue
        if end_min <= start_min:
            errors.append(_issue('end_not_after_start', date=date, detail=f'{start} - {end}'))
            continue
        valid.append({'date': date, 'start_time': start, 'end_time': end,
                      'is_remote': bool(s.get('is_remote', True)), 'start_min': start_min, 'end_min': end_min})

    days = _group_by_day(valid)
    remote_total = net_total = 0.0
    for date in sorted(days):
        ordered = sorted(days[date], key=lambda s: (s['start_min'], s['end_min']))
        if any(a['end_min'] > b['start_min'] for a, b in zip(ordered, ordered[1:])):
            errors.append(_issue('overlap', date=date))
            continue
        pauses, nets = _day_net_hours(ordered)
        day_net = sum(nets)
        net_total += day_net
        remote_total += sum(n for s, n in zip(ordered, nets) if s['is_remote'])
        if day_net > MAX_NET_HOURS_PER_DAY:
            warnings.append(_issue('long_day', date=date, detail=f'{day_net:.2f}'))
        reason = is_working_day_valid(date, {}, allow_historical=True)
        if reason:
            warnings.append(_issue('non_working_day', date=date, detail=reason))

    summary = {'days': len(days), 'session_count': len(valid),
               'net_hours': round(net_total, 2), 'remote_hours': round(remote_total, 2)}
    return errors, warnings, summary


def _finalize(report):
    report['status'] = _status(report['errors'], report['warnings'])
    return report


def failed_report(filename, code, detail=None):
    """Report for a file that could not be analysed at all (wrong type, too large, unreadable)."""
    return _finalize({'filename': filename, 'year': None, 'month': None, 'month_name': None, 'key': None,
                      'errors': [_issue(code, detail=detail)], 'warnings': [], 'summary': {}, 'sessions': [],
                      'flex_balance': None, 'quote': None, 'target': None})


def review_statement(analysis, filename, today=None):
    """Report for ONE statement from `PDFService.analyze_pdf` (see the module docstring)."""
    report = {'filename': filename, 'year': None, 'month': None, 'month_name': None, 'key': None,
              'errors': [], 'warnings': [], 'summary': {}, 'sessions': [], 'flex_balance': None,
              'quote': None, 'target': None}
    if not isinstance(analysis, dict) or not analysis.get('success'):
        message = analysis.get('message') if isinstance(analysis, dict) else None
        report['errors'].append(_issue('parse_failed', detail=message))
        return _finalize(report)

    structure = analysis.get('structure') or {}
    year, month = structure.get('year'), structure.get('month')
    source = structure.get('period_source')
    if _is_int(year) and _is_int(month) and 1 <= month <= 12:
        report.update(year=year, month=month, month_name=MONTH_NAMES[month - 1], key=f'{year}-{month:02d}')
    if source not in RELIABLE_PERIOD_SOURCES or report['key'] is None:
        report['errors'].append(_issue('period_unknown'))
    elif source == 'filename':
        report['warnings'].append(_issue('period_from_filename'))

    period_end = structure.get('period_end')
    if report['key'] and isinstance(period_end, str) and period_end[:7] != report['key']:
        report['errors'].append(_issue('period_multi_month', detail=period_end))

    report['sessions'] = analysis.get('sessions') if isinstance(analysis.get('sessions'), list) else []
    report['flex_balance'] = clean_flex_balance(analysis.get('flex_balance'))
    if report['key']:
        errors, warnings, summary = review_sessions(year, month, report['sessions'], today)
        report['errors'] += errors
        report['warnings'] += warnings
        report['summary'] = summary
    return _finalize(report)


def review_batch(reports):
    """Checks across statements: two files for the same month would silently overwrite each other."""
    by_key = {}
    for r in reports:
        if r.get('key'):
            by_key.setdefault(r['key'], []).append(r)
    for key, group in by_key.items():
        if len(group) > 1:
            for r in group:
                others = ', '.join(o['filename'] for o in group if o is not r)
                r['errors'].append(_issue('duplicate_month', detail=others))
                _finalize(r)
    return reports


def _is_closed(state, year, month):
    """True when the month is over (it belongs into the history); the open month and later ones are not."""
    return (year, month) < (state['aktuelles_jahr'], Config.MONATS_NUMMERN[state['aktueller_monat']])


def _manual_entries_state(state, year, month):
    """A state that only holds the entries of that month that were NOT imported from a statement."""
    prefix = month_prefix(MONTH_NAMES[month - 1], year)
    kept = {}
    for date, entries in (state.get('daily_records') or {}).items():
        if isinstance(date, str) and date.startswith(prefix) and isinstance(entries, list):
            manual = [e for e in entries if isinstance(e, dict) and e.get('source') != 'pdf_import']
            if manual:
                kept[date] = manual
    return {'daily_records': kept, 'language': state.get('language', 'de')}


def state_issues(state, year, month, sessions):
    """(errors, warnings) that depend on the saved state."""
    errors, warnings = [], []
    month_name = MONTH_NAMES[month - 1]
    manual = _manual_entries_state(state, year, month)
    clashes = sorted({s['date'] for s in sessions
                      if check_time_overlap(s['date'], s['start_time'], s['end_time'], manual)})
    for date in clashes:
        errors.append(_issue('overlaps_existing', date=date))
    manual_count = sum(len(v) for v in manual['daily_records'].values())
    if manual_count and not clashes:
        warnings.append(_issue('has_manual_entries', detail=str(manual_count)))
    if any(isinstance(m, dict) and m.get('monat') == month_name and m.get('jahr') == year
           for m in state.get('monatliche_historie') or []):
        warnings.append(_issue('replaces_history'))
    return errors, warnings


def annotate_with_state(report, state):
    """Add what the saved state knows to a report (read only)."""
    if report.get('key') and not report['errors']:
        errors, warnings = state_issues(state, report['year'], report['month'], report['sessions'])
        report['errors'] += errors
        report['warnings'] += warnings
        _finalize(report)
    if report.get('key'):
        report['target'] = 'history' if _is_closed(state, report['year'], report['month']) else 'daily'
        report['quote'] = _existing_quote(state, report['year'], report['month'])
    return report


def _existing_quote(state, year, month):
    month_name = MONTH_NAMES[month - 1]
    for m in state.get('monatliche_historie') or []:
        if isinstance(m, dict) and m.get('monat') == month_name and m.get('jahr') == year:
            return safe_number(m.get('individuelle_quote'), state['individuelle_quote_prozent'])
    return state['individuelle_quote_prozent']


def _entries_for(sessions, now_ms):
    """Daily-record entries for the sessions of one month (break per day derived like the single import)."""
    entries = []
    for date, day in sorted(_group_by_day(sessions).items()):
        ordered = sorted(day, key=lambda s: (s['start_time'], s['end_time']))
        pauses, nets = _day_net_hours(ordered)
        for s, pause, net in zip(ordered, pauses, nets):
            entries.append({
                'id': f"{date}|{s['start_time']}|{s['end_time']}|{now_ms}",
                'datum': date,
                'startTime': s['start_time'],
                'endTime': s['end_time'],
                'pauseMinutes': pause,
                'remoteStundenHeute': net if s.get('is_remote', True) else 0,
                'totalStundenHeute': net,
                'source': 'pdf_import',
                'pauseWarning': None,
                'pauseWarningDe': None,
                'pauseWarningEn': None,
            })
    return entries


def _replace_statement_entries(state, year, month, new_entries):
    """Drop the earlier statement entries of the month, then add the new ones (a second import corrects)."""
    prefix = month_prefix(MONTH_NAMES[month - 1], year)
    records = state.setdefault('daily_records', {})
    for date in [d for d in records if isinstance(d, str) and d.startswith(prefix)]:
        entries = records[date]
        kept = [e for e in entries if not (isinstance(e, dict) and e.get('source') == 'pdf_import')] \
            if isinstance(entries, list) else entries
        if kept:
            records[date] = kept
        else:
            del records[date]
    for entry in new_entries:
        records.setdefault(entry['datum'], []).append(entry)


def _rejected(item, codes):
    return {'key': item.get('key'), 'filename': item.get('filename'), 'status': 'rejected', 'codes': codes,
            'target': None, 'entries': 0}


def _import_month(state, item, today, now_ms):
    year, month, sessions = item.get('year'), item.get('month'), item.get('sessions')
    errors, warnings, _ = review_sessions(year, month, sessions, today)
    if not errors:
        more_errors, more_warnings = state_issues(state, year, month, sessions)
        errors, warnings = errors + more_errors, warnings + more_warnings

    quote = item.get('quote')
    if quote is not None:
        value = safe_number(quote, None)
        if value is None or not Config.MIN_INDIVIDUELLE_QUOTE_PROZENT <= value <= Config.MAX_INDIVIDUELLE_QUOTE_PROZENT:
            errors.append(_issue('invalid_quote', detail=str(quote)))
        quote = value
    key = f'{year}-{month:02d}' if _is_int(year) and _is_int(month) and 1 <= month <= 12 else None
    item = dict(item, key=key)
    if errors:
        return _rejected(item, [e['code'] for e in errors]), None
    if warnings and item.get('confirmed') is not True:
        return _rejected(item, ['needs_confirmation'] + [w['code'] for w in warnings]), None

    _replace_statement_entries(state, year, month, _entries_for(sessions, now_ms))
    month_name = MONTH_NAMES[month - 1]
    target = 'daily'
    quartal = None
    if _is_closed(state, year, month):
        record = build_month_record(state, month_name, year,
                                    _existing_quote(state, year, month) if quote is None else quote)
        history = [m for m in state.get('monatliche_historie') or []
                   if not (isinstance(m, dict) and m.get('monat') == month_name and m.get('jahr') == year)]
        history.append(record)
        state['monatliche_historie'] = normalize_history(history)
        target, quartal = 'history', record['quartal']
    entries = sum(len(v) for k, v in state['daily_records'].items()
                  if isinstance(k, str) and k.startswith(month_prefix(month_name, year)))
    return {'key': key, 'filename': item.get('filename'), 'status': 'imported', 'codes': [w['code'] for w in warnings],
            'target': target, 'entries': entries}, quartal


def apply_batch(state, months, today=None):
    """Import the confirmed months into `state` (changed in place; the caller saves). Returns the results."""
    today = today or datetime.now()
    now_ms = int(today.timestamp() * 1000)
    results, quartals, newest_flex = [], set(), None

    items = [m for m in months if isinstance(m, dict)]
    items.sort(key=lambda m: (m.get('year') if _is_int(m.get('year')) else 0,
                              m.get('month') if _is_int(m.get('month')) else 0))
    for item in items:
        result, quartal = _import_month(state, item, today, now_ms)
        results.append(result)
        if quartal:
            quartals.add(quartal)
        flex = clean_flex_balance(item.get('flex_balance'))
        if result['status'] == 'imported' and flex:
            record_flex(state, flex, item['year'], item['month'])       # every month keeps its own numbers
            when = (item['year'], item['month'])
            if newest_flex is None or when >= newest_flex[0]:
                newest_flex = (when, flex)

    for quartal in quartals:
        update_quarter_summary(state['monatliche_historie'], quartal)

    if newest_flex:
        current = state.get('gleitzeit_saldo') if isinstance(state.get('gleitzeit_saldo'), dict) else {}
        current_when = (current.get('year') if _is_int(current.get('year')) else 0,
                        current.get('month') if _is_int(current.get('month')) else 0)
        if newest_flex[0] >= current_when:
            state['gleitzeit_saldo'] = newest_flex[1]
    return results
