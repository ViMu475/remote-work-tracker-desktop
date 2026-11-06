"""Batch import of time statements: review of statements and import of whole months (fictional data only)."""
import calendar
import copy
from datetime import date

import pytest

from config import Config
from services.history_service import build_month_record
from services.statement_import import (
    annotate_with_state, apply_batch, clean_flex_balance, failed_report, review_batch, review_sessions,
    review_statement,
)

# The suite runs on 2026-03-15 (conftest.py): March 2026 is the open month, everything before it is over.


def workdays(year, month, count):
    """The first `count` Monday-Friday dates of a month that are no holiday."""
    days = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        iso = f'{year}-{month:02d}-{day:02d}'
        if date(year, month, day).weekday() < 5 and iso not in Config.BAYERN_FEIERTAGE:
            days.append(iso)
    return days[:count]


def session(day, start='08:00', end='16:30', remote=True):
    return {'date': day, 'start_time': start, 'end_time': end, 'is_remote': remote}


def month_sessions(year, month, count=5, **kw):
    return [session(d, **kw) for d in workdays(year, month, count)]


def analysis(year, month, sessions=None, source='header', period_end=None, flex=None):
    return {'success': True, 'message': 'ok', 'sessions': month_sessions(year, month) if sessions is None else sessions,
            'flex_balance': flex,
            'structure': {'year': year, 'month': month, 'period_source': source, 'period_end': period_end}}


def item(year, month, sessions=None, **kw):
    out = {'year': year, 'month': month, 'filename': f'{year}-{month:02d}.pdf',
           'sessions': month_sessions(year, month) if sessions is None else sessions}
    out.update(kw)
    return out


def free_march_sessions():
    """Three days of the open month (March 2026) that the sample state has no entries for."""
    return [session(d) for d in workdays(2026, 3, 8)[5:8]]


def manual_entry(day, start='09:00', end='12:00'):
    return {'id': 'manual', 'datum': day, 'startTime': start, 'endTime': end,
            'remoteStundenHeute': 3.0, 'totalStundenHeute': 3.0, 'source': None}


def codes(issues):
    return [i['code'] for i in issues]


@pytest.fixture
def state(sample_state):
    return copy.deepcopy(sample_state)


