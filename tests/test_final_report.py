"""History ordering, over-quota flag and the quarterly final report (all platforms use the same rules)."""
import pytest

from services.final_report import (
    GOOD, TIGHT, EXCEEDED, build_final_report, is_over_quota, sort_history,
)


def month(name, year, remote, max_remote, soll=160.0, gesamt=None, quote=40.0, quartal=None):
    return {'monat': name, 'jahr': year, 'ist_remote_stunden_laufend': remote, 'max_remote_stunden': max_remote,
            'soll_stunden_gesamt': soll, 'ist_arbeitszeit_laufend': gesamt if gesamt is not None else soll,
            'individuelle_quote': quote, 'quartal': quartal}


class TestOverQuota:
    def test_over_when_remote_exceeds_max(self):
        assert is_over_quota(month('Juli', 2026, 130.25, 110.40))

    def test_not_over_when_below_or_equal(self):
        assert not is_over_quota(month('Mai', 2026, 80.43, 86.40))
        assert not is_over_quota(month('Mai', 2026, 86.40, 86.40))

    def test_rounding_noise_is_not_an_overrun(self):
        assert not is_over_quota(month('Mai', 2026, 86.4000000001, 86.40))

    def test_missing_values_are_not_over(self):
        assert not is_over_quota({})


class TestSortHistory:
    def test_screenshot_order_becomes_chronological(self):
        names = ['Juli', 'Mai', 'Juni', 'April', 'Oktober', 'September', 'August']
        hist = [month(n, 2026, 1, 1) for n in names]
        assert [m['monat'] for m in sort_history(hist)] == ['April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober']

    def test_newest_first(self):
        hist = [month('Dezember', 2025, 1, 1), month('Januar', 2026, 1, 1), month('März', 2025, 1, 1)]
        assert [(m['monat'], m['jahr']) for m in sort_history(hist, newest_first=True)] == \
            [('Januar', 2026), ('Dezember', 2025), ('März', 2025)]

    def test_input_is_not_modified(self):
        hist = [month('Mai', 2026, 1, 1), month('April', 2026, 1, 1)]
        sort_history(hist)
        assert hist[0]['monat'] == 'Mai'


