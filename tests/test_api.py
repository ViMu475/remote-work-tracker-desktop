"""Tests for all API endpoints in routes/api.py."""
import json
import io
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
EXISTING_ENTRY_ID = "1709300000000"       # 2026-03-02 08:00-16:30
EXISTING_ENTRY_ID_2 = "1709300000001"     # 2026-03-03 09:00-17:30
VALID_DATE = "2026-03-04"                 # Wednesday – no existing entries
WEEKEND_DATE = "2026-03-07"              # Saturday
SUNDAY_DATE = "2026-03-08"               # Sunday
HOLIDAY_DATE = "2026-01-06"              # Heilige Drei Könige (Bayern)


# ===================================================================
# GET /api/state
# ===================================================================
class TestGetState:
    def test_returns_state(self, client):
        resp = client.get("/api/state")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "daily_records" in data
        assert "current_month_data" in data
        assert data["aktueller_monat"] == "März"


# ===================================================================
# POST /api/protokoll
# ===================================================================
class TestProtokoll:
    def test_add_entry_happy_path(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "16:30",
            "pause": 30,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert VALID_DATE in data["state"]["daily_records"]

    def test_add_entry_defaults_remote_to_total(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "12:00",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        records = data["state"]["daily_records"][VALID_DATE]
        entry = records[-1]
        assert entry["remoteStundenHeute"] == entry["totalStundenHeute"]

    def test_missing_fields(self, client):
        resp = client.post("/api/protokoll", json={"datum": VALID_DATE})
        assert resp.status_code == 400

    def test_invalid_pause(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "16:00",
            "pause": "abc",
        })
        assert resp.status_code == 400

    def test_weekend_rejected(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": WEEKEND_DATE,
            "start": "08:00",
            "end": "16:00",
        })
        assert resp.status_code == 400

    def test_sunday_rejected(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": SUNDAY_DATE,
            "start": "08:00",
            "end": "16:00",
        })
        assert resp.status_code == 400

    def test_overlap_rejected(self, client):
        # 2026-03-02 already has 08:00-16:30
        resp = client.post("/api/protokoll", json={
            "datum": "2026-03-02",
            "start": "10:00",
            "end": "14:00",
        })
        assert resp.status_code == 400
        assert "overlap" in resp.get_json()["message"].lower() or "überlappung" in resp.get_json()["message"].lower()

    def test_negative_net_hours(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "09:00",
            "pause": 120,  # 2h pause on 1h gross => negative
        })
        assert resp.status_code == 400

    def test_remote_exceeds_total(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "12:00",
            "pause": 0,
            "remote": 99,
        })
        assert resp.status_code == 400


