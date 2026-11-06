"""Flextime traffic light, detailed month analysis and the proposals to reduce overtime (fictional data only)."""
import os
import re
from datetime import date

import pytest

from services import flex_analysis, flex_service
from services.final_report import build_final_report
from services.flex_analysis import advice, analyze_month, workdays
from services.flex_service import status, summarize

from .test_flextime import import_months

ROOT = os.path.join(os.path.dirname(__file__), '..')
JS = open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8').read()
HTML = open(os.path.join(ROOT, 'templates', 'index.html'), encoding='utf-8').read()
TODAY = date(2026, 11, 6)           # a Friday: 17 working days are left in November 2026


class TestStatus:
    @pytest.mark.parametrize('balance, expected', [
        (0, 'ok'), (39.99, 'ok'), (40.0, 'ok'), (40.01, 'yellow_pos'), (59.99, 'yellow_pos'), (60.0, 'yellow_pos'),
        (60.01, 'red_pos'), (250, 'red_pos'),
        (-40.0, 'ok'), (-40.01, 'yellow_neg'), (-60.0, 'yellow_neg'), (-60.01, 'red_neg'),
    ])
    def test_the_thresholds_of_the_employee_portal(self, balance, expected):
        assert status(balance) == expected

    @pytest.mark.parametrize('balance', [None, True, 'x', float('nan'), [], {}])
    def test_no_number_no_status(self, balance):
        assert status(balance) is None

    def test_series_entries_carry_their_status(self):
        data = {'gleitzeit_verlauf': [{'jahr': 2026, 'monat': 1, 'gesamt': 41.0}, {'jahr': 2026, 'monat': 2, 'gesamt': -61.0},
                                      {'jahr': 2026, 'monat': 3, 'aktuell': 2.0}]}
        assert [e['status'] for e in flex_service.series(data)] == ['yellow_pos', 'red_neg', None]

    def test_summary_counts_the_yellow_and_red_months(self):
        entries = flex_service.series({'gleitzeit_verlauf': [
            {'jahr': 2026, 'monat': m, 'gesamt': v} for m, v in enumerate([10, 45, 55, 70, -45, 5], start=1)]})
        s = summarize(entries)
        assert (s['months_yellow'], s['months_red'], s['status']) == (3, 1, 'ok')

    def test_report_rows_and_quarters_have_a_status(self):
        history = [{'monat': m, 'jahr': 2026, 'quartal': 'Q1/2026', 'ist_remote_stunden_laufend': 1.0, 'max_remote_stunden': 40.0,
                    'soll_stunden_gesamt': 160.0, 'ist_arbeitszeit_laufend': 160.0, 'individuelle_quote': 40.0}
                   for m in ('Januar', 'Februar', 'März')]
        series = [{'jahr': 2026, 'monat': 1, 'gesamt': 10.0}, {'jahr': 2026, 'monat': 2, 'gesamt': 45.0}, {'jahr': 2026, 'monat': 3, 'gesamt': 61.0}]
        quarter = build_final_report(history, series)['quarters'][0]
        assert [m['flex_status'] for m in quarter['months']] == ['ok', 'yellow_pos', 'red_pos']
        assert quarter['flex_status'] == 'red_pos'

    def test_report_without_flextime_has_no_status(self):
        history = [{'monat': 'Januar', 'jahr': 2026, 'quartal': 'Q1/2026'}]
        quarter = build_final_report(history)['quarters'][0]
        assert quarter['flex_status'] is None and quarter['months'][0]['flex_status'] is None


def entry(day, start, end, net, remote=0.0):
    return {'datum': day, 'startTime': start, 'endTime': end, 'totalStundenHeute': net, 'remoteStundenHeute': remote}


def november_state():
    return {'soll_stunden_pro_tag': 8.0, 'daily_records': {
        '2025-11-03': [entry('2025-11-03', '08:00', '16:30', 8.0, 8.0)],
        '2025-11-04': [entry('2025-11-04', '08:00', '19:00', 10.5)],          # more than 10 hours
        '2025-11-05': [entry('2025-11-05', '05:30', '14:00', 8.0, 4.0)],      # before 06:00
        '2025-11-06': [entry('2025-11-06', '12:00', '20:30', 8.0)],           # after 20:00
        '2025-11-08': [entry('2025-11-08', '09:00', '12:00', 3.0)],           # Saturday
    }, 'gleitzeit_verlauf': [{'jahr': 2025, 'monat': 11, 'vorperiode': 20.0, 'aktuell': -122.0, 'gesamt': -102.0}]}


