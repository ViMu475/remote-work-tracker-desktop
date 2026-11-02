"""Additional PDFService tests: header formats, fallbacks, error paths, Gemini.

pdfplumber and the Gemini client are replaced with fakes, so no real PDF,
network access or API key is needed. The date is frozen by conftest.py
(2026-03-15).
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.pdf_service as pdf_module
from services.pdf_service import PDFService


def _fake_pdfplumber(text):
    """Return a stand-in for the pdfplumber module that yields `text`."""
    page = MagicMock()
    page.extract_text.return_value = text
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__.return_value = pdf
    pdf.__exit__.return_value = False
    fake = MagicMock()
    fake.open.return_value = pdf
    return fake


def _parse(text, path='/tmp/report.pdf'):
    with patch.object(pdf_module, 'pdfplumber', _fake_pdfplumber(text), create=True):
        return PDFService()._parse_sap_timestatement(path)


@pytest.fixture
def svc():
    with patch.object(pdf_module.Config, 'GOOGLE_API_KEY', None):
        return PDFService()


# ── Header formats ────────────────────────────────────────────────────

class TestHeaderFormats:
    def test_english_range(self):
        r = _parse("from 01.07.2025 to 31.07.2025\n"
                   "01 TU Time Postings : At work 07:30 17:00 9,50")
        assert r['success'] is True
        assert r['structure']['year'] == 2025
        assert r['structure']['month'] == 7
        assert r['sessions'][0]['date'] == '2025-07-01'

    def test_german_range(self):
        r = _parse("vom 01.10.2025 bis 28.10.2025\n"
                   "01 DI Zeitbuchungen : Anwesend 07:30 17:00 9,50")
        assert r['structure']['year'] == 2025
        assert r['structure']['month'] == 10
        assert r['sessions'][0]['date'] == '2025-10-01'

    def test_english_month_name(self):
        r = _parse("Month: July - 2025\n"
                   "01 TU Time Postings : At work 07:30 17:00 9,50")
        assert (r['structure']['year'], r['structure']['month']) == (2025, 7)

    def test_unknown_english_month_name_falls_back_to_january(self):
        r = _parse("Month: Smarch - 2025\n"
                   "01 WE Time Postings : At work 07:30 17:00 9,50")
        assert (r['structure']['year'], r['structure']['month']) == (2025, 1)

    def test_german_month_name(self):
        r = _parse("Monat: März - 2026\n"
                   "02 MO Zeitbuchungen : Anwesend 08:00 16:30 8,50")
        assert (r['structure']['year'], r['structure']['month']) == (2026, 3)

    def test_unknown_german_month_name_falls_back_to_january(self):
        r = _parse("Monat: Foobar - 2026\n"
                   "02 FR Zeitbuchungen : Anwesend 08:00 16:30 8,50")
        assert (r['structure']['year'], r['structure']['month']) == (2026, 1)

    def test_filename_fallback(self):
        r = _parse("01 TU Time Postings : At work 07:30 17:00 9,50",
                   path='/x/TimeStatement_20310701_20310731.pdf')
        assert (r['structure']['year'], r['structure']['month']) == (2031, 7)
        assert r['sessions'][0]['date'] == '2031-07-01'

    def test_system_date_fallback(self):
        # Date is frozen to 2026-03-15 by conftest.py.
        r = _parse("02 MO Time Postings : At work 08:00 16:30 8,50",
                   path='/x/report.pdf')
        assert (r['structure']['year'], r['structure']['month']) == (2026, 3)
        assert r['sessions'][0]['date'] == '2026-03-02'


# ── Session extraction ────────────────────────────────────────────────

class TestSessionExtraction:
    def test_remote_and_office_are_classified(self):
        r = _parse("from 01.07.2025 to 31.07.2025\n"
                   "01 TU Time Postings : At work 07:30 17:00 9,50\n"
                   "03 TH Time Postings : Remote Work 08:00 17:15 9,25")
        flags = {s['date']: s['is_remote'] for s in r['sessions']}
        assert flags == {'2025-07-01': False, '2025-07-03': True}
        assert r['structure']['remote_sessions'] == 1
        assert r['structure']['office_sessions'] == 1
        assert '1 remote, 1 office' in r['message']

    @pytest.mark.parametrize('work_type,expected', [
        ('Telearbeit', True),
        ('Home Office', True),
        ('Homeoffice', True),
        ('Im Büro', False),
        ('Büro', False),
        ('anwesend', False),
    ])
    def test_german_work_types(self, work_type, expected):
        r = _parse("vom 01.10.2025 bis 31.10.2025\n"
                   f"01 MI Zeitbuchungen : {work_type} 08:00 12:00 4,00")
        assert len(r['sessions']) == 1
        assert r['sessions'][0]['is_remote'] is expected

    def test_split_day_creates_two_sessions(self):
        r = _parse("from 01.07.2025 to 31.07.2025\n"
                   "01 TU Time Postings : At work 07:30 12:00 4,50\n"
                   "Time Postings : Remote Work 13:00 17:00 4,00")
        assert [(s['date'], s['start_time'], s['is_remote']) for s in r['sessions']] == [
            ('2025-07-01', '07:30', False),
            ('2025-07-01', '13:00', True),
        ]

    def test_sessions_are_sorted_by_date_and_time(self):
        r = _parse("from 01.07.2025 to 31.07.2025\n"
                   "03 TH Time Postings : At work 08:00 12:00 4,00\n"
                   "01 TU Time Postings : At work 09:00 17:00 8,00\n"
                   "01 TU Time Postings : At work 07:00 08:30 1,50")
        keys = [(s['date'], s['start_time']) for s in r['sessions']]
        assert keys == sorted(keys)

    def test_invalid_day_is_skipped(self):
        # April has 30 days, so "31" must be ignored without failing.
        r = _parse("from 01.04.2025 to 30.04.2025\n"
                   "31 MO Time Postings : At work 08:00 16:00 8,00\n"
                   "30 WE Time Postings : At work 08:00 16:00 8,00")
        assert [s['date'] for s in r['sessions']] == ['2025-04-30']

    def test_invalid_day_continuation_is_skipped(self):
        r = _parse("from 01.04.2025 to 30.04.2025\n"
                   "31 MO Time Postings : At work 08:00 12:00 4,00\n"
                   "Time Postings : Remote Work 13:00 17:00 4,00")
        assert r['sessions'] == []

    def test_continuation_without_day_is_ignored(self):
        r = _parse("from 01.07.2025 to 31.07.2025\n"
                   "Time Postings : Remote Work 13:00 17:00 4,00")
        assert r['sessions'] == []

    def test_empty_text_gives_success_without_sessions(self):
        r = _parse("")
        assert r['success'] is True
        assert r['sessions'] == []
        assert r['structure']['total_sessions'] == 0

    def test_parse_error_is_reported(self):
        fake = MagicMock()
        fake.open.side_effect = RuntimeError('corrupt pdf')
        with patch.object(pdf_module, 'pdfplumber', fake, create=True):
            r = PDFService()._parse_sap_timestatement('/tmp/bad.pdf')
        assert r['success'] is False
        assert 'corrupt pdf' in r['message']
        assert r['sessions'] == []


# ── analyze_pdf routing ───────────────────────────────────────────────

class TestAnalyzeRouting:
    def test_local_result_is_used_when_sessions_found(self, svc):
        local = {'success': True, 'sessions': [{'date': '2025-07-01'}], 'message': 'ok'}
        with patch.object(svc, '_parse_sap_timestatement', return_value=local), \
             patch.object(svc, '_analyze_with_gemini') as gemini:
            assert svc.analyze_pdf('x.pdf') is local
        gemini.assert_not_called()

    def test_gemini_used_when_local_finds_nothing(self, svc):
        svc.model = MagicMock()
        empty = {'success': True, 'sessions': [], 'message': ''}
        remote = {'success': True, 'sessions': [{'date': '2025-07-01'}], 'message': 'g'}
        with patch.object(svc, '_parse_sap_timestatement', return_value=empty), \
             patch.object(svc, '_analyze_with_gemini', return_value=remote) as gemini:
            assert svc.analyze_pdf('x.pdf') is remote
        gemini.assert_called_once_with('x.pdf')

    def test_nothing_found_and_no_gemini(self, svc):
        empty = {'success': True, 'sessions': [], 'message': ''}
        with patch.object(svc, '_parse_sap_timestatement', return_value=empty):
            r = svc.analyze_pdf('x.pdf')
        assert r['success'] is False
        assert 'Could not extract' in r['message']

    def test_no_parser_available_at_all(self, svc):
        with patch.object(pdf_module, 'PDFPLUMBER_AVAILABLE', False):
            r = svc.analyze_pdf('x.pdf')
        assert r['success'] is False
        assert 'No PDF parsing method available' in r['message']

    def test_gemini_only_when_pdfplumber_missing(self, svc):
        svc.model = MagicMock()
        remote = {'success': True, 'sessions': [], 'message': 'g'}
        with patch.object(pdf_module, 'PDFPLUMBER_AVAILABLE', False), \
             patch.object(svc, '_analyze_with_gemini', return_value=remote):
            assert svc.analyze_pdf('x.pdf') is remote


# ── Gemini ────────────────────────────────────────────────────────────

class TestGemini:
    def _with_response(self, svc, text):
        svc.model = MagicMock()
        svc.model.generate_content.return_value = MagicMock(text=text)
        with patch.object(pdf_module, 'genai', MagicMock(), create=True):
            return svc._analyze_with_gemini('x.pdf')

    def test_not_configured(self, svc):
        r = svc._analyze_with_gemini('x.pdf')
        assert r['success'] is False
        assert 'not configured' in r['message']

    def test_plain_json(self, svc):
        payload = {'sessions': [{'date': '2025-07-01', 'start_time': '08:00',
                                 'end_time': '16:00', 'is_remote': True}]}
        r = self._with_response(svc, json.dumps(payload))
        assert r['success'] is True
        assert r['sessions'] == payload['sessions']
        assert r['structure'] == {'method': 'gemini'}

    def test_json_in_markdown_fence(self, svc):
        r = self._with_response(svc, '```json\n{"sessions": [{"date": "2025-07-01"}]}\n```')
        assert r['success'] is True
        assert len(r['sessions']) == 1

    def test_json_in_plain_fence(self, svc):
        r = self._with_response(svc, '```\n{"sessions": []}\n```')
        assert r['success'] is True
        assert r['sessions'] == []

    def test_invalid_json(self, svc):
        r = self._with_response(svc, 'this is not json')
        assert r['success'] is False
        assert 'Gemini' in r['message']

    def test_api_error(self, svc):
        svc.model = MagicMock()
        svc.model.generate_content.side_effect = RuntimeError('quota exceeded')
        with patch.object(pdf_module, 'genai', MagicMock(), create=True):
            r = svc._analyze_with_gemini('x.pdf')
        assert r['success'] is False
        assert 'quota exceeded' in r['message']


# ── Construction ──────────────────────────────────────────────────────

class TestConstruction:
    def test_model_created_when_api_key_is_set(self):
        genai = MagicMock()
        with patch.object(pdf_module, 'GEMINI_AVAILABLE', True), \
             patch.object(pdf_module, 'genai', genai, create=True), \
             patch.object(pdf_module.Config, 'GOOGLE_API_KEY', 'test-key'):
            service = PDFService()
        genai.configure.assert_called_once_with(api_key='test-key')
        assert service.model is genai.GenerativeModel.return_value

    def test_no_model_without_api_key(self):
        with patch.object(pdf_module.Config, 'GOOGLE_API_KEY', None):
            assert PDFService().model is None
