"""Robustness: broken / mistyped / hostile request bodies must never cause a 5xx or corrupt the state file."""
import json
import math

import pytest

BAD_BODIES = [
    ('null', 'null'), ('list', '[]'), ('list_of_dicts', '[{"a":1}]'), ('string', '"abc"'), ('number', '42'),
    ('true', 'true'), ('empty_obj', '{}'), ('broken', '{"datum": '), ('empty', ''), ('nan', '{"quote": NaN}'),
    ('inf', '{"quote": Infinity}'), ('huge', '{"quote": 1e999}'),
]

JSON_POST = ['/api/protokoll', '/api/quote', '/api/sollstunden', '/api/darkmode', '/api/language',
             '/api/view/month', '/api/pdf/import', '/api/restore']


def _state_bytes(client):
    from routes import api as api_module
    with open(api_module.state_service.data_file, 'rb') as f:
        return f.read()


@pytest.mark.parametrize('url', JSON_POST)
@pytest.mark.parametrize('name,body', BAD_BODIES, ids=[b[0] for b in BAD_BODIES])
def test_bad_json_bodies_never_5xx(client, url, name, body):
    before = _state_bytes(client)
    resp = client.post(url, data=body, content_type='application/json')
    assert resp.status_code < 500, (url, name, resp.status_code, resp.get_data(as_text=True)[:200])
    if resp.status_code >= 400:
        assert _state_bytes(client) == before   # a rejected request never changes the file


@pytest.mark.parametrize('url', JSON_POST)
def test_wrong_content_type_never_5xx(client, url):
    resp = client.post(url, data='x=1', content_type='text/plain')
    assert resp.status_code < 500


@pytest.mark.parametrize('method', ['put'])
@pytest.mark.parametrize('name,body', BAD_BODIES, ids=[b[0] for b in BAD_BODIES])
def test_update_bad_bodies_never_5xx(client, method, name, body):
    resp = getattr(client, method)('/api/update/whatever', data=body, content_type='application/json')
    assert resp.status_code < 500


QUOTE_VALUES = [None, [], {}, 'abc', '', True, False, float('nan'), float('inf'), -float('inf'), 1e308, -1, 0,
                '50', 10 ** 400, '１２', [1], {'a': 1}]


@pytest.mark.parametrize('value', QUOTE_VALUES, ids=repr)
def test_quote_values(client, value):
    body = '{"quote": %s}' % (json.dumps(value) if not isinstance(value, int) or abs(value) < 10 ** 300 else str(value))
    resp = client.post('/api/quote', data=body, content_type='application/json')
    assert resp.status_code < 500
    if resp.status_code == 200:
        q = resp.get_json()['state']['individuelle_quote_prozent']
        assert math.isfinite(q) and 40 <= q <= 60


@pytest.mark.parametrize('value', QUOTE_VALUES, ids=repr)
def test_sollstunden_values(client, value):
    body = '{"sollStunden": %s}' % (json.dumps(value) if not isinstance(value, int) or abs(value) < 10 ** 300 else str(value))
    resp = client.post('/api/sollstunden', data=body, content_type='application/json')
    assert resp.status_code < 500
    if resp.status_code == 200:
        s = resp.get_json()['state']['soll_stunden_pro_tag']
        assert math.isfinite(s) and 1 <= s <= 10


@pytest.mark.parametrize('value', [None, [], {}, 1, 'de ', 'EN', 'fr', '', ['de'], {'a': 1}, True], ids=repr)
def test_language_values(client, value):
    resp = client.post('/api/language', json={'language': value})
    assert resp.status_code < 500
    if resp.status_code == 200:
        assert resp.get_json()['state']['language'] in ('de', 'en')


@pytest.mark.parametrize('month,year', [
    ('Januar', 2026), ('März', 'x'), ('März', None), ('März', 2026.0), ('März', True), ('März', 10 ** 30),
    ('März', -5), (None, 2026), (['März'], 2026), ({'a': 1}, 2026), ('März\u0000', 2026), ('März', 1989),
    ('März', 2101), ('ä' * 5000, 2026), ('März', float('nan'))])
def test_view_month_values(client, month, year):
    resp = client.post('/api/view/month', json={'month': month, 'year': year})
    assert resp.status_code < 500


ENTRY_VALUES = [None, '', 'abc', 1, [], {}, '25:00', '24:00', '8', '08:00:00', '-1:00', '08:-5', '٠٨:٠٠', '08:00\n',
                ' 08:00', '99999999999999999999:00', '08:00' * 1000, '\u0000', '😀', '2026-02-30', '2026-13-01',
                '2026-03-0٣', '0000-00-00', '../../etc/passwd', "'; DROP TABLE x;--"]