class TestAnalyzeMonth:
    def test_totals_of_a_finished_month(self):
        a = analyze_month(november_state(), 2025, 11, today=TODAY)
        t = a['totals']
        assert a['complete'] is True and a['has_entries'] is True
        assert (t['days_worked'], t['net'], t['remote'], t['soll'], t['delta_calc']) == (5, 37.5, 12.0, 160.0, -122.5)
        assert (t['avg_net'], t['avg_start'], t['avg_end']) == (7.5, '08:30', '16:24')
        assert t['longest'] == {'datum': '2025-11-04', 'net': 10.5}

    def test_signs_of_overtime_are_counted(self):
        t = analyze_month(november_state(), 2025, 11, today=TODAY)['totals']
        assert (t['long_days'], t['early_days'], t['late_days'], t['non_working_days']) == (1, 1, 1, 1)

    def test_working_days_without_an_entry_are_listed_with_their_target_hours(self):
        t = analyze_month(november_state(), 2025, 11, today=TODAY)['totals']
        assert len(t['missing_days']) == 16 and t['missing_hours'] == 128.0
        assert '2025-11-07' in t['missing_days'] and '2025-11-03' not in t['missing_days']

    def test_the_running_balance_ends_at_net_minus_target(self):
        a = analyze_month(november_state(), 2025, 11, today=TODAY)
        assert a['days'][-1]['balance'] == a['totals']['delta_calc']
        assert a['days'][0]['datum'] == '2025-11-03' and a['days'][0]['balance'] == 0.0
        assert a['days'][1]['balance'] == 2.5                                  # 8.0 - 8 + 10.5 - 8

    def test_rows_carry_their_flags(self):
        rows = {r['datum']: r for r in analyze_month(november_state(), 2025, 11, today=TODAY)['days']}
        assert rows['2025-11-04']['flags'] == ['long_day'] and rows['2025-11-05']['flags'] == ['early']
        assert rows['2025-11-06']['flags'] == ['late'] and rows['2025-11-08']['flags'] == ['non_working_day']
        assert rows['2025-11-07']['flags'] == ['no_entry'] and rows['2025-11-08']['soll'] == 0.0

    def test_weeks_add_up_to_the_month(self):
        a = analyze_month(november_state(), 2025, 11, today=TODAY)
        assert [w['week'] for w in a['weeks']] == [45, 46, 47, 48]
        assert round(sum(w['delta'] for w in a['weeks']), 2) == a['totals']['delta_calc']
        assert (a['weeks'][0]['net'], a['weeks'][0]['soll'], a['weeks'][0]['days']) == (37.5, 40.0, 5)

    def test_the_numbers_of_the_statement_and_the_difference(self):
        a = analyze_month(november_state(), 2025, 11, today=TODAY)
        assert a['flex'] == {'vorperiode': 20.0, 'aktuell': -122.0, 'gesamt': -102.0, 'status': 'red_neg'}
        assert a['difference'] == 0.5                                           # statement change minus net-minus-target

    def test_a_running_month_counts_the_target_only_until_today(self):
        state = {'soll_stunden_pro_tag': 8.0, 'daily_records': {'2026-03-02': [entry('2026-03-02', '08:00', '16:30', 8.0)]}}
        a = analyze_month(state, 2026, 3, today=date(2026, 3, 15))
        assert a['complete'] is False and a['totals']['soll'] == 80.0           # 10 working days up to the 13th
        assert a['difference'] is None

    def test_a_future_month_has_no_target_and_no_rows(self):
        a = analyze_month({'soll_stunden_pro_tag': 8.0, 'daily_records': {}}, 2026, 6, today=date(2026, 3, 15))
        assert a['days'] == [] and a['totals']['soll'] == 0.0 and a['has_entries'] is False

    def test_a_month_without_entries_lists_all_working_days_as_missing(self):
        a = analyze_month({'soll_stunden_pro_tag': 8.0, 'daily_records': {}}, 2025, 11, today=TODAY)
        assert a['has_entries'] is False and len(a['totals']['missing_days']) == 20
        assert a['totals']['avg_net'] is None and a['totals']['longest'] is None

    def test_the_target_follows_the_state(self):
        state = {'soll_stunden_pro_tag': 7.5, 'daily_records': {}}
        assert analyze_month(state, 2025, 11, today=TODAY)['totals']['soll'] == 150.0

    @pytest.mark.parametrize('records', [
        None, 'x', {'2025-11-03': 'x'}, {'2025-11-03': [None, 'x', 5]}, {'kaputt': [entry('kaputt', '08:00', '09:00', 1.0)]},
        {'2025-11-03': [{'startTime': 'x', 'endTime': None, 'totalStundenHeute': 'viel', 'remoteStundenHeute': True}]},
    ])
    def test_damaged_records_do_not_break_the_analysis(self, records):
        a = analyze_month({'soll_stunden_pro_tag': 8.0, 'daily_records': records}, 2025, 11, today=TODAY)
        assert a['totals']['net'] == 0.0 and a['year'] == 2025

    def test_damaged_target_hours_fall_back_to_eight(self):
        assert analyze_month({'soll_stunden_pro_tag': 'x', 'daily_records': {}}, 2025, 11, today=TODAY)['totals']['soll'] == 160.0

    def test_the_analysis_does_not_change_the_state(self):
        state = november_state()
        before = repr(state)
        analyze_month(state, 2025, 11, today=TODAY)
        assert repr(state) == before


