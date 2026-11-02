"""Tests for services/report_service.py"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.report_service import ReportService


def _make_month_data(**overrides):
    data = {
        "monat": "Januar",
        "jahr": 2026,
        "soll_stunden_gesamt": 168.0,
        "ist_arbeitszeit_laufend": 80.0,
        "ist_remote_stunden_laufend": 32.0,
        "max_remote_stunden": 67.2,
        "individuelle_quote": 40,
    }
    data.update(overrides)
    return data


def _make_day_record(day=1, **overrides):
    rec = {
        "datum": f"2026-01-{day:02d}",
        "startTime": "08:00",
        "endTime": "16:30",
        "pauseMinutes": 30,
        "remoteStundenHeute": 4.0,
        "totalStundenHeute": 8.0,
    }
    rec.update(overrides)
    return rec


class TestReportService:
    def setup_method(self):
        self.svc = ReportService()

    def test_generates_valid_pdf_bytes(self):
        """Normal month data + 2 records -> returns bytes starting with %PDF."""
        month = _make_month_data()
        records = [_make_day_record(day=5), _make_day_record(day=6)]

        result = self.svc.generate_monthly_pdf(month, records)

        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        assert len(result) > 0

    def test_empty_records(self):
        """Month data + empty list -> still generates valid PDF."""
        month = _make_month_data()

        result = self.svc.generate_monthly_pdf(month, [])

        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_many_records_pagination(self):
        """22 records -> generates larger PDF (pagination works)."""
        month = _make_month_data()
        records = [_make_day_record(day=d) for d in range(1, 23)]

        result_many = self.svc.generate_monthly_pdf(month, records)
        result_few = self.svc.generate_monthly_pdf(month, [_make_day_record()])

        assert isinstance(result_many, bytes)
        assert result_many[:5] == b"%PDF-"
        assert len(result_many) > len(result_few)
