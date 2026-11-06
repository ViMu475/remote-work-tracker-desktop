"""Flextime per month: the series, the flextime lines of the final report and where the numbers come from."""
import json
import os
import re

import pytest

from services.final_report import build_final_report
from services.flex_service import clean_entry, normalize_series, record_flex, remove_month, series, summarize
from services.statement_import import apply_batch

from .test_batch_import_e2e import analyze, months_from, statement_pdf
from .test_statement_import import item, state, workdays  # noqa: F401  (state is a fixture)

ROOT = os.path.join(os.path.dirname(__file__), '..')
JS = open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8').read()
HTML = open(os.path.join(ROOT, 'templates', 'index.html'), encoding='utf-8').read()


def flex(previous=None, current=None, total=None, year=None, month=None):
    return {k: v for k, v in (('previous', previous), ('current', current), ('total', total),
                              ('year', year), ('month', month)) if v is not None}


class TestCleanEntry:
    def test_a_complete_entry(self):
        assert clean_entry({'jahr': 2026, 'monat': 5, 'vorperiode': 12.5, 'aktuell': 3.25, 'gesamt': 15.75}) == \
            {'jahr': 2026, 'monat': 5, 'vorperiode': 12.5, 'aktuell': 3.25, 'gesamt': 15.75}

    def test_one_number_is_enough_and_numbers_are_rounded(self):
        assert clean_entry({'jahr': 2026, 'monat': 5, 'gesamt': 1.23456}) == {'jahr': 2026, 'monat': 5, 'gesamt': 1.23}

    @pytest.mark.parametrize('raw', [
        None, 'text', [], {}, {'jahr': 2026, 'monat': 5},                                   # nothing to show
        {'jahr': True, 'monat': 5, 'gesamt': 1.0}, {'jahr': 2026, 'monat': True, 'gesamt': 1.0},
        {'jahr': 2026, 'monat': 0, 'gesamt': 1.0}, {'jahr': 2026, 'monat': 13, 'gesamt': 1.0},
        {'jahr': 1800, 'monat': 5, 'gesamt': 1.0}, {'jahr': '2026', 'monat': 5, 'gesamt': 1.0},
        {'jahr': 2026, 'monat': 5, 'gesamt': '15,75'}, {'jahr': 2026, 'monat': 5, 'gesamt': True},
        {'jahr': 2026, 'monat': 5, 'gesamt': float('nan')}, {'jahr': 2026, 'monat': 5, 'gesamt': float('inf')},
        {'jahr': 2026, 'monat': 5, 'gesamt': 1e9},
    ])
    def test_damaged_entries_are_rejected(self, raw):
        assert clean_entry(raw) is None

    def test_a_damaged_number_is_dropped_but_the_entry_stays(self):
        assert clean_entry({'jahr': 2026, 'monat': 5, 'aktuell': 'x', 'gesamt': 2.0}) == {'jahr': 2026, 'monat': 5, 'gesamt': 2.0}


class TestNormalizeSeries:
    def test_sorted_by_year_and_month_and_one_entry_per_month(self):
        raw = [{'jahr': 2026, 'monat': 3, 'gesamt': 3.0}, {'jahr': 2025, 'monat': 12, 'gesamt': 1.0},
               {'jahr': 2026, 'monat': 3, 'gesamt': 9.0}, {'jahr': 2025, 'monat': 2, 'gesamt': 0.5}]
        assert [(e['jahr'], e['monat'], e['gesamt']) for e in normalize_series(raw)] == [(2025, 2, 0.5), (2025, 12, 1.0), (2026, 3, 9.0)]

    @pytest.mark.parametrize('raw', [None, {}, 'x', 5, [None, 'x', 5, {}]])
    def test_nothing_usable_gives_an_empty_series(self, raw):
        assert normalize_series(raw) == []


