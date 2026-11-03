"""Tests for PDFService: SAP parsing (local) and mocked Gemini fallback."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

def _get_pdf_service():
    """Import and instantiate PDFService inside function to avoid
    module-level import errors if google.generativeai is not configured."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from services.pdf_service import PDFService
    return PDFService()


def _make_statement_pdf(tmp_path, name, lines):
    """Writes a small PDF with FICTIONAL content (no real person, no real hours).

    The tests used to read real SAP statements; those contain personal data and are not part of
    the repository, so the layout the parser expects is generated here instead.
    """
    from reportlab.pdfgen import canvas
    path = tmp_path / name
    c = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
    c.save()
    return str(path)


ENGLISH = ["TimeStatement", "from 01.07.2031 to 31.07.2031",
           "01 TU  Time Postings : At work  07:30  16:00  8,00",
           "02 WE  Time Postings : Remote Work  08:00  16:30  8,00",
           "03 TH  Time Postings : Remote Work  08:15  12:15  4,00",
           "Time Postings : At work  13:00  17:00  4,00"]
GERMAN = ["Zeitnachweis", "vom 01.10.2031 bis 31.10.2031",
          "01 MI  Zeitbuchungen : Anwesend  07:45  16:15  8,00",
          "02 DO  Zeitbuchungen : Remote Work  08:00  16:30  8,00"]


# ── 1. English TimeStatement ──────────────────────────────────────────

class TestEnglishTimeStatement:
    def test_parse_english_pdf(self, tmp_path):
        pdf_path = _make_statement_pdf(tmp_path, 'TimeStatement_20310701_20310731.pdf', ENGLISH)
        result = _get_pdf_service()._parse_sap_timestatement(pdf_path)

        assert result['success'] is True
        got = [(s['date'], s['start_time'], s['end_time'], s['is_remote']) for s in result['sessions']]
        assert got == [('2031-07-01', '07:30', '16:00', False),
                       ('2031-07-02', '08:00', '16:30', True),
                       ('2031-07-03', '08:15', '12:15', True),
                       ('2031-07-03', '13:00', '17:00', False)]
        for session in result['sessions']:
            assert set(session) >= {'date', 'start_time', 'end_time', 'is_remote'}


# ── 2. German Zeitnachweis ────────────────────────────────────────────

class TestGermanZeitnachweis:
    def test_parse_german_pdf(self, tmp_path):
        pdf_path = _make_statement_pdf(tmp_path, 'Zeitnachweis_20311001_20311031.pdf', GERMAN)
        result = _get_pdf_service()._parse_sap_timestatement(pdf_path)

        assert result['success'] is True
        got = [(s['date'], s['start_time'], s['end_time'], s['is_remote']) for s in result['sessions']]
        assert got == [('2031-10-01', '07:45', '16:15', False), ('2031-10-02', '08:00', '16:30', True)]


# ── 3. Month taken from the file name when the text has no header ─────

class TestMonthFromFileName:
    def test_parse_without_header_uses_the_file_name(self, tmp_path):
        pdf_path = _make_statement_pdf(tmp_path, 'Zeitnachweis_20311201_20311231.pdf',
                                       ["Zeitnachweis", "01 MO  Zeitbuchungen : Anwesend  08:00  16:30  8,00"])
        result = _get_pdf_service()._parse_sap_timestatement(pdf_path)

        assert result['success'] is True
        assert result['sessions'][0]['date'] == '2031-12-01'


# ── 4. Remote keyword detection ───────────────────────────────────────

class TestRemoteDetection:
    def test_sessions_include_remote_and_office(self, tmp_path):
        pdf_path = _make_statement_pdf(tmp_path, 'TimeStatement_20310701_20310731.pdf', ENGLISH)
        result = _get_pdf_service()._parse_sap_timestatement(pdf_path)

        assert result['success'] is True
        remote_flags = {s['is_remote'] for s in result['sessions']}
        assert True in remote_flags, "Expected at least one remote session"
        assert False in remote_flags, "Expected at least one office session"


# ── 5. Nonexistent PDF ───────────────────────────────────────────────

