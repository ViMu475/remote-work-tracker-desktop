"""Additional API tests for routes/api.py: validation errors, month/quarter
switching, historical reports, restore failures, PDF upload/import, shutdown.

The date is frozen to 2026-03-15 by conftest.py; the sample state contains two
entries (2026-03-02 and 2026-03-03).
"""
import copy
import io
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import routes.api as api_module

EXISTING_ENTRY_ID = "1709300000000"   # 2026-03-02 08:00-16:30
EXISTING_ENTRY_ID_2 = "1709300000001"  # 2026-03-03 09:00-17:30
VALID_DATE = "2026-03-04"             # Wednesday, no entries
SUNDAY_DATE = "2026-03-08"


def _put(client, entry_id=EXISTING_ENTRY_ID, **overrides):
    body = {"datum": "2026-03-02", "start": "08:00", "end": "16:30", "pause": 30}
    body.update(overrides)
    return client.put(f"/api/update/{entry_id}", json=body)


def _restore(client, state):
    resp = client.post("/api/restore", data=json.dumps(state),
                       content_type="application/json")
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["state"]


def _history_month(monat, jahr, quartal, ist_remote, soll=160.0, quote=40.0):
    return {
        "monat": monat, "jahr": jahr, "quartal": quartal,
        "soll_stunden_gesamt": soll,
        "ist_remote_stunden_laufend": ist_remote,
        "ist_arbeitszeit_laufend": ist_remote,
        "max_remote_stunden": soll * quote / 100,
        "individuelle_quote": quote,
        "tatsaechliche_remote_quote": ist_remote / soll * 100,
    }


def _december_state(sample_state, ist_remote_history):
    """State where December 2026 is the open month and Q4 has two closed months."""
    state = copy.deepcopy(sample_state)
    state.update({
        "aktueller_monat": "Dezember", "aktuelles_jahr": 2026,
        "view_month": "Dezember", "view_year": 2026,
        "current_quartal": "Q4/2026", "daily_records": {},
        "current_month_data": {
            "monat": "Dezember", "jahr": 2026, "soll_stunden_gesamt": 160.0,
            "ist_remote_stunden_laufend": 0.0, "ist_arbeitszeit_laufend": 0.0,
            "max_remote_stunden": 64.0, "individuelle_quote": 40.0,
        },
        "monatliche_historie": [
            _history_month("Oktober", 2026, "Q4/2026", ist_remote_history),
            _history_month("November", 2026, "Q4/2026", ist_remote_history),
        ],
    })
    return state


# ── POST /api/protokoll ───────────────────────────────────────────────

class TestProtokollEdgeCases:
    def test_negative_net_hours_rejected(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE, "start": "08:00", "end": "08:30", "pause": 60})
        assert resp.status_code == 400
        assert "Zeitangabe" in resp.get_json()["message"]

    def test_invalid_remote_value_rejected(self, client):
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE, "start": "08:00", "end": "16:00",
            "pause": 30, "remote": "abc"})
        assert resp.status_code == 400
        assert "Remote" in resp.get_json()["message"]

    def test_english_message_contains_pause_warning(self, client):
        client.post("/api/language", json={"language": "en"})
        resp = client.post("/api/protokoll", json={
            "datum": VALID_DATE, "start": "08:00", "end": "16:00", "pause": 0})
        assert resp.status_code == 200
        message = resp.get_json()["message"]
        assert message.startswith(f"Log for {VALID_DATE} saved")
        assert " | " in message  # a 30-minute pause is required for 6h+


# ── PUT /api/update/<id> ──────────────────────────────────────────────

class TestUpdateEdgeCases:
    def test_missing_fields(self, client):
        resp = client.put(f"/api/update/{EXISTING_ENTRY_ID}", json={"datum": "2026-03-02"})
        assert resp.status_code == 400

    def test_invalid_pause(self, client):
        assert _put(client, pause="abc").status_code == 400

    def test_weekend_rejected(self, client):
        resp = _put(client, datum="2026-03-07")
        assert resp.status_code == 400

    def test_overlap_with_other_entry_rejected(self, client):
        # Entry 2 occupies 2026-03-03 09:00-17:30
        resp = _put(client, datum="2026-03-03", start="10:00", end="12:00")
        assert resp.status_code == 400

    def test_negative_net_hours_rejected(self, client):
        resp = _put(client, start="08:00", end="08:30", pause=60)
        assert resp.status_code == 400
        assert "Zeitangabe" in resp.get_json()["message"]

    def test_invalid_remote_rejected(self, client):
        assert _put(client, remote="abc").status_code == 400

    def test_remote_greater_than_net_rejected(self, client):
        resp = _put(client, remote=12)
        assert resp.status_code == 400
        assert "Remote-Stunden" in resp.get_json()["message"]

    def test_update_moves_entry_and_reports_in_english(self, client):
        client.post("/api/language", json={"language": "en"})
        resp = _put(client, datum=VALID_DATE, start="09:00", end="12:00", pause=0)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["message"].startswith(f"Entry updated for {VALID_DATE}")
        records = data["state"]["daily_records"]
        assert VALID_DATE in records
        assert "2026-03-02" not in records  # moved away, old day is now empty


