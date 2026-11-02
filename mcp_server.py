#!/usr/bin/env python3
"""MCP Server for Remote Work Quote Tracker.

Exposes all 19 Flask API endpoints as MCP tools.
Requires the Flask app to be running at http://localhost:5000.
"""

import json
import os
import re
from mcp.server.fastmcp import FastMCP
import httpx

BASE_URL = os.environ.get("TRACKER_API_URL", "http://localhost:5000")
TIMEOUT = 5.0

mcp = FastMCP("remote-work-tracker")


async def _request(method: str, path: str, **kwargs) -> str:
    """Make HTTP request to Flask API."""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
            resp = await client.request(method, path, **kwargs)
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                return json.dumps(resp.json(), ensure_ascii=False, indent=2)
            elif "text/csv" in content_type:
                return resp.text
            elif "application/pdf" in content_type:
                # Save PDF to /tmp and return path
                filename = "report.pdf"
                disp = resp.headers.get("content-disposition", "")
                if "filename=" in disp:
                    filename = disp.split("filename=")[-1].strip()
                path_out = f"/tmp/{filename}"
                with open(path_out, "wb") as f:
                    f.write(resp.content)
                return json.dumps({"success": True, "file": path_out})
            else:
                return resp.text
    except httpx.ConnectError:
        return json.dumps({
            "error": "Flask app not reachable at " + BASE_URL,
            "fix": "Start with: cd <project folder> && source venv/bin/activate && python app.py"
        })
    except httpx.TimeoutException:
        return json.dumps({"error": "Request timed out after 5 seconds"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Tools ---

@mcp.tool()
async def get_state() -> str:
    """Get current tracker state including monthly totals, quota, daily entries, and history."""
    return await _request("GET", "/api/state")


@mcp.tool()
async def log_work(datum: str, start: str, end: str, pause: float = 0, remote: float | None = None) -> str:
    """Log a work session. Validates weekends, Bayern holidays, time overlaps, and ArbZG pause rules.

    Args:
        datum: Date in YYYY-MM-DD format
        start: Start time in HH:MM format
        end: End time in HH:MM format
        pause: Break duration in minutes (default: 0)
        remote: Remote hours (default: all hours count as remote)
    """
    body = {"datum": datum, "start": start, "end": end, "pause": pause}
    if remote is not None:
        body["remote"] = remote
    return await _request("POST", "/api/protokoll", json=body)


@mcp.tool()
async def update_entry(entry_id: str, datum: str, start: str, end: str, pause: float = 0, remote: float | None = None) -> str:
    """Update an existing work entry by ID.

    Args:
        entry_id: The entry ID to update
        datum: Date in YYYY-MM-DD format
        start: Start time in HH:MM format
        end: End time in HH:MM format
        pause: Break duration in minutes (default: 0)
        remote: Remote hours (default: all hours)
    """
    body = {"datum": datum, "start": start, "end": end, "pause": pause}
    if remote is not None:
        body["remote"] = remote
    return await _request("PUT", f"/api/update/{entry_id}", json=body)


@mcp.tool()
async def delete_entry(entry_id: str) -> str:
    """Delete a work entry by ID.

    Args:
        entry_id: The entry ID to delete
    """
    return await _request("DELETE", f"/api/delete/{entry_id}")


@mcp.tool()
async def delete_all_entries() -> str:
    """Delete all work entries for the current month."""
    return await _request("POST", "/api/delete_all_entries")


@mcp.tool()
async def analyze_pdf(pdf_path: str) -> str:
    """Extract work sessions from a SAP TimeStatement or Zeitnachweis PDF file.

    Args:
        pdf_path: Absolute path to the PDF file on disk
    """
    if not os.path.exists(pdf_path):
        return json.dumps({"error": f"File not found: {pdf_path}"})
    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        return await _request("POST", "/api/pdf/analyze", files=files)


@mcp.tool()
async def import_pdf_sessions(sessions: list) -> str:
    """Import previously extracted PDF sessions into the tracker.

    Args:
        sessions: Array of session objects with keys: date, start_time, end_time, is_remote, type
    """
    return await _request("POST", "/api/pdf/import", json={"sessions": sessions})


@mcp.tool()
async def set_quota(quote: float) -> str:
    """Set the individual remote work quota percentage (40-60%).

    Args:
        quote: Quota percentage (40.0 to 60.0)
    """
    return await _request("POST", "/api/quote", json={"quote": quote})


@mcp.tool()
async def set_target_hours(hours: float) -> str:
    """Set the target work hours per day (Soll-Stunden).

    Args:
        hours: Hours per day (1.0 to 10.0)
    """
    return await _request("POST", "/api/sollstunden", json={"sollStunden": hours})


@mcp.tool()
async def toggle_dark_mode(enabled: bool) -> str:
    """Enable or disable dark mode.

    Args:
        enabled: True to enable dark mode, False to disable
    """
    return await _request("POST", "/api/darkmode", json={"darkMode": enabled})


@mcp.tool()
async def set_language(language: str) -> str:
    """Set the UI language.

    Args:
        language: "de" for German, "en" for English
    """
    return await _request("POST", "/api/language", json={"language": language})


@mcp.tool()
async def close_month() -> str:
    """Close the current month, archive to history, initialize next month. At quarter-end, auto-adjusts quota."""
    return await _request("POST", "/api/month/switch")


@mcp.tool()
async def view_current_month() -> str:
    """Reset the view to the current system month."""
    return await _request("POST", "/api/view/current_month")


@mcp.tool()
async def export_csv() -> str:
    """Export current month's daily records as CSV text."""
    return await _request("GET", "/api/export/daily_csv")


@mcp.tool()
async def generate_report(year: int | None = None, month: str | None = None) -> str:
    """Generate a monthly PDF report. Saves to /tmp/ and returns the file path.

    Args:
        year: Year (default: current year)
        month: German month name e.g. 'März' (default: current month)
    """
    params = {}
    if year is not None:
        params["year"] = year
    if month is not None:
        params["month"] = month
    return await _request("GET", "/api/report/monthly_pdf", params=params)


@mcp.tool()
async def download_backup() -> str:
    """Download the complete tracker state as JSON backup."""
    return await _request("GET", "/api/backup")


@mcp.tool()
async def restore_backup(backup_json: str) -> str:
    """Restore tracker state from a JSON backup string.

    Args:
        backup_json: JSON string of the full state to restore
    """
    try:
        data = json.loads(backup_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    return await _request("POST", "/api/restore", content=json.dumps(data).encode(), headers={"Content-Type": "application/json"})


@mcp.tool()
async def delete_month(month_name: str, year: int) -> str:
    """Delete a specific month from the history archive.

    Args:
        month_name: German month name (e.g. 'März')
        year: Year (e.g. 2026)
    """
    return await _request("DELETE", f"/api/delete_month/{month_name}/{year}")


@mcp.tool()
async def clear_all_history() -> str:
    """Clear all monthly history and daily records. Resets quota to 40%. Cannot be undone."""
    return await _request("POST", "/api/clear_all_history")


async def _fetch_shutdown_token():
    """Read the per-run shutdown token from the app's start page.

    /api/shutdown only accepts requests that carry this token (the web UI gets it
    the same way). Returns None if the app is not reachable or has no token.
    """
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
            resp = await client.get("/")
        match = re.search(r'<meta name="rw-shutdown-token" content="([^"]+)"', resp.text)
        return match.group(1) if match else None
    except httpx.HTTPError:
        return None


@mcp.tool()
async def shutdown_server() -> str:
    """Shutdown the Flask server gracefully. Saves state before stopping."""
    token = await _fetch_shutdown_token()
    if not token:
        return json.dumps({
            "error": "Could not read the shutdown token from " + BASE_URL,
            "fix": "Start the app first (python app.py); only local requests may shut it down."
        })
    return await _request("POST", "/api/shutdown", headers={"X-RW-Token": token})


if __name__ == "__main__":
    mcp.run()
