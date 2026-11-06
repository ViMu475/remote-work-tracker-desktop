"""Detailed analysis of one month and proposals to reduce (or build up) flextime.

The month analysis is computed from the daily records of the app: net hours per day against the target hours,
a running balance, weeks, working days without an entry (holiday, leave, flextime day ...) and the usual
signs of overtime (days above 10 hours, work before 06:00 or after 20:00, work on a non-working day).
It is shown next to the numbers of the statement (balance at the start / end of the month, change in the month),
because the statement also counts absences that are not in the daily records.

The proposals follow the rules of the employee portal: above 40 hours of flextime the balance is yellow,
above 60 hours red (the hours above 60 are cut off at the end of the month). They only suggest, nothing is changed.
"""
import calendar
from datetime import date, timedelta

from config import Config
from services import flex_service
from services.calculation import SPECIAL_DAY_FACTOR

LONG_DAY_HOURS = 10.0
EARLIEST_START = 6 * 60          # work before 06:00 does not count
LATEST_END = 20 * 60             # work after 20:00 does not count
TARGET_BUFFER = 30.0             # comfortable level below the yellow limit, the goal of the proposals
HIGH_FROM = 50.0                 # from here on the proposals are urgent
MIN_HORIZON_WORKDAYS = 5         # fewer working days left in the month: plan until the end of the next month
TREND_MONTHS = 3
MIN_TREND_PER_MONTH = 0.5
MAX_TREND_WARNING_MONTHS = 6
DAILY_SURPLUS_FROM = 0.3
PRIORITIES = {'high': 0, 'medium': 1, 'info': 2}


def _number(value, default=0.0):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value else default


def _minutes(clock):
    try:
        hours, minutes = str(clock).split(':')
        return int(hours) * 60 + int(minutes)
    except (ValueError, TypeError):
        return None


def _clock(minutes):
    return f'{int(minutes) // 60:02d}:{int(minutes) % 60:02d}'


def target_hours(day, per_day):
    """Target hours of a calendar day: 0 on weekends and holidays, the special days of December are shortened."""
    if day.weekday() >= 5 or day.isoformat() in Config.BAYERN_FEIERTAGE:
        return 0.0
    return per_day * SPECIAL_DAY_FACTOR.get((day.month, day.day), 1.0)


def workdays(start, end, per_day=8.0):
    """Working days (with target hours) from `start` to `end`, both included."""
    days, day = [], start
    while day <= end:
        if target_hours(day, per_day) > 0:
            days.append(day)
        day += timedelta(days=1)
    return days


def _day_entries(state, year, month):
    """{date: [entries]} of one month from the daily records."""
    prefix = f'{year}-{month:02d}-'
    out = {}
    records = state.get('daily_records')
    for key, entries in (records.items() if isinstance(records, dict) else ()):
        if not (isinstance(key, str) and key.startswith(prefix) and isinstance(entries, list)):
            continue
        try:
            day = date.fromisoformat(key)
        except ValueError:
            continue
        entries = [e for e in entries if isinstance(e, dict)]
        if entries:
            out[day] = entries
    return out


