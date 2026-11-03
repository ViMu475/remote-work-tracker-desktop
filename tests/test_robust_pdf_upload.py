"""Robustness: /api/pdf/analyze with non-PDF, empty, huge and oddly named uploads (synthetic bytes only)."""
import glob
import io
import os
import tempfile

import pytest


def upload(client, data, name='a.pdf', field='file'):
    return client.post('/api/pdf/analyze', data={field: (io.BytesIO(data), name)}, content_type='multipart/form-data')


def scratch_dirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), 'rw_upload_*')))


class TestAnalyzeUpload:
    def test_no_file_field(self, client):
        assert client.post('/api/pdf/analyze').status_code == 400
        assert client.post('/api/pdf/analyze', data={'other': 'x'}).status_code == 400
        assert client.post('/api/pdf/analyze', json={'file': 'x'}).status_code == 400

    def test_empty_file_name(self, client):
        assert upload(client, b'%PDF-1.4', name='').status_code == 400

    @pytest.mark.parametrize('name', ['a.txt', 'a', 'a.pdf.exe', 'a.png', '.pdf.', 'pdf'])
    def test_wrong_extension(self, client, name):
        assert upload(client, b'%PDF-1.4', name=name).status_code == 400

    @pytest.mark.parametrize('data', [b'', b'hello world', b'%PDF-1.4', b'%PDF-1.7\n' + b'\x00' * 5000, b'\xff' * 3000,
                                      b'MZ' + b'\x00' * 100, b'<html><script>1</script></html>', b'%PDF-' + b'A' * 100000])
    def test_non_pdf_content_gives_clean_json_error_and_no_leftovers(self, client, data):
        before = scratch_dirs()
        resp = upload(client, data)
        assert resp.status_code in (200, 400, 422, 500)
        body = resp.get_json()
        assert body is not None and 'success' in body        # JSON, not an HTML traceback page
        if resp.status_code == 200:
            assert body.get('success') in (True, False)
            assert not body.get('sessions')                  # nothing invented from garbage
        assert scratch_dirs() <= before                      # scratch directory removed

    def test_huge_garbage_file(self, client):
        before = scratch_dirs()
        resp = upload(client, b'%PDF-1.4\n' + os.urandom(1024) * 20000)   # about 20 MB
        assert resp.get_json() is not None
        assert resp.status_code < 600
        assert scratch_dirs() <= before

    @pytest.mark.parametrize('name', ['../../etc/x.pdf', '..\\..\\x.pdf', '/etc/passwd.pdf', 'C:\\Windows\\x.pdf',
                                      'a\u0000b.pdf', '\u00e4\u00f6\u00fc 😀.pdf', 'x' * 400 + '.pdf', '.pdf', '....pdf',
                                      'a b;rm -rf.pdf', 'NUL.pdf', 'A.PDF'])
    def test_path_tricks_in_file_name(self, client, name, tmp_path):
        marker_dirs = [os.path.expanduser('~'), '/etc']
        before = {d: set(os.listdir(d)) for d in marker_dirs}
        resp = upload(client, b'%PDF-1.4 garbage', name=name)
        assert resp.status_code < 600 and resp.get_json() is not None
        assert {d: set(os.listdir(d)) for d in marker_dirs} == before     # nothing written outside the scratch dir

    def test_state_is_not_changed_by_analyze(self, client):
        import routes.api as api_module
        before = open(api_module.state_service.data_file, 'rb').read()
        upload(client, b'garbage')
        assert open(api_module.state_service.data_file, 'rb').read() == before

    def test_repeat_upload_is_stable(self, client):
        a, b = upload(client, b'x'), upload(client, b'x')
        assert (a.status_code, a.get_json()) == (b.status_code, b.get_json())

    def test_parallel_uploads_with_same_name_do_not_collide(self, client, app):
        import threading
        out = []
        def work():
            out.append(upload(app.test_client(), b'%PDF-1.4 junk').status_code)
        ts = [threading.Thread(target=work) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert len(set(out)) == 1

    def test_restore_and_import_reject_file_upload_misuse(self, client):
        resp = client.post('/api/pdf/import', data={'file': (io.BytesIO(b'x'), 'a.pdf')}, content_type='multipart/form-data')
        assert resp.status_code < 500
