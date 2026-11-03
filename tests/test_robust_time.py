"""Robustness: time edge cases (midnight, 24:00, DST, leap year, year change, special days, closing months)."""
import calendar
import copy
import json
import random
from datetime import date, timedelta

import pytest

from config import Config
from services.calculation import (assign_statement_breaks, berechne_soll_stunden_monat, calculate_net_hours,
                                  check_time_overlap, is_working_day_valid, parse_hhmm, statement_break_minutes)


def import_sessions(client, sessions):
    resp = client.post('/api/pdf/import', json={'sessions': sessions})
    assert resp.status_code == 200, resp.get_data(as_text=True)[:300]
    return resp.get_json()


def sess(day, start, end, remote=True):
    return {'date': day, 'start_time': start, 'end_time': end, 'is_remote': remote}


# ---------- time strings ----------

class TestParseTime:
    @pytest.mark.parametrize('t,m', [('00:00', 0), ('00:01', 1), ('12:30', 750), ('23:59', 1439)])
    def test_valid(self, t, m):
        assert parse_hhmm(t) == m

    @pytest.mark.parametrize('t', ['24:00', '24:01', '25:00', '99:99', '8:00', '08:0', '08:60', '-1:00', '08:-5', '',
                                   ' 08:00', '08:00 ', '08:00\n', '08:00:00', '٠٨:٠٠', '０８:００', '08.00', '0800', None,
                                   8, 8.5, ['08:00'], '08:00' * 100])
    def test_invalid(self, t):
        with pytest.raises(ValueError):
            parse_hhmm(t)

    def test_net_hours_rejects_24_00(self):
        with pytest.raises(ValueError):
            calculate_net_hours('08:00', '24:00', 0)


class TestEntriesAtMidnight:
    def post(self, client, **kw):
        body = {'datum': '2026-03-10', 'start': '08:00', 'end': '16:00', 'pause': 0}
        body.update(kw)
        return client.post('/api/protokoll', json=body)

    def test_zero_length_and_full_day_are_rejected(self, client):
        assert self.post(client, start='00:00', end='00:00').status_code == 400
        assert self.post(client, start='12:00', end='12:00').status_code == 400

    @pytest.mark.parametrize('end', ['24:00', '24:30', '25:00'])
    def test_24_00_is_rejected(self, client, end):
        assert self.post(client, start='08:00', end=end).status_code == 400
        assert self.post(client, start=end, end='08:00').status_code == 400
        assert client.get('/api/state').get_json()['daily_records'].get('2026-03-10') in (None, [])

    def test_overnight_entry_counts_past_midnight(self, client):
        r = self.post(client, start='22:00', end='02:00')
        assert r.status_code == 200
        e = r.get_json()['state']['daily_records']['2026-03-10'][0]
        assert e['totalStundenHeute'] == 4.0

    def test_one_minute_before_midnight(self, client):
        e = self.post(client, start='23:59', end='00:00').get_json()['state']['daily_records']['2026-03-10'][0]
        assert e['totalStundenHeute'] == pytest.approx(1 / 60)

    def test_whole_day_00_00_to_23_59(self, client):
        e = self.post(client, start='00:00', end='23:59').get_json()['state']['daily_records']['2026-03-10'][0]
        assert e['totalStundenHeute'] == pytest.approx(23 + 59 / 60)

    def test_pause_longer_than_entry_is_rejected(self, client):
        assert self.post(client, start='08:00', end='09:00', pause=61).status_code == 400
        assert self.post(client, start='08:00', end='09:00', pause=60).status_code == 200

    def test_overnight_overlap_is_detected(self):
        state = {'daily_records': {'2026-03-10': [{'id': 'a', 'startTime': '22:00', 'endTime': '02:00'}]}}
        assert check_time_overlap('2026-03-10', '23:00', '23:30', state)
        assert check_time_overlap('2026-03-10', '01:00', '03:00', state) is None   # early morning of the same date
        assert check_time_overlap('2026-03-10', '02:00', '03:00', state) is None
        assert check_time_overlap('2026-03-10', '24:00', '03:00', state) == 'Ungültiges Zeitformat'

    def test_remote_larger_than_net_is_rejected(self, client):
        assert self.post(client, remote=8.01).status_code == 400
        assert self.post(client, remote=8).status_code == 200
        assert self.post(client, start='17:00', end='18:00', remote=-1).status_code == 400


