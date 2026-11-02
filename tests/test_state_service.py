"""Tests for StateService."""
import json
import os
import pytest

from services.state_service import StateService
from services.calculation import berechne_soll_stunden_monat
from config import Config


class TestLoadStateExistingFile:
    """Test load_state with an existing file."""

    def test_loads_state_with_daily_records(self, state_service):
        state = state_service.load_state()
        assert 'daily_records' in state
        assert isinstance(state['daily_records'], dict)
        assert len(state['daily_records']) == 2

    def test_loads_correct_entries(self, state_service):
        state = state_service.load_state()
        dr = state['daily_records']
        assert '2026-03-02' in dr
        assert '2026-03-03' in dr
        # Each date has a list of records
        assert isinstance(dr['2026-03-02'], list)
        assert len(dr['2026-03-02']) == 1
        assert dr['2026-03-02'][0]['remoteStundenHeute'] == 8.0

    def test_sets_system_month(self, state_service):
        state = state_service.load_state()
        # load_state overwrites aktueller_monat with system month (March 2026)
        assert state['aktueller_monat'] == 'März'
        assert state['aktuelles_jahr'] == 2026


class TestLoadStateMissingFile:
    """Test load_state when the file does not exist."""

    def test_returns_initial_state(self, empty_state_service):
        state = empty_state_service.load_state()
        assert state['daily_records'] == {}
        assert state['monatliche_historie'] == []
        assert state['individuelle_quote_prozent'] == Config.BASIS_QUOTE_PROZENT
        assert state['soll_stunden_pro_tag'] == Config.SOLL_STUNDEN_PRO_TAG

    def test_initial_state_has_system_date(self, empty_state_service):
        state = empty_state_service.load_state()
        assert state['aktueller_monat'] == 'März'
        assert state['aktuelles_jahr'] == 2026


class TestMigrationDictToList:
    """Test migration from old dict format to list format."""

    def test_dict_entry_converted_to_list(self, tmp_path):
        old_state = {
            'individuelle_quote_prozent': 40.0,
            'soll_stunden_pro_tag': 8.0,
            'aktuelles_jahr': 2026,
            'aktueller_monat': 'März',
            'current_quartal': 'Q1/2026',
            'view_month': 'März',
            'view_year': 2026,
            'monatliche_historie': [],
            'current_month_data': {
                'monat': 'März',
                'jahr': 2026,
                'soll_stunden_gesamt': 0.0,
                'ist_remote_stunden_laufend': 0.0,
                'ist_arbeitszeit_laufend': 0.0,
                'max_remote_stunden': 0.0,
                'individuelle_quote': 40.0
            },
            'daily_records': {
                '2026-03-05': {
                    'datum': '2026-03-05',
                    'startTime': '08:00',
                    'endTime': '16:30',
                    'pauseMinutes': 30,
                    'remoteStundenHeute': 8.0,
                    'totalStundenHeute': 8.0
                }
            }
        }
        state_file = str(tmp_path / 'migrate.json')
        with open(state_file, 'w') as f:
            json.dump(old_state, f)

        svc = StateService(data_file=state_file)
        state = svc.load_state()

        # Dict entry should now be a list
        val = state['daily_records']['2026-03-05']
        assert isinstance(val, list)
        assert len(val) == 1
        assert val[0]['datum'] == '2026-03-05'


class TestAutoAssignIds:
    """Test that entries without IDs get auto-assigned IDs."""

    def test_list_entry_without_id_gets_id(self, tmp_path):
        old_state = {
            'individuelle_quote_prozent': 40.0,
            'soll_stunden_pro_tag': 8.0,
            'aktuelles_jahr': 2026,
            'aktueller_monat': 'März',
            'current_quartal': 'Q1/2026',
            'view_month': 'März',
            'view_year': 2026,
            'monatliche_historie': [],
            'current_month_data': {
                'monat': 'März',
                'jahr': 2026,
                'soll_stunden_gesamt': 0.0,
                'ist_remote_stunden_laufend': 0.0,
                'ist_arbeitszeit_laufend': 0.0,
                'max_remote_stunden': 0.0,
                'individuelle_quote': 40.0
            },
            'daily_records': {
                '2026-03-10': [
                    {
                        'datum': '2026-03-10',
                        'startTime': '09:00',
                        'endTime': '17:00',
                        'pauseMinutes': 30,
                        'remoteStundenHeute': 7.5,
                        'totalStundenHeute': 7.5
                    }
                ]
            }
        }
        state_file = str(tmp_path / 'noid.json')
        with open(state_file, 'w') as f:
            json.dump(old_state, f)

        svc = StateService(data_file=state_file)
        state = svc.load_state()

        entry = state['daily_records']['2026-03-10'][0]
        assert 'id' in entry
        assert len(entry['id']) > 0

    def test_dict_entry_without_id_gets_id(self, tmp_path):
        old_state = {
            'individuelle_quote_prozent': 40.0,
            'soll_stunden_pro_tag': 8.0,
            'aktuelles_jahr': 2026,
            'aktueller_monat': 'März',
            'current_quartal': 'Q1/2026',
            'view_month': 'März',
            'view_year': 2026,
            'monatliche_historie': [],
            'current_month_data': {
                'monat': 'März',
                'jahr': 2026,
                'soll_stunden_gesamt': 0.0,
                'ist_remote_stunden_laufend': 0.0,
                'ist_arbeitszeit_laufend': 0.0,
                'max_remote_stunden': 0.0,
                'individuelle_quote': 40.0
            },
            'daily_records': {
                '2026-03-11': {
                    'datum': '2026-03-11',
                    'startTime': '08:00',
                    'endTime': '16:00',
                    'pauseMinutes': 30,
                    'remoteStundenHeute': 7.5,
                    'totalStundenHeute': 7.5
                }
            }
        }
        state_file = str(tmp_path / 'noid_dict.json')
        with open(state_file, 'w') as f:
            json.dump(old_state, f)

        svc = StateService(data_file=state_file)
        state = svc.load_state()

        entry = state['daily_records']['2026-03-11'][0]
        assert 'id' in entry
        assert len(entry['id']) > 0


