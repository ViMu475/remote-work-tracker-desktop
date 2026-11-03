"""Robustness: /api/restore with broken / old / foreign state, damaged state file, parallel access."""
import copy
import glob
import json
import os
import threading

import pytest

import routes.api as api_module
from services.state_service import StateService


def post_restore(client, state):
    return client.post('/api/restore', data=json.dumps(state), content_type='application/json')


def state_file():
    return api_module.state_service.data_file


# ---------- /api/restore ----------

class TestRestoreValidation:
    @pytest.mark.parametrize('field,value', [
        ('daily_records', []), ('daily_records', None), ('daily_records', 'x'),
        ('current_month_data', []), ('current_month_data', 5),
        ('individuelle_quote_prozent', 'viel'), ('individuelle_quote_prozent', None), ('individuelle_quote_prozent', 99),
        ('individuelle_quote_prozent', True), ('soll_stunden_pro_tag', 0), ('soll_stunden_pro_tag', 99),
        ('soll_stunden_pro_tag', [8]), ('aktuelles_jahr', '2026'), ('aktuelles_jahr', 2026.5), ('aktuelles_jahr', 10 ** 12),
        ('aktuelles_jahr', None), ('aktueller_monat', 'Smarch'), ('aktueller_monat', 3), ('aktueller_monat', ['März']),
        ('view_month', 'x'), ('view_year', 'x'), ('monatliche_historie', 'x'), ('monatliche_historie', [1, 2]),
        ('monatliche_historie', {'a': 1})])
    def test_wrong_typed_field_is_rejected_and_state_untouched(self, client, sample_state, field, value):
        client.get('/api/state')
        before = open(state_file(), 'rb').read()
        st = copy.deepcopy(sample_state)
        st[field] = value
        resp = post_restore(client, st)
        assert resp.status_code == 400, resp.get_data(as_text=True)[:200]
        assert open(state_file(), 'rb').read() == before
        assert client.get('/api/state').status_code == 200

    @pytest.mark.parametrize('payload', [b'', b'\xff\xfe\x00', b'{"a":', b'[' * 100000, b'nul', b'{"a": 1e999999}x'])
    def test_garbage_payload(self, client, payload):
        resp = client.post('/api/restore', data=payload, content_type='application/json')
        assert resp.status_code == 400

    def test_multipart_upload_of_garbage_and_empty_file(self, client):
        import io
        for data in (b'', b'not json', b'\x00' * 1000):
            resp = client.post('/api/restore', data={'file': (io.BytesIO(data), 'b.json')},
                               content_type='multipart/form-data')
            assert resp.status_code == 400

    def test_old_state_without_new_fields_works_everywhere(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        for k in ('gleitzeit_saldo', 'view_month', 'view_year', 'monatliche_historie', 'current_quartal',
                  'language', 'dark_mode', 'quartal_data'):
            st.pop(k, None)
        resp = post_restore(client, st)
        assert resp.status_code == 200
        assert resp.get_json()['state']['monatliche_historie'] == []
        for url in ('/api/state', '/api/backup', '/api/report/final', '/api/export/daily_csv', '/api/report/monthly_pdf'):
            assert client.get(url).status_code < 500, url
        assert client.post('/api/month/switch').status_code == 200
        assert client.post('/api/view/current_month').status_code == 200
        assert client.post('/api/delete_all_entries').status_code == 200
        assert client.delete('/api/delete_month/Januar/2020').status_code == 404

    def test_foreign_fields_survive_and_do_not_break(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        st.update({'__proto__': {'x': 1}, 'constructor': 'x', 'zukunft': [1, 2, {'a': None}], 'ü😀': 'ß'})
        assert post_restore(client, st).status_code == 200
        out = client.get('/api/backup').get_json()
        assert out['zukunft'] == [1, 2, {'a': None}] and out['ü😀'] == 'ß'

    @pytest.mark.parametrize('flex', [None, 5, 'x', [], {}, {'total': 'x'}, {'total': float('nan')}, {'total': 10 ** 9},
                                      {'total': True}, {'foo': 1}])
    def test_bad_gleitzeit_saldo_is_dropped(self, client, sample_state, flex):
        st = copy.deepcopy(sample_state)
        st['gleitzeit_saldo'] = flex
        resp = client.post('/api/restore', data=json.dumps(st), content_type='application/json')
        assert resp.status_code == 200
        assert 'gleitzeit_saldo' not in resp.get_json()['state']

    def test_good_gleitzeit_saldo_is_kept(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        st['gleitzeit_saldo'] = {'total': 10.0, 'previous': 5, 'current': 5.0, 'evil': 'x'}
        out = post_restore(client, st).get_json()['state']
        assert out['gleitzeit_saldo'] == {'total': 10.0, 'previous': 5.0, 'current': 5.0}

    def test_restore_twice_is_idempotent(self, client, sample_state):
        a = post_restore(client, sample_state).get_json()['state']
        b = post_restore(client, a).get_json()['state']
        assert a == b

    def test_backup_restore_roundtrip(self, client):
        a = client.get('/api/backup').get_json()
        b = post_restore(client, a).get_json()['state']
        assert client.get('/api/backup').get_json() == b

    def test_records_with_garbage_inside_are_survivable(self, client, sample_state):
        st = copy.deepcopy(sample_state)
        st['daily_records'].update({'2026-03-02': [1, None, 'x', {'remoteStundenHeute': 'a'}], 'kaputt': 5,
                                    '2026-03-03': {'startTime': 7}, '2026-03-04': None})
        assert post_restore(client, st).status_code == 200
        for url in ('/api/state', '/api/backup', '/api/export/daily_csv', '/api/report/monthly_pdf'):
            assert client.get(url).status_code < 500, url
        assert client.post('/api/protokoll', json={'datum': '2026-03-02', 'start': '08:00', 'end': '09:00'}).status_code < 500
        assert client.post('/api/month/switch').status_code < 500


# ---------- damaged state file ----------

class TestDamagedStateFile:
    @pytest.mark.parametrize('content', [b'', b'{', b'{"individuelle_quote_prozent": 40, "daily_records": {"2026-03',
                                         b'\x00' * 50, b'[]', b'null', b'"x"', b'\xff\xfe', b'{"a": 1}'[:-1]])
    def test_unreadable_file_gives_fresh_state_not_a_500(self, client, content):
        with open(state_file(), 'wb') as f:
            f.write(content)
        assert client.get('/api/state').status_code == 200
        for url in ('/api/backup', '/api/report/final', '/api/export/daily_csv', '/api/report/monthly_pdf'):
            assert client.get(url).status_code < 500
        assert json.load(open(state_file()))   # readable again

    def test_unreadable_file_is_kept_as_copy_before_it_is_overwritten(self, client):
        broken = b'{"daily_records": {"2026-03-02": [{"id": "x"'
        with open(state_file(), 'wb') as f:
            f.write(broken)
        assert client.get('/api/state').status_code == 200
        copies = glob.glob(state_file() + '.unreadable-*')
        assert len(copies) == 1 and open(copies[0], 'rb').read() == broken

    def test_empty_file_makes_no_copy(self, client):
        open(state_file(), 'wb').close()
        client.get('/api/state')
        assert glob.glob(state_file() + '.unreadable-*') == []

    def test_state_with_wrong_field_types_does_not_5xx(self, client, sample_state):
        for patch in ({'daily_records': []}, {'current_month_data': None}, {'monatliche_historie': 'x'},
                      {'soll_stunden_pro_tag': 'x'}, {'aktueller_monat': 'x'}):
            st = copy.deepcopy(sample_state)
            st.update(patch)
            with open(state_file(), 'w', encoding='utf-8') as f:
                json.dump(st, f)
            assert client.get('/api/state').status_code < 500, patch

    def test_save_leaves_no_temp_files_and_survives_unwritable_target(self, tmp_path):
        svc = StateService(data_file=str(tmp_path / 's.json'))
        assert svc.save_state({'a': 1}) is True
        assert os.listdir(tmp_path) == ['s.json']
        bad = StateService(data_file=str(tmp_path / 'no_such_dir' / 's.json'))
        assert bad.save_state({'a': 1}) is False

    def test_failed_save_keeps_previous_content(self, tmp_path):
        svc = StateService(data_file=str(tmp_path / 's.json'))
        svc.save_state({'v': 1})
        class Unserializable:
            pass
        assert svc.save_state({'v': Unserializable()}) is False
        assert json.load(open(tmp_path / 's.json')) == {'v': 1}
        assert os.listdir(tmp_path) == ['s.json']


# ---------- parallel access ----------

class TestParallelAccess:
    def test_parallel_entries_are_all_kept(self, client, app):
        """30 parallel POSTs for distinct slots: with a lost update some would be missing."""
        client.post('/api/delete_all_entries')
        days = [d for d in range(2, 28) if d not in (7, 8, 14, 15, 21, 22)]
        results = []

        def work(i):
            c = app.test_client()
            day = days[i % len(days)]
            hour = 6 + i // len(days) * 2
            r = c.post('/api/protokoll', json={'datum': f'2026-03-{day:02d}', 'start': f'{hour:02d}:00',
                                              'end': f'{hour + 1:02d}:00', 'pause': 0})
            results.append(r.status_code)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(40)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        ok = results.count(200)
        stored = sum(len(v) for v in json.load(open(state_file()))['daily_records'].values())
        assert all(code in (200, 400) for code in results)
        assert stored == ok and ok >= 30

    def test_readers_never_see_a_half_written_file(self, client, app):
        stop = threading.Event()
        errors = []

        def writer():
            c = app.test_client()
            i = 0
            while not stop.is_set():
                c.post('/api/quote', json={'quote': 40 + (i % 3) * 10})
                i += 1

        def reader():
            while not stop.is_set():
                try:
                    with open(state_file(), encoding='utf-8') as f:
                        json.load(f)
                except FileNotFoundError:
                    errors.append('missing')
                except ValueError as e:
                    errors.append(str(e))

        ts = [threading.Thread(target=writer) for _ in range(3)] + [threading.Thread(target=reader) for _ in range(2)]
        [t.start() for t in ts]
        threading.Event().wait(1.5)
        stop.set()
        [t.join() for t in ts]
        assert errors == []

    def test_parallel_delete_of_same_entry_has_exactly_one_winner(self, client, app):
        eid = client.post('/api/protokoll', json={'datum': '2026-03-03', 'start': '08:00', 'end': '09:00'}) \
            .get_json()['state']['daily_records']['2026-03-03'][-1]['id']
        codes = []
        def work():
            codes.append(app.test_client().delete('/api/delete/' + eid.replace('|', '%7C')).status_code)
        ts = [threading.Thread(target=work) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert sorted(codes) == [200] + [404] * 7

    def test_parallel_month_switch_does_not_skip_months(self, client, app, sample_state):
        client.post('/api/delete_all_entries')
        client.post('/api/protokoll', json={'datum': '2026-03-03', 'start': '08:00', 'end': '12:00'})
        ts = [threading.Thread(target=lambda: app.test_client().post('/api/month/switch')) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        st = json.load(open(state_file()))
        assert st['view_month'] == 'Mai'     # exactly two switches: März -> April -> Mai