@pytest.mark.parametrize('field', ['datum', 'start', 'end'])
@pytest.mark.parametrize('value', ENTRY_VALUES, ids=lambda v: repr(v)[:30])
def test_protokoll_field_garbage(client, field, value):
    body = {'datum': '2026-03-10', 'start': '08:00', 'end': '16:00', 'pause': 30}
    body[field] = value
    before = _state_bytes(client)
    resp = client.post('/api/protokoll', json=body)
    assert resp.status_code < 500, (field, value, resp.get_data(as_text=True)[:200])
    if resp.status_code >= 400:
        assert _state_bytes(client) == before


@pytest.mark.parametrize('field', ['pause', 'remote'])
@pytest.mark.parametrize('value', [None, [], {}, 'abc', True, float('nan'), float('inf'), -float('inf'), -30, 1e308,
                                   '30', '3e2', '0x10', '١٠', 'nan', 'inf', ' 30 '], ids=repr)
def test_protokoll_numeric_garbage(client, field, value):
    body = {'datum': '2026-03-10', 'start': '08:00', 'end': '16:00', 'pause': 30}
    body[field] = value
    resp = client.post('/api/protokoll', data=json.dumps(body), content_type='application/json')
    assert resp.status_code < 500, (field, value, resp.get_data(as_text=True)[:200])
    if resp.status_code == 200:
        e = resp.get_json()['state']['daily_records']['2026-03-10'][-1]
        for k in ('pauseMinutes', 'remoteStundenHeute', 'totalStundenHeute'):
            assert math.isfinite(e[k]), (k, e[k])
        assert 0 <= e['remoteStundenHeute'] <= e['totalStundenHeute'] + 1e-9
        assert e['pauseMinutes'] >= 0


@pytest.mark.parametrize('path', ['..%2F..%2Fetc%2Fpasswd', '%00', 'a' * 5000, '%F0%9F%98%80', '.', '..', 'x y'])
def test_path_ids_delete_update(client, path):
    assert client.delete('/api/delete/' + path).status_code in (404, 405, 308, 400)
    r = client.put('/api/update/' + path, json={'datum': '2026-03-10', 'start': '08:00', 'end': '09:00'})
    assert r.status_code < 500


@pytest.mark.parametrize('name', ['..', 'x/y', '%00', 'ä' * 300, 'März', "'", '<script>'])
def test_delete_month_odd_names(client, name):
    from urllib.parse import quote
    r = client.delete('/api/delete_month/%s/2026' % quote(name, safe=''))
    assert r.status_code < 500
    assert client.delete('/api/delete_month/März/99999999999999999999999').status_code in (404, 400)


def test_delete_is_idempotent(client):
    st = client.get('/api/state').get_json()
    resp = client.post('/api/protokoll', json={'datum': '2026-03-11', 'start': '09:00', 'end': '10:00', 'pause': 0})
    eid = resp.get_json()['state']['daily_records']['2026-03-11'][-1]['id']
    r1 = client.delete('/api/delete/' + eid.replace('|', '%7C'))
    r2 = client.delete('/api/delete/' + eid.replace('|', '%7C'))
    assert r1.status_code == 200 and r2.status_code == 404


def test_double_submit_same_entry_is_rejected_as_overlap(client):
    body = {'datum': '2026-03-12', 'start': '08:00', 'end': '12:00', 'pause': 0}
    assert client.post('/api/protokoll', json=body).status_code == 200
    assert client.post('/api/protokoll', json=body).status_code == 400
    day = client.get('/api/state').get_json()['daily_records']['2026-03-12']
    assert len(day) == 1


@pytest.mark.parametrize('url', ['/api/delete_all_entries', '/api/clear_all_history', '/api/view/current_month',
                                 '/api/month/switch'])
def test_repeat_is_stable(client, url):
    a = client.post(url)
    b = client.post(url)
    assert a.status_code < 500 and b.status_code < 500
    if url != '/api/month/switch':
        sa, sb = a.get_json()['state'], b.get_json()['state']
        assert sa == sb


def test_idempotent_settings(client):
    for url, body in (('/api/quote', {"quote": 50}), ('/api/sollstunden', {'sollStunden': 8}),
                      ('/api/darkmode', {'darkMode': True}), ('/api/language', {'language': 'en'})):
        a = client.post(url, json=body).get_json()['state']
        b = client.post(url, json=body).get_json()['state']
        assert a == b


@pytest.mark.parametrize('url', ['/api/state', '/api/backup', '/api/report/final', '/api/export/daily_csv',
                                 '/api/report/monthly_pdf'])
def test_get_endpoints_with_junk_query(client, url):
    for qs in ('?month=%00&year=abc', '?month=' + 'x' * 5000, '?year=99999999999999999999', '?month=März&year=-1',
               '?month[]=a&year[]=1'):
        assert client.get(url + qs).status_code < 500


def test_unicode_roundtrip_in_backup(client):
    st = client.get('/api/state').get_json()
    st['sonder'] = 'Grüße 😀 ‮'
    r = client.post('/api/restore', data=json.dumps(st, ensure_ascii=False).encode('utf-8'),
                    content_type='application/json')
    assert r.status_code == 200
    assert client.get('/api/backup').get_json()['sonder'] == 'Grüße 😀 ‮'
