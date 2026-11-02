"""Soak tests: model-based random runs over many months (see soak_lib.py).

Quick variant runs in the normal suite. Heavy variant: RW_SOAK_STEPS=3000 RW_SOAK_SEEDS=20 pytest tests/test_soak.py -s
"""
import datetime
import os
import time

import pytest

from tests.soak_lib import Driver, Fail, FIRST_DAY, from_index, month_index

STEPS = int(os.environ.get('RW_SOAK_STEPS', '150'))
SEEDS = int(os.environ.get('RW_SOAK_SEEDS', '4'))


@pytest.fixture
def fresh(client, app):
    path = app.config['DATA_FILE']
    if os.path.exists(path):
        os.remove(path)
    return client, path


@pytest.mark.parametrize('seed', range(SEEDS))
def test_random_run(fresh, seed):
    client, path = fresh
    d = Driver(client, path, seed=seed, label='random')
    t0 = time.time()
    d.run(STEPS)
    print(f'\nseed={seed}: {d.steps} Schritte, {d.checks} Prüfungen, {time.time() - t0:.1f}s, Beobachtungen={dict(d.model.obs)}')


def test_forward_then_backward_through_all_months(fresh):
    """Close month after month 2025-01..2030-12 (history grows, quarters, year changes),
    then load every month backwards and view it again."""
    client, path = fresh
    d = Driver(client, path, seed=1, label='vorwärts-rückwärts')
    idx = month_index(2025, 1)
    for i in range(72):
        y, mo = from_index(idx + i)
        d.model.now = datetime.datetime(y, mo, 20, 9, 0)
        d.check(d.get_state())
        d.import_statement(y, mo, label='vorwärts ')
        d.month_switch()
    assert len(d.model.history) == 72
    # backwards: import each month again and look at it (clock now at end of 2030)
    d.model.now = datetime.datetime(2030, 12, 30, 9, 0)
    for i in reversed(range(72)):
        y, mo = from_index(idx + i)
        d.import_statement(y, mo, label='rückwärts ')
        d.view_current()
    print(f'\nvorwärts/rückwärts: {d.steps} Schritte, {d.checks} Prüfungen, Beobachtungen={dict(d.model.obs)}')


def test_history_delete_and_clear_cycle(fresh):
    client, path = fresh
    d = Driver(client, path, seed=2, label='historie')
    for rnd in range(3):
        for i in range(8):
            y, mo = from_index(month_index(2025, 1) + i)
            d.model.now = datetime.datetime(y, mo, 15, 9, 0)
            d.import_statement(y, mo)
            d.month_switch()
        for h in list(d.model.history)[::2]:
            d.delete_month(h['monat'], h['jahr'])
        d.delete_month('Januar', 1999)       # unknown month -> 404
        d.clear_history()
        assert d.model.history == []


def test_history_snapshot_keeps_quote_set_before_closing(fresh):
    """Regression (found by the soak model): the quote set via /api/quote must end up in the
    history snapshot, not the quote the month was initialised with."""
    client, path = fresh
    d = Driver(client, path, seed=3, label='quote-snapshot')
    d.set_quote(50)
    d.month_switch()
    assert d.get_state()['monatliche_historie'][-1]['individuelle_quote'] == 50


@pytest.mark.parametrize('year', range(2025, 2031))
def test_quarter_planning_exists_for_every_supported_year(year):
    """Regression (found by the soak model): the quarterly quote rule only knew 2025/2026."""
    from config import Config
    for q, months in enumerate([['Januar', 'Februar', 'März'], ['April', 'Mai', 'Juni'],
                                ['Juli', 'August', 'September'], ['Oktober', 'November', 'Dezember']], 1):
        assert Config.QUARTALS_PLANUNG[f'Q{q}/{year}'] == months


class TestMonthCloseOnlyAffectsThatMonth:
    """B5: 'Monat abschliessen' used to wipe the entries of ALL months, close the viewed month
    again and again into duplicate history rows and keep the history in insertion order.
    The Driver checks every step against the model, so these scenarios assert the whole state."""

    def two_months(self, fresh):
        client, path = fresh
        d = Driver(client, path, seed=5, label='B5')
        d.model.now = datetime.datetime(2026, 3, 20, 9, 0)
        d.check(d.get_state())
        d.import_statement(2026, 1)
        d.import_statement(2026, 2)                          # view is now February
        return d

    def test_other_months_keep_their_entries(self, fresh):
        d = self.two_months(fresh)
        january = {k for k in d.model.entries if k[0].startswith('2026-01-')}
        assert january
        d.month_switch()                                      # closes February only
        assert {k for k in d.model.entries if k[0].startswith('2026-01-')} == january
        assert {k[0][:7] for k in d.get_state_keys()} == {'2026-01'}

    def test_closing_an_empty_month_again_keeps_the_saved_snapshot(self, fresh):
        d = self.two_months(fresh)
        d.month_switch()
        before = d.get_state()['monatliche_historie']
        d.import_statement(2026, 2)                           # February shown again ...
        d.delete_all_entries()                                # ... and emptied
        d.month_switch()                                      # nothing to add: no duplicate, no overwrite
        assert d.get_state()['monatliche_historie'] == before

    def test_history_is_sorted_and_a_reloaded_month_is_updated_not_duplicated(self, fresh):
        d = self.two_months(fresh)
        d.month_switch()                                      # February first
        d.import_statement(2026, 1)
        d.month_switch()                                      # then January
        d.import_statement(2026, 2)
        d.month_switch()                                      # February again, with entries: updated
        months = [(h['jahr'], h['monat']) for h in d.get_state()['monatliche_historie']]
        assert months == [(2026, 'Januar'), (2026, 'Februar')]
