#!/usr/bin/env python3
"""Privacy guard (GDPR): fails when the repository contains data that must stay on a private machine.

The app processes working times of a real person. Time statements (PDF), screenshots, backups, the
state file and the .env file therefore never belong into a Git repository.

  python tools/check_privacy.py [folder]     (default: the repository root)

Checks
  * forbidden files: PDFs, images, office files, CSV, state files, backups, .env, databases
  * text files: e-mail addresses, street addresses, postal code + city, phone numbers,
    personnel numbers, home directories of real users

Exit code 0 = clean, 1 = findings. It runs in the test suite (tests/test_repo_hygiene.py) and in CI.
"""
import os
import re
import sys

SKIP_DIRS = {'.git', 'venv', '.venv', '.venv-build', 'build', 'dist', 'node_modules', '__pycache__',
             '.pytest_cache', 'real_statements', '.idea'}
SELF = {'check_privacy.py', 'test_repo_hygiene.py'}   # contain the patterns / sample strings on purpose

FORBIDDEN_SUFFIXES = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.webp', '.heic',
                      '.doc', '.docx', '.xls', '.xlsx', '.odt', '.ods', '.csv', '.db', '.sqlite', '.sqlite3',
                      '.bak', '.zip', '.7z', '.tar', '.gz'}
FORBIDDEN_NAMES = (re.compile(r'^tracker_state.*\.json$'), re.compile(r'^\.env(\..*)?$'),
                   re.compile(r'^remote_tracker_backup.*', re.I), re.compile(r'^daily_records_.*', re.I))
TEXT_SUFFIXES = {'.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.sh', '.bat', '.yml', '.yaml',
                  '.spec', '.ini', '.toml', '.cfg', '.xml', '.example', ''}

EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}')
ALLOWED_MAIL_DOMAINS = ('example.com', 'example.org', 'users.noreply.github.com')
RULES = [
    ('street address', re.compile(r'\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|strasse|str\.|weg|platz|allee|gasse)\s+\d+[a-z]?\b')),
    ('postal code and city', re.compile(r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]{2,}\b')),
    ('phone number', re.compile(r'(?<![\d.])(?:\+49|0049)[\s/-]?\d{2,5}[\s/-]?\d{4,}|(?<![\d.])0\d{2,4}[\s/-]\d{5,}')),
    ('personnel number', re.compile(r'(?i)personal(?:nummer|\s*no\.?|\s*number)\s*[:#]?\s*\d{4,}')),
    ('home directory of a user', re.compile(r'(?:/home/(?!<)[a-z][\w.-]*/|/Users/(?!<)[A-Za-z][\w.-]*/|[A-Za-z]:\\Users\\(?!<)[\w.-]+\\)')),
]


def _walk(root):
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield os.path.join(folder, name)


def publishable_files(root):
    """Files Git would publish: tracked plus untracked-but-not-ignored. None if root is no Git checkout."""
    import subprocess
    if not os.path.isdir(os.path.join(root, '.git')):
        return None
    out = subprocess.run(['git', '-C', root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                         capture_output=True, check=True).stdout
    return [os.path.join(root, p) for p in out.decode('utf-8').split('\0') if p]


def scan(root, paths=None):
    """Findings for every file below root, or only for `paths` (absolute paths)."""
    findings = []
    for path in (_walk(root) if paths is None else paths):
        name = os.path.basename(path)
        rel = os.path.relpath(path, root)
        suffix = os.path.splitext(name)[1].lower()
        if suffix in FORBIDDEN_SUFFIXES or any(p.match(name) for p in FORBIDDEN_NAMES):
            findings.append((rel, 0, 'forbidden file type or name'))
            continue
        if name in SELF or suffix not in TEXT_SUFFIXES:
            continue
        try:
            with open(path, encoding='utf-8') as fh:
                lines = fh.read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            for match in EMAIL.finditer(line):
                if not match.group(0).lower().endswith(ALLOWED_MAIL_DOMAINS):
                    findings.append((rel, number, 'e-mail address'))
            for label, pattern in RULES:
                if pattern.search(line):
                    findings.append((rel, number, label))
    return findings


def main(argv):
    root = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    files = publishable_files(root)
    findings = scan(root, files)
    if not findings:
        print(f'privacy check OK: nothing found in {root} ({"Git files" if files is not None else "all files"})')
        return 0
    print('privacy check FAILED - do not publish these files:')
    for rel, number, what in findings:
        print(f'  {rel}{":" + str(number) if number else ""}: {what}')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