class TestWorkdays:
    def test_holidays_and_weekends_are_skipped(self):
        assert [d.isoformat() for d in workdays(date(2026, 5, 1), date(2026, 5, 5))] == ['2026-05-04', '2026-05-05']   # May Day is a Friday

    def test_christmas_eve_has_no_target_new_year_eve_half(self):
        assert date(2026, 12, 24) not in workdays(date(2026, 12, 21), date(2026, 12, 31))
        assert flex_analysis.target_hours(date(2026, 12, 31), 8.0) == 4.0


def series_of(*balances, changes=None, start_month=1):
    """A series of month-end balances (and their changes) as flex_service.series() delivers it."""
    out = []
    for i, balance in enumerate(balances):
        item = {'jahr': 2026, 'monat': start_month + i, 'gesamt': balance}
        if changes:
            item['aktuell'] = changes[i]
        out.append(item)
    return out


def codes(result):
    return [item['code'] for item in result['items']]


def item_of(result, code):
    return next(i for i in result['items'] if i['code'] == code)


class TestAdvice:
    def test_no_data_no_proposals(self):
        assert advice({}, today=TODAY, entries=[]) == {'as_of': None, 'balance': None, 'status': None, 'trend': None, 'items': []}

    def test_yellow_balance_gets_a_plan_to_get_below_the_buffer(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(45.0))
        assert result['status'] == 'yellow_pos' and result['as_of']['monat_name'] == 'Januar'
        assert codes(result) == ['reduce', 'flex_days', 'shorter_days']
        assert item_of(result, 'reduce')['params'] == {'balance': 45.0, 'over': 5.0, 'limit': 40.0, 'target': 30.0, 'need': 15.0}
        assert item_of(result, 'flex_days')['params'] == {'days': 1.9, 'full_days': 1, 'rest': 7.0, 'soll': 8.0}
        assert item_of(result, 'shorter_days')['params'] == {'per_day': 0.88, 'workdays': 17, 'until': '2026-11-30'}
        assert {i['priority'] for i in result['items']} == {'medium'}

    def test_a_high_balance_is_urgent_and_asks_to_talk_to_the_manager(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(55.0))
        assert [i['priority'] for i in result['items']][:3] == ['high', 'high', 'high']
        assert 'approval' in codes(result) and item_of(result, 'approval')['priority'] == 'medium'

    def test_above_sixty_hours_the_cut_off_is_announced_first(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(62.0))
        assert codes(result)[0] == 'cap_cut' and item_of(result, 'cap_cut')['params']['over'] == 2.0
        assert result['status'] == 'red_pos'

    def test_close_to_the_yellow_limit_is_a_warning_before_it_happens(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(35.0))
        assert 'near_limit' in codes(result) and 'reduce' not in codes(result)
        assert item_of(result, 'near_limit')['params']['to_limit'] == 5.0

    def test_a_comfortable_balance_needs_nothing(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(20.0, changes=[0.0]))
        assert codes(result) == ['on_track']

    def test_a_growing_balance_is_announced_with_the_months_left(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(13.0, 17.0, 21.0, 25.0, changes=[4.0, 4.0, 4.0, 4.0]))
        assert codes(result) == ['trend_up'] and item_of(result, 'trend_up')['params']['months'] == 3.8

    def test_a_distant_limit_is_not_a_warning(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(0.0, 1.0, 2.0, changes=[1.0, 1.0, 1.0]))
        assert 'trend_up' not in codes(result)

    def test_a_balance_over_the_limit_that_keeps_growing_says_so(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(40.0, 45.0, changes=[3.0, 5.0]))
        assert 'trend_up_over' in codes(result) and item_of(result, 'trend_up_over')['params']['trend'] == 4.0

    def test_strongly_negative_balance_asks_to_check_the_bookings(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(-45.0))
        assert codes(result) == ['check_missing'] and result['items'][0]['priority'] == 'high'

    def test_a_slightly_negative_balance_is_a_note(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(-15.0))
        assert codes(result) == ['build_up'] and item_of(result, 'build_up')['params']['need'] == 15.0

    def test_the_plan_continues_into_the_next_month_when_few_days_are_left(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=date(2026, 11, 27), entries=series_of(45.0))
        params = item_of(result, 'shorter_days')['params']
        assert params['until'] == '2026-12-31' and params['workdays'] > 5

    def test_the_target_hours_of_the_state_are_used(self):
        result = advice({'soll_stunden_pro_tag': 7.5}, today=TODAY, entries=series_of(45.0))
        assert item_of(result, 'flex_days')['params']['soll'] == 7.5

    def test_items_are_sorted_by_priority(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(55.0, changes=[5.0]))
        order = [flex_analysis.PRIORITIES[i['priority']] for i in result['items']]
        assert order == sorted(order)

    def test_a_month_with_overtime_signs_adds_the_causes(self):
        analysis = {'totals': {'long_days': 3, 'avg_net': 8.9, 'days_worked': 20, 'non_working_days': 1, 'early_days': 1, 'late_days': 2}}
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(45.0), analysis=analysis)
        assert {'long_days', 'daily_surplus', 'weekend_work', 'outside_window'} <= set(codes(result))
        assert item_of(result, 'daily_surplus')['params'] == {'avg_over': 0.9, 'per_month': 18.0, 'soll': 8.0}
        assert item_of(result, 'outside_window')['params'] == {'n': 3}

    def test_the_causes_are_only_listed_when_there_is_overtime(self):
        analysis = {'totals': {'long_days': 3, 'avg_net': 8.9, 'days_worked': 20, 'non_working_days': 1, 'early_days': 1, 'late_days': 2}}
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(5.0), analysis=analysis)
        assert codes(result) == ['on_track']

    def test_proposals_use_the_latest_month_with_a_balance(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(70.0, 10.0))
        assert result['balance'] == 10.0 and result['as_of']['monat'] == 2

    def test_junk_entries_are_ignored(self):
        result = advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=[None, 'x', {'jahr': 2026, 'monat': 1}, series_of(45.0)[0]])
        assert result['balance'] == 45.0

    def test_advice_does_not_change_the_state(self):
        state = {'soll_stunden_pro_tag': 8.0, 'gleitzeit_verlauf': series_of(45.0)}
        before = repr(state)
        advice(state, today=TODAY)
        assert repr(state) == before


