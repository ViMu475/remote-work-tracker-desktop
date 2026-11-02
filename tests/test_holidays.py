"""Bavarian public holidays: complete for 2025-2030 and effective in the rules.

The expected dates are derived here from fixed Easter Sundays (looked up, not
computed with the code under test) so the check is independent of the
implementation.
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from services.calculation import berechne_soll_stunden_monat, is_working_day_valid

EASTER = {
    2025: datetime.date(2025, 4, 20), 2026: datetime.date(2026, 4, 5),
    2027: datetime.date(2027, 3, 28), 2028: datetime.date(2028, 4, 16),
    2029: datetime.date(2029, 4, 1), 2030: datetime.date(2030, 4, 21),
}
YEARS = sorted(EASTER)
D = datetime.timedelta


def expected_holidays(year):
    easter = EASTER[year]
    return {
        datetime.date(year, 1, 1), datetime.date(year, 1, 6),      # Neujahr, Heilige Drei Könige
        easter - D(days=2), easter + D(days=1),                    # Karfreitag, Ostermontag
        datetime.date(year, 5, 1),                                 # Tag der Arbeit
        easter + D(days=39), easter + D(days=50), easter + D(days=60),  # Himmelfahrt, Pfingstmontag, Fronleichnam
        datetime.date(year, 8, 15), datetime.date(year, 10, 3),    # Mariä Himmelfahrt, Tag der Deutschen Einheit
        datetime.date(year, 11, 1),                                # Allerheiligen
        datetime.date(year, 12, 25), datetime.date(year, 12, 26),  # Weihnachten
    }


def configured(year):
    return {datetime.date.fromisoformat(s) for s in Config.BAYERN_FEIERTAGE if s.startswith(f'{year}-')}


class TestHolidayList:
    @pytest.mark.parametrize('year', YEARS)
    def test_every_bavarian_holiday_is_listed(self, year):
        missing = sorted(expected_holidays(year) - configured(year))
        assert missing == [], f'{year}: missing {[d.isoformat() for d in missing]}'

    @pytest.mark.parametrize('year', YEARS)
    def test_no_extra_days_are_listed(self, year):
        extra = sorted(configured(year) - expected_holidays(year))
        assert extra == [], f'{year}: unexpected {[d.isoformat() for d in extra]}'

    def test_list_is_sorted_unique_and_iso_formatted(self):
        values = Config.BAYERN_FEIERTAGE
        assert values == sorted(set(values))
        for v in values:
            datetime.date.fromisoformat(v)
            assert len(v) == 10

    def test_original_2025_entries_are_unchanged(self):
        original = {'2025-01-01', '2025-01-06', '2025-04-18', '2025-04-21', '2025-05-01', '2025-05-29',
                    '2025-06-09', '2025-06-19', '2025-08-15', '2025-10-03', '2025-12-25', '2025-12-26'}
        assert original <= set(Config.BAYERN_FEIERTAGE)

    def test_covers_the_next_four_full_years(self):
        years = {int(v[:4]) for v in Config.BAYERN_FEIERTAGE}
        assert {2026, 2027, 2028, 2029, 2030} <= years


class TestHolidaysAreEnforced:
    def _state(self, year):
        return {'aktuelles_jahr': year, 'aktueller_monat': 'Dezember', 'current_quartal': f'Q4/{year}'}

    @pytest.mark.parametrize('datum', [
        '2026-04-03', '2026-04-06', '2026-05-14', '2026-05-25', '2026-06-04', '2026-12-25',
        '2027-03-26', '2027-05-27', '2027-11-01', '2028-06-15', '2029-05-31', '2030-06-20',
    ])
    def test_entries_on_holidays_are_rejected(self, datum):
        msg = is_working_day_valid(datum, self._state(int(datum[:4])))
        assert msg is not None and 'Feiertag' in msg

    def test_a_normal_workday_next_to_a_holiday_is_allowed(self):
        assert is_working_day_valid('2027-05-28', self._state(2027)) is None

    @pytest.mark.parametrize('jahr,monat,soll', [
        (2026, 4, 160.0),   # 22 Werktage - Karfreitag - Ostermontag
        (2026, 5, 144.0),   # 21 Werktage - 1. Mai - Himmelfahrt - Pfingstmontag
        (2026, 12, 176.0),  # 23 Werktage - 25.12.
        (2027, 5, 144.0),   # 21 Werktage - Himmelfahrt - Pfingstmontag - Fronleichnam (1. Mai ist Samstag)
    ])
    def test_monthly_target_hours_exclude_holidays(self, jahr, monat, soll):
        assert berechne_soll_stunden_monat(jahr, monat, 8.0) == soll