class TestDateStrings:
    @pytest.mark.parametrize('d', ['2026-3-10', '2026-03-1', '2026-03-10 ', ' 2026-03-10', '2026-02-29', '2026-02-30',
                                   '2026-13-01', '2026-00-10', '0000-01-01', '٢٠٢٦-٠٣-١٠', '2026/03/10', '10.03.2026',
                                   '', None, 20260310, ['2026-03-10'], {}])
    def test_noncanonical_dates_rejected(self, d):
        state = {'aktueller_monat': 'März', 'aktuelles_jahr': 2026}
        assert is_working_day_valid(d, state) == 'Ungültiges Datumsformat.'

    @pytest.mark.parametrize('d', ['2026-3-10', '2026-02-29', '2026-03-10 '])
    def test_api_rejects_noncanonical_dates(self, client, d):
        r = client.post('/api/protokoll', json={'datum': d, 'start': '08:00', 'end': '09:00'})
        assert r.status_code == 400

    def test_leap_day_accepted_in_leap_year_only(self):
        state = {'aktueller_monat': 'März', 'aktuelles_jahr': 2026}
        assert is_working_day_valid('2024-02-29', state, allow_historical=True) is None   # Thursday
        assert is_working_day_valid('2025-02-29', state, allow_historical=True) == 'Ungültiges Datumsformat.'

    def test_future_dates_rejected_even_far_away(self, client):
        for d in ('2026-04-01', '2027-01-01', '9999-12-31'):
            assert client.post('/api/protokoll', json={'datum': d, 'start': '08:00', 'end': '09:00'}).status_code == 400


# ---------- Soll hours, special days, leap years, DST ----------

def workdays(year, month, per_day=8.0):
    total = 0.0
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        day = date(year, month, d)
        if day.weekday() < 5 and day.isoformat() not in Config.BAYERN_FEIERTAGE:
            total += per_day * {(12, 24): 0.0, (12, 31): 0.5}.get((month, d), 1.0)
    return total