class TestRecordFlex:
    def test_stores_the_three_numbers_of_the_statement(self):
        data = {}
        assert record_flex(data, flex(12.5, 3.25, 15.75, year=2026, month=5)) is True
        assert data['gleitzeit_verlauf'] == [{'jahr': 2026, 'monat': 5, 'vorperiode': 12.5, 'aktuell': 3.25, 'gesamt': 15.75}]

    def test_year_and_month_can_be_given_explicitly(self):
        data = {}
        assert record_flex(data, flex(total=4.0), 2025, 10) is True
        assert (data['gleitzeit_verlauf'][0]['jahr'], data['gleitzeit_verlauf'][0]['monat']) == (2025, 10)

    def test_the_same_month_is_replaced_and_the_series_stays_sorted(self):
        data = {}
        record_flex(data, flex(total=3.0), 2026, 3)
        record_flex(data, flex(total=1.0), 2025, 12)
        record_flex(data, flex(total=7.0), 2026, 3)
        assert [(e['jahr'], e['monat'], e['gesamt']) for e in data['gleitzeit_verlauf']] == [(2025, 12, 1.0), (2026, 3, 7.0)]

    @pytest.mark.parametrize('raw', [None, 'x', {}, flex(total=1.0), flex(total=1.0, year=2026), flex(year=2026, month=5)])
    def test_without_month_or_numbers_nothing_is_stored(self, raw):
        data = {}
        assert record_flex(data, raw) is False
        assert 'gleitzeit_verlauf' not in data

    def test_a_damaged_series_in_the_state_is_repaired(self):
        data = {'gleitzeit_verlauf': 'kaputt'}
        assert record_flex(data, flex(total=2.0), 2026, 1) is True
        assert len(data['gleitzeit_verlauf']) == 1


