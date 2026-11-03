"""Special days 24 Dec / 31 Dec in the target hours and the flextime balance of a statement (fictional values)."""
import copy
import json

from services.calculation import berechne_soll_stunden_monat
from services.pdf_service import parse_flex_balance


class TestSpecialDays:
    def test_december_2025_has_two_days_less_and_half_a_day(self):
        # 23 weekdays - 25./26.12. (holidays) - 24.12. (off) - 0.5 (31.12.) = 19.5 days
        assert berechne_soll_stunden_monat(2025, 12, 8.0) == 19.5 * 8.0

    def test_other_months_are_unchanged(self):
        assert berechne_soll_stunden_monat(2026, 3, 8.0) == 22 * 8.0

    def test_24_dec_2026_is_zero_but_31_dec_2026_is_half(self):
        # December 2026: 23 weekdays, 25. is a Friday holiday, 26. a Saturday; 24. (Thu) off, 31. (Thu) half
        assert berechne_soll_stunden_monat(2026, 12, 8.0) == (23 - 1 - 1 - 0.5) * 8.0


class TestFlexBalanceParser:
    def test_german_summary(self):
        text = ("GLZ-Saldo Vorperiode 12,50 Mehrarbeit Kompensation 0,00\n"
                "GLZ-Saldo akt. Periode 3,25- Mehrarbeit Vergütung 0,00\n"
                "GLZ-Saldo Gesamt 9,25 Mehrarbeit Grundl./Freiz. 0,00\n")
        assert parse_flex_balance(text) == {'previous': 12.5, 'current': -3.25, 'total': 9.25}

    def test_english_summary(self):
        text = ("Flex. Bal. Prev. Period 10,00 Overtime Compensated 0,00\n"
                "Flextime Bal. Curr. Period 2,50 Overtime Remunerated 0,00\n"
                "Flextime Balance Total 12,50 Overtime Basic Pay/Time Off 0,00\n"
                "Credit Days 0,00 Flex. Bal. Prev. Period 7,77\n")
        assert parse_flex_balance(text) == {'previous': 10.0, 'current': 2.5, 'total': 12.5}

    def test_minus_glued_to_the_next_column(self):
        assert parse_flex_balance("GLZ-Saldo akt. Periode 4,00-Mehrarbeit Vergütung 0,00\n") == {'current': -4.0}

    def test_thousands_separator(self):
        assert parse_flex_balance("GLZ-Saldo Gesamt 1.234,50\n") == {'total': 1234.5}

    def test_no_summary_gives_none(self):
        assert parse_flex_balance("01 MO Zeitbuchungen : anwesend 08:00 16:30\n") is None


class TestFlexBalanceImport:
    def _post(self, client, payload):
        return client.post('/api/pdf/import', data=json.dumps(payload), content_type='application/json')

    def test_balance_is_stored_and_cleaned(self, client):
        resp = self._post(client, {'sessions': [], 'flex_balance': {
            'previous': 1.5, 'current': -2.0, 'total': -0.5, 'year': 2025, 'month': 12,
            'evil': '<script>', 'extra': 5}})
        assert resp.status_code == 200
        saldo = resp.get_json()['state']['gleitzeit_saldo']
        assert saldo == {'previous': 1.5, 'current': -2.0, 'total': -0.5, 'year': 2025, 'month': 12}

    def test_invalid_balance_is_ignored(self, client):
        resp = self._post(client, {'sessions': [], 'flex_balance': {'current': 'abc', 'total': True, 'previous': 99999}})
        assert resp.status_code == 200
        assert 'gleitzeit_saldo' not in resp.get_json()['state']

    def test_no_balance_keeps_the_old_one(self, client):
        self._post(client, {'sessions': [], 'flex_balance': {'total': 3.0}})
        resp = self._post(client, {'sessions': []})
        assert resp.get_json()['state']['gleitzeit_saldo'] == {'total': 3.0}


class TestStaleTargetIsRecalculated:
    """A state file saved before the special days still holds the old target; loading must correct it."""

    def _write_stale(self, state):
        from routes import api as api_module
        with open(api_module.state_service.data_file, 'w', encoding='utf-8') as f:
            json.dump(state, f)

    def test_get_state_recalculates_december_target(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        st.update({'aktueller_monat': 'Dezember', 'aktuelles_jahr': 2025, 'view_month': 'Dezember',
                   'view_year': 2025, 'soll_stunden_pro_tag': 8.0, 'individuelle_quote_prozent': 40.0})
        st['current_month_data'] = {'monat': 'Dezember', 'jahr': 2025, 'soll_stunden_gesamt': 168.0,
                                    'max_remote_stunden': 67.2, 'ist_remote_stunden_laufend': 0.0,
                                    'ist_arbeitszeit_laufend': 0.0, 'individuelle_quote': 40.0}
        self._write_stale(st)
        data = client.get('/api/state').get_json()
        assert data['current_month_data']['soll_stunden_gesamt'] == 156.0
        assert data['current_month_data']['max_remote_stunden'] == 156.0 * 0.4

    def test_closed_months_in_the_history_keep_their_snapshot(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        closed = {'monat': 'Dezember', 'jahr': 2024, 'soll_stunden_gesamt': 168.0, 'max_remote_stunden': 67.2,
                  'ist_remote_stunden_laufend': 10.0, 'ist_arbeitszeit_laufend': 80.0,
                  'individuelle_quote': 40.0, 'tatsaechliche_remote_quote': 5.9, 'quartal': 'Q4/2024'}
        st['monatliche_historie'] = [closed]
        self._write_stale(st)
        data = client.get('/api/state').get_json()
        assert data['monatliche_historie'][0]['soll_stunden_gesamt'] == 168.0
