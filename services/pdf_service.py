import os
import re
import json
from datetime import datetime
from config import Config

# Try to import pdfplumber for local parsing
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("WARNING: pdfplumber not installed. Install with: pip install pdfplumber")

# Try to import google.generativeai for AI-based parsing
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


_NUM = r'(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})(-)?'
_FLEX_PATTERNS = {
    'previous': r'(?:GLZ-Saldo\s+Vorperiode|Flex\.?\s*Bal\.?\s*Prev\.?\s*Period)\s+' + _NUM,
    'current': r'(?:GLZ-Saldo\s+akt\.?\s*Periode|Flextime\s+Bal\.?\s*Curr\.?\s*Period)\s*' + _NUM,
    'total': r'(?:GLZ-Saldo\s+Gesamt|Flextime\s+Balance\s+Total)\s+' + _NUM,
}


def parse_flex_balance(text):
    """Flextime balance (hours) from the summary of a statement, or None when it has none.

    Keys: previous period, current period, total. A trailing minus sign ("12,50-") means negative.
    Only the first match counts: the same labels appear again in the overtime table on the right.
    """
    result = {}
    for key, pattern in _FLEX_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = float(m.group(1).replace('.', '').replace(',', '.'))
            result[key] = -value if m.group(2) else value
    return result or None