# ===================================================================
# PUT /api/update/<entry_id>
# ===================================================================
class TestUpdateEntry:
    def test_update_happy_path(self, client):
        resp = client.put(f"/api/update/{EXISTING_ENTRY_ID}", json={
            "datum": "2026-03-02",
            "start": "07:00",
            "end": "15:30",
            "pause": 30,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_update_not_found(self, client):
        resp = client.put("/api/update/nonexistent", json={
            "datum": VALID_DATE,
            "start": "08:00",
            "end": "16:00",
        })
        assert resp.status_code == 404

    def test_update_missing_fields(self, client):
        resp = client.put(f"/api/update/{EXISTING_ENTRY_ID}", json={
            "datum": "2026-03-02",
        })
        assert resp.status_code == 400


# ===================================================================
# DELETE /api/delete/<entry_id>
# ===================================================================
class TestDeleteEntry:
    def test_delete_happy_path(self, client):
        resp = client.delete(f"/api/delete/{EXISTING_ENTRY_ID}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        # Entry should be gone
        assert "2026-03-02" not in data["state"]["daily_records"]

    def test_delete_not_found(self, client):
        resp = client.delete("/api/delete/nonexistent_id")
        assert resp.status_code == 404


# ===================================================================
# POST /api/quote
# ===================================================================
class TestQuote:
    def test_set_quote_happy_path(self, client):
        resp = client.post("/api/quote", json={"quote": 50.0})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["individuelle_quote_prozent"] == 50.0

    def test_quote_below_minimum(self, client):
        resp = client.post("/api/quote", json={"quote": 30.0})
        assert resp.status_code == 400

    def test_quote_above_maximum(self, client):
        resp = client.post("/api/quote", json={"quote": 70.0})
        assert resp.status_code == 400

    def test_quote_missing_key(self, client):
        resp = client.post("/api/quote", json={"value": 50.0})
        assert resp.status_code == 400

    def test_quote_invalid_value(self, client):
        resp = client.post("/api/quote", json={"quote": "abc"})
        assert resp.status_code == 400


# ===================================================================
# POST /api/sollstunden
# ===================================================================
class TestSollstunden:
    def test_set_sollstunden_happy_path(self, client):
        resp = client.post("/api/sollstunden", json={"sollStunden": 7.5})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["soll_stunden_pro_tag"] == 7.5

    def test_sollstunden_below_minimum(self, client):
        resp = client.post("/api/sollstunden", json={"sollStunden": 0.5})
        assert resp.status_code == 400

    def test_sollstunden_above_maximum(self, client):
        resp = client.post("/api/sollstunden", json={"sollStunden": 11.0})
        assert resp.status_code == 400

    def test_sollstunden_missing_key(self, client):
        resp = client.post("/api/sollstunden", json={"stunden": 8.0})
        assert resp.status_code == 400

    def test_sollstunden_invalid_value(self, client):
        resp = client.post("/api/sollstunden", json={"sollStunden": "xyz"})
        assert resp.status_code == 400


# ===================================================================
# POST /api/darkmode
# ===================================================================
class TestDarkmode:
    def test_enable_darkmode(self, client):
        resp = client.post("/api/darkmode", json={"darkMode": True})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["state"]["dark_mode"] is True

    def test_disable_darkmode(self, client):
        resp = client.post("/api/darkmode", json={"darkMode": False})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["state"]["dark_mode"] is False


# ===================================================================
# POST /api/language
# ===================================================================
class TestLanguage:
    def test_set_german(self, client):
        resp = client.post("/api/language", json={"language": "de"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["state"]["language"] == "de"

    def test_set_english(self, client):
        resp = client.post("/api/language", json={"language": "en"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["state"]["language"] == "en"

    def test_unsupported_language(self, client):
        resp = client.post("/api/language", json={"language": "fr"})
        assert resp.status_code == 400


# ===================================================================
# POST /api/month/switch
# ===================================================================
class TestMonthSwitch:
    def test_switch_month(self, client):
        resp = client.post("/api/month/switch")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        # März -> April
        assert data["state"]["view_month"] == "April"
        assert data["state"]["view_year"] == 2026
        # History should now have one entry
        assert len(data["state"]["monatliche_historie"]) == 1


# ===================================================================
# POST /api/view/current_month
# ===================================================================
class TestViewCurrentMonth:
    def test_set_view_to_current(self, client):
        resp = client.post("/api/view/current_month")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["view_month"] == data["state"]["aktueller_monat"]
        assert data["state"]["view_year"] == data["state"]["aktuelles_jahr"]


# ===================================================================
# GET /api/export/daily_csv
# ===================================================================
class TestExportCSV:
    def test_csv_export(self, client):
        resp = client.get("/api/export/daily_csv")
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/csv")
        text = resp.data.decode("utf-8-sig")
        lines = text.strip().split("\n")
        # Header + 2 entries for März 2026
        assert len(lines) >= 3
        assert "datum" in lines[0]

    def test_csv_has_correct_records(self, client):
        resp = client.get("/api/export/daily_csv")
        text = resp.data.decode("utf-8-sig")
        assert "2026-03-02" in text
        assert "2026-03-03" in text


# ===================================================================
# GET /api/report/monthly_pdf
# ===================================================================
class TestMonthlyPDF:
    def test_pdf_report_current_month(self, client):
        resp = client.get("/api/report/monthly_pdf?year=2026&month=März")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"
        assert resp.data[:4] == b"%PDF"

    def test_pdf_report_not_found(self, client):
        resp = client.get("/api/report/monthly_pdf?year=2020&month=Januar")
        assert resp.status_code == 404


# ===================================================================
# GET /api/backup
# ===================================================================
class TestBackup:
    def test_backup_returns_json(self, client):
        resp = client.get("/api/backup")
        assert resp.status_code == 200
        assert "application/json" in resp.content_type
        data = json.loads(resp.data)
        assert "daily_records" in data
        assert "individuelle_quote_prozent" in data


# ===================================================================
# POST /api/restore
# ===================================================================
class TestRestore:
    def test_restore_from_json_body(self, client):
        # First get a backup
        backup_resp = client.get("/api/backup")
        backup_data = json.loads(backup_resp.data)
        backup_data["individuelle_quote_prozent"] = 55.0

        resp = client.post("/api/restore",
                           data=json.dumps(backup_data),
                           content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["individuelle_quote_prozent"] == 55.0

    def test_restore_from_file_upload(self, client):
        backup_resp = client.get("/api/backup")
        backup_data = json.loads(backup_resp.data)

        data_bytes = json.dumps(backup_data).encode("utf-8")
        resp = client.post("/api/restore",
                           data={"file": (io.BytesIO(data_bytes), "backup.json")},
                           content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_restore_invalid_json(self, client):
        resp = client.post("/api/restore",
                           data="not json at all",
                           content_type="application/json")
        assert resp.status_code == 400

    def test_restore_missing_keys(self, client):
        resp = client.post("/api/restore",
                           data=json.dumps({"foo": "bar"}),
                           content_type="application/json")
        assert resp.status_code == 400


# ===================================================================
# POST /api/delete_all_entries
# ===================================================================
class TestDeleteAllEntries:
    def test_delete_all_entries(self, client):
        resp = client.post("/api/delete_all_entries")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["daily_records"] == {}


# ===================================================================
# DELETE /api/delete_month/<month_name>/<year>
# ===================================================================
class TestDeleteMonth:
    def test_delete_month_not_found(self, client):
        # No history in test state, so any month is 404
        resp = client.delete("/api/delete_month/Januar/2026")
        assert resp.status_code == 404

    def test_delete_month_from_history(self, client):
        # First close the month to create history
        client.post("/api/month/switch")
        # Now delete März 2026 from history
        resp = client.delete("/api/delete_month/März/2026")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        # Should be empty again
        assert len(data["state"]["monatliche_historie"]) == 0


# ===================================================================
# POST /api/clear_all_history
# ===================================================================
class TestClearAllHistory:
    def test_clear_all_history(self, client):
        resp = client.post("/api/clear_all_history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["state"]["monatliche_historie"] == []
        assert data["state"]["daily_records"] == {}
        assert data["state"]["individuelle_quote_prozent"] == 40.0


# ===================================================================
# POST /api/pdf/analyze
# ===================================================================
class TestPDFAnalyze:
    def test_no_file(self, client):
        resp = client.post("/api/pdf/analyze")
        assert resp.status_code == 400

    def test_empty_filename(self, client):
        resp = client.post("/api/pdf/analyze",
                           data={"file": (io.BytesIO(b""), "")},
                           content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_non_pdf_file(self, client):
        resp = client.post("/api/pdf/analyze",
                           data={"file": (io.BytesIO(b"hello"), "test.txt")},
                           content_type="multipart/form-data")
        assert resp.status_code == 400


# ===================================================================
# POST /api/pdf/import
# ===================================================================
class TestPDFImport:
    def test_import_sessions(self, client):
        # Use a past date that is a weekday in March 2026
        resp = client.post("/api/pdf/import", json={
            "sessions": [
                {
                    "date": "2026-03-05",
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "is_remote": True,
                    "type": "work",
                },
            ]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["imported_count"] == 1

    def test_import_empty_sessions(self, client):
        resp = client.post("/api/pdf/import", json={"sessions": []})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["imported_count"] == 0

    def test_import_invalid_session_skipped(self, client):
        resp = client.post("/api/pdf/import", json={
            "sessions": [
                {"date": "", "start_time": "", "end_time": ""},
            ]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["imported_count"] == 0
        assert len(data["errors"]) > 0


# ===================================================================
# POST /api/shutdown
# ===================================================================
class TestShutdown:
    def test_shutdown_returns_success(self, client):
        import routes.api as api_module
        with patch('threading.Thread') as mock_thread, \
             patch('os._exit'):
            resp = client.post('/api/shutdown',
                               headers={'X-RW-Token': api_module.SHUTDOWN_TOKEN})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['success'] is True
            assert 'heruntergefahren' in data['message']
