"""'Monat abschließen': no empty month, no duplicate month, history always sorted (fictional data only)."""
import copy
import json

from services.final_report import normalize_history


def hist(name, year, remote=10.0, quartal=None):
    return {'monat': name, 'jahr': year, 'ist_remote_stunden_laufend': remote, 'max_remote_stunden': 64.0,
            'soll_stunden_gesamt': 160.0, 'ist_arbeitszeit_laufend': 160.0, 'individuelle_quote': 40.0,
            'tatsaechliche_remote_quote': remote / 160 * 100, 'quartal': quartal}


def entry(date):
    return {'id': 'x' + date, 'datum': date, 'startTime': '08:00', 'endTime': '16:30', 'pauseMinutes': 30,
            'remoteStundenHeute': 4.0, 'totalStundenHeute': 8.0, 'pauseWarning': None, 'source': None}


def state_for(sample_state, month, year, entries, history=()):
    """State whose viewed month is `month`/`year` with `entries` (list of ISO dates)."""
    from config import Config
    state = copy.deepcopy(sample_state)
    state.update({
        'aktueller_monat': month, 'aktuelles_jahr': year, 'view_month': month, 'view_year': year,
        'daily_records': {d: [entry(d)] for d in entries},
        'monatliche_historie': copy.deepcopy(list(history)),
        'current_month_data': {'monat': month, 'jahr': year, 'soll_stunden_gesamt': 160.0,
                               'ist_remote_stunden_laufend': 0.0, 'ist_arbeitszeit_laufend': 0.0,
                               'max_remote_stunden': 64.0, 'individuelle_quote': 40.0},
    })
    return state


def restore(client, state):
    resp = client.post('/api/restore', data=json.dumps(state), content_type='application/json')
    assert resp.status_code == 200, resp.get_json()


def close(client):
    resp = client.post('/api/month/switch')
    assert resp.status_code == 200
    return resp.get_json()


def names(state):
    return [(m['monat'], m['jahr']) for m in state['monatliche_historie']]


class TestEmptyMonth:
    def test_month_without_entries_is_not_added(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, []))
        data = close(client)
        assert data['state']['monatliche_historie'] == []
        assert 'keine Einträge' in data['message']

    def test_empty_month_does_not_touch_the_existing_history(self, client, sample_state):
        restore(client, state_for(sample_state, 'Juni', 2026, [], [hist('April', 2026), hist('Mai', 2026)]))
        data = close(client)
        assert names(data['state']) == [('April', 2026), ('Mai', 2026)]

    def test_month_with_entries_is_added(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04', '2026-05-05']))
        data = close(client)
        assert names(data['state']) == [('Mai', 2026)]
        assert 'keine Einträge' not in data['message']

    def test_english_message_for_empty_month(self, client, sample_state):
        st = state_for(sample_state, 'Mai', 2026, [])
        st['language'] = 'en'
        restore(client, st)
        assert 'has no entries' in close(client)['message']

    def test_empty_month_still_advances_to_next_month(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, []))
        state = close(client)['state']
        assert (state['aktueller_monat'], state['aktuelles_jahr']) == ('Juni', 2026)


class TestNoDuplicates:
    def test_closing_a_month_twice_keeps_one_row(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04']))
        close(client)
        # the user views May again, loads a statement again and closes once more
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04', '2026-05-05'], [hist('Mai', 2026, 5.0)]))
        data = close(client)
        assert names(data['state']) == [('Mai', 2026)]

    def test_existing_month_with_entries_is_updated_not_duplicated(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04'], [hist('Mai', 2026, 99.0)]))
        data = close(client)
        rows = [m for m in data['state']['monatliche_historie'] if m['monat'] == 'Mai']
        assert len(rows) == 1 and rows[0]['ist_remote_stunden_laufend'] != 99.0

    def test_existing_month_without_entries_keeps_the_saved_snapshot(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, [], [hist('Mai', 2026, 77.0)]))
        data = close(client)
        rows = data['state']['monatliche_historie']
        assert len(rows) == 1 and rows[0]['ist_remote_stunden_laufend'] == 77.0

    def test_same_month_in_another_year_is_a_different_month(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04'], [hist('Mai', 2025)]))
        data = close(client)
        assert names(data['state']) == [('Mai', 2025), ('Mai', 2026)]


class TestAlwaysSorted:
    def test_months_closed_in_any_order_end_up_sorted(self, client, sample_state):
        order = [('Juli', 2026, '2026-07-01'), ('Mai', 2026, '2026-05-04'), ('Januar', 2027, '2027-01-04'),
                 ('Dezember', 2025, '2025-12-01'), ('Juni', 2026, '2026-06-01')]
        history = []
        for name, year, day in order:
            restore(client, state_for(sample_state, name, year, [day], history))
            history = close(client)['state']['monatliche_historie']
        assert [(m['monat'], m['jahr']) for m in history] == [
            ('Dezember', 2025), ('Mai', 2026), ('Juni', 2026), ('Juli', 2026), ('Januar', 2027)]

    def test_year_wins_over_month_name(self, client, sample_state):
        restore(client, state_for(sample_state, 'Januar', 2026, ['2026-01-05'], [hist('Dezember', 2026), hist('März', 2025)]))
        assert names(close(client)['state']) == [('März', 2025), ('Januar', 2026), ('Dezember', 2026)]

    def test_restore_sorts_a_shuffled_history(self, client, sample_state):
        st = state_for(sample_state, 'Mai', 2027, [], [hist('Juli', 2026), hist('Mai', 2026), hist('Juni', 2026)])
        resp = client.post('/api/restore', data=json.dumps(st), content_type='application/json')
        assert names(resp.get_json()['state']) == [('Mai', 2026), ('Juni', 2026), ('Juli', 2026)]

    def test_restore_removes_duplicate_months(self, client, sample_state):
        st = state_for(sample_state, 'Mai', 2027, [], [hist('Mai', 2026, 1.0), hist('Mai', 2026, 2.0), hist('April', 2026)])
        state = client.post('/api/restore', data=json.dumps(st), content_type='application/json').get_json()['state']
        assert names(state) == [('April', 2026), ('Mai', 2026)]
        assert state['monatliche_historie'][1]['ist_remote_stunden_laufend'] == 2.0   # the last one wins

    def test_final_report_lists_the_months_in_order(self, client, sample_state):
        restore(client, state_for(sample_state, 'Mai', 2026, ['2026-05-04'], [hist('Juli', 2026), hist('April', 2026)]))
        close(client)
        rep = client.get('/api/report/final').get_json()['report']
        months = [(m['monat']) for q in rep['quarters'] for m in q['months']]
        assert months == ['April', 'Mai', 'Juli']


class TestNormalizeHistory:
    def test_sorted_and_unique(self):
        got = normalize_history([hist('Mai', 2026, 1), hist('Januar', 2026), hist('Mai', 2026, 2), hist('Dezember', 2025)])
        assert [(m['monat'], m['jahr']) for m in got] == [('Dezember', 2025), ('Januar', 2026), ('Mai', 2026)]
        assert got[2]['ist_remote_stunden_laufend'] == 2

    def test_empty_and_none(self):
        assert normalize_history([]) == [] and normalize_history(None) == []

    def test_input_list_is_not_modified(self):
        data = [hist('Mai', 2026), hist('April', 2026)]
        normalize_history(data)
        assert data[0]['monat'] == 'Mai'
