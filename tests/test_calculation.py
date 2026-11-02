"""Tests for services/calculation.py"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.calculation import (
    calculate_net_hours,
    check_time_overlap,
    is_working_day_valid,
    berechne_soll_stunden_monat,
    get_quartal_for_month,
)


# ---------------------------------------------------------------------------
# calculate_net_hours
# ---------------------------------------------------------------------------

class TestCalculateNetHours:
    def test_normal_8h_day_with_30min_pause(self):
        result = calculate_net_hours("08:00", "16:30", 30)
        assert result['gross'] == 8.5
        assert result['net'] == 8.0
        assert result['pause_warning'] is None

    def test_no_pause_under_6h(self):
        """Under 6 hours gross, no statutory pause required."""
        result = calculate_net_hours("08:00", "13:00", 0)
        assert result['gross'] == 5.0
        assert result['net'] == 5.0
        assert result['pause_warning'] is None

    def test_pause_warning_at_6h_no_pause(self):
        """6h gross with 0 pause triggers 30min warning."""
        result = calculate_net_hours("08:00", "14:00", 0)
        assert result['gross'] == 6.0
        assert result['pause_warning'] is not None
        assert "0.50" in result['pause_warning']

    def test_pause_warning_at_6h_insufficient_pause(self):
        result = calculate_net_hours("08:00", "14:00", 15)
        assert result['pause_warning'] is not None

    def test_no_warning_at_6h_sufficient_pause(self):
        result = calculate_net_hours("08:00", "14:30", 30)
        assert result['gross'] == 6.5
        assert result['pause_warning'] is None

    def test_pause_warning_at_9h_no_pause(self):
        """9h gross with 0 pause triggers 45min warning."""
        result = calculate_net_hours("08:00", "17:00", 0)
        assert result['gross'] == 9.0
        assert result['pause_warning'] is not None
        assert "0.75" in result['pause_warning']

    def test_no_warning_at_9h_sufficient_pause(self):
        result = calculate_net_hours("08:00", "17:45", 45)
        assert result['gross'] == 9.75
        assert result['net'] == 9.0
        assert result['pause_warning'] is None

    def test_overnight_shift(self):
        """End time before start means overnight."""
        result = calculate_net_hours("22:00", "06:00", 30)
        assert result['gross'] == 8.0
        assert result['net'] == 7.5

    def test_short_shift_no_pause_needed(self):
        result = calculate_net_hours("09:00", "11:00", 0)
        assert result['gross'] == 2.0
        assert result['net'] == 2.0
        assert result['pause_warning'] is None

    def test_returns_all_keys(self):
        result = calculate_net_hours("08:00", "16:00", 0)
        assert 'gross' in result
        assert 'net' in result
        assert 'pause_warning_de' in result
        assert 'pause_warning_en' in result
        assert 'pause_warning' in result


# ---------------------------------------------------------------------------
# check_time_overlap
# ---------------------------------------------------------------------------

class TestCheckTimeOverlap:
    def _make_state(self, entries=None):
        state = {
            'language': 'de',
            'daily_records': {},
        }
        if entries:
            state['daily_records']['2026-03-02'] = entries
        return state

    def test_no_overlap_different_times(self):
        entries = [{
            'id': '1', 'startTime': '08:00', 'endTime': '12:00',
        }]
        state = self._make_state(entries)
        result = check_time_overlap('2026-03-02', '13:00', '17:00', state)
        assert result is None

    def test_overlap_detected(self):
        entries = [{
            'id': '1', 'startTime': '08:00', 'endTime': '12:00',
        }]
        state = self._make_state(entries)
        result = check_time_overlap('2026-03-02', '10:00', '14:00', state)
        assert result is not None
        assert 'Zeitüberlappung' in result or 'overlap' in result.lower()

    def test_empty_day_no_overlap(self):
        state = self._make_state()
        result = check_time_overlap('2026-03-05', '08:00', '16:00', state)
        assert result is None

    def test_exclude_id_for_edits(self):
        entries = [{
            'id': 'edit-me', 'startTime': '08:00', 'endTime': '12:00',
        }]
        state = self._make_state(entries)
        # Same time range but excluded by id -> no overlap
        result = check_time_overlap('2026-03-02', '08:00', '12:00', state, exclude_id='edit-me')
        assert result is None

    def test_overlap_not_excluded_for_different_id(self):
        entries = [{
            'id': 'other', 'startTime': '08:00', 'endTime': '12:00',
        }]
        state = self._make_state(entries)
        result = check_time_overlap('2026-03-02', '08:00', '12:00', state, exclude_id='edit-me')
        assert result is not None

    def test_adjacent_times_no_overlap(self):
        """End of one = start of next should not overlap (boundary)."""
        entries = [{
            'id': '1', 'startTime': '08:00', 'endTime': '12:00',
        }]
        state = self._make_state(entries)
        result = check_time_overlap('2026-03-02', '12:00', '16:00', state)
        # The implementation checks existing_start < new_end <= existing_end
        # 12:00 start with existing 08:00-12:00: existing_start(480) <= new_start(720) is False
        # So no overlap for adjacent blocks
        assert result is None


# ---------------------------------------------------------------------------
# is_working_day_valid
# ---------------------------------------------------------------------------

class TestIsWorkingDayValid:
    def _make_state(self, monat='März', jahr=2026, quartal='Q1/2026'):
        return {
            'aktueller_monat': monat,
            'aktuelles_jahr': jahr,
            'current_quartal': quartal,
            'language': 'de',
        }

    def test_valid_weekday(self):
        # 2026-03-02 is a Monday
        state = self._make_state()
        result = is_working_day_valid('2026-03-02', state)
        assert result is None

    def test_sunday_rejected(self):
        # 2026-03-01 is a Sunday
        state = self._make_state()
        result = is_working_day_valid('2026-03-01', state)
        assert result is not None
        assert 'Sonntag' in result or 'Sunday' in result.lower()

    def test_saturday_rejected(self):
        # 2026-03-07 is a Saturday
        state = self._make_state()
        result = is_working_day_valid('2026-03-07', state)
        assert result is not None
        assert 'Samstag' in result or 'Saturday' in result.lower()

    def test_holiday_rejected(self):
        # 2026-01-01 is Neujahr (in BAYERN_FEIERTAGE)
        state = self._make_state(monat='Januar', quartal='Q1/2026')
        result = is_working_day_valid('2026-01-01', state)
        assert result is not None
        assert 'Feiertag' in result

    def test_holiday_epiphany_rejected(self):
        # 2026-01-06 is Heilige Drei Könige
        state = self._make_state(monat='Januar', quartal='Q1/2026')
        result = is_working_day_valid('2026-01-06', state)
        assert result is not None
        assert 'Feiertag' in result

    def test_earlier_year_is_allowed(self):
        # B6: manual entries for months of earlier years used to be rejected, only the PDF import could add them
        state = self._make_state()
        assert is_working_day_valid('2025-03-03', state) is None

    def test_earlier_year_still_rejects_weekends_and_holidays(self):
        state = self._make_state()
        assert 'Feiertag' in is_working_day_valid('2025-12-25', state)
        assert 'Sonntag' in is_working_day_valid('2025-03-02', state)

    def test_future_year_rejected(self):
        state = self._make_state()
        result = is_working_day_valid('2027-03-01', state)
        assert result is not None and 'zukünftig' in result

    def test_future_month_of_earlier_year_is_fine_but_later_month_of_this_year_is_not(self):
        state = self._make_state(monat='März')
        assert is_working_day_valid('2025-11-03', state) is None          # November 2025 is in the past
        assert is_working_day_valid('2026-04-01', state) is not None      # April 2026 is in the future

    def test_future_month_rejected(self):
        # State says current month is Januar, but date is in März
        state = self._make_state(monat='Januar', quartal='Q1/2026')
        result = is_working_day_valid('2026-03-02', state)
        assert result is not None

    def test_historical_allowed(self):
        # With allow_historical=True, past dates in different months are fine
        state = self._make_state()
        result = is_working_day_valid('2026-01-05', state, allow_historical=True)
        # 2026-01-05 is a Monday, not a holiday -> should be valid
        assert result is None

    def test_invalid_date_format(self):
        state = self._make_state()
        result = is_working_day_valid('not-a-date', state)
        assert result is not None
        assert 'Ungültig' in result


# ---------------------------------------------------------------------------
# berechne_soll_stunden_monat
# ---------------------------------------------------------------------------

class TestBerechneSollStundenMonat:
    def test_march_2026(self):
        """March 2026 has 22 working days (no Bayern holidays)."""
        result = berechne_soll_stunden_monat(2026, 3, 8.0)
        assert result == 22 * 8.0  # 176.0

    def test_january_2026_with_holidays(self):
        """January 2026: 2 holidays (Jan 1 Thu, Jan 6 Tue) reduce working days."""
        # Jan 2026: 31 days, starts Thursday
        # Weekdays (Mon-Fri): need to count manually
        # Jan 1 (Thu) = holiday, Jan 6 (Tue) = holiday
        # Working days = total weekdays - 2 holidays
        # Weekdays in Jan 2026: 22 (31 days, starts Thu)
        # Minus 2 holidays = 20
        result = berechne_soll_stunden_monat(2026, 1, 8.0)
        assert result == 20 * 8.0  # 160.0

    def test_custom_hours_per_day(self):
        result = berechne_soll_stunden_monat(2026, 3, 6.0)
        assert result == 22 * 6.0  # 132.0

    def test_february_2026(self):
        """February 2026: 28 days, no Bayern holidays, 20 working days."""
        result = berechne_soll_stunden_monat(2026, 2, 8.0)
        assert result == 20 * 8.0  # 160.0


# ---------------------------------------------------------------------------
# get_quartal_for_month
# ---------------------------------------------------------------------------

class TestGetQuartalForMonth:
    def test_q1(self):
        assert get_quartal_for_month("Januar", 2026) == "Q1/2026"
        assert get_quartal_for_month("Februar", 2026) == "Q1/2026"
        assert get_quartal_for_month("März", 2026) == "Q1/2026"

    def test_q2(self):
        assert get_quartal_for_month("April", 2026) == "Q2/2026"
        assert get_quartal_for_month("Mai", 2026) == "Q2/2026"
        assert get_quartal_for_month("Juni", 2026) == "Q2/2026"

    def test_q3(self):
        assert get_quartal_for_month("Juli", 2026) == "Q3/2026"
        assert get_quartal_for_month("August", 2026) == "Q3/2026"
        assert get_quartal_for_month("September", 2026) == "Q3/2026"

    def test_q4(self):
        assert get_quartal_for_month("Oktober", 2026) == "Q4/2026"
        assert get_quartal_for_month("November", 2026) == "Q4/2026"
        assert get_quartal_for_month("Dezember", 2026) == "Q4/2026"

    def test_fallback_unknown_year(self):
        """Year not in QUARTALS_PLANUNG falls back to dynamic calculation."""
        result = get_quartal_for_month("April", 2030)
        assert result == "Q2/2030"