# ── DELETE /api/delete/<id> ───────────────────────────────────────────

class TestDeleteEdgeCases:
    def test_deleting_one_of_two_entries_on_a_day_keeps_the_day(self, client):
        client.post("/api/protokoll", json={
            "datum": "2026-03-02", "start": "17:00", "end": "18:00", "pause": 0})
        resp = client.delete(f"/api/delete/{EXISTING_ENTRY_ID}")
        assert resp.status_code == 200
        remaining = resp.get_json()["state"]["daily_records"]["2026-03-02"]
        assert len(remaining) == 1
        assert remaining[0]["id"] != EXISTING_ENTRY_ID


# ── POST /api/month/switch ────────────────────────────────────────────

class TestMonthSwitchEdgeCases:
    def test_december_rolls_over_to_january_next_year(self, client, sample_state):
        _restore(client, _december_state(sample_state, ist_remote_history=10))
        resp = client.post("/api/month/switch")
        assert resp.status_code == 200
        state = resp.get_json()["state"]
        assert state["aktueller_monat"] == "Januar"
        assert state["aktuelles_jahr"] == 2027
        assert state["view_month"] == "Januar"
        assert state["view_year"] == 2027
        assert state["current_quartal"] == "Q1/2027"
        assert len(state["monatliche_historie"]) == 3

    def test_quarter_end_within_quota_raises_quota(self, client, sample_state):
        _restore(client, _december_state(sample_state, ist_remote_history=10))
        data = client.post("/api/month/switch").get_json()
        assert data["quartal_msg"].startswith("EINGEHALTEN")
        assert data["state"]["individuelle_quote_prozent"] == 50.0

    def test_quarter_end_over_quota_is_critical_and_keeps_minimum(self, client, sample_state):
        _restore(client, _december_state(sample_state, ist_remote_history=150))
        data = client.post("/api/month/switch").get_json()
        assert data["quartal_msg"].startswith("KRITISCH")
        # Quote cannot fall below the 40% minimum.
        assert data["state"]["individuelle_quote_prozent"] == 40.0
        assert "KRITISCH" in data["message"]

    def test_quarter_end_with_incomplete_history_changes_nothing(self, client, sample_state):
        state = _december_state(sample_state, ist_remote_history=10)
        state["monatliche_historie"] = state["monatliche_historie"][:1]
        _restore(client, state)
        data = client.post("/api/month/switch").get_json()
        assert data["quartal_msg"] is None
        assert data["state"]["individuelle_quote_prozent"] == 40.0


# ── GET /api/report/monthly_pdf ───────────────────────────────────────

class TestMonthlyPdfEdgeCases:
    def test_current_month_report(self, client):
        resp = client.get("/api/report/monthly_pdf?year=2026&month=März")
        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"
        assert resp.data.startswith(b"%PDF")
        assert "Monatsbericht_März_2026.pdf" in resp.headers["Content-Disposition"]

    def test_report_for_closed_month_from_history(self, client, sample_state):
        state = copy.deepcopy(sample_state)
        state["monatliche_historie"] = [_history_month("Oktober", 2025, "Q4/2025", 20.0)]
        _restore(client, state)
        resp = client.get("/api/report/monthly_pdf?year=2025&month=Oktober")
        assert resp.status_code == 200
        assert resp.data.startswith(b"%PDF")

    def test_generation_failure_returns_500(self, client):
        with patch.object(api_module.report_service, "generate_monthly_pdf",
                          side_effect=RuntimeError("boom")):
            resp = client.get("/api/report/monthly_pdf?year=2026&month=März")
        assert resp.status_code == 500
        assert "boom" in resp.get_json()["message"]


# ── POST /api/restore ─────────────────────────────────────────────────