class TestReviewSessions:
    def test_clean_month_has_no_issues_and_correct_totals(self):
        errors, warnings, summary = review_sessions(2025, 11, month_sessions(2025, 11))
        assert errors == [] and warnings == []
        # 08:00-16:30 is 8.5 h booked, the time system deducts 30 min: 8 h net per day
        assert summary == {'days': 5, 'session_count': 5, 'net_hours': 40.0, 'remote_hours': 40.0}

    def test_office_days_do_not_count_as_remote(self):
        sessions = month_sessions(2025, 11, 2) + month_sessions(2025, 11, 4, remote=False)[2:]
        _, _, summary = review_sessions(2025, 11, sessions)
        assert summary['net_hours'] == 32.0 and summary['remote_hours'] == 16.0

    def test_two_sessions_of_one_day_get_one_break(self):
        day = workdays(2025, 11, 1)[0]
        sessions = [session(day, '08:00', '12:00'), session(day, '12:30', '17:00')]
        errors, warnings, summary = review_sessions(2025, 11, sessions)
        assert errors == [] and warnings == []
        # 4 h + 4.5 h booked; the 30 min gap already is the legal break, so nothing more is deducted
        assert summary['net_hours'] == 8.5

    @pytest.mark.parametrize('start,end', [('16:30', '08:00'), ('08:00', '08:00')])
    def test_end_not_after_start(self, start, end):
        day = workdays(2025, 11, 1)[0]
        errors, _, _ = review_sessions(2025, 11, [session(day, start, end)])
        assert codes(errors) == ['end_not_after_start']

    @pytest.mark.parametrize('start,end', [('25:00', '16:00'), ('8:00', '16:00'), ('08:00', 'abc'), (None, '16:00')])
    def test_invalid_time(self, start, end):
        day = workdays(2025, 11, 1)[0]
        errors, _, _ = review_sessions(2025, 11, [session(day, start, end)])
        assert codes(errors) == ['invalid_time']

    def test_date_outside_the_statement_month(self):
        errors, _, _ = review_sessions(2025, 11, [session('2025-12-01')])
        assert codes(errors) == ['date_outside_month']

    @pytest.mark.parametrize('bad', ['2025-02-30', '2025-2-3', 'abc', None, 20251103, ' 2025-11-03'])
    def test_invalid_date(self, bad):
        errors, _, _ = review_sessions(2025, 11, [session(bad)])
        assert codes(errors) == ['invalid_date']

    def test_future_month_and_future_day(self):
        errors, _, _ = review_sessions(2026, 5, [session('2026-05-04')])
        assert 'future_month' in codes(errors)
        errors, _, _ = review_sessions(2026, 3, [session('2026-03-20')])      # today is 2026-03-15
        assert codes(errors) == ['future_date']

    def test_overlap_and_duplicate_session(self):
        day = workdays(2025, 11, 1)[0]
        errors, _, _ = review_sessions(2025, 11, [session(day, '08:00', '12:00'), session(day, '11:00', '15:00')])
        assert codes(errors) == ['overlap'] and errors[0]['date'] == day
        errors, _, _ = review_sessions(2025, 11, [session(day), session(day)])
        assert codes(errors) == ['overlap']

    def test_sessions_that_only_touch_are_no_overlap(self):
        day = workdays(2025, 11, 1)[0]
        errors, _, _ = review_sessions(2025, 11, [session(day, '08:00', '12:00'), session(day, '12:00', '16:00')])
        assert errors == []

    @pytest.mark.parametrize('sessions', [[], None, 'x', {}])
    def test_no_sessions(self, sessions):
        errors, _, _ = review_sessions(2025, 11, sessions)
        assert codes(errors) == ['no_sessions']

    def test_garbage_session_entries_do_not_crash(self):
        errors, _, _ = review_sessions(2025, 11, [None, 5, 'x', [], session(workdays(2025, 11, 1)[0])])
        assert codes(errors) == ['invalid_date'] * 4

    @pytest.mark.parametrize('year,month', [(None, 11), (2025, None), (2025, 13), (2025, 0), (True, 1), (1800, 1), ('2025', 11)])
    def test_unusable_period(self, year, month):
        errors, _, _ = review_sessions(year, month, month_sessions(2025, 11))
        assert codes(errors) == ['period_unknown']

    def test_long_day_is_only_a_warning(self):
        day = workdays(2025, 11, 1)[0]
        errors, warnings, _ = review_sessions(2025, 11, [session(day, '07:00', '19:00')])
        assert errors == [] and codes(warnings) == ['long_day']

    def test_holiday_and_weekend_are_warnings(self):
        holiday = next(d for d in Config.BAYERN_FEIERTAGE if d.startswith('2025-12'))
        errors, warnings, _ = review_sessions(2025, 12, [session(holiday), session('2025-12-06'), session('2025-12-07')])
        assert errors == []
        assert codes(warnings) == ['non_working_day'] * 3
        assert sorted(w['date'] for w in warnings) == sorted([holiday, '2025-12-06', '2025-12-07'])


class TestReviewStatement:
    def test_good_statement(self):
        report = review_statement(analysis(2025, 11), 'nov.pdf')
        assert report['status'] == 'ok' and report['key'] == '2025-11' and report['month_name'] == 'November'
        assert report['summary']['days'] == 5

    def test_unreadable_statement(self):
        report = review_statement({'success': False, 'message': 'kaputt', 'sessions': []}, 'x.pdf')
        assert report['status'] == 'error' and report['errors'][0]['code'] == 'parse_failed'
        assert report['errors'][0]['detail'] == 'kaputt'
        assert review_statement(None, 'x.pdf')['status'] == 'error'

    @pytest.mark.parametrize('source', ['fallback_now', 'unrecognized', None, 'guess'])
    def test_period_that_was_guessed_is_rejected(self, source):
        report = review_statement(analysis(2025, 11, source=source), 'x.pdf')
        assert report['status'] == 'error' and 'period_unknown' in codes(report['errors'])

    def test_period_from_the_file_name_needs_confirmation(self):
        report = review_statement(analysis(2025, 11, source='filename'), 'x.pdf')
        assert report['status'] == 'warning' and codes(report['warnings']) == ['period_from_filename']

    def test_statement_over_two_months_is_rejected(self):
        report = review_statement(analysis(2025, 11, period_end='2025-12-31'), 'x.pdf')
        assert 'period_multi_month' in codes(report['errors'])
        assert review_statement(analysis(2025, 11, period_end='2025-11-30'), 'x.pdf')['status'] == 'ok'

    def test_flex_balance_is_cleaned(self):
        report = review_statement(analysis(2025, 11, flex={'total': 12.5, 'evil': 1, 'year': 2025, 'month': 11}), 'x.pdf')
        assert report['flex_balance'] == {'total': 12.5, 'year': 2025, 'month': 11}

    def test_failed_report(self):
        report = failed_report('a.txt', 'not_pdf')
        assert report['status'] == 'error' and codes(report['errors']) == ['not_pdf']


