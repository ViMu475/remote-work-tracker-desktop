"""Break handling of imported statements: the app must show the same time as the statement's 'Istz'.

The rule was derived from real statements (every day of two statements matched exactly); these tests use
fictional values only.
"""
import json

import pytest

from services.calculation import assign_statement_breaks, statement_break_minutes


def minutes(h, m=0):
    return h * 60 + m


@pytest.mark.parametrize('work, expected', [
    (minutes(4), 0), (minutes(6), 0),                  # up to 6 h: no break
    (minutes(6, 2), 2), (minutes(6, 15), 15),          # just above 6 h: only the excess, never below 6 h net
    (minutes(6, 30), 30), (minutes(8), 30), (minutes(9, 30), 30),
    (minutes(9, 40), 40), (minutes(9, 45), 45),        # above 9.5 h: net never below 9 h
    (minutes(10), 45), (minutes(12), 45),
])
def test_break_of_one_booking(work, expected):
    assert statement_break_minutes(work) == expected


def test_gap_between_bookings_counts_as_break():
    assert statement_break_minutes(minutes(8), gap_minutes=45) == 0
    assert statement_break_minutes(minutes(8), gap_minutes=10) == 20
    assert statement_break_minutes(minutes(10), gap_minutes=30) == 15


class TestAssignBreaks:
    def test_single_session(self):
        assert assign_statement_breaks([('08:00', '17:00')]) == [30.0]

    def test_split_day_with_long_gap_has_no_deduction(self):
        assert assign_statement_breaks([('08:00', '11:00'), ('12:00', '17:00')]) == [0.0, 0.0]

    def test_split_day_with_short_gap_deducts_the_rest_from_the_longest_session(self):
        assert assign_statement_breaks([('08:00', '11:00'), ('11:10', '17:00')]) == [0.0, 20.0]

    def test_order_of_the_input_does_not_matter(self):
        assert assign_statement_breaks([('12:00', '17:00'), ('08:00', '11:00')]) == [0.0, 0.0]

    def test_short_day_has_no_break(self):
        assert assign_statement_breaks([('08:00', '13:00')]) == [0.0]

    def test_empty(self):
        assert assign_statement_breaks([]) == []


def session(date, start, end, remote=True):
    return {'date': date, 'start_time': start, 'end_time': end, 'is_remote': remote, 'type': 'Remote Work'}


def do_import(client, sessions):
    resp = client.post('/api/pdf/import', data=json.dumps({'sessions': sessions}), content_type='application/json')
    assert resp.status_code == 200
    return resp.get_json()


def entries(data, day):
    return data['state']['daily_records'][day]


class TestImportShowsStatementTime:
    def test_remote_day_shows_booked_time_minus_break(self, client):
        data = do_import(client, [session('2026-02-02', '08:00', '17:00')])
        e = entries(data, '2026-02-02')[0]
        assert e['pauseMinutes'] == 30 and e['totalStundenHeute'] == pytest.approx(8.5)
        assert e['remoteStundenHeute'] == pytest.approx(8.5)

    def test_long_day_never_drops_below_nine_hours(self, client):
        data = do_import(client, [session('2026-02-03', '07:50', '17:25')])        # 9 h 35 min booked
        assert entries(data, '2026-02-03')[0]['totalStundenHeute'] == pytest.approx(9.0)

    def test_office_day_has_no_remote_hours(self, client):
        data = do_import(client, [session('2026-02-04', '08:00', '17:00', remote=False)])
        e = entries(data, '2026-02-04')[0]
        assert e['remoteStundenHeute'] == 0 and e['totalStundenHeute'] == pytest.approx(8.5)

    def test_split_day_keeps_both_parts(self, client):
        data = do_import(client, [session('2026-02-05', '08:00', '11:00'), session('2026-02-05', '12:00', '17:00', remote=False)])
        total = sum(e['totalStundenHeute'] for e in entries(data, '2026-02-05'))
        remote = sum(e['remoteStundenHeute'] for e in entries(data, '2026-02-05'))
        assert total == pytest.approx(8.0) and remote == pytest.approx(3.0)

    def test_short_booking_below_six_hours_is_not_reduced(self, client):
        data = do_import(client, [session('2026-02-06', '08:00', '13:30')])
        assert entries(data, '2026-02-06')[0]['totalStundenHeute'] == pytest.approx(5.5)

    def test_month_total_equals_sum_of_statement_days(self, client):
        sessions = [session('2026-02-09', '08:00', '16:30'), session('2026-02-10', '08:00', '17:30'),
                    session('2026-02-11', '09:00', '15:00')]
        data = do_import(client, sessions)
        total = sum(e['totalStundenHeute'] for d in ('2026-02-09', '2026-02-10', '2026-02-11') for e in entries(data, d))
        assert total == pytest.approx(8.0 + 9.0 + 6.0)       # statement days: 8.00, 9.00, 6.00

    def test_loading_the_statement_again_corrects_an_old_import_without_duplicates(self, client):
        data = do_import(client, [session('2026-02-12', '08:00', '17:00')])
        # simulate an entry imported by the old version: break 0, 9.0 h
        old = entries(data, '2026-02-12')[0]
        state = data['state']
        old['pauseMinutes'], old['totalStundenHeute'], old['remoteStundenHeute'] = 0, 9.0, 9.0
        resp = client.post('/api/restore', data=json.dumps(state), content_type='application/json')
        assert resp.status_code == 200
        again = do_import(client, [session('2026-02-12', '08:00', '17:00')])
        day = entries(again, '2026-02-12')
        assert len(day) == 1 and day[0]['totalStundenHeute'] == pytest.approx(8.5)
        assert again['imported_count'] == 0 and again['updated_count'] == 1

    def test_manual_entries_are_not_overwritten_by_an_import(self, client):
        added = client.post('/api/protokoll', data=json.dumps({'datum': '2026-02-13', 'start': '08:00', 'end': '17:00',
                                                                 'pause': 30}), content_type='application/json')
        assert added.status_code == 200
        data = do_import(client, [session('2026-02-13', '08:00', '17:00')])
        assert data['imported_count'] == 0 and data['errors']
