"""history_service (month record, quarter summary) and the year check of the quarter totals (fictional data)."""
import copy

import pytest

from services.history_service import (
    build_month_record, month_entry_totals, month_has_entries, safe_number, update_quarter_summary,
)
from services.state_service import StateService

from .test_close_month_history import close, restore, state_for


def day_entry(date, remote=4.0, total=8.0):
    return {'id': 'x' + date, 'datum': date, 'startTime': '08:00', 'endTime': '16:30', 'pauseMinutes': 30,
            'remoteStundenHeute': remote, 'totalStundenHeute': total, 'source': None}


@pytest.fixture
def state(sample_state):
    return copy.deepcopy(sample_state)


class TestSafeNumber:
    @pytest.mark.parametrize('value,expected', [(1, 1.0), ('2.5', 2.5), (None, 0.0), (True, 0.0), ('x', 0.0), ([1], 0.0),
                                                (float('nan'), 0.0), (float('inf'), 0.0), (10 ** 400, 0.0)])
    def test_values(self, value, expected):
        assert safe_number(value) == expected

    def test_default(self):
        assert safe_number('x', None) is None and safe_number(None, 7) == 7


class TestMonthRecord:
    def test_totals_and_limits_of_a_month(self, state):
        state['daily_records'] = {'2025-11-03': [day_entry('2025-11-03', 4, 8)], '2025-11-04': [day_entry('2025-11-04', 8, 8)],
                                  '2025-12-01': [day_entry('2025-12-01', 8, 8)]}
        record = build_month_record(state, 'November', 2025)
        assert record['ist_remote_stunden_laufend'] == 12.0 and record['ist_arbeitszeit_laufend'] == 16.0
        assert record['quartal'] == 'Q4/2025' and record['individuelle_quote'] == 40.0
        assert record['max_remote_stunden'] == record['soll_stunden_gesamt'] * 0.4
        assert record['tatsaechliche_remote_quote'] == 12.0 / record['soll_stunden_gesamt'] * 100

    def test_own_quota(self, state):
        record = build_month_record(state, 'November', 2025, quote=50)
        assert record['individuelle_quote'] == 50 and record['max_remote_stunden'] == record['soll_stunden_gesamt'] * 0.5

    def test_damaged_entries_count_as_zero(self, state):
        state['daily_records'] = {'2025-11-03': [day_entry('2025-11-03'), None, 'x', {'remoteStundenHeute': 'bad'}],
                                  '2025-11-04': 'not a list', 5: [day_entry('2025-11-05')]}
        assert month_entry_totals(state, 'November', 2025) == (4.0, 8.0)

    def test_has_entries(self, state):
        state['daily_records'] = {'2025-11-03': [day_entry('2025-11-03')], '2025-12-01': []}
        assert month_has_entries(state, 'November', 2025)
        assert not month_has_entries(state, 'Dezember', 2025) and not month_has_entries(state, 'Januar', 2026)

    def test_same_record_as_closing_the_month_by_hand(self, client, sample_state):
        dates = ['2026-01-05', '2026-01-06', '2026-01-07']
        state = state_for(sample_state, 'Januar', 2026, dates)
        expected = build_month_record(state, 'Januar', 2026)
        restore(client, state)
        closed = close(client)['state']['monatliche_historie'][0]
        assert closed == expected


class TestQuarterSummary:
    def months(self, remote=(10.0, 20.0, 30.0)):
        return [{'monat': name, 'quartal': 'Q4/2025', 'soll_stunden_gesamt': 160.0, 'ist_remote_stunden_laufend': r,
                 'ist_arbeitszeit_laufend': 150.0, 'tatsaechliche_remote_quote': r / 160 * 100}
                for name, r in zip(('Oktober', 'November', 'Dezember'), remote)]

    def test_incomplete_quarter_is_left_alone(self):
        history = self.months()[:2]
        assert update_quarter_summary(history, 'Q4/2025') is None
        assert all('quartal_quote' not in m for m in history)

    def test_complete_quarter(self):
        history = self.months() + [{'monat': 'Januar', 'quartal': 'Q1/2026'}]
        summary = update_quarter_summary(history, 'Q4/2025')
        assert summary['gesamt_ist_remote'] == 60.0 and summary['gesamt_soll'] == 480.0
        assert all(m['quartal_remote'] == 60.0 and m['quartal_soll'] == 480.0 and m['quartal_gesamt'] == 450.0
                   for m in history[:3])
        assert 'quartal_remote' not in history[3]
        assert summary['quartal_quote'] == pytest.approx(sum(r / 160 * 100 for r in (10, 20, 30)) / 3)

    def test_damaged_months_do_not_break_it(self):
        history = self.months() + [None, 'x', {'quartal': 'Q4/2025', 'ist_remote_stunden_laufend': 'bad'}]
        assert update_quarter_summary(history, 'Q4/2025')['gesamt_ist_remote'] == 60.0


class TestQuarterTotalsRespectTheYear:
    def test_entries_of_the_same_months_in_other_years_do_not_count(self, state):
        state['current_quartal'] = 'Q1/2026'
        state['daily_records'] = {'2026-02-03': [day_entry('2026-02-03', 4, 8)],
                                  '2025-02-03': [day_entry('2025-02-03', 8, 8)],      # kept import of last year
                                  '2024-03-04': [day_entry('2024-03-04', 8, 8)]}
        totals = StateService(data_file='unused').calculate_quartal_totals(state)
        assert totals['quartal_remote'] == 4.0 and totals['quartal_gesamt'] == 8.0

    def test_an_unreadable_quarter_name_keeps_the_old_behaviour(self, state):
        state['current_quartal'] = 'broken'
        assert StateService(data_file='unused').calculate_quartal_totals(state)['quartal_remote'] == 0.0