class PDFService:
    def __init__(self):
        self.model = None
        if GEMINI_AVAILABLE and Config.GOOGLE_API_KEY:
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            print("INFO: Gemini not configured. Using local PDF parsing (pdfplumber).")

    def analyze_pdf(self, pdf_path):
        """
        Analyze PDF and extract work sessions.
        First tries local pdfplumber parsing for SAP TimeStatements.
        Falls back to Gemini AI if local parsing fails or finds no sessions.
        """
        # Try local parsing first (faster, no API needed)
        if PDFPLUMBER_AVAILABLE:
            result = self._parse_sap_timestatement(pdf_path)
            if result['success'] and result['sessions']:
                return result
            print(f"Local parsing found no sessions, trying Gemini...")

        # Fall back to Gemini if available
        if self.model:
            return self._analyze_with_gemini(pdf_path)

        # No method available
        if not PDFPLUMBER_AVAILABLE and not self.model:
            return {
                "success": False,
                "message": "No PDF parsing method available. Install pdfplumber or configure Google API Key.",
                "sessions": []
            }

        return {
            "success": False,
            "message": "Could not extract sessions from PDF.",
            "sessions": []
        }

    def _parse_sap_timestatement(self, pdf_path):
        """
        Parse SAP TimeStatement PDF format locally using pdfplumber.

        Expected format:
        - Header: "from DD.MM.YYYY to DD.MM.YYYY" or "vom DD.MM.YYYY bis DD.MM.YYYY"
        - Entries: "DD WD  Time Postings/Zeitbuchungen : At work/Remote Work/anwesend  HH:MM  HH:MM  ..."
        """
        try:
            sessions = []
            year = None
            month = None

            print(f"DEBUG: Opening PDF file: {pdf_path}")
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"

            print(f"DEBUG: Extracted {len(full_text)} characters from PDF")

            # Extract date range from header (e.g., "from 01.07.2025 to 31.07.2025")
            date_range_match = re.search(r'from\s+(\d{2})\.(\d{2})\.(\d{4})\s+to\s+\d{2}\.\d{2}\.\d{4}', full_text)
            if date_range_match:
                month = int(date_range_match.group(2))
                year = int(date_range_match.group(3))

            # Also try German format "vom DD.MM.YYYY bis DD.MM.YYYY"
            date_range_match_de = re.search(r'vom\s+(\d{2})\.(\d{2})\.(\d{4})\s+bis\s+\d{2}\.\d{2}\.\d{4}', full_text, re.IGNORECASE)
            if date_range_match_de and not year:
                month = int(date_range_match_de.group(2))
                year = int(date_range_match_de.group(3))

            # Also try "Month: July - 2025" format (English)
            month_year_match = re.search(r'Month:\s+(\w+)\s+-\s+(\d{4})', full_text)
            if month_year_match and not year:
                month_names = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                month_name = month_year_match.group(1)
                month = month_names.get(month_name, 1)
                year = int(month_year_match.group(2))

            # Also try German format "Monat: Juli - 2025"
            month_year_match_de = re.search(r'Monat:\s+(\w+)\s+-\s+(\d{4})', full_text, re.IGNORECASE)
            if month_year_match_de and not year:
                month_names_de = {
                    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
                    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
                    'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
                }
                month_name = month_year_match_de.group(1)
                month = month_names_de.get(month_name, 1)
                year = int(month_year_match_de.group(2))

            if not year or not month:
                # Try to extract from filename (e.g., TimeStatement_20310701_20310731.pdf)
                filename_match = re.search(r'(\d{4})(\d{2})(\d{2})', os.path.basename(pdf_path))
                if filename_match:
                    year = int(filename_match.group(1))
                    month = int(filename_match.group(2))

            if not year:
                year = datetime.now().year
            if not month:
                month = datetime.now().month

            # Pattern for time entries:
            # English: "01 TU  Time Postings : At work  07:30  17:00  9,50 ..."
            # English: "03 TH  Time Postings : Remote Work  08:00  17:15  9,25 ..."
            # German:  "01 DI  Zeitbuchungen : Anwesend  07:30  17:00  9,50 ..."
            # German:  "03 DO  Zeitbuchungen : Remote Work  08:00  17:15  9,25 ..."
            # Also handles split entries

            # Weekday patterns (English + German)
            weekdays = r'(?:MO|TU|WE|TH|FR|SA|SU|DI|MI|DO|SO)'

            # Work type patterns (English + German)
            # English: "Time Postings : At work" / "Time Postings : Remote Work"
            # German: "Zeitbuchungen : anwesend" / "Zeitbuchungen : Remote Work" / "Zeitbuchungen : Telearbeit" / "Zeitbuchungen : Home Office"
            work_type_pattern = r'(?:Time Postings|Zeitbuchungen)\s*:\s*(At work|Remote Work|[Aa]nwesend|Telearbeit|Home Office|Homeoffice|Im Büro|Büro)'

            # First pattern: day + weekday + type + times
            pattern1 = re.compile(
                r'(\d{2})\s+' + weekdays + r'\s+' +
                work_type_pattern + r'\s+' +
                r'(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})',
                re.IGNORECASE
            )

            # Second pattern: continuation entries (no day, just type + times)
            pattern2 = re.compile(
                work_type_pattern + r'\s+' +
                r'(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})',
                re.IGNORECASE
            )

            # Helper function to determine if work type is remote
            def is_remote_work(work_type):
                remote_keywords = ['remote work', 'remote', 'telearbeit', 'home office', 'homeoffice']
                office_keywords = ['at work', 'anwesend', 'im büro', 'büro']
                work_type_lower = work_type.lower().strip()
                # Check remote keywords first
                for kw in remote_keywords:
                    if kw in work_type_lower:
                        return True
                # Check office keywords
                for kw in office_keywords:
                    if kw in work_type_lower:
                        return False
                return False  # Default to office if unknown

            lines = full_text.split('\n')
            current_day = None

            day_start = re.compile(r'^\s*(\d{2})\s+' + weekdays + r'\b', re.IGNORECASE)

            for line in lines:
                # Every day line starts a new day, also lines without a booking of their own
                # (flextime compensation, holiday): a following continuation line belongs to THAT day.
                day_line = day_start.match(line)
                if day_line:
                    current_day = int(day_line.group(1))

                # Try first pattern (with day number)
                match1 = pattern1.search(line)
                if match1:
                    day = int(match1.group(1))
                    current_day = day
                    work_type = match1.group(2)
                    start_time = match1.group(3)
                    end_time = match1.group(4)
                    is_remote = is_remote_work(work_type)

                    try:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        # Validate date
                        datetime.strptime(date_str, '%Y-%m-%d')

                        sessions.append({
                            'date': date_str,
                            'start_time': start_time,
                            'end_time': end_time,
                            'is_remote': is_remote,
                            'type': work_type
                        })
                    except ValueError:
                        continue
                    continue

                # Try second pattern (continuation without day)
                match2 = pattern2.search(line)
                # Check for both English and German headers
                if match2 and current_day and ('Time Postings' in line or 'Zeitbuchungen' in line):
                    # Check this isn't a duplicate from pattern1
                    if not pattern1.search(line):
                        work_type = match2.group(1)
                        start_time = match2.group(2)
                        end_time = match2.group(3)
                        is_remote = is_remote_work(work_type)

                        try:
                            date_str = f"{year}-{month:02d}-{current_day:02d}"
                            datetime.strptime(date_str, '%Y-%m-%d')

                            sessions.append({
                                'date': date_str,
                                'start_time': start_time,
                                'end_time': end_time,
                                'is_remote': is_remote,
                                'type': work_type
                            })
                        except ValueError:
                            continue

            # Sort by date and time
            sessions.sort(key=lambda x: (x['date'], x['start_time']))

            print(f"DEBUG: Found {len(sessions)} sessions total")

            # Count remote vs office
            remote_count = sum(1 for s in sessions if s['is_remote'])
            office_count = len(sessions) - remote_count

            flex_balance = parse_flex_balance(full_text)
            if flex_balance:
                flex_balance.update({'year': year, 'month': month})

            return {
                "success": True,
                "message": f"Parsed SAP TimeStatement. Found {len(sessions)} sessions ({remote_count} remote, {office_count} office).",
                "sessions": sessions,
                "flex_balance": flex_balance,
                "structure": {
                    "format": "SAP TimeStatement",
                    "year": year,
                    "month": month,
                    "total_sessions": len(sessions),
                    "remote_sessions": remote_count,
                    "office_sessions": office_count
                }
            }

        except Exception as e:
            print(f"Local PDF parsing error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error parsing PDF locally: {str(e)}",
                "sessions": []
            }

    def _analyze_with_gemini(self, pdf_path):
        """Analyze PDF using Gemini AI (fallback method)."""
        if not self.model:
            return {
                "success": False,
                "message": "Google API Key not configured.",
                "sessions": []
            }

        try:
            # Upload the file to Gemini
            sample_file = genai.upload_file(path=pdf_path, display_name="Work Log PDF")

            # Prompt for extraction
            prompt = """
            Analyze this PDF and extract work sessions.
            Return a JSON object with a key 'sessions' which is a list of objects.
            Each object should have:
            - 'date': YYYY-MM-DD
            - 'start_time': HH:MM
            - 'end_time': HH:MM
            - 'is_remote': boolean (true if text suggests remote/home office, else false)

            Look for patterns like "HH:MM - HH:MM" or tables with dates and times.
            Look for "Time Postings : Remote Work" or "Time Postings : At work" to determine remote status.
            Ignore breaks if possible, just get start and end of the main shift or segments.
            If there are multiple segments per day, list them separately.
            """

            response = self.model.generate_content([sample_file, prompt])

            # Clean up response text to get JSON
            text = response.text
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            sessions = data.get('sessions', [])

            return {
                "success": True,
                "message": f"Analyzed PDF with Gemini AI. Found {len(sessions)} sessions.",
                "sessions": sessions,
                "structure": {"method": "gemini"}
            }

        except Exception as e:
            print(f"Gemini Error: {e}")
            return {
                "success": False,
                "message": f"Error analyzing PDF with Gemini: {str(e)}",
                "sessions": []
            }