class TestRestoreEdgeCases:
    def test_save_failure_returns_500(self, client, sample_state):
        with patch.object(api_module.state_service, "save_state", return_value=False):
            resp = client.post("/api/restore", data=json.dumps(sample_state),
                               content_type="application/json")
        assert resp.status_code == 500
        assert "fehlgeschlagen" in resp.get_json()["message"]

    def test_restore_from_uploaded_file(self, client, sample_state):
        resp = client.post("/api/restore", data={
            "file": (io.BytesIO(json.dumps(sample_state).encode()), "backup.json")},
            content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ── POST /api/pdf/analyze ─────────────────────────────────────────────

class TestPdfAnalyzeEdgeCases:
    def test_non_pdf_rejected(self, client):
        resp = client.post("/api/pdf/analyze", data={
            "file": (io.BytesIO(b"hello"), "notes.txt")},
            content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_is_analyzed_and_temp_file_removed(self, client, tmp_path):
        seen = {}

        def fake_analyze(path):
            seen["path"] = path
            with open(path, "rb") as f:
                seen["content"] = f.read()
            return {"success": True, "sessions": [], "message": "ok"}

        with patch.object(api_module.tempfile, "gettempdir", return_value=str(tmp_path)), \
             patch.object(api_module.pdf_service, "analyze_pdf", side_effect=fake_analyze):
            resp = client.post("/api/pdf/analyze", data={
                "file": (io.BytesIO(b"%PDF-1.4 test"), "sheet.pdf")},
                content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "ok"
        assert seen["content"] == b"%PDF-1.4 test"
        assert not (tmp_path / "sheet.pdf").exists()

    def test_analysis_exception_returns_500(self, client, tmp_path):
        with patch.object(api_module.tempfile, "gettempdir", return_value=str(tmp_path)), \
             patch.object(api_module.pdf_service, "analyze_pdf",
                          side_effect=RuntimeError("parser exploded")):
            resp = client.post("/api/pdf/analyze", data={
                "file": (io.BytesIO(b"%PDF"), "sheet.pdf")},
                content_type="multipart/form-data")
        assert resp.status_code == 500
        assert "parser exploded" in resp.get_json()["message"]


class TestPdfUploadFilenameSafety:
    """The client-supplied filename must never decide where the file is written."""

    def _upload(self, client, root, filename, analyze=None):
        seen = {}

        def fake_analyze(path):
            seen["path"] = path
            seen["real"] = os.path.realpath(path)
            seen["exists_during"] = os.path.exists(path)
            if analyze:
                return analyze(path)
            return {"success": True, "sessions": [], "message": "ok"}

        with patch.object(api_module.tempfile, "gettempdir", return_value=str(root)), \
             patch.object(api_module.pdf_service, "analyze_pdf", side_effect=fake_analyze):
            resp = client.post("/api/pdf/analyze", data={
                "file": (io.BytesIO(b"%PDF-1.4"), filename)},
                content_type="multipart/form-data")
        return resp, seen

    @pytest.fixture
    def root(self, tmp_path):
        root = tmp_path / "tmp"
        root.mkdir()
        return root

    @pytest.mark.parametrize("filename", [
        "../escape.pdf",
        "../../escape.pdf",
        "..\\escape.pdf",
        "sub/../../escape.pdf",
    ])
    def test_traversal_names_stay_inside_temp_dir(self, client, root, tmp_path, filename):
        resp, seen = self._upload(client, root, filename)
        assert resp.status_code == 200
        assert seen["exists_during"] is True
        assert seen["real"].startswith(str(root.resolve()) + os.sep)
        assert not (tmp_path / "escape.pdf").exists()

    def test_absolute_path_name_is_not_used(self, client, root, tmp_path):
        target = tmp_path / "outside" / "abs.pdf"
        target.parent.mkdir()
        resp, seen = self._upload(client, root, str(target))
        assert resp.status_code == 200
        assert seen["real"].startswith(str(root.resolve()) + os.sep)
        assert not target.exists()

    def test_saved_name_ends_with_pdf_even_if_sanitizing_strips_it(self, client, root):
        resp, seen = self._upload(client, root, "../.pdf")
        assert resp.status_code == 200
        assert seen["path"].endswith(".pdf")
        assert seen["real"].startswith(str(root.resolve()) + os.sep)

    def test_sanitized_original_name_is_kept_for_date_detection(self, client, root):
        # PDFService falls back to the date range in the file name.
        resp, seen = self._upload(client, root, "TimeStatement_20310701_20310731.pdf")
        assert os.path.basename(seen["path"]) == "TimeStatement_20310701_20310731.pdf"

    def test_temp_files_are_removed_after_success(self, client, root):
        self._upload(client, root, "sheet.pdf")
        assert list(root.iterdir()) == []

    def test_temp_files_are_removed_after_failure(self, client, root):
        def boom(path):
            raise RuntimeError("parser exploded")
        resp, _ = self._upload(client, root, "sheet.pdf", analyze=boom)
        assert resp.status_code == 500
        assert list(root.iterdir()) == []

    def test_same_name_uploads_do_not_share_a_path(self, client, root):
        _, first = self._upload(client, root, "sheet.pdf")
        _, second = self._upload(client, root, "sheet.pdf")
        # Both ran in their own scratch directory (not directly in the temp root).
        assert os.path.dirname(first["real"]) != str(root.resolve())
        assert os.path.dirname(second["real"]) != str(root.resolve())


# ── POST /api/pdf/import ──────────────────────────────────────────────

class TestPdfImportEdgeCases:
    def _import(self, client, sessions):
        resp = client.post("/api/pdf/import", json={"sessions": sessions})
        assert resp.status_code == 200
        return resp.get_json()

    def test_valid_sessions_are_imported_and_view_is_switched(self, client):
        data = self._import(client, [
            {"date": VALID_DATE, "start_time": "08:00", "end_time": "12:00", "is_remote": True},
            {"date": VALID_DATE, "start_time": "13:00", "end_time": "17:00", "is_remote": False},
        ])
        assert data["imported_count"] == 2
        assert data["errors"] == []
        assert data["message"] == "2 Sessions importiert"
        entries = data["state"]["daily_records"][VALID_DATE]
        assert [e["remoteStundenHeute"] for e in entries] == [4.0, 0]
        assert data["state"]["view_month"] == "März"
        assert data["state"]["view_year"] == 2026

    def test_incomplete_session_is_reported(self, client):
        data = self._import(client, [{"date": VALID_DATE, "start_time": "08:00"}])
        assert data["imported_count"] == 0
        assert "Ungültige Session" in data["errors"][0]

    def test_sunday_is_rejected(self, client):
        data = self._import(client, [
            {"date": SUNDAY_DATE, "start_time": "08:00", "end_time": "12:00"}])
        assert data["imported_count"] == 0
        assert data["errors"][0].startswith(SUNDAY_DATE)

    def test_overlapping_session_is_rejected(self, client):
        # 2026-03-02 already has 08:00-16:30
        data = self._import(client, [
            {"date": "2026-03-02", "start_time": "09:00", "end_time": "10:00"}])
        assert data["imported_count"] == 0
        assert data["errors"][0].startswith("2026-03-02")

    def test_partial_import_reports_error_count(self, client):
        data = self._import(client, [
            {"date": VALID_DATE, "start_time": "08:00", "end_time": "12:00"},
            {"date": SUNDAY_DATE, "start_time": "08:00", "end_time": "12:00"},
        ])
        assert data["imported_count"] == 1
        assert data["message"] == "1 Sessions importiert (1 Fehler)"

    def test_unexpected_error_in_session_is_collected(self, client):
        with patch.object(api_module, "is_working_day_valid", side_effect=ValueError("bad")):
            data = self._import(client, [
                {"date": VALID_DATE, "start_time": "08:00", "end_time": "12:00"}])
        assert data["imported_count"] == 0
        assert "Fehler bei Session" in data["errors"][0]


# ── POST /api/shutdown ────────────────────────────────────────────────

class TestShutdown:
    """/api/shutdown ends the whole program, so it must not be reachable by
    other computers, by other web pages open in the browser (CSRF), or through
    DNS rebinding. It needs the per-run token that only the app's own page
    (and local tools that fetch it) can read."""

    @staticmethod
    def _post(client, headers=None, token=True, **kwargs):
        sent = {}
        if token:
            sent["X-RW-Token"] = api_module.SHUTDOWN_TOKEN
        sent.update(headers or {})
        with patch("threading.Thread") as thread:
            resp = client.post("/api/shutdown", headers=sent, **kwargs)
        return resp, thread

    def test_valid_request_schedules_exit_without_killing_the_test_process(self, client):
        resp, thread = self._post(client)
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()

    def test_missing_token_is_rejected(self, client):
        resp, thread = self._post(client, token=False)
        assert resp.status_code == 403
        assert resp.get_json()["success"] is False
        thread.assert_not_called()

    @pytest.mark.parametrize("token", ["", "wrong", "x" * 200])
    def test_wrong_token_is_rejected(self, client, token):
        resp, thread = self._post(client, headers={"X-RW-Token": token}, token=False)
        assert resp.status_code == 403
        thread.assert_not_called()

    def test_token_in_body_or_query_is_not_accepted(self, client):
        with patch("threading.Thread") as thread:
            resp = client.post(f"/api/shutdown?token={api_module.SHUTDOWN_TOKEN}",
                               json={"token": api_module.SHUTDOWN_TOKEN})
        assert resp.status_code == 403
        thread.assert_not_called()

    def test_rejected_request_does_not_touch_the_saved_state(self, client):
        with patch.object(api_module.state_service, "save_state") as save:
            self._post(client, token=False)
        save.assert_not_called()

    def test_get_is_not_allowed(self, client):
        assert client.get("/api/shutdown").status_code == 405

    # -- who may call -----------------------------------------------------

    @pytest.mark.parametrize("addr", ["127.0.0.1", "::1", "::ffff:127.0.0.1"])
    def test_loopback_clients_are_allowed(self, client, addr):
        resp, _ = self._post(client, environ_overrides={"REMOTE_ADDR": addr})
        assert resp.status_code == 200

    @pytest.mark.parametrize("addr", ["192.168.1.20", "10.0.0.5", "8.8.8.8", "fe80::1"])
    def test_other_computers_are_rejected_even_with_the_token(self, client, addr):
        resp, thread = self._post(client, environ_overrides={"REMOTE_ADDR": addr})
        assert resp.status_code == 403
        thread.assert_not_called()

    # -- DNS rebinding ----------------------------------------------------

    @pytest.mark.parametrize("base", [
        "http://localhost/", "http://localhost:5000/",
        "http://127.0.0.1:5000/", "http://[::1]:5000/",
    ])
    def test_local_host_names_are_allowed(self, client, base):
        resp, _ = self._post(client, base_url=base)
        assert resp.status_code == 200

    @pytest.mark.parametrize("base", [
        "http://evil.example/", "http://evil.example:5000/",
        "http://localhost.evil.example/", "http://192.168.1.20:5000/",
    ])
    def test_foreign_host_header_is_rejected(self, client, base):
        resp, thread = self._post(client, base_url=base)
        assert resp.status_code == 403
        thread.assert_not_called()

    # -- cross-site requests ------------------------------------------------

    def test_same_origin_is_allowed(self, client):
        resp, _ = self._post(client, headers={"Origin": "http://localhost"})
        assert resp.status_code == 200

    @pytest.mark.parametrize("origin", [
        "http://evil.example", "null", "http://localhost:9999",
        "https://localhost", "http://127.0.0.1",
    ])
    def test_cross_origin_is_rejected(self, client, origin):
        resp, thread = self._post(client, headers={"Origin": origin})
        assert resp.status_code == 403
        thread.assert_not_called()

    @pytest.mark.parametrize("site", ["same-origin", "none"])
    def test_fetch_metadata_allows_own_page_and_direct_requests(self, client, site):
        resp, _ = self._post(client, headers={"Sec-Fetch-Site": site})
        assert resp.status_code == 200

    @pytest.mark.parametrize("site", ["cross-site", "same-site"])
    def test_fetch_metadata_rejects_other_sites(self, client, site):
        resp, thread = self._post(client, headers={"Sec-Fetch-Site": site})
        assert resp.status_code == 403
        thread.assert_not_called()

    # -- how the UI gets the token ------------------------------------------

    def test_token_is_long_and_random(self):
        assert len(api_module.SHUTDOWN_TOKEN) >= 32

    def test_index_page_hands_the_token_to_the_ui(self, client):
        html = client.get("/").get_data(as_text=True)
        assert f'<meta name="rw-shutdown-token" content="{api_module.SHUTDOWN_TOKEN}">' in html

    def test_ui_sends_the_token_and_checks_the_answer(self):
        js = open(os.path.join(os.path.dirname(__file__), "..", "static", "js", "app.js"),
                  encoding="utf-8").read()
        body = js[js.index("async function handleShutdown"):]
        body = body[:body.index("\n}\n")]
        assert "X-RW-Token" in body
        assert "rw-shutdown-token" in body
        assert "res.ok" in body