class TestRemoveMonth:
    def test_removes_only_that_month(self):
        data = {'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 4, 'gesamt': 1.0}, {'jahr': 2026, 'monat': 5, 'gesamt': 2.0},
                                      {'jahr': 2025, 'monat': 5, 'gesamt': 3.0}]}
        assert remove_month(data, 2026, 'Mai') is True
        assert [(e['jahr'], e['monat']) for e in data['gleitzeit_verlauf']] == [(2025, 5), (2026, 4)]

    @pytest.mark.parametrize('name', ['Mai', 'Smarch', None])
    def test_unknown_month_changes_nothing(self, name):
        data = {'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 4, 'gesamt': 1.0}]}
        assert remove_month(data, 2030, name) is False
        assert len(data['gleitzeit_verlauf']) == 1


class TestSeriesForCharts:
    def test_month_names_are_added(self):
        assert series({'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 3, 'gesamt': 1.0}]})[0]['monat_name'] == 'März'

    def test_older_data_with_only_the_latest_balance_still_shows_a_point(self):
        data = {'gleitzeit_saldo': {'previous': 1.0, 'current': 2.0, 'total': 3.0, 'year': 2026, 'month': 2}}
        assert [(e['jahr'], e['monat'], e['gesamt']) for e in series(data)] == [(2026, 2, 3.0)]

    def test_the_latest_balance_is_not_added_twice(self):
        data = {'gleitzeit_saldo': {'total': 3.0, 'year': 2026, 'month': 2},
                'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 2, 'gesamt': 8.0}]}
        assert [(e['monat'], e['gesamt']) for e in series(data)] == [(2, 8.0)]

    def test_no_data_no_series(self):
        assert series({}) == [] and series({'gleitzeit_saldo': 'x'}) == []

    def test_summary_of_the_series(self):
        s = summarize(series({'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 1, 'gesamt': 4.0}, {'jahr': 2026, 'monat': 2, 'gesamt': -6.5},
                                                    {'jahr': 2026, 'monat': 4, 'gesamt': 12.0}, {'jahr': 2026, 'monat': 5, 'gesamt': 9.0}]}))
        assert (s['latest'], s['min'], s['max']) == (9.0, -6.5, 12.0)
        assert (s['min_month']['monat_name'], s['max_month']['monat']) == ('Februar', 4)

    def test_summary_of_nothing(self):
        assert summarize([]) == {'latest': None, 'latest_month': None, 'min': None, 'min_month': None, 'max': None, 'max_month': None,
                                 'status': None, 'months_yellow': 0, 'months_red': 0}


def history_month(name, year, remote=10.0):
    return {'monat': name, 'jahr': year, 'ist_remote_stunden_laufend': remote, 'max_remote_stunden': 40.0,
            'soll_stunden_gesamt': 160.0, 'ist_arbeitszeit_laufend': 160.0, 'individuelle_quote': 40.0, 'quartal': 'Q1/2026'}


class TestFinalReportFlextime:
    HISTORY = [history_month('Januar', 2026), history_month('Februar', 2026), history_month('März', 2026)]
    SERIES = [{'jahr': 2026, 'monat': 1, 'aktuell': 2.0, 'gesamt': 10.0, 'monat_name': 'Januar'},
              {'jahr': 2026, 'monat': 2, 'aktuell': -3.5, 'gesamt': 6.5, 'monat_name': 'Februar'}]

    def test_months_carry_their_flextime(self):
        months = build_final_report(self.HISTORY, self.SERIES)['quarters'][0]['months']
        assert [(m['flex_total'], m['flex_change']) for m in months] == [(10.0, 2.0), (6.5, -3.5), (None, None)]

    def test_quarter_has_the_balance_at_its_end_and_the_change(self):
        q = build_final_report(self.HISTORY, self.SERIES)['quarters'][0]
        assert (q['flex_end'], q['flex_change']) == (6.5, -1.5)

    def test_whole_series_and_summary_are_part_of_the_report(self):
        part = build_final_report(self.HISTORY, self.SERIES)['flex']
        assert part['series'] == self.SERIES
        assert (part['summary']['latest'], part['summary']['min'], part['summary']['max']) == (6.5, 6.5, 10.0)

    def test_without_flextime_the_values_are_empty(self):
        report = build_final_report(self.HISTORY)
        assert report['quarters'][0]['flex_end'] is None and report['quarters'][0]['flex_change'] is None
        assert report['flex']['series'] == [] and report['flex']['summary']['latest'] is None
        assert all(m['flex_total'] is None for m in report['quarters'][0]['months'])

    def test_flextime_of_another_year_does_not_leak_into_the_month(self):
        other_year = [{'jahr': 2025, 'monat': 1, 'aktuell': 9.0, 'gesamt': 99.0, 'monat_name': 'Januar'}]
        assert build_final_report(self.HISTORY, other_year)['quarters'][0]['months'][0]['flex_total'] is None

    def test_the_other_values_of_the_report_do_not_change(self):
        assert build_final_report(self.HISTORY, self.SERIES)['overall'] == build_final_report(self.HISTORY)['overall']

    def test_a_series_with_junk_does_not_break_the_report(self):
        report = build_final_report(self.HISTORY, [None, 'x', {'jahr': 2026}, {'monat': 1}])
        assert report['quarters'][0]['flex_end'] is None


class TestBatchImportKeepsFlextime:
    def test_every_imported_month_keeps_its_own_numbers(self, state):
        apply_batch(state, [item(2025, 11, flex_balance=flex(1.0, 2.0, 3.0, 2025, 11)),
                            item(2025, 10, flex_balance=flex(-1.0, 1.0, 0.0, 2025, 10))])
        assert [(e['monat'], e['vorperiode'], e['aktuell'], e['gesamt']) for e in state['gleitzeit_verlauf']] == \
            [(10, -1.0, 1.0, 0.0), (11, 1.0, 2.0, 3.0)]
        assert state['gleitzeit_saldo']['total'] == 3.0                      # unchanged rule: the newest month

    def test_the_month_of_the_import_counts_not_the_one_in_the_flextime_data(self, state):
        apply_batch(state, [item(2025, 11, flex_balance=flex(total=3.0, year=1999, month=1))])
        assert [(e['jahr'], e['monat']) for e in state['gleitzeit_verlauf']] == [(2025, 11)]

    def test_a_rejected_month_records_nothing(self, state):
        results = apply_batch(state, [item(2025, 11, flex_balance=flex(total=3.0, year=2025, month=11), quote=99)])
        assert results[0]['status'] == 'rejected'
        assert not state.get('gleitzeit_verlauf')

    def test_a_month_without_flextime_records_nothing(self, state):
        apply_batch(state, [item(2025, 11)])
        assert not state.get('gleitzeit_verlauf')

    def test_importing_again_replaces_the_month(self, state):
        apply_batch(state, [item(2025, 11, flex_balance=flex(total=3.0, year=2025, month=11))])
        apply_batch(state, [item(2025, 11, confirmed=True, flex_balance=flex(total=5.0, year=2025, month=11))])
        assert [(e['monat'], e['gesamt']) for e in state['gleitzeit_verlauf']] == [(11, 5.0)]

    def test_an_older_statement_adds_a_point_without_changing_the_latest_balance(self, state):
        apply_batch(state, [item(2025, 11, flex_balance=flex(total=3.0, year=2025, month=11))])
        apply_batch(state, [item(2025, 9, flex_balance=flex(total=-4.0, year=2025, month=9))])
        assert [e['monat'] for e in state['gleitzeit_verlauf']] == [9, 11]
        assert state['gleitzeit_saldo']['total'] == 3.0


def import_months(client, *months):
    """Real PDF files with the flextime summary of SAP through the real parser and the batch routes."""
    files = []
    for year, month, previous, current, total in months:
        header = [f'Time statement from 01.{month:02d}.{year} to 28.{month:02d}.{year}', f'Flex. Bal. Prev. Period {previous}',
                  f'Flextime Bal. Curr. Period {current}', f'Flextime Balance Total {total}']
        # March 2026 is the open month of the sample state, which has hand-typed entries on its first days
        days = workdays(year, month, 12)[6:9] if (year, month) == (2026, 3) else workdays(year, month, 3)
        files.append((f'm{year}{month}.pdf', statement_pdf(header, [(d, '08:00', '16:30', 'Remote Work') for d in days])))
    reports = analyze(client, files)['reports']
    return client.post('/api/pdf/batch/import', json={'months': months_from(reports, confirmed=True)}).get_json()


def flex_part(client):
    return client.get('/api/report/final').get_json()['report']['flex']


class TestRoutes:
    def test_real_pdfs_flextime_reaches_the_report_per_month_and_quarter(self, client):
        body = import_months(client, (2025, 10, '1,00', '2,00', '3,00'), (2025, 11, '3,00', '1,50-', '1,50'),
                             (2025, 12, '1,50', '4,00', '5,50'))
        assert body['imported_count'] == 3
        report = client.get('/api/report/final').get_json()['report']
        assert [(e['monat'], e['aktuell'], e['gesamt']) for e in report['flex']['series']] == [(10, 2.0, 3.0), (11, -1.5, 1.5), (12, 4.0, 5.5)]
        quarter = report['quarters'][0]
        assert (quarter['flex_end'], quarter['flex_change']) == (5.5, 4.5)
        assert [m['flex_total'] for m in quarter['months']] == [3.0, 1.5, 5.5]
        assert report['flex']['summary']['min'] == 1.5

    def test_the_open_month_is_in_the_series_but_not_in_the_quarters(self, client):
        import_months(client, (2026, 3, '1,00', '2,00', '3,00'))             # March 2026 is the open month in the suite
        assert 3 in [e['monat'] for e in flex_part(client)['series']]

    def test_single_import_records_the_month_too(self, client):
        sessions = [{'date': d, 'start_time': '08:00', 'end_time': '16:30', 'is_remote': True} for d in workdays(2025, 11, 2)]
        body = client.post('/api/pdf/import', json={'sessions': sessions, 'flex_balance': flex(1.0, 2.0, 3.0, 2025, 11)}).get_json()
        assert body['success'] is True
        assert [(e['jahr'], e['monat'], e['gesamt']) for e in flex_part(client)['series']] == [(2025, 11, 3.0)]

    def test_deleting_a_month_from_the_history_removes_its_point(self, client):
        import_months(client, (2025, 10, '0,00', '1,00', '1,00'), (2025, 11, '1,00', '1,00', '2,00'))
        assert client.delete('/api/delete_month/Oktober/2025').get_json()['success'] is True
        assert [e['monat'] for e in flex_part(client)['series']] == [11]

    def test_clearing_the_history_clears_the_series(self, client):
        import_months(client, (2025, 10, '0,00', '1,00', '1,00'))
        assert 10 in [e['monat'] for e in flex_part(client)['series']]
        client.post('/api/clear_all_history')
        assert 10 not in [e['monat'] for e in flex_part(client)['series']]

    def test_backup_and_restore_keep_the_series(self, client):
        import_months(client, (2025, 10, '0,00', '1,00', '1,00'), (2025, 11, '1,00', '1,00', '2,00'))
        backup = client.get('/api/backup').get_data()
        client.post('/api/clear_all_history')
        restored = client.post('/api/restore', data=backup, content_type='application/json').get_json()
        assert restored['success'] is True
        assert [e['monat'] for e in flex_part(client)['series']] == [10, 11]

    def test_restore_of_an_old_backup_without_the_series_works(self, client):
        backup = json.loads(client.get('/api/backup').get_data())
        backup.pop('gleitzeit_verlauf', None)
        restored = client.post('/api/restore', data=json.dumps(backup), content_type='application/json').get_json()
        assert restored['success'] is True
        assert client.get('/api/state').get_json()['gleitzeit_verlauf'] == []

    def test_restore_drops_damaged_entries(self, client):
        backup = json.loads(client.get('/api/backup').get_data())
        backup['gleitzeit_verlauf'] = [{'jahr': 2026, 'monat': 2, 'gesamt': 1.0}, {'jahr': 'x'}, None, 'x']
        assert client.post('/api/restore', data=json.dumps(backup), content_type='application/json').get_json()['success'] is True
        assert client.get('/api/state').get_json()['gleitzeit_verlauf'] == [{'jahr': 2026, 'monat': 2, 'gesamt': 1.0}]


class TestFrontend:
    def keys(self, language):
        start = JS.index(f'    {language}: {{')
        block = JS[start:JS.index('\n    }', start)]
        return {k for k in re.findall(r"(\w+): '", block) if k.startswith(('flex_', 'err_flex', 'advice_', 'fm_'))}

    def test_both_languages_have_the_same_flextime_texts(self):
        de, en = self.keys('de'), self.keys('en')
        assert de == en and {'flex_title', 'flex_chart_empty', 'flex_quarter_end', 'flex_legend_total', 'err_flex'} <= de

    def test_dialog_button_and_handlers_exist(self):
        for element in ('flex-chart-modal', 'flex-chart-body', 'btn-flex-chart'):
            assert f'id="{element}"' in HTML
        for handler in ('handleFlexChart', 'closeFlexChart', 'renderFlexChart'):
            assert f'function {handler}' in JS
        assert 'handleFlexChart()' in HTML and 'closeFlexChart()' in HTML

    def test_the_report_shows_the_chart_and_the_flextime_lines(self):
        body = JS.split('function renderFinalReport')[1].split('function signedHours')[0]
        assert 'renderFlexChart(report.flex)' in body and 'flex_quarter_end' in body and 'flex_total' in body
