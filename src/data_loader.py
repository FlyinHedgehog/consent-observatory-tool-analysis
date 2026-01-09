"""
Utilities for loading consent-observatory records and submitting to server.
"""
from pathlib import Path
import json
import zipfile
import time
import requests
import urllib.parse
from typing import List, Any, Dict, Tuple, Optional

import pandas as pd


def load_records_from_zip(zip_path: Path) -> List[Dict[str, Any]]:
    """Read newline-delimited JSON records from a zip file."""
    records = []
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as z:
            names = [n for n in z.namelist() if n.endswith('data.json')]
            if names:
                with z.open(names[0]) as f:
                    for line in f:
                        try:
                            decoded = line.decode('utf-8').strip()
                            if decoded:
                                records.append(json.loads(decoded))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
    except Exception:
        pass
    return records


def load_records_from_json_file(json_path: Path) -> List[Dict[str, Any]]:
    """Load newline-delimited JSON records from a file."""
    records = []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return records


def load_any_records(existing_records: List[Dict[str, Any]] = None,
                     examples_dir: Path = None,
                     example_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load records from a specific file or from examples folder."""
    if existing_records:
        return existing_records
    
    cwd = Path.cwd()
    examples_dir = examples_dir or cwd / 'examples'

    # If specific file requested, load only from that file
    if example_file:
        file_path = Path(example_file) if Path(example_file).is_absolute() else examples_dir / example_file
        
        if file_path.exists():
            if file_path.suffix == '.zip':
                return load_records_from_zip(file_path)
            else:
                return load_records_from_json_file(file_path)
        return []

    # Try all JSON files in examples folder
    if examples_dir.exists():
        for json_file in sorted(examples_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            records = load_records_from_json_file(json_file)
            if records and any(('url' in r for r in records)):
                return records
    
    return []


def submit_urls_to_server(server_url: str,
                          urls: List[str],
                          user_email: str,
                          ruleset_name: str,
                          ports_to_try: Optional[List[int]] = None,
                          timeout: int = 240,
                          completed_dir: Optional[Path] = None) -> Tuple[Optional[str], Optional[str]]:
    """Submit URLs to the consent-observatory server.

    Returns a tuple: (job_id, completed_zip_name).
    - `job_id` is set when the server returns an identifier.
    - `completed_zip_name` is set when a new completed zip appears within `timeout` seconds.
    If neither is available the function returns (None, None).
    """
    parsed = urllib.parse.urlparse(server_url)
    scheme = parsed.scheme or 'http'
    host = parsed.hostname or 'localhost'
    provided_port = parsed.port
    if ports_to_try is None:
        ports = [provided_port] if provided_port else [5173, 3000, 80]
    else:
        ports = ports_to_try

    cwd = Path.cwd()
    completed_dir = completed_dir or (cwd / 'consent-observatory.eu' / 'data' / 'completed')
    latest_mtime = 0
    if completed_dir.exists():
        zips = list(completed_dir.glob('data-*.zip'))
        if zips:
            latest_mtime = max(p.stat().st_mtime for p in zips)

    form = {
        'email': user_email,
        'urls': '\n'.join(urls),
        'rulesetName': ruleset_name,
        'rulesetOption.CMPGatherer': 'true',
        'rulesetOption.ButtonGatherer': 'true',
        'rulesetOption.CookieGatherer': 'true',
        'rulesetOption.VisibilityAnalyzer': 'true',
        'rulesetOption.InspectorAnalyzer': 'true',
        'rulesetOption.EventListenerGatherer': 'true',
        'rulesetOption.WordBoxGatherer': 'true',
        'rulesetOption.skipWaiting': 'false',
    }

    job_id: Optional[str] = None
    found_zip: Optional[str] = None

    for p in ports:
        if p is None:
            continue
        origin = f'{scheme}://{host}' + (f':{p}' if p not in (80, 443) else '')
        endpoint = origin.rstrip('/') + '/analysis/new'
        headers = {
            'Origin': origin,
            'Referer': origin.rstrip('/') + '/analysis/new',
            'User-Agent': 'python-requests/auto',
            'Accept': 'application/json',
        }
        try:
            request_timeout = max(60, timeout)
            r = requests.post(endpoint, data=form, headers=headers, timeout=request_timeout)
            try:
                resp = r.json()
                if isinstance(resp, dict):
                    for key in ('jobId', 'job_id', 'id', 'job'):
                        if key in resp:
                            job_candidate = resp[key]
                            if isinstance(job_candidate, dict) and 'id' in job_candidate:
                                job_id = job_candidate.get('id')
                            else:
                                job_id = str(job_candidate)
                            break
            except Exception:
                pass

            if r.status_code in (200, 201, 202):
                steps = max(1, timeout // 3)
                elapsed = 0
                progress_interval = 20
                
                print(f"\n[...] Waiting for server to process (max {timeout} seconds)...")
                
                for step in range(steps):
                    time.sleep(3)
                    elapsed += 3
                    
                    if (step + 1) % progress_interval == 0:
                        remaining = timeout - elapsed
                        print(f"[...] Still waiting... {elapsed}s elapsed, {remaining}s remaining")
                    
                    if completed_dir.exists():
                        zips = sorted(completed_dir.glob('data-*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
                        if zips and zips[0].stat().st_mtime > latest_mtime:
                            found_zip = zips[0].name
                            print(f"[OK] Results ready after {elapsed} seconds!")
                            break
                
                if not found_zip and elapsed >= timeout:
                    print(f"[TIMEOUT] Server did not complete within {timeout} seconds")
                
                return job_id, found_zip
        except requests.exceptions.RequestException:
            continue

    return None, None