class TestReviewBatch:
    def test_same_month_twice_is_an_error_for_both(self):
        reports = review_batch([review_statement(analysis(2025, 11), 'a.pdf'),
                                review_statement(analysis(2025, 11), 'b.pdf'),
                                review_statement(analysis(2025, 12), 'c.pdf')])
        assert [r['status'] for r in reports] == ['error', 'error', 'ok']
        assert reports[0]['errors'][0]['detail'] == 'b.pdf' and reports[1]['errors'][0]['detail'] == 'a.pdf'

    def test_unreadable_files_are_never_duplicates(self):
        reports = review_batch([failed_report('a.pdf', 'parse_failed'), failed_report('b.pdf', 'parse_failed')])
        assert all(codes(r['errors']) == ['parse_failed'] for r in reports)


class TestAnnotateWithState:
    def test_target_and_quote(self, state):
        closed = annotate_with_state(review_statement(analysis(2025, 11), 'a.pdf'), state)
        # the sample state has hand-typed entries on 2026-03-02/03: other days are fine, they only warn
        open_month = annotate_with_state(review_statement(analysis(2026, 3, free_march_sessions()), 'b.pdf'), state)
        assert (closed['target'], closed['quote']) == ('history', 40.0)
        assert open_month['target'] == 'daily' and codes(open_month['warnings']) == ['has_manual_entries']

    def test_month_in_history_is_a_warning(self, state):
        apply_batch(state, [item(2025, 11)])
        report = annotate_with_state(review_statement(analysis(2025, 11), 'a.pdf'), state)
        assert codes(report['warnings']) == ['replaces_history']

    def test_manual_entry_on_the_same_time_is_an_error(self, state):
        day = workdays(2025, 11, 1)[0]
        state['daily_records'][day] = [manual_entry(day)]
        report = annotate_with_state(review_statement(analysis(2025, 11), 'a.pdf'), state)
        assert report['status'] == 'error' and codes(report['errors']) == ['overlaps_existing']

    def test_manual_entry_on_another_day_is_a_warning(self, state):
        other_day = workdays(2025, 11, 9)[8]
        state['daily_records'][other_day] = [manual_entry(other_day)]
        report = annotate_with_state(review_statement(analysis(2025, 11), 'a.pdf'), state)
        assert codes(report['warnings']) == ['has_manual_entries']