class TestRoutes:
    def test_month_analysis_of_imported_statements(self, client):
        import_months(client, (2025, 11, '1,00', '2,00', '3,00'))
        body = client.get('/api/flex/month/2025/11').get_json()
        assert body['success'] is True
        a = body['analysis']
        assert (a['year'], a['month'], a['monat_name']) == (2025, 11, 'November')
        assert a['flex'] == {'vorperiode': 1.0, 'aktuell': 2.0, 'gesamt': 3.0, 'status': 'ok'}
        assert a['totals']['days_worked'] == 3 and a['complete'] is True

    @pytest.mark.parametrize('path', ['/api/flex/month/2025/0', '/api/flex/month/2025/13', '/api/flex/month/1800/5', '/api/flex/month/9999/5'])
    def test_an_invalid_month_is_rejected(self, client, path):
        assert client.get(path).status_code == 400

    def test_a_month_without_any_data_still_answers(self, client):
        body = client.get('/api/flex/month/2020/1').get_json()
        assert body['success'] is True and body['analysis']['has_entries'] is False

    def test_the_report_carries_advice_and_limits(self, client):
        import_months(client, (2025, 10, '30,00', '16,00', '46,00'))
        flex = client.get('/api/report/final').get_json()['report']['flex']
        assert flex['limits'] == {'yellow': 40.0, 'red': 60.0, 'target': 30.0}
        assert flex['advice']['status'] == 'yellow_pos' and 'reduce' in [i['code'] for i in flex['advice']['items']]
        assert flex['series'][0]['status'] == 'yellow_pos' and flex['summary']['months_yellow'] == 1

    def test_the_report_without_flextime_has_empty_advice(self, client):
        flex = client.get('/api/report/final').get_json()['report']['flex']
        assert flex['advice']['items'] == [] and flex['advice']['balance'] is None