class TestFinalReport:
    def screenshot_history(self):
        rows = [('Juli', 130.25, 110.40, 184.00), ('Mai', 80.43, 86.40, 144.00), ('Juni', 107.63, 100.80, 168.00),
                ('April', 101.62, 96.00, 160.00), ('Oktober', 90.47, 105.60, 176.00), ('September', 109.98, 105.60, 176.00),
                ('August', 94.60, 100.80, 168.00)]
        q = {'April': 'Q2/2026', 'Mai': 'Q2/2026', 'Juni': 'Q2/2026', 'Juli': 'Q3/2026', 'August': 'Q3/2026',
             'September': 'Q3/2026', 'Oktober': 'Q4/2026'}
        return [month(n, 2026, r, mx, soll=mx / 0.6, quote=60.0, quartal=q[n]) for n, r, mx, _ in rows]

    def test_empty_history(self):
        rep = build_final_report([])
        assert rep['quarters'] == [] and rep['overall']['months'] == 0 and rep['overall']['rating'] is None

    def test_quarters_are_ordered_and_months_inside_too(self):
        rep = build_final_report(self.screenshot_history())
        assert [q['quartal'] for q in rep['quarters']] == ['Q2/2026', 'Q3/2026', 'Q4/2026']
        assert [m['monat'] for m in rep['quarters'][0]['months']] == ['April', 'Mai', 'Juni']

    def test_quarter_sums_and_rating(self):
        q2, q3, q4 = build_final_report(self.screenshot_history())['quarters']
        assert q2['remote'] == pytest.approx(101.62 + 80.43 + 107.63)
        assert q2['max_remote'] == pytest.approx(96.0 + 86.4 + 100.8)
        assert q2['rating'] == EXCEEDED              # 289.68 > 283.2
        assert q2['months_over'] == 2 and q2['complete'] is True
        assert q3['rating'] == EXCEEDED and q3['months_over'] == 2
        assert q4['rating'] == GOOD and q4['complete'] is False and q4['month_count'] == 1

    def test_tight_between_90_and_100_percent_of_limit(self):
        hist = [month(n, 2026, 95, 100, quartal='Q1/2026') for n in ('Januar', 'Februar', 'März')]
        assert build_final_report(hist)['quarters'][0]['rating'] == TIGHT

    def test_good_at_or_below_90_percent(self):
        hist = [month(n, 2026, 90, 100, quartal='Q1/2026') for n in ('Januar', 'Februar', 'März')]
        assert build_final_report(hist)['quarters'][0]['rating'] == GOOD

    def test_single_month_over_but_quarter_within_limit(self):
        hist = [month('Januar', 2026, 120, 100, quartal='Q1/2026'), month('Februar', 2026, 50, 100, quartal='Q1/2026'),
                month('März', 2026, 50, 100, quartal='Q1/2026')]
        q = build_final_report(hist)['quarters'][0]
        assert q['months_over'] == 1 and q['rating'] == GOOD

    def test_quarter_label_is_derived_when_missing(self):
        rep = build_final_report([month('November', 2026, 1, 10)])
        assert rep['quarters'][0]['quartal'] == 'Q4/2026'

    def test_same_quarter_in_two_years_stays_separate_and_sorted(self):
        rep = build_final_report([month('Februar', 2026, 1, 10), month('Februar', 2025, 1, 10)])
        assert [q['quartal'] for q in rep['quarters']] == ['Q1/2025', 'Q1/2026']

    def test_duplicate_month_counted_once(self):
        rep = build_final_report([month('Mai', 2026, 10, 20), month('Mai', 2026, 10, 20)])
        assert rep['quarters'][0]['month_count'] == 1 and rep['quarters'][0]['remote'] == 10

    def test_overall(self):
        o = build_final_report(self.screenshot_history())['overall']
        assert o['months'] == 7 and o['months_over'] == 4 and o['quarters'] == 3 and o['quarters_exceeded'] == 2
        assert o['rating'] == EXCEEDED

    def test_zero_soll_does_not_divide_by_zero(self):
        q = build_final_report([month('Mai', 2026, 0, 0, soll=0.0)])['quarters'][0]
        assert q['actual_quote'] == 0 and q['rating'] == GOOD


class TestFinalReportApi:
    def test_endpoint_returns_report_for_stored_history(self, client):
        data = client.get('/api/report/final').get_json()
        assert data['success'] is True
        assert set(data['report']) == {'quarters', 'overall', 'flex'}
        hist = client.get('/api/state').get_json()['monatliche_historie']
        assert data['report']['overall']['months'] == len({(m['monat'], m['jahr']) for m in hist})

    def test_endpoint_language_independent_codes(self, client):
        rep = client.get('/api/report/final').get_json()['report']
        for q in rep['quarters']:
            assert q['rating'] in (GOOD, TIGHT, EXCEEDED)


class TestIndexPage:
    def test_final_report_button_modal_and_red_style_are_in_the_page(self, client):
        html = client.get('/').get_data(as_text=True)
        assert 'handleFinalReport()' in html and 'id="final-report-modal"' in html
        # the styles moved from the inline <style> (Tailwind CDN) to the local static/css/app.css; the
        # over-limit marker now uses theme variables, so the dark theme needs no extra .over-quota rule
        assert '/static/css/app.css' in html and 'cdn.tailwindcss.com' not in html
        css = client.get('/static/css/app.css').get_data(as_text=True)
        assert '.over-quota' in css and '.dark-mode' in css

    def test_script_sorts_history_and_marks_over_quota(self, client):
        js = client.get('/static/js/app.js').get_data(as_text=True)
        assert 'sortedHistory(history)' in js and 'isOverQuota(m)' in js and '/api/report/final' in js
        assert 'history.slice().reverse()' not in js