def analyze_month(state, year, month, today=None):
    """The detailed analysis of one month (see the module text). `today` defaults to the current date."""
    today = today or date.today()
    per_day = _number(state.get('soll_stunden_pro_tag'), 8.0) or 8.0
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    first_day = date(year, month, 1)
    through = last_day if today >= last_day else (today if today >= first_day else None)   # target hours count until here
    entries = _day_entries(state, year, month)

    days = sorted(set(entries) | (set(workdays(first_day, through, per_day)) if through else set()))
    rows, balance = [], 0.0
    for day in days:
        mine = entries.get(day, [])
        net = sum(_number(e.get('totalStundenHeute')) for e in mine)
        remote = sum(_number(e.get('remoteStundenHeute')) for e in mine)
        starts = [m for m in (_minutes(e.get('startTime')) for e in mine) if m is not None]
        ends = [m for m in (_minutes(e.get('endTime')) for e in mine) if m is not None]
        soll = target_hours(day, per_day) if (through and day <= through) else 0.0
        balance += net - soll
        flags = []
        if not mine:
            flags.append('no_entry')
        if net > LONG_DAY_HOURS:
            flags.append('long_day')
        if starts and min(starts) < EARLIEST_START:
            flags.append('early')
        if ends and max(ends) > LATEST_END:
            flags.append('late')
        if mine and target_hours(day, per_day) == 0:
            flags.append('non_working_day')
        rows.append({'datum': day.isoformat(), 'weekday': day.weekday(), 'entries': len(mine),
                     'start': _clock(min(starts)) if starts else None, 'end': _clock(max(ends)) if ends else None,
                     'net': round(net, 2), 'remote': round(remote, 2), 'soll': round(soll, 2),
                     'delta': round(net - soll, 2), 'balance': round(balance, 2), 'flags': flags})

    weeks = {}
    for row in rows:
        iso = date.fromisoformat(row['datum']).isocalendar()
        week = weeks.setdefault((iso[0], iso[1]), {'year': iso[0], 'week': iso[1], 'days': 0, 'net': 0.0, 'soll': 0.0})
        week['days'] += 1 if row['net'] > 0 else 0
        week['net'] += row['net']
        week['soll'] += row['soll']
    week_rows = [{**w, 'net': round(w['net'], 2), 'soll': round(w['soll'], 2), 'delta': round(w['net'] - w['soll'], 2)}
                 for _, w in sorted(weeks.items())]

    worked = [r for r in rows if r['net'] > 0]
    net_total = sum(r['net'] for r in rows)
    soll_total = sum(r['soll'] for r in rows)
    start_minutes = [_minutes(r['start']) for r in worked if r['start']]
    end_minutes = [_minutes(r['end']) for r in worked if r['end']]
    longest = max(worked, key=lambda r: r['net']) if worked else None
    delta_calc = round(net_total - soll_total, 2)

    flex = next((e for e in flex_service.series(state) if (e['jahr'], e['monat']) == (year, month)), None)
    month_over = through == last_day
    aktuell = flex.get('aktuell') if flex else None
    return {
        'year': year, 'month': month, 'monat_name': flex_service.MONTH_NAMES[month - 1],
        'complete': month_over, 'has_entries': bool(entries), 'days': rows, 'weeks': week_rows,
        'totals': {
            'days_worked': len(worked), 'net': round(net_total, 2), 'remote': round(sum(r['remote'] for r in rows), 2),
            'soll': round(soll_total, 2), 'delta_calc': delta_calc,
            'avg_net': round(net_total / len(worked), 2) if worked else None,
            'avg_start': _clock(sum(start_minutes) / len(start_minutes)) if start_minutes else None,
            'avg_end': _clock(sum(end_minutes) / len(end_minutes)) if end_minutes else None,
            'longest': {'datum': longest['datum'], 'net': longest['net']} if longest else None,
            'long_days': sum(1 for r in rows if 'long_day' in r['flags']),
            'early_days': sum(1 for r in rows if 'early' in r['flags']),
            'late_days': sum(1 for r in rows if 'late' in r['flags']),
            'non_working_days': sum(1 for r in rows if 'non_working_day' in r['flags']),
            'missing_days': [r['datum'] for r in rows if 'no_entry' in r['flags']],
            'missing_hours': round(sum(r['soll'] for r in rows if 'no_entry' in r['flags']), 2),
        },
        'flex': ({k: flex[k] for k in ('vorperiode', 'aktuell', 'gesamt', 'status') if flex.get(k) is not None} if flex else None),
        'difference': round(aktuell - delta_calc, 2) if (aktuell is not None and month_over and entries) else None,
    }


