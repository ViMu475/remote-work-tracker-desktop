"""Parser additions for the batch import: how reliable the period is, the end of the header range, no AI upload."""
from unittest.mock import MagicMock, patch

import pytest

import services.pdf_service as pdf_module
from services.pdf_service import PDFService

from .test_pdf_service_extra import _parse

LINE = "02 MO Time Postings : At work 08:00 16:30 8,50"


class TestPeriodSource:
    def test_english_date_range(self):
        r = _parse("Time statement from 01.11.2025 to 30.11.2025\n" + LINE)
        assert r['structure']['period_source'] == 'header' and r['structure']['period_end'] == '2025-11-30'

    def test_german_date_range(self):
        r = _parse("Zeitnachweis vom 01.11.2025 bis 30.11.2025\n02 MO Zeitbuchungen : Anwesend 08:00 16:30 8,50")
        assert r['structure']['period_source'] == 'header' and r['structure']['period_end'] == '2025-11-30'

    def test_a_range_over_two_months_shows_its_end(self):
        r = _parse("from 15.11.2025 to 14.12.2025\n" + LINE)
        assert (r['structure']['month'], r['structure']['period_end']) == (11, '2025-12-14')

    @pytest.mark.parametrize('header', ['Month: July - 2025', 'Monat: Juli - 2025'])
    def test_month_header(self, header):
        r = _parse(header + "\n" + LINE.replace('MO', 'TU'))
        assert (r['structure']['year'], r['structure']['month']) == (2025, 7)
        assert r['structure']['period_source'] == 'header' and r['structure']['period_end'] is None

    @pytest.mark.parametrize('header', ['Month: Smarch - 2025', 'Monat: Foobar - 2025'])
    def test_unknown_month_name_is_marked_as_not_trustworthy(self, header):
        r = _parse(header + "\n" + LINE)
        assert r['structure']['month'] == 1                      # unchanged behaviour of the single import
        assert r['structure']['period_source'] == 'unrecognized'

    def test_period_from_the_file_name(self):
        r = _parse(LINE, path='/x/TimeStatement_20310701_20310731.pdf')
        assert r['structure']['period_source'] == 'filename' and r['structure']['month'] == 7

    def test_a_number_in_the_file_name_that_is_no_month_is_not_used(self):
        r = _parse(LINE, path='/x/scan_20251399.pdf')
        assert r['structure']['period_source'] == 'fallback_now'

    def test_nothing_in_the_document_is_marked_as_a_guess(self):
        r = _parse(LINE, path='/x/report.pdf')
        assert r['structure']['period_source'] == 'fallback_now'
        assert (r['structure']['year'], r['structure']['month']) == (2026, 3)     # frozen system date


class TestNoAiUpload:
    def fake_service(self, text):
        service = PDFService()
        service.model = MagicMock()                                 # as if a Google API key were configured
        return service

    def test_ai_is_used_by_default_when_the_local_parser_finds_nothing(self):
        service = self.fake_service('nothing useful')
        with patch.object(pdf_module, 'pdfplumber', None, create=True), \
                patch.object(pdf_module, 'PDFPLUMBER_AVAILABLE', False), \
                patch.object(service, '_analyze_with_gemini', return_value={'success': True, 'sessions': []}) as gemini:
            service.analyze_pdf('/x/a.pdf')
        gemini.assert_called_once()

    def test_ai_is_never_used_when_it_is_switched_off(self):
        service = self.fake_service('nothing useful')
        with patch.object(pdf_module, 'PDFPLUMBER_AVAILABLE', False), \
                patch.object(service, '_analyze_with_gemini') as gemini:
            result = service.analyze_pdf('/x/a.pdf', allow_ai=False)
        gemini.assert_not_called()
        assert result['success'] is False and result['sessions'] == []

    def test_local_parsing_that_finds_no_sessions_does_not_fall_back_to_ai_when_it_is_off(self):
        service = self.fake_service('no bookings in here')
        fake_plumber = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = 'no bookings in here'
        pdf = MagicMock()
        pdf.pages = [page]
        pdf.__enter__.return_value = pdf
        pdf.__exit__.return_value = False
        fake_plumber.open.return_value = pdf
        with patch.object(pdf_module, 'PDFPLUMBER_AVAILABLE', True), \
                patch.object(pdf_module, 'pdfplumber', fake_plumber, create=True), \
                patch.object(service, '_analyze_with_gemini') as gemini:
            result = service.analyze_pdf('/x/a.pdf', allow_ai=False)
        gemini.assert_not_called()
        assert result['success'] is False