class TestViewAnyMonth:
    """B4: the viewed month could only be changed by loading a statement or closing a month."""

    def post(self, client, **payload):
        return client.post('/api/view/month', json=payload)

    def test_switches_view_and_recalculates_that_month(self, client):
        before = client.get('/api/state').get_json()['current_month_data']['ist_arbeitszeit_laufend']
        assert before > 0                                        # the sample data has entries in March 2026
        data = self.post(client, month='Februar', year=2025).get_json()
        assert data['success'] and data['state']['view_month'] == 'Februar' and data['state']['view_year'] == 2025
        assert data['state']['current_month_data']['ist_arbeitszeit_laufend'] == 0
        assert data['state']['current_month_data']['soll_stunden_gesamt'] == 20 * 8     # February 2025: 20 working days
        back = self.post(client, month='März', year=2026).get_json()['state']['current_month_data']
        assert back['ist_arbeitszeit_laufend'] == before

    def test_view_is_persisted(self, client):
        self.post(client, month='Mai', year=2025)
        st = client.get('/api/state').get_json()
        assert (st['view_month'], st['view_year']) == ('Mai', 2025)

    @pytest.mark.parametrize('payload', [{}, {'month': 'Mai'}, {'year': 2025}, {'month': 'Smarch', 'year': 2025},
                                         {'month': 'Mai', 'year': 'x'}, {'month': 'Mai', 'year': 1800},
                                         {'month': 'Mai', 'year': 3000}, {'month': 5, 'year': 2025}])
    def test_rejects_invalid_input(self, client, payload):
        resp = self.post(client, **payload)
        assert resp.status_code == 400 and resp.get_json()['success'] is False


class TestStartEqualsEnd:
    """Kotlin rejected an entry whose start equals its end; Flask stored it as a zero-hour entry."""

    def test_add_rejects_it(self, client):
        r = client.post('/api/protokoll', json={'datum': '2026-03-10', 'start': '08:00', 'end': '08:00', 'pause': 0})
        assert r.status_code == 400 and r.get_json()['success'] is False

    def test_update_rejects_it(self, client):
        client.post('/api/protokoll', json={'datum': '2026-03-10', 'start': '14:00', 'end': '15:00', 'pause': 0})
        state = client.get('/api/state').get_json()
        rec = next(r for r in state['daily_records']['2026-03-10'] if r['startTime'] == '14:00')
        r = client.put(f"/api/update/{rec['id']}", json={'datum': '2026-03-10', 'start': '14:00', 'end': '14:00', 'pause': 0})
        assert r.status_code == 400


class TestNoPauseWarningForImportedEntries:
    """A statement lists work sessions without breaks, so the import stores pause 0 and every
    long session would carry an ArbZG warning. Imported entries get no warning."""

    SESSION = {'date': '2026-03-09', 'start_time': '08:00', 'end_time': '16:30', 'is_remote': True}

    def records(self, client):
        return client.get('/api/state').get_json()['daily_records']['2026-03-09']

    def test_import_stores_no_warning(self, client):
        client.post('/api/pdf/import', json={'sessions': [self.SESSION]})
        rec = self.records(client)[0]
        assert rec['source'] == 'pdf_import'
        assert not rec.get('pauseWarning') and not rec.get('pauseWarningDe') and not rec.get('pauseWarningEn')

    def test_manual_entry_still_warns(self, client):
        client.post('/api/protokoll', json={'datum': '2026-03-09', 'start': '08:00', 'end': '16:30', 'pause': 0})
        assert 'ArbZG' in self.records(client)[0]['pauseWarning']

    def test_csv_export_has_no_warning_for_imported_entries(self, client):
        client.post('/api/pdf/import', json={'sessions': [self.SESSION]})
        client.post('/api/view/month', json={'month': 'März', 'year': 2026})
        csv_text = client.get('/api/export/daily_csv').get_data(as_text=True)
        assert '2026-03-09' in csv_text and 'ArbZG' not in csv_text

    def test_page_hides_the_warning_of_imported_entries_stored_earlier(self, client):
        js = client.get('/static/js/app.js').get_data(as_text=True)
        assert "r.source !== 'pdf_import'" in js
