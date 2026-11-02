"""Model-based long-run ("soak") testing of the Flask API.

An independent model of the app (entries, history, quota, view, clock) is driven in
parallel to the real API. After EVERY step the complete visible state is compared with
the model and a list of invariants is checked. The clock is frozen per request and moved
forward step by step, so month changes, quarter ends and year changes really happen.

The model encodes what the app is specified to do. Behaviour that is questionable but
deliberate (e.g. "Monat abschliessen" closes the VIEWED month and clears ALL entries)
is mirrored and counted in `Model.obs` so it shows up in the report instead of
silently passing.
"""
import calendar
import collections
import copy
import datetime
import json
import os
import random
import sys

from freezegun import freeze_time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config  # noqa: E402
from tests.test_holidays import expected_holidays  # noqa: E402

MONTHS = list(Config.MONATS_NUMMERN)
FIRST_DAY = datetime.datetime(2025, 1, 2, 9, 0)
LAST_DAY = datetime.datetime(2030, 12, 30, 9, 0)   # holiday table ends 2030
QUARTER_END_MONTHS = (3, 6, 9, 12)


def mins(t):
    return int(t[:2]) * 60 + int(t[3:])


def hhmm(total):
    return f'{total // 60:02d}:{total % 60:02d}'


def net_hours(start, end, pause):
    a, b = mins(start), mins(end)
    if b < a:
        b += 1440
    return (b - a) / 60 - pause / 60


def holidays_of(year):
    return expected_holidays(year) if 2025 <= year <= 2030 else set()   # app has no table outside


def is_workday(d):
    return d.weekday() < 5 and d not in holidays_of(d.year)


def soll(year, month, per_day):
    n = sum(1 for day in range(1, calendar.monthrange(year, month)[1] + 1)
            if is_workday(datetime.date(year, month, day)))
    return n * per_day


def quartal_label(year, month):
    return f'Q{(month - 1) // 3 + 1}/{year}'


def month_index(year, month):
    return year * 12 + month - 1


def from_index(i):
    i = max(i, month_index(2025, 1))      # holiday table starts in 2025
    return i // 12, i % 12 + 1


class Fail(AssertionError):
    pass


class Model:
    def __init__(self, now, quarter_years):
        self.now = now
        self.quarter_years = set(quarter_years)
        self.entries = {}                  # (datum, start, end) -> (pause, remote, total)
        self.history = []                  # dicts
        self.quote = 40.0
        self.soll_day = 8.0
        self.view = (now.year, now.month)
        self.obs = collections.Counter()

    # -- helpers ----------------------------------------------------
    def snapshot(self):
        return copy.deepcopy((self.entries, self.history, self.quote, self.soll_day, self.view))

    def restore(self, snap):
        self.entries, self.history, self.quote, self.soll_day, self.view = copy.deepcopy(snap)

    def overlaps(self, datum, start, end, ignore=None):
        a, b = mins(start), mins(end)
        if b < a:
            b += 1440
        for (d, s, e) in self.entries:
            if d != datum or (s, e) == ignore:
                continue
            x, y = mins(s), mins(e)
            if y < x:
                y += 1440
            if a < y and x < b:
                return True
        return False

    def view_sums(self):
        y, m = self.view
        prefix = f'{y}-{m:02d}-'
        rem = tot = 0.0
        for (d, _s, _e), (_p, r, t) in self.entries.items():
            if d.startswith(prefix):
                rem += r
                tot += t
        return rem, tot

    def manual_allowed(self, datum):
        """Rules of is_working_day_valid without allow_historical: any month up to the current one."""
        d = datetime.date.fromisoformat(datum)
        if (d.year, d.month) > (self.now.year, self.now.month):
            return False
        return is_workday(d)


# ── statements ──────────────────────────────────────────────────────