class TestApplyBatch:
    def test_months_enter_the_history_sorted_whatever_the_input_order(self, state):
        results = apply_batch(state, [item(2026, 1), item(2025, 11), item(2025, 12), item(2025, 9)])
        assert [r['status'] for r in results] == ['imported'] * 4
        assert [(m['jahr'], m['monat']) for m in state['monatliche_historie']] == [
            (2025, 'September'), (2025, 'November'), (2025, 'Dezember'), (2026, 'Januar')]

    def test_history_is_sorted_together_with_months_that_are_already_there(self, state):
        apply_batch(state, [item(2025, 12)])
        apply_batch(state, [item(2025, 10), item(2026, 2)])
        assert [(m['jahr'], m['monat']) for m in state['monatliche_historie']] == [
            (2025, 'Oktober'), (2025, 'Dezember'), (2026, 'Februar')]

    def test_days_stay_in_the_daily_records_and_the_record_has_the_numbers(self, state):
        apply_batch(state, [item(2025, 11)])
        days = [d for d in state['daily_records'] if d.startswith('2025-11')]
        assert sorted(days) == workdays(2025, 11, 5)
        record = state['monatliche_historie'][0]
        assert record['ist_arbeitszeit_laufend'] == 40.0 and record['ist_remote_stunden_laufend'] == 40.0
        assert record['quartal'] == 'Q4/2025' and record['individuelle_quote'] == 40.0
        assert record['max_remote_stunden'] == record['soll_stunden_gesamt'] * 0.4

    def test_record_equals_the_one_of_a_hand_closed_month(self, state):
        apply_batch(state, [item(2025, 11)])
        assert state['monatliche_historie'][0] == build_month_record(state, 'November', 2025)

    def test_an_open_month_that_clashes_with_typed_entries_is_rejected(self, state):
        results = apply_batch(state, [item(2026, 3, month_sessions(2026, 3, 3), confirmed=True)])
        assert results[0]['status'] == 'rejected' and results[0]['codes'] == ['overlaps_existing'] * 2   # one per day

    def test_the_open_month_only_gets_daily_records(self, state):
        results = apply_batch(state, [item(2026, 3, free_march_sessions(), confirmed=True)])
        assert results[0]['status'] == 'imported' and results[0]['target'] == 'daily'
        assert state['monatliche_historie'] == []
        assert len([d for d in state['daily_records'] if d.startswith('2026-03')]) == 5   # 2 typed + 3 imported

    def test_quota_and_open_month_stay_untouched(self, state):
        keys = ('individuelle_quote_prozent', 'aktueller_monat', 'aktuelles_jahr', 'current_quartal')
        before = {k: copy.deepcopy(state[k]) for k in keys}
        apply_batch(state, [item(2025, 10), item(2025, 11), item(2025, 12)])
        assert {k: state[k] for k in keys} == before

    def test_an_error_rejects_the_whole_month_and_writes_nothing(self, state):
        bad = month_sessions(2025, 11, 4) + [session(workdays(2025, 11, 5)[4], '16:00', '08:00')]
        snapshot = copy.deepcopy(state)
        results = apply_batch(state, [item(2025, 11, bad)])
        assert results[0]['status'] == 'rejected' and results[0]['codes'] == ['end_not_after_start']
        assert state == snapshot

    def test_a_bad_month_does_not_stop_the_good_ones(self, state):
        results = apply_batch(state, [item(2025, 11, []), item(2025, 12)])
        assert [r['status'] for r in results] == ['rejected', 'imported']
        assert [(m['jahr'], m['monat']) for m in state['monatliche_historie']] == [(2025, 'Dezember')]
        assert not any(d.startswith('2025-11') for d in state['daily_records'])

    def test_warnings_need_the_confirmation(self, state):
        long_nov = [session(workdays(2025, 11, 1)[0], '07:00', '19:00')]
        long_dec = [session(workdays(2025, 12, 1)[0], '07:00', '19:00')]
        refused = apply_batch(state, [item(2025, 11, long_nov)])
        assert refused[0]['status'] == 'rejected' and refused[0]['codes'][:2] == ['needs_confirmation', 'long_day']
        assert state['monatliche_historie'] == []
        assert apply_batch(state, [item(2025, 11, long_nov, confirmed=True)])[0]['status'] == 'imported'
        assert apply_batch(state, [item(2025, 12, long_dec, confirmed='yes')])[0]['status'] == 'rejected'

    def test_own_quota_for_a_month(self, state):
        apply_batch(state, [item(2025, 11, quote=50)])
        record = state['monatliche_historie'][0]
        assert record['individuelle_quote'] == 50 and record['max_remote_stunden'] == record['soll_stunden_gesamt'] * 0.5
        assert state['individuelle_quote_prozent'] == 40.0

    @pytest.mark.parametrize('quote', [10, 90, -1, 'abc', float('nan'), True, [50]])
    def test_invalid_quota_rejects_the_month(self, state, quote):
        results = apply_batch(state, [item(2025, 11, quote=quote)])
        assert results[0]['status'] == 'rejected' and 'invalid_quote' in results[0]['codes']
        assert state['monatliche_historie'] == []

    def test_a_complete_quarter_gets_its_summary_without_changing_the_quota(self, state):
        apply_batch(state, [item(2025, 10), item(2025, 11)])
        assert all('quartal_quote' not in m for m in state['monatliche_historie'])
        apply_batch(state, [item(2025, 12)])
        months = state['monatliche_historie']
        assert len(months) == 3 and all(m['quartal'] == 'Q4/2025' for m in months)
        assert all(m['quartal_remote'] == 120.0 and m['quartal_gesamt'] == 120.0 for m in months)
        assert all(m['quartal_soll'] == sum(x['soll_stunden_gesamt'] for x in months) for m in months)
        assert state['individuelle_quote_prozent'] == 40.0

    def test_importing_the_same_statements_again_changes_nothing(self, state):
        batch = [item(2025, 11), item(2025, 12)]
        apply_batch(state, batch)
        first = copy.deepcopy(state)
        results = apply_batch(state, [dict(i, confirmed=True) for i in batch])
        assert [r['status'] for r in results] == ['imported', 'imported']
        assert state['daily_records'] == first['daily_records']
        assert state['monatliche_historie'] == first['monatliche_historie']

    def test_replacing_a_month_in_the_history_needs_confirmation_and_keeps_its_quota(self, state):
        apply_batch(state, [item(2025, 11, quote=50)])
        refused = apply_batch(state, [item(2025, 11, month_sessions(2025, 11, 3))])
        assert refused[0]['codes'] == ['needs_confirmation', 'replaces_history']
        assert state['monatliche_historie'][0]['ist_arbeitszeit_laufend'] == 40.0
        apply_batch(state, [item(2025, 11, month_sessions(2025, 11, 3), confirmed=True)])
        assert len(state['monatliche_historie']) == 1
        record = state['monatliche_historie'][0]
        assert record['ist_arbeitszeit_laufend'] == 24.0 and record['individuelle_quote'] == 50

    def test_manual_entries_are_kept_and_counted(self, state):
        manual_day = workdays(2025, 11, 9)[8]
        state['daily_records'][manual_day] = [manual_entry(manual_day)]
        assert apply_batch(state, [item(2025, 11)])[0]['codes'] == ['needs_confirmation', 'has_manual_entries']
        apply_batch(state, [item(2025, 11, confirmed=True)])
        assert state['daily_records'][manual_day][0]['id'] == 'manual'
        assert state['monatliche_historie'][0]['ist_arbeitszeit_laufend'] == 43.0

    def test_overlap_with_a_manual_entry_rejects_the_month(self, state):
        day = workdays(2025, 11, 1)[0]
        state['daily_records'][day] = [manual_entry(day)]
        results = apply_batch(state, [item(2025, 11, confirmed=True)])
        assert results[0]['status'] == 'rejected' and results[0]['codes'] == ['overlaps_existing']
        assert state['monatliche_historie'] == [] and len(state['daily_records'][day]) == 1

    def test_flex_balance_of_the_newest_month_wins(self, state):
        def flex(month, total):
            return {'total': total, 'year': 2025, 'month': month}
        apply_batch(state, [item(2025, 12, flex_balance=flex(12, 30.0)), item(2025, 10, flex_balance=flex(10, 5.0)),
                            item(2025, 11, flex_balance=flex(11, 20.0))])
        assert state['gleitzeit_saldo']['total'] == 30.0
        apply_batch(state, [item(2025, 9, flex_balance=flex(9, 1.0))])
        assert state['gleitzeit_saldo']['total'] == 30.0          # an older statement never overwrites a newer balance

    def test_garbage_input_is_rejected_without_an_exception(self, state):
        snapshot = copy.deepcopy(state)
        garbage = [None, 5, 'x', [], {}, {'year': '2025', 'month': 11, 'sessions': []},
                   {'year': 2025, 'month': 11}, {'year': 2025, 'month': 13, 'sessions': [session('2025-11-03')]},
                   {'year': True, 'month': 1, 'sessions': [session('2025-01-02')]}]
        results = apply_batch(state, garbage)
        assert len(results) == 5 and all(r['status'] == 'rejected' for r in results)     # the 4 non-dicts are skipped
        assert state == snapshot


class TestFlexHelper:
    def test_clean_flex_balance(self):
        assert clean_flex_balance(None) is None and clean_flex_balance({'x': 1}) is None
        assert clean_flex_balance({'total': 1e9}) is None
        assert clean_flex_balance({'total': True}) is None
        assert clean_flex_balance({'previous': 1.234, 'current': 2, 'total': 3.5}) == {'previous': 1.23, 'current': 2.0, 'total': 3.5}