ALL_CODES = ['cap_cut', 'reduce', 'near_limit', 'flex_days', 'shorter_days', 'approval', 'trend_up', 'trend_up_over', 'long_days',
             'daily_surplus', 'weekend_work', 'outside_window', 'build_up', 'check_missing', 'on_track']


def language_texts(name):
    start = JS.index(f'    {name}: {{')
    block = JS[start:JS.index('\n    }', start)]
    return dict(re.findall(r"(\w+): '((?:[^'\\]|\\.)*)'", block))


DE, EN = language_texts('de'), language_texts('en')


class TestFrontend:
    @pytest.mark.parametrize('code', ALL_CODES)
    def test_every_proposal_the_server_can_make_has_a_text_in_both_languages(self, code):
        assert f'advice_{code}' in DE and f'advice_{code}' in EN

    def test_the_proposals_of_the_server_cover_exactly_these_codes(self):
        source = open(os.path.join(ROOT, 'services', 'flex_analysis.py'), encoding='utf-8').read()
        assert set(re.findall(r"add\('(\w+)'", source)) == set(ALL_CODES)

    def test_the_texts_use_the_placeholders_the_server_sends(self):
        analysis = {'totals': {'long_days': 1, 'avg_net': 9.0, 'days_worked': 20, 'non_working_days': 1, 'early_days': 1, 'late_days': 0}}
        scenarios = [
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(62.0, changes=[5.0]), analysis=analysis),
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(35.0)),
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(13.0, 17.0, 21.0, 25.0, changes=[4.0, 4.0, 4.0, 4.0])),
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(-45.0)),
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(-15.0)),
            advice({'soll_stunden_pro_tag': 8.0}, today=TODAY, entries=series_of(20.0)),
        ]
        seen = {}
        for result in scenarios:
            for found in result['items']:
                seen[found['code']] = set(found['params'])
        for code, params in seen.items():
            for texts in (DE, EN):
                assert set(re.findall(r'\{(\w+)\}', texts[f'advice_{code}'])) == params, (code, texts is DE)
        assert set(seen) == set(ALL_CODES)

    def test_german_and_english_have_the_same_texts(self):
        prefixes = ('flex_', 'advice_', 'fm_')
        assert {k for k in DE if k.startswith(prefixes)} == {k for k in EN if k.startswith(prefixes)}

    @pytest.mark.parametrize('flag', ['no_entry', 'long_day', 'early', 'late', 'non_working_day'])
    def test_every_day_flag_has_a_text(self, flag):
        assert f'fm_flag_{flag}' in DE and f'fm_flag_{flag}' in EN

    @pytest.mark.parametrize('state', ['ok', 'yellow_pos', 'red_pos', 'yellow_neg', 'red_neg'])
    def test_every_status_has_a_text(self, state):
        assert f'flex_status_{state}' in DE and f'flex_status_{state}' in EN

    def test_functions_and_elements_exist(self):
        for function in ('renderFlexAdvice', 'renderFlexMonth', 'loadFlexMonth', 'flexBadge', 'tp', 'adviceParams'):
            assert f'function {function}' in JS
        assert 'flex-chart-modal' in HTML and 'min(96vw,56rem)' in HTML

    def test_the_chart_draws_both_bands_and_their_limit_lines(self):
        body = JS.split('function renderFlexChart')[1].split('async function handleFlexChart')[0]
        assert 'data-flex-band' in body and 'data-flex-limit' in body and 'limits.yellow' in body and 'limits.red' in body