def make_statement(year, month, rng, noise=True):
    sessions = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = datetime.date(year, month, day)
        iso = d.isoformat()
        if is_workday(d):
            if rng.random() < 0.35:
                parts = [('08:00', '12:00'), ('13:00', '17:30')]
            else:
                parts = [('08:00', '16:30')]
            for s, e in parts:
                sessions.append({'date': iso, 'start_time': s, 'end_time': e, 'is_remote': rng.random() < 0.5})
        if noise and rng.random() < 0.04:                       # weekend or holiday booking: must be rejected
            if d.weekday() >= 5 or d in holidays_of(year):
                sessions.append({'date': iso, 'start_time': '09:00', 'end_time': '10:00', 'is_remote': True})
        if noise and is_workday(d) and rng.random() < 0.03:     # overlapping booking: must be rejected
            sessions.append({'date': iso, 'start_time': '10:00', 'end_time': '11:00', 'is_remote': True})
    return sessions


# ── driver ──────────────────────────────────────────────────────────

class Driver:
    def __init__(self, client, data_file, seed=0, quarter_years=range(2025, 2031), now=FIRST_DAY, label=''):
        self.client = client
        self.data_file = data_file
        self.rng = random.Random(seed)
        self.seed = seed
        self.label = label
        self.model = Model(now, quarter_years)
        self.log = collections.deque(maxlen=12)
        self.steps = 0
        self.checks = 0
        self.timing = collections.defaultdict(list)
        self.view_current()

    # -- plumbing ---------------------------------------------------
    def call(self, method, path, payload=None):
        with freeze_time(self.model.now):
            fn = getattr(self.client, method)
            resp = fn(path, json=payload) if payload is not None else fn(path)
        return resp

    def fail(self, msg):
        ctx = '\n  '.join(self.log)
        raise Fail(f'[{self.label} seed={self.seed} step={self.steps} now={self.model.now:%Y-%m-%d}] {msg}\n'
                   f'  letzte Schritte:\n  {ctx}')

    def note(self, text):
        self.steps += 1
        self.log.append(f'{self.steps}: {text}')

    def expect(self, cond, msg):
        self.checks += 1
        if not cond:
            self.fail(msg)

    def get_state_keys(self):
        return [(d, r['startTime'], r['endTime']) for d, lst in self.get_state()['daily_records'].items() for r in lst]

    def get_state(self):
        resp = self.call('get', '/api/state')
        self.expect(resp.status_code == 200, f'GET /api/state -> {resp.status_code}')
        return resp.get_json()

    # -- operations ---------------------------------------------------
    def view_current(self):
        self.note('Ansicht: aktueller Monat')
        resp = self.call('post', '/api/view/current_month')
        self.expect(resp.status_code == 200, f'view/current_month -> {resp.status_code}')
        self.model.view = (self.model.now.year, self.model.now.month)
        self.check(resp.get_json()['state'])

    def view_month(self, year, month):
        self.note(f'Ansicht: {year}-{month:02d} wählen')
        resp = self.call('post', '/api/view/month', {'month': MONTHS[month - 1], 'year': year})
        self.expect(resp.status_code == 200, f'view/month -> {resp.status_code}')
        self.model.view = (year, month)
        self.check(resp.get_json()['state'])

    def advance_clock(self, days=None):
        days = days if days is not None else self.rng.choice([1, 1, 2, 3, 7, 14, 20, 31, 45])
        new = self.model.now + datetime.timedelta(days=days)
        if new > LAST_DAY:
            return
        self.note(f'Uhr +{days} Tage -> {new:%Y-%m-%d}')
        self.model.now = new
        self.check(self.get_state())

    def goto_first_of_next_month(self):
        y, m = self.model.now.year, self.model.now.month
        y, m = from_index(month_index(y, m) + 1)
        new = datetime.datetime(y, m, 1, 9, 0)
        if new > LAST_DAY:
            return False
        self.note(f'Uhr -> {new:%Y-%m-%d}')
        self.model.now = new
        self.check(self.get_state())
        return True

    def import_statement(self, year, month, sessions=None, label=''):
        m = self.model
        sessions = sessions if sessions is not None else make_statement(year, month, self.rng)
        self.note(f'Import {label}{year}-{month:02d} ({len(sessions)} Sessions)')
        accepted = rejected = 0
        for s in sessions:
            d = datetime.date.fromisoformat(s['date'])
            ok = (datetime.datetime(d.year, d.month, d.day) <= m.now and is_workday(d)
                  and not m.overlaps(s['date'], s['start_time'], s['end_time']))
            if ok:
                total = net_hours(s['start_time'], s['end_time'], 0)
                m.entries[(s['date'], s['start_time'], s['end_time'])] = (0, total if s['is_remote'] else 0.0, total)
                accepted += 1
            else:
                rejected += 1
        if sessions:
            first = datetime.date.fromisoformat(sessions[0]['date'])
            m.view = (first.year, first.month)
        resp = self.call('post', '/api/pdf/import', {'sessions': sessions})
        self.expect(resp.status_code == 200, f'pdf/import -> {resp.status_code}')
        data = resp.get_json()
        self.expect(data['imported_count'] == accepted,
                    f'Import: App hat {data["imported_count"]} Sessions übernommen, Modell erwartet {accepted}')
        self.expect(len(data['errors']) == rejected,
                    f'Import: App lehnt {len(data["errors"])} ab, Modell erwartet {rejected}')
        self.check(data['state'])
        return accepted, rejected

    def add_manual(self, datum, start, end, pause=30, remote=None):
        m = self.model
        self.note(f'Eintrag {datum} {start}-{end}')
        ok = (m.manual_allowed(datum) and not m.overlaps(datum, start, end))
        total = net_hours(start, end, pause)
        if remote is not None and remote > total + 1e-9:
            ok = False
        payload = {'datum': datum, 'start': start, 'end': end, 'pause': pause}
        if remote is not None:
            payload['remote'] = remote
        resp = self.call('post', '/api/protokoll', payload)
        self.expect(resp.status_code == (200 if ok else 400),
                    f'Eintrag {datum}: App antwortet {resp.status_code}, Modell erwartet {"200" if ok else "400"} ({resp.get_json().get("message")})')
        if ok:
            m.entries[(datum, start, end)] = (pause, total if remote is None else remote, total)
        self.check(resp.get_json().get('state') if ok else self.get_state())
        return ok

    def delete_entry(self, key):
        self.note(f'Löschen {key}')
        eid = self.find_id(key)
        resp = self.call('delete', f'/api/delete/{eid}')
        self.expect(resp.status_code == 200, f'delete {key} -> {resp.status_code}')
        del self.model.entries[key]
        self.check(resp.get_json()['state'])

    def update_entry(self, key, delta_min):
        m = self.model
        datum, start, end = key
        new_end_min = mins(end) + delta_min
        if not (mins(start) < new_end_min < 1440):
            return
        new_end = hhmm(new_end_min)
        self.note(f'Ändern {key} -> Ende {new_end}')
        pause, _remote, _total = m.entries[key]
        ok = (m.manual_allowed(datum) and not m.overlaps(datum, start, new_end, ignore=(start, end))
              and net_hours(start, new_end, pause) >= 0)       # app rejects a negative net time
        eid = self.find_id(key)
        resp = self.call('put', f'/api/update/{eid}', {'datum': datum, 'start': start, 'end': new_end, 'pause': pause})
        self.expect(resp.status_code == (200 if ok else 400),
                    f'Ändern {key}: App {resp.status_code}, Modell erwartet {"200" if ok else "400"} ({resp.get_json().get("message")})')
        if ok:
            total = net_hours(start, new_end, pause)
            del m.entries[key]
            m.entries[(datum, start, new_end)] = (pause, total, total)
            self.check(resp.get_json()['state'])
        else:
            self.check(self.get_state())

    def delete_all_entries(self):
        self.note('Alle Einträge löschen')
        resp = self.call('post', '/api/delete_all_entries')
        self.expect(resp.status_code == 200, f'delete_all_entries -> {resp.status_code}')
        self.model.entries = {}
        self.check(resp.get_json()['state'])

    def set_quote(self, quote):
        self.note(f'Quote {quote}')
        resp = self.call('post', '/api/quote', {'quote': quote})
        self.expect(resp.status_code == 200, f'quote -> {resp.status_code}')
        self.model.quote = float(quote)
        self.check(resp.get_json()['state'])

    def set_soll(self, hours):
        self.note(f'Soll/Tag {hours}')
        resp = self.call('post', '/api/sollstunden', {'sollStunden': hours})
        self.expect(resp.status_code == 200, f'sollstunden -> {resp.status_code}')
        self.model.soll_day = float(hours)
        self.check(resp.get_json()['state'])

    def month_switch(self):
        m = self.model
        y, mo = m.view
        self.note(f'Monat abschließen ({y}-{mo:02d}, aktuell {m.now:%Y-%m})')
        rem, tot = m.view_sums()
        s = soll(y, mo, m.soll_day)
        snap = {'monat': MONTHS[mo - 1], 'jahr': y, 'soll': s, 'ist_remote': rem, 'ist_gesamt': tot,
                'max': s * m.quote / 100, 'quote': m.quote, 'quartal': quartal_label(y, mo)}
        if (y, mo) != (m.now.year, m.now.month):
            m.obs['Monatsabschluss eines nicht aktuellen Monats'] += 1
        prefix = f'{y}-{mo:02d}-'
        has_entries = any(d.startswith(prefix) for (d, _s, _e) in m.entries)
        existing = next((i for i, h in enumerate(m.history) if h['monat'] == snap['monat'] and h['jahr'] == y), None)
        changed = True
        if existing is None:
            m.history.append(snap)
        elif has_entries:
            m.history[existing] = snap
            m.obs['Monat in der Historie aktualisiert'] += 1
        else:
            changed = False
            m.obs['Erneuter Abschluss ohne Einträge: Historie unverändert'] += 1
        m.history.sort(key=lambda h: (h['jahr'], MONTHS.index(h['monat'])))
        if changed and mo in QUARTER_END_MONTHS and y in m.quarter_years:
            qh = [h for h in m.history if h['quartal'] == snap['quartal']]
            if len(qh) >= 3:
                base = qh[0]['quote']
                if sum(h['ist_remote'] for h in qh) > sum(h['soll'] for h in qh) * base / 100:
                    m.quote = max(base - 10, 40.0)
                else:
                    m.quote = min(base + 10, 60.0)
                m.obs['Quartalsabschluss ausgewertet'] += 1
        m.entries = {k: v for k, v in m.entries.items() if not k[0].startswith(prefix)}
        m.view = from_index(month_index(y, mo) + 1)
        resp = self.call('post', '/api/month/switch')
        self.expect(resp.status_code == 200, f'month/switch -> {resp.status_code}')
        self.check(resp.get_json()['state'])

    def delete_month(self, name, year):
        m = self.model
        self.note(f'Historie: Monat {name} {year} löschen')
        exists = any(h['monat'] == name and h['jahr'] == year for h in m.history)
        resp = self.call('delete', f'/api/delete_month/{name}/{year}')
        self.expect(resp.status_code == (200 if exists else 404),
                    f'delete_month {name} {year}: App {resp.status_code}, Modell erwartet {"200" if exists else "404"}')
        m.history = [h for h in m.history if not (h['monat'] == name and h['jahr'] == year)]
        self.check(self.get_state())

    def clear_history(self):
        m = self.model
        self.note('Komplette Historie löschen')
        resp = self.call('post', '/api/clear_all_history')
        self.expect(resp.status_code == 200, f'clear_all_history -> {resp.status_code}')
        m.history, m.entries, m.quote = [], {}, 40.0
        m.view = (m.now.year, m.now.month)
        self.check(resp.get_json()['state'])

    def backup(self):
        self.note('Backup')
        resp = self.call('get', '/api/backup')
        self.expect(resp.status_code == 200, f'backup -> {resp.status_code}')
        return json.loads(resp.data), self.model.snapshot()

    def restore(self, backup, snap):
        self.note('Restore')
        resp = self.call('post', '/api/restore', backup)
        self.expect(resp.status_code == 200, f'restore -> {resp.status_code}')
        self.model.restore(snap)
        self.check(resp.get_json()['state'])

    # -- verification ---------------------------------------------------
    def find_id(self, key):
        st = self.get_state()
        for rec in st['daily_records'].get(key[0], []):
            if (rec['startTime'], rec['endTime']) == (key[1], key[2]):
                return rec['id']
        self.fail(f'Eintrag {key} fehlt in der App')

    def check(self, response_state):
        m = self.model
        st = self.get_state()
        self.expect(response_state is not None, 'Antwort ohne Zustand')
        for key in ('current_month_data', 'view_month', 'view_year', 'individuelle_quote_prozent', 'soll_stunden_pro_tag'):
            self.expect(response_state[key] == st[key], f'Antwort und GET /api/state unterscheiden sich in {key}: {response_state[key]} / {st[key]}')
        self.expect(len(response_state['monatliche_historie']) == len(st['monatliche_historie']), 'Historie in Antwort und GET verschieden lang')

        # 1) system month follows the clock
        self.expect((st['aktuelles_jahr'], MONTHS.index(st['aktueller_monat']) + 1) == (m.now.year, m.now.month),
                    f'aktueller Monat {st["aktueller_monat"]} {st["aktuelles_jahr"]} passt nicht zur Uhr')
        # 2) view, quote, target hours per day
        self.expect((st['view_year'], MONTHS.index(st['view_month']) + 1) == m.view, f'Ansicht {st["view_month"]} {st["view_year"]}, Modell {m.view}')
        self.expect(st['individuelle_quote_prozent'] == m.quote, f'Quote {st["individuelle_quote_prozent"]}, Modell {m.quote}')
        self.expect(40 <= st['individuelle_quote_prozent'] <= 60, 'Quote außerhalb 40 bis 60')
        self.expect(st['soll_stunden_pro_tag'] == m.soll_day, f'Soll/Tag {st["soll_stunden_pro_tag"]}, Modell {m.soll_day}')
        # 3) all entries
        app = {}
        ids = set()
        for datum, lst in st['daily_records'].items():
            for r in lst:
                self.expect(r['datum'] == datum, f'Eintrag unter falschem Tag {datum}')
                self.expect(r['id'] not in ids, f'doppelte Eintrags-ID {r["id"]}')
                ids.add(r['id'])
                key = (datum, r['startTime'], r['endTime'])
                self.expect(key not in app, f'doppelter Eintrag {key}')
                app[key] = (r['pauseMinutes'], r['remoteStundenHeute'], r['totalStundenHeute'])
                self.expect(abs(r['totalStundenHeute'] - net_hours(r['startTime'], r['endTime'], r['pauseMinutes'])) < 1e-6,
                            f'Netto-Stunden von {key} falsch: {r["totalStundenHeute"]}')
                self.expect(-1e-9 <= r['remoteStundenHeute'] <= r['totalStundenHeute'] + 1e-9, f'Remote-Stunden von {key} unplausibel')
                self.expect(is_workday(datetime.date.fromisoformat(datum)), f'Eintrag an Wochenende/Feiertag {datum}')
        self.expect(set(app) == set(m.entries), f'Einträge weichen ab: nur App {sorted(set(app) - set(m.entries))[:3]}, nur Modell {sorted(set(m.entries) - set(app))[:3]}')
        for key, (p, r, t) in m.entries.items():
            ap = app[key]
            self.expect(abs(ap[0] - p) < 1e-9 and abs(ap[1] - r) < 1e-6 and abs(ap[2] - t) < 1e-6, f'Werte von {key}: App {ap}, Modell {(p, r, t)}')
        by_day = collections.defaultdict(list)
        for (d, s, e) in app:
            by_day[d].append((mins(s), mins(e) + (1440 if mins(e) < mins(s) else 0)))
        for d, spans in by_day.items():
            spans.sort()
            for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
                self.expect(b1 <= a2, f'überlappende Einträge am {d}')
        # 4) monthly numbers of the viewed month
        y, mo = m.view
        rem, tot = m.view_sums()
        c = st['current_month_data']
        s = soll(y, mo, m.soll_day)
        for name, want in (('ist_remote_stunden_laufend', rem), ('ist_arbeitszeit_laufend', tot),
                           ('soll_stunden_gesamt', s), ('max_remote_stunden', s * m.quote / 100)):
            self.expect(abs(c[name] - want) < 0.011, f'{name} zeigt {c[name]}, richtig für {y}-{mo:02d} ist {want}')
        # 5) history
        hist = st['monatliche_historie']
        self.expect(len(hist) == len(m.history), f'Historie hat {len(hist)} Einträge, Modell {len(m.history)}')
        for got, want in zip(hist, m.history):
            self.expect((got['monat'], got['jahr']) == (want['monat'], want['jahr']), f'Historie: {got["monat"]} {got["jahr"]} statt {want["monat"]} {want["jahr"]}')
            self.expect(got.get('quartal') == want['quartal'], f'Historie-Quartal {got.get("quartal")} statt {want["quartal"]}')
            for gk, wk in (('soll_stunden_gesamt', 'soll'), ('ist_remote_stunden_laufend', 'ist_remote'),
                           ('ist_arbeitszeit_laufend', 'ist_gesamt'), ('max_remote_stunden', 'max'), ('individuelle_quote', 'quote')):
                self.expect(abs(got[gk] - want[wk]) < 0.011, f'Historie {want["monat"]} {want["jahr"]}: {gk} {got[gk]} statt {want[wk]}')
        # 6) the file on disk is what the API reports
        with open(self.data_file, encoding='utf-8') as f:
            disk = json.load(f)
        self.expect(disk['daily_records'] == st['daily_records'], 'Zustandsdatei und API unterscheiden sich bei den Einträgen')
        self.expect(len(disk['monatliche_historie']) == len(hist), 'Zustandsdatei und API unterscheiden sich bei der Historie')
        self.expect(disk['individuelle_quote_prozent'] == st['individuelle_quote_prozent'], 'Zustandsdatei und API unterscheiden sich bei der Quote')
        return st

    # -- random operation ---------------------------------------------------
    def random_step(self):
        rng, m = self.rng, self.model
        r = rng.random()
        cur = month_index(m.now.year, m.now.month)
        if r < 0.28:                                         # load a statement: backward (mostly), current month, or forward
            off = rng.choice([0, 0, -1, -1, -2, -3, -6, -12, -24, -48, -70, 1, 2, 12])
            y, mo = from_index(cur + off)
            self.import_statement(y, mo, label='rückwärts ' if off < 0 else ('vorwärts ' if off > 0 else ''))
        elif r < 0.36:
            self.advance_clock()
        elif r < 0.40:
            self.goto_first_of_next_month()
        elif r < 0.52:                                       # manual entry
            y, mo = from_index(cur - rng.choice([0, 0, 0, 1, 2, 5, 13]))
            day = rng.randint(1, calendar.monthrange(y, mo)[1])
            start = hhmm(rng.choice([7, 8, 9, 14, 17]) * 60 + rng.choice([0, 15, 30]))
            end = hhmm(mins(start) + rng.choice([60, 120, 240, 420, 510]))
            if mins(end) < 1440:
                self.add_manual(f'{y}-{mo:02d}-{day:02d}', start, end, pause=rng.choice([0, 30, 45]),
                                remote=rng.choice([None, None, 0.0]))
        elif r < 0.58 and m.entries:
            self.delete_entry(rng.choice(sorted(m.entries)))
        elif r < 0.63 and m.entries:
            self.update_entry(rng.choice(sorted(m.entries)), rng.choice([-30, 30, 60]))
        elif r < 0.66:
            self.view_current()
        elif r < 0.69:
            self.view_month(*from_index(self.rng.randint(month_index(2025, 1), month_index(2030, 12))))
        elif r < 0.72:
            self.set_quote(rng.choice([40, 50, 60]))
        elif r < 0.74:
            self.set_soll(rng.choice([6, 7.5, 8, 9]))
        elif r < 0.81:
            self.month_switch()
        elif r < 0.85 and m.history:
            h = rng.choice(m.history)
            self.delete_month(h['monat'], h['jahr'])
        elif r < 0.855:
            self.delete_all_entries()
        elif r < 0.862:
            self.clear_history()
        elif r < 0.90:
            backup, snap = self.backup()
            for _ in range(rng.randint(1, 4)):               # mutate, then restore
                sub = rng.random()
                if sub < 0.4:
                    self.import_statement(*from_index(cur - rng.randint(0, 20)))
                elif sub < 0.7:
                    self.advance_clock()
                else:
                    self.month_switch()
            self.restore(backup, snap)
        else:
            self.advance_clock(1)

    def run(self, steps):
        for _ in range(steps):
            self.random_step()
        return self