def advice(state, today=None, entries=None, analysis=None):
    """Proposals from the latest month-end balance (see the module text).

    Returns {'as_of', 'balance', 'status', 'trend', 'items'}; every item has a code (translated by the page),
    a priority (high, medium, info) and its numbers in `params`. `analysis`: analyze_month() of the latest month.
    """
    today = today or date.today()
    entries = [e for e in (entries if entries is not None else flex_service.series(state))
               if isinstance(e, dict) and isinstance(e.get('gesamt'), (int, float))]
    if not entries:
        return {'as_of': None, 'balance': None, 'status': None, 'trend': None, 'items': []}
    latest = entries[-1]
    balance = latest['gesamt']
    state_now = flex_service.status(balance)
    per_day = _number(state.get('soll_stunden_pro_tag'), 8.0) or 8.0
    changes = [e['aktuell'] for e in entries[-TREND_MONTHS:] if isinstance(e.get('aktuell'), (int, float))]
    trend = round(sum(changes) / len(changes), 2) if changes else None

    end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    plan_days = workdays(today, end, per_day)
    if len(plan_days) < MIN_HORIZON_WORKDAYS:
        following = end + timedelta(days=1)
        plan_days = workdays(today, date(following.year, following.month, calendar.monthrange(following.year, following.month)[1]), per_day)

    items = []

    def add(code, priority, **params):
        items.append({'code': code, 'priority': priority, 'params': params})

    if state_now == flex_service.RED_POS:
        add('cap_cut', 'high', over=round(balance - flex_service.RED_LIMIT, 2), limit=flex_service.RED_LIMIT)
    if balance > TARGET_BUFFER:
        need = round(balance - TARGET_BUFFER, 2)
        priority = 'high' if (balance >= HIGH_FROM or state_now == flex_service.RED_POS) else 'medium'
        if state_now in (flex_service.YELLOW_POS, flex_service.RED_POS):
            add('reduce', priority, balance=balance, over=round(balance - flex_service.YELLOW_LIMIT, 2),
                limit=flex_service.YELLOW_LIMIT, target=TARGET_BUFFER, need=need)
        else:
            add('near_limit', priority, balance=balance, to_limit=round(flex_service.YELLOW_LIMIT - balance, 2),
                limit=flex_service.YELLOW_LIMIT, target=TARGET_BUFFER, need=need)
        full = int(need // per_day)
        add('flex_days', priority, days=round(need / per_day, 1), full_days=full,
            rest=round(need - full * per_day, 2), soll=per_day)
        if plan_days:
            add('shorter_days', priority, per_day=round(need / len(plan_days), 2), workdays=len(plan_days),
                until=plan_days[-1].isoformat())
        if balance >= HIGH_FROM or state_now == flex_service.RED_POS:
            add('approval', 'medium')
        if trend is not None and trend > MIN_TREND_PER_MONTH:
            add('trend_up_over', 'medium', trend=trend)
    elif trend is not None and trend > MIN_TREND_PER_MONTH:
        months = (flex_service.YELLOW_LIMIT - balance) / trend
        if months <= MAX_TREND_WARNING_MONTHS:
            add('trend_up', 'medium', trend=trend, months=round(months, 1), limit=flex_service.YELLOW_LIMIT)

    if balance > 10 and analysis and analysis.get('totals'):
        totals = analysis['totals']
        if totals.get('long_days'):
            add('long_days', 'medium', n=totals['long_days'], limit=LONG_DAY_HOURS)
        surplus = (totals['avg_net'] - per_day) if totals.get('avg_net') is not None else 0.0
        if surplus > DAILY_SURPLUS_FROM:
            add('daily_surplus', 'medium', avg_over=round(surplus, 2), per_month=round(surplus * totals['days_worked'], 1), soll=per_day)
        if totals.get('non_working_days'):
            add('weekend_work', 'medium', n=totals['non_working_days'])
        if totals.get('early_days') or totals.get('late_days'):
            add('outside_window', 'info', n=totals.get('early_days', 0) + totals.get('late_days', 0))

    if state_now in (flex_service.YELLOW_NEG, flex_service.RED_NEG):
        add('check_missing', 'high', balance=balance)
    elif balance < -10:
        add('build_up', 'info', balance=balance, need=round(-balance, 2))
    if not items:
        add('on_track', 'info', balance=balance)

    items.sort(key=lambda item: PRIORITIES[item['priority']])
    return {'as_of': {'jahr': latest['jahr'], 'monat': latest['monat'], 'monat_name': flex_service.MONTH_NAMES[latest['monat'] - 1]},
            'balance': balance, 'status': state_now, 'trend': trend, 'items': items}
