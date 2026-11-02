"""Parser check against real SAP time statements (local only).

The PDFs contain personal data and are NOT part of the repository. Point
ZEITNACHWEISE_DIR at a folder with TimeStatement_*.pdf / Zeitnachweis_*.pdf
files (searched recursively). Without that folder the tests are skipped.

Instead of hard-coded numbers, every PDF is checked against an independent
count of its own text lines, so new statements can be dropped in unchanged.
"""
import glob
import os
import re
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# git-ignored folder inside the repository; only used on the developer's own machine
DEFAULT_DIR = os.path.join(os.path.dirname(__file__), 'real_statements')
REAL_DIR = os.environ.get('ZEITNACHWEISE_DIR', DEFAULT_DIR)

_PDFS = sorted(p for p in glob.glob(os.path.join(REAL_DIR, '**', '*.pdf'), recursive=True)
               if os.path.basename(p).startswith(('TimeStatement_', 'Zeitnachweis_')))
_PARAMS = [pytest.param(p, id=os.path.basename(p)) for p in _PDFS] or [
    pytest.param(None, id='no-pdfs', marks=pytest.mark.skip(
        reason=f'No real time statements found in {REAL_DIR} (set ZEITNACHWEISE_DIR)'))
]

DAY_LINE = re.compile(
    r'\d{2}\s+(?:MO|TU|WE|TH|FR|SA|SU|DI|MI|DO|SO)\s+(?:Time Postings|Zeitbuchungen)')
CONTINUATION = re.compile(r'(?:Time Postings|Zeitbuchungen)\s*:')


def _expected_session_count(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        text = '\n'.join((page.extract_text() or '') for page in pdf.pages)
    lines = text.split('\n')
    return (sum(1 for l in lines if DAY_LINE.match(l))
            + sum(1 for l in lines if CONTINUATION.match(l)))


@pytest.fixture(scope='module')
def service():
    from services.pdf_service import PDFService
    return PDFService()


@pytest.mark.parametrize('pdf_path', _PARAMS)
class TestRealStatements:
    def test_parses_successfully(self, service, pdf_path):
        result = service._parse_sap_timestatement(pdf_path)
        assert result['success'] is True
        assert result['sessions']

    def test_session_count_matches_pdf_lines(self, service, pdf_path):
        result = service._parse_sap_timestatement(pdf_path)
        assert len(result['sessions']) == _expected_session_count(pdf_path)

    def test_sessions_are_plausible(self, service, pdf_path):
        result = service._parse_sap_timestatement(pdf_path)
        structure = result['structure']
        seen = set()
        for s in result['sessions']:
            date = datetime.strptime(s['date'], '%Y-%m-%d')
            assert (date.year, date.month) == (structure['year'], structure['month'])
            assert date.weekday() < 6, f"Sunday session on {s['date']}"
            start = datetime.strptime(s['start_time'], '%H:%M')
            end = datetime.strptime(s['end_time'], '%H:%M')
            assert end > start, f"End before start on {s['date']}"
            key = (s['date'], s['start_time'], s['end_time'])
            assert key not in seen, f'Duplicate session {key}'
            seen.add(key)

    def test_summary_counts_add_up(self, service, pdf_path):
        structure = service._parse_sap_timestatement(pdf_path)['structure']
        assert (structure['remote_sessions'] + structure['office_sessions']
                == structure['total_sessions'])


# ── loading several real statements, in any order ─────────────────────

def _read_sessions(path):
    import contextlib
    import io
    from services.pdf_service import PDFService
    with contextlib.redirect_stdout(io.StringIO()):
        result = PDFService()._parse_sap_timestatement(path)
    return result['sessions']


def _remote_hours_without_overlaps(sessions):
    """Remote hours as the importer accepts them (a session overlapping an accepted one is rejected)."""
    from services.calculation import calculate_net_hours
    minutes = lambda t: int(t[:2]) * 60 + int(t[3:])
    accepted, total = {}, 0.0
    for s in sorted(sessions, key=lambda x: (x['date'], x['start_time'])):
        a, b = minutes(s['start_time']), minutes(s['end_time'])
        if any(a < y and b > x for x, y in accepted.get(s['date'], [])):
            continue
        accepted.setdefault(s['date'], []).append((a, b))
        if s['is_remote']:
            total += calculate_net_hours(s['start_time'], s['end_time'], 0)['net']
    return round(total, 2)


_PDFS_2026 = [p for p in _PDFS if os.path.basename(p).startswith('TimeStatement_2026')]
_REAL_MARK = pytest.mark.skipif(len(_PDFS_2026) < 2, reason='needs at least two 2026 statements in ZEITNACHWEISE_DIR')


@_REAL_MARK
class TestRealStatementsInSequence:
    """The reported bug with the user's own statements: values must follow every import and view change."""

    @pytest.mark.parametrize('direction', ['alphabetisch', 'umgekehrt'])
    def test_every_step_shows_correct_values(self, client, direction):
        from freezegun import freeze_time
        from tests.test_state_consistency import assert_consistent, assert_same_as_get

        files = sorted(_PDFS_2026, key=lambda p: os.path.basename(p))
        files = files if direction == 'alphabetisch' else files[::-1]
        statements = {p: _read_sessions(p) for p in files}
        months_seen = set()
        with freeze_time('2026-11-01 12:00:00'):
            client.post('/api/view/current_month')
            for path, sessions in statements.items():
                name = os.path.basename(path)
                resp = client.post('/api/pdf/import', json={'sessions': sessions}).get_json()
                state = resp['state']
                assert_consistent(state, f'Import {name}')
                assert_same_as_get(client, state, f'Import {name}')
                month = sessions[0]['date'][:7]
                if month not in months_seen:
                    # first statement for this month: compare with the independent PDF numbers
                    assert state['current_month_data']['ist_remote_stunden_laufend'] == pytest.approx(
                        _remote_hours_without_overlaps(sessions), abs=0.011), name
                months_seen.add(month)

                back = client.post('/api/view/current_month').get_json()['state']
                assert (back['view_month'], back['view_year']) == ('November', 2026)
                assert_consistent(back, f'Aktueller Monat nach {name}')
                assert_same_as_get(client, back, f'Aktueller Monat nach {name}')

                again = client.post('/api/pdf/import', json={'sessions': sessions}).get_json()
                assert again['imported_count'] == 0, f'{name}: second import must only find duplicates'
                assert again['state']['view_month'] == state['view_month']
                assert_consistent(again['state'], f'Doppelter Import {name}')