class TestSollHours:
    @pytest.mark.parametrize('year', [2024, 2025, 2026, 2027, 2028])
    @pytest.mark.parametrize('month', range(1, 13))
    def test_matches_independent_count(self, year, month):
        if year not in getattr(Config, 'HOLIDAY_YEARS', [year]):
            pytest.skip('year without holiday table')
        assert berechne_soll_stunden_monat(year, month, 8.0) == workdays(year, month)

    def test_february_leap_year(self):
        assert berechne_soll_stunden_monat(2028, 2, 8.0) == 21 * 8     # Feb 2028: 29 days, 21 weekdays
        assert berechne_soll_stunden_monat(2027, 2, 8.0) == 20 * 8

    @pytest.mark.parametrize('year', [2025, 2026, 2027])
    def test_24_dec_is_zero_and_31_dec_is_half(self, year):
        full = 0.0
        for d in range(1, 32):
            day = date(year, 12, d)
            if day.weekday() < 5 and day.isoformat() not in Config.BAYERN_FEIERTAGE:
                full += 8.0
        reduction = (8.0 if date(year, 12, 24).weekday() < 5 and f'{year}-12-24' not in Config.BAYERN_FEIERTAGE else 0) \
            + (4.0 if date(year, 12, 31).weekday() < 5 and f'{year}-12-31' not in Config.BAYERN_FEIERTAGE else 0)
        assert berechne_soll_stunden_monat(year, 12, 8.0) == full - reduction
        assert reduction > 0

    @pytest.mark.parametrize('per_day', [1.0, 7.5, 10.0])
    def test_scales_linearly(self, per_day):
        assert berechne_soll_stunden_monat(2026, 12, per_day) == pytest.approx(
            berechne_soll_stunden_monat(2026, 12, 1.0) * per_day)

    def test_dst_weeks_have_no_effect(self):
        # clocks change on Sundays only: the March/October Soll is the plain weekday count
        assert berechne_soll_stunden_monat(2026, 3, 8.0) == workdays(2026, 3)
        assert berechne_soll_stunden_monat(2026, 10, 8.0) == workdays(2026, 10)
        for d in ('2025-03-30', '2025-10-26', '2024-10-27'):
            assert 'Sonntag' in is_working_day_valid(d, {}, allow_historical=True)

    def test_no_implicit_timezone_arithmetic_around_the_clock_change(self):
        # 02:30 does not exist on the spring DST day and exists twice in autumn: the app is wall-clock only
        assert calculate_net_hours('01:00', '04:00', 0)['net'] == 3.0
        assert calculate_net_hours('01:30', '03:30', 0)['net'] == 2.0

    def test_year_change_month_switch_december_to_january(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        st.update({'aktueller_monat': 'Dezember', 'aktuelles_jahr': 2025, 'view_month': 'Dezember', 'view_year': 2025})
        assert client.post('/api/restore', json=st).status_code == 200
        import_sessions(client, [sess('2025-12-23', '08:00', '12:00')])
        out = client.post('/api/month/switch').get_json()['state']
        assert (out['view_month'], out['view_year']) == ('Januar', 2026)
        assert out['aktuelles_jahr'] == 2026
        assert [(m['monat'], m['jahr']) for m in out['monatliche_historie']][-1] == ('Dezember', 2025)

    def test_special_days_can_be_booked_and_dont_break_totals(self, client):
        out = import_sessions(client, [sess('2025-12-24', '08:00', '12:00'), sess('2025-12-31', '08:00', '12:00'),
                                       sess('2024-02-29', '09:00', '10:00'), sess('2025-12-30', '08:00', '16:00')])
        assert out['imported_count'] == 4 and out['errors'] == []
        recs = out['state']['daily_records']
        assert {'2025-12-24', '2025-12-31', '2024-02-29', '2025-12-30'} <= set(recs)


# ---------- closing months ----------

def state_with(sample_state, month, year, dates, history=()):
    st = copy.deepcopy(sample_state)
    st.update({'aktueller_monat': month, 'aktuelles_jahr': year, 'view_month': month, 'view_year': year,
               'daily_records': {d: [{'id': 'i' + d, 'datum': d, 'startTime': '08:00', 'endTime': '16:30',
                                      'pauseMinutes': 30, 'remoteStundenHeute': 4.0, 'totalStundenHeute': 8.0}]
                                 for d in dates},
               'monatliche_historie': list(history)})
    return st


class TestCloseMonth:
    def test_close_empty_month_twice_changes_nothing_but_the_month(self, client, sample_state):
        assert client.post('/api/restore', json=state_with(sample_state, 'Mai', 2026, [])).status_code == 200
        a = client.post('/api/month/switch').get_json()['state']
        assert a['monatliche_historie'] == [] and a['view_month'] == 'Juni'
        b = client.post('/api/month/switch').get_json()['state']
        assert b['monatliche_historie'] == [] and b['view_month'] == 'Juli'

    def test_close_repeatedly_through_year_end_and_history_stays_sorted_unique(self, client, sample_state):
        dates = ['2026-10-05', '2026-11-04', '2026-12-02', '2027-01-12']
        st = state_with(sample_state, 'Oktober', 2026, dates)
        st['view_month'], st['view_year'] = 'Oktober', 2026
        assert client.post('/api/restore', json=st).status_code == 200
        for _ in range(5):
            out = client.post('/api/month/switch').get_json()['state']
        names = [(m['monat'], m['jahr']) for m in out['monatliche_historie']]
        assert names == [('Oktober', 2026), ('November', 2026), ('Dezember', 2026), ('Januar', 2027)]
        assert (out['view_month'], out['view_year']) == ('März', 2027)
        assert out['daily_records'] == {}

    def test_history_order_is_independent_of_closing_order(self, client, sample_state):
        hist = [{'monat': 'Dezember', 'jahr': 2025, 'soll_stunden_gesamt': 100.0, 'ist_remote_stunden_laufend': 1.0,
                 'ist_arbeitszeit_laufend': 1.0, 'max_remote_stunden': 40.0, 'individuelle_quote': 40.0},
                {'monat': 'Februar', 'jahr': 2026, 'soll_stunden_gesamt': 100.0, 'ist_remote_stunden_laufend': 1.0,
                 'ist_arbeitszeit_laufend': 1.0, 'max_remote_stunden': 40.0, 'individuelle_quote': 40.0}]
        st = state_with(sample_state, 'Januar', 2026, ['2026-01-13'], hist)
        client.post('/api/restore', json=st)
        out = client.post('/api/month/switch').get_json()['state']
        assert [(m['monat'], m['jahr']) for m in out['monatliche_historie']] == [
            ('Dezember', 2025), ('Januar', 2026), ('Februar', 2026)]

    def test_leap_february_closes(self, client, sample_state):
        st = state_with(sample_state, 'Februar', 2028, ['2028-02-29'])
        st['aktuelles_jahr'] = 2028
        client.post('/api/restore', json=st)
        out = client.post('/api/month/switch').get_json()['state']
        assert out['monatliche_historie'][0]['jahr'] == 2028 and out['view_month'] == 'März'

    def test_entries_of_other_months_survive_a_close(self, client, sample_state):
        st = state_with(sample_state, 'April', 2026, ['2026-04-07', '2026-05-05', '2025-04-08'])
        client.post('/api/restore', json=st)
        out = client.post('/api/month/switch').get_json()['state']
        assert set(out['daily_records']) == {'2026-05-05', '2025-04-08'}

    def test_close_with_zero_soll_stunden_in_history_does_not_divide_by_zero(self, client, sample_state):
        hist = [{'monat': 'Januar', 'jahr': 2026, 'soll_stunden_gesamt': 0, 'ist_remote_stunden_laufend': 0,
                 'ist_arbeitszeit_laufend': 0, 'max_remote_stunden': 0, 'individuelle_quote': 40.0, 'quartal': 'Q1/2026'}]
        st = state_with(sample_state, 'Februar', 2026, ['2026-02-03'], hist)
        client.post('/api/restore', json=st)
        assert client.post('/api/month/switch').status_code == 200

    def test_quarter_close_with_damaged_history_entries_does_not_5xx(self, client, sample_state):
        hist = [{'monat': 'Januar', 'jahr': 2026, 'quartal': 'Q1/2026'},
                {'monat': 'Februar', 'jahr': 2026, 'quartal': 'Q1/2026'}]
        st = state_with(sample_state, 'März', 2026, ['2026-03-03'], hist)
        client.post('/api/restore', json=st)
        assert client.post('/api/month/switch').status_code < 500

    def test_history_with_garbage_values_is_survivable(self, client, sample_state):
        hist = [{'monat': 'Foo', 'jahr': 'x'}, {'monat': None, 'jahr': None}, {}]
        st = state_with(sample_state, 'März', 2026, ['2026-03-03'], hist)
        assert client.post('/api/restore', json=st).status_code == 200
        assert client.post('/api/month/switch').status_code < 500
        assert client.get('/api/report/final').status_code < 500


# ---------- pdf/import robustness ----------

class TestImportRobust:
    @pytest.mark.parametrize('sessions', [None, 5, 'x', {'a': 1}])
    def test_sessions_must_be_a_list(self, client, sessions):
        assert client.post('/api/pdf/import', json={'sessions': sessions}).status_code == 400

    def test_garbage_items_are_reported_not_fatal(self, client):
        out = import_sessions(client, [None, 5, 'x', [], {}, {'date': 5, 'start_time': 'a', 'end_time': 'b'},
                                       sess('2026-03-10', '25:00', '26:00'), sess('2026-03-10', '24:00', '08:00'),
                                       sess('2026-03-10', '08:00', '12:00'), {'date': ['x'], 'start_time': {}, 'end_time': 1}])
        assert out['imported_count'] == 1
        assert len(out['errors']) == 9

    def test_same_statement_twice_is_idempotent(self, client):
        s = [sess('2026-03-10', '08:00', '16:30'), sess('2026-03-11', '08:00', '12:00', remote=False)]
        a = import_sessions(client, s)['state']['daily_records']
        b = import_sessions(client, s)
        assert b['imported_count'] == 0 and b['updated_count'] == 2
        assert {k: [(e['startTime'], e['endTime'], e['pauseMinutes'], e['totalStundenHeute']) for e in v]
                for k, v in b['state']['daily_records'].items()} == \
               {k: [(e['startTime'], e['endTime'], e['pauseMinutes'], e['totalStundenHeute']) for e in v]
                for k, v in a.items()}

    def test_flex_balance_garbage(self, client):
        for flex in ({'total': float('nan')}, {'total': 'x'}, 'x', [], {'total': 10 ** 9}, {'total': True}, 5):
            r = client.post('/api/pdf/import', data=json.dumps({'sessions': [], 'flex_balance': flex}),
                            content_type='application/json')
            assert r.status_code == 200
            assert 'gleitzeit_saldo' not in r.get_json()['state']

    def test_weekend_holiday_and_future_are_reported(self, client):
        out = import_sessions(client, [sess('2026-03-08', '08:00', '12:00'), sess('2026-01-01', '08:00', '12:00'),
                                       sess('2026-12-01', '08:00', '12:00')])
        assert out['imported_count'] == 0 and len(out['errors']) == 3

    def test_many_sessions_for_one_day(self, client):
        sessions = [sess('2026-03-10', f'{h:02d}:00', f'{h:02d}:30') for h in range(0, 24)]
        out = import_sessions(client, sessions)
        assert out['imported_count'] == 24
        total = sum(e['totalStundenHeute'] for e in out['state']['daily_records']['2026-03-10'])
        assert total >= 0

    def test_overlapping_sessions_in_one_statement(self, client):
        out = import_sessions(client, [sess('2026-03-10', '08:00', '12:00'), sess('2026-03-10', '11:00', '13:00')])
        assert out['imported_count'] == 1 and len(out['errors']) == 1


# ---------- break rule: property tests ----------

def rand_sessions(rng):
    n = rng.randint(0, 6)
    out = []
    for _ in range(n):
        s = rng.randrange(0, 1440)
        length = rng.choice([0, 1, 5, 30, 59, 60, 240, 359, 360, 361, 390, 391, 480, 570, 571, 600, 720, 900, 1439])
        e = (s + length) % 1440
        out.append((f'{s // 60:02d}:{s % 60:02d}', f'{e // 60:02d}:{e % 60:02d}'))
    return out


def span(sess_):
    s, e = parse_hhmm(sess_[0]), parse_hhmm(sess_[1])
    return (e + 1440 if e < s else e) - s


class TestBreakProperties:
    def test_random_days_seed_1234(self):
        rng = random.Random(1234)
        for _ in range(5000):
            sessions = rand_sessions(rng)
            breaks = assign_statement_breaks(sessions)
            again = assign_statement_breaks(list(sessions))
            assert breaks == again                                   # deterministic
            assert len(breaks) == len(sessions)
            assert all(b >= 0 and b == b and b != float('inf') for b in breaks)   # never negative
            work = sum(span(x) for x in sessions)
            assert sum(breaks) <= max(work, 0)                       # never more than worked time
            assert sum(breaks) <= 45                                 # legal maximum
            assert sum(1 for b in breaks if b) <= 1                  # whole deduction on one session
            net_total = work - sum(breaks)
            assert net_total >= 0

    def test_deduction_goes_to_a_session_that_can_bear_it_when_possible(self):
        rng = random.Random(99)
        for _ in range(3000):
            sessions = rand_sessions(rng)
            breaks = assign_statement_breaks(sessions)
            for x, b in zip(sessions, breaks):
                if b:
                    assert b <= span(x) or span(x) == max(span(y) for y in sessions)

    def test_permutation_invariance_of_total(self):
        rng = random.Random(7)
        for _ in range(2000):
            sessions = rand_sessions(rng)
            shuffled = sessions[:]
            rng.shuffle(shuffled)
            assert sum(assign_statement_breaks(sessions)) == sum(assign_statement_breaks(shuffled))

    def test_does_not_mutate_input(self):
        sessions = [('08:00', '12:00'), ('13:00', '19:00')]
        snapshot = copy.deepcopy(sessions)
        assign_statement_breaks(sessions)
        assert sessions == snapshot

    def test_monotone_in_work_time_for_one_booking(self):
        previous = 0
        for work in range(0, 1441):
            now = statement_break_minutes(work)
            assert now >= 0 and now <= work
            assert work - now >= previous or work <= 360     # net time never shrinks when working more
            previous = max(previous, work - now)

    @pytest.mark.parametrize('bad', [[('08:00', '24:00')], [('8:00', '12:00')], [('08:00', None)], [(None, None)],
                                     [('08:00', '12:00'), ('x', 'y')]])
    def test_invalid_input_raises_value_error_only(self, bad):
        with pytest.raises(ValueError):
            assign_statement_breaks(bad)

    def test_gaps_reduce_the_break(self):
        assert sum(assign_statement_breaks([('08:00', '12:00'), ('12:30', '16:30')])) == 0
        assert sum(assign_statement_breaks([('08:00', '12:00'), ('12:10', '16:30')])) == 20

    def test_import_random_days_never_gives_negative_net(self, client):
        rng = random.Random(2026)
        days = ['2026-03-02', '2026-03-03', '2026-03-04', '2026-03-05', '2026-03-06', '2026-03-09', '2026-03-10']
        sessions = []
        for d in days:
            for s, e in rand_sessions(rng):
                sessions.append(sess(d, s, e, remote=rng.random() < 0.5))
        out = import_sessions(client, sessions)
        for lst in out['state']['daily_records'].values():
            for e in lst:
                assert e['totalStundenHeute'] >= -1e-9, e
                assert 0 <= e['remoteStundenHeute'] <= e['totalStundenHeute'] + 1e-9
                assert e['pauseMinutes'] >= 0