class TestNonexistentPDF:
    def test_nonexistent_pdf_returns_failure(self):
        svc = _get_pdf_service()
        result = svc._parse_sap_timestatement('/tmp/does_not_exist_12345.pdf')

        assert result['success'] is False


# ── 6. Gemini fallback (mocked) ──────────────────────────────────────

class TestGeminiFallback:
    @patch('services.pdf_service.genai', new_callable=MagicMock)
    def test_gemini_fallback_when_local_finds_nothing(self, mock_genai):
        """When _parse_sap_timestatement returns no sessions, analyze_pdf
        should fall back to Gemini (mocked)."""
        svc = _get_pdf_service()

        # Force Gemini to be "available" by assigning a mock model
        mock_model = MagicMock()
        svc.model = mock_model

        fake_response = MagicMock()
        fake_response.text = json.dumps({
            "sessions": [
                {"date": "2025-07-01", "start_time": "08:00",
                 "end_time": "17:00", "is_remote": True}
            ]
        })
        mock_model.generate_content.return_value = fake_response
        mock_genai.upload_file.return_value = MagicMock()

        # Patch local parser to return no sessions
        with patch.object(svc, '_parse_sap_timestatement', return_value={
            'success': True, 'message': '', 'sessions': []
        }):
            result = svc.analyze_pdf('/tmp/dummy.pdf')

        assert result['success'] is True
        assert len(result['sessions']) == 1
        assert result['sessions'][0]['is_remote'] is True


# ── 7. Gemini markdown code block cleanup ─────────────────────────────

class TestGeminiMarkdownCleanup:
    @patch('services.pdf_service.genai', new_callable=MagicMock)
    def test_markdown_code_blocks_stripped(self, mock_genai):
        """Gemini sometimes wraps JSON in ```json ... ``` blocks."""
        svc = _get_pdf_service()

        mock_model = MagicMock()
        svc.model = mock_model

        raw_json = json.dumps({
            "sessions": [
                {"date": "2025-12-01", "start_time": "09:00",
                 "end_time": "18:00", "is_remote": False}
            ]
        })
        fake_response = MagicMock()
        fake_response.text = f"```json\n{raw_json}\n```"
        mock_model.generate_content.return_value = fake_response
        mock_genai.upload_file.return_value = MagicMock()

        # Go directly through Gemini path
        result = svc._analyze_with_gemini('/tmp/dummy.pdf')

        assert result['success'] is True
        assert len(result['sessions']) == 1
        assert result['sessions'][0]['date'] == '2025-12-01'
        assert result['structure']['method'] == 'gemini'


# ── 5. Day lines without a booking must not swallow the next day's continuation line ──

class TestDayWithoutOwnBooking:
    def test_continuation_after_flextime_compensation_belongs_to_that_day(self, tmp_path):
        lines = ["Zeitnachweis", "vom 01.10.2031 bis 31.10.2031",
                 "14 DI  Zeitbuchungen : Remote Work  08:00  17:00  9,00",
                 "15 MI  Gleitzeitausgleich  08:00  12:00  4,00",
                 "Zeitbuchungen : Remote Work  12:00  17:00  5,00"]
        pdf_path = _make_statement_pdf(tmp_path, 'Zeitnachweis_20311001_20311031.pdf', lines)
        got = [(s['date'], s['start_time'], s['end_time']) for s in _get_pdf_service()._parse_sap_timestatement(pdf_path)['sessions']]
        assert got == [('2031-10-14', '08:00', '17:00'), ('2031-10-15', '12:00', '17:00')]

    def test_continuation_after_a_holiday_line_is_not_attached_to_the_day_before(self, tmp_path):
        lines = ["Zeitnachweis", "vom 01.10.2031 bis 31.10.2031",
                 "02 MI  Zeitbuchungen : Remote Work  08:00  16:00  8,00",
                 "03 DO  Tag der Deutschen Einheit",
                 "Zeitbuchungen : Remote Work  09:00  10:00  1,00"]
        pdf_path = _make_statement_pdf(tmp_path, 'Zeitnachweis_20311001_20311031.pdf', lines)
        got = [(s['date'], s['start_time']) for s in _get_pdf_service()._parse_sap_timestatement(pdf_path)['sessions']]
        assert ('2031-10-02', '09:00') not in got