class TestSaveAndReload:
    """Test save_state and reload."""

    def test_save_and_reload_roundtrip(self, tmp_path):
        state_file = str(tmp_path / 'roundtrip.json')
        svc = StateService(data_file=state_file)

        state = svc.get_initial_state()
        state['daily_records'] = {
            '2026-03-15': [
                {
                    'id': 'test-id-1',
                    'datum': '2026-03-15',
                    'startTime': '08:00',
                    'endTime': '16:30',
                    'pauseMinutes': 30,
                    'remoteStundenHeute': 8.0,
                    'totalStundenHeute': 8.0
                }
            ]
        }

        result = svc.save_state(state)
        assert result is True

        loaded = svc.load_state()
        assert '2026-03-15' in loaded['daily_records']
        assert loaded['daily_records']['2026-03-15'][0]['id'] == 'test-id-1'
        assert loaded['daily_records']['2026-03-15'][0]['remoteStundenHeute'] == 8.0


class TestRecalcMonthlyTotals:
    """Test recalc_monthly_totals."""

    def test_sums_match_expected(self, state_service):
        state = state_service.load_state()
        # The test data has 2026-03-02 (8h remote, 8h total) and 2026-03-03 (0h remote, 8h total)
        # view_month=März, view_year=2026
        state_service.recalc_monthly_totals(state)

        cmd = state['current_month_data']
        assert cmd['ist_remote_stunden_laufend'] == 8.0
        assert cmd['ist_arbeitszeit_laufend'] == 16.0

        # soll for March 2026
        expected_soll = berechne_soll_stunden_monat(2026, 3, 8.0)
        assert cmd['soll_stunden_gesamt'] == expected_soll
        assert cmd['max_remote_stunden'] == expected_soll * 0.4

    def test_recalc_with_empty_records(self, tmp_path):
        state_file = str(tmp_path / 'empty_rec.json')
        svc = StateService(data_file=state_file)
        state = svc.get_initial_state()
        state['view_month'] = 'März'
        state['view_year'] = 2026

        svc.recalc_monthly_totals(state)

        cmd = state['current_month_data']
        assert cmd['ist_remote_stunden_laufend'] == 0.0
        assert cmd['ist_arbeitszeit_laufend'] == 0.0


class TestCalculateQuartalTotals:
    """Test calculate_quartal_totals."""

    def test_quartal_aggregation(self, state_service):
        state = state_service.load_state()
        result = state_service.calculate_quartal_totals(state)

        assert 'quartal_remote' in result
        assert 'quartal_gesamt' in result
        assert 'quartal_soll' in result
        assert 'quartal_quote' in result

        # Q1/2026 includes Jan, Feb, Mar. Test data only has March entries.
        assert result['quartal_remote'] == 8.0
        assert result['quartal_gesamt'] == 16.0
        assert result['quartal_soll'] > 0
        assert result['quartal_quote'] == pytest.approx(
            8.0 / result['quartal_soll'] * 100, rel=1e-2
        )


class TestInitialisiereMonat:
    """Test initialisiere_monat."""

    def test_should_save_true_clears_records(self, state_service):
        state = state_service.load_state()
        assert len(state['daily_records']) > 0

        state_service.initialisiere_monat(state, 'April', should_save=True)

        assert state['daily_records'] == {}
        assert state['aktueller_monat'] == 'April'
        cmd = state['current_month_data']
        assert cmd['monat'] == 'April'
        assert cmd['ist_remote_stunden_laufend'] == 0.0
        assert cmd['ist_arbeitszeit_laufend'] == 0.0

        expected_soll = berechne_soll_stunden_monat(2026, 4, 8.0)
        assert cmd['soll_stunden_gesamt'] == expected_soll
        assert cmd['max_remote_stunden'] == expected_soll * 0.4

    def test_should_save_false_recalculates(self, state_service):
        state = state_service.load_state()
        state_service.initialisiere_monat(state, 'März', should_save=False)

        assert state['aktueller_monat'] == 'März'
        # Records should NOT be cleared
        assert len(state['daily_records']) == 2

        cmd = state['current_month_data']
        expected_soll = berechne_soll_stunden_monat(2026, 3, 8.0)
        assert cmd['soll_stunden_gesamt'] == expected_soll
        assert cmd['max_remote_stunden'] == expected_soll * 0.4
        assert cmd['individuelle_quote'] == 40.0
