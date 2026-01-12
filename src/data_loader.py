"""
Data Loader Module
==================

Provides utilities for loading consent-observatory records from various
file formats and submitting URLs to the server for analysis.

Supported Formats:
    - ZIP files containing newline-delimited JSON (JSONL)
    - Plain JSON files with JSONL format
    - Standard JSON array files

Server Integration:
    - Submit URLs for analysis via HTTP POST
    - Auto-detect server ports (5173, 3000, 80)
    - Poll for completed results with configurable timeout
"""

import json
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# =============================================================================
# CONSTANTS
# =============================================================================

# Default ports to try when connecting to the consent-observatory server
DEFAULT_SERVER_PORTS = [5173, 3000, 80]

# Standard HTTP success codes
SUCCESS_STATUS_CODES = (200, 201, 202)

# Polling interval when waiting for server results (seconds)
POLL_INTERVAL_SECONDS = 3


# =============================================================================
# FILE LOADING FUNCTIONS
# =============================================================================

def load_records_from_zip(zip_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSONL records from a ZIP archive.
    
    Searches for files ending in 'data.json' within the archive and
    parses them as newline-delimited JSON (JSONL).
    
    Args:
        zip_path: Path to the ZIP file
    
    Returns:
        List of parsed record dictionaries
    
    Note:
        Silently skips malformed JSON lines to handle partial data.
    """
    records: List[Dict[str, Any]] = []
    
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as archive:
            # Find data files within the archive
            data_files = [name for name in archive.namelist() 
                          if name.endswith('data.json')]
            
            if not data_files:
                return records
            
            # Parse each data file as JSONL
            with archive.open(data_files[0]) as file:
                for line in file:
                    try:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line:
                            records.append(json.loads(decoded_line))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Skip malformed lines
                        continue
                        
    except (zipfile.BadZipFile, FileNotFoundError, OSError):
        # Return empty list on file errors
        pass
    
    return records


def load_records_from_json_file(json_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSONL records from a plain JSON file.
    
    Expects newline-delimited JSON format where each line is a
    complete JSON object.
    
    Args:
        json_path: Path to the JSON file
    
    Returns:
        List of parsed record dictionaries
    """
    records: List[Dict[str, Any]] = []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (FileNotFoundError, OSError):
        pass
    
    return records


def load_any_records(
    existing_records: Optional[List[Dict[str, Any]]] = None,
    examples_dir: Optional[Path] = None,
    example_file: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load records from a file or discover from examples folder.
    
    This function provides a flexible interface for loading data:
    1. Returns existing records if provided (passthrough)
    2. Loads from specific file if example_file is given
    3. Auto-discovers from examples folder as fallback
    
    Args:
        existing_records: Pre-loaded records to return directly
        examples_dir: Directory containing example data files
        example_file: Specific file to load (relative or absolute path)
    
    Returns:
        List of record dictionaries, or empty list if nothing found
    """
    # Passthrough if records already provided
    if existing_records:
        return existing_records
    
    # Default examples directory
    cwd = Path.cwd()
    examples_dir = examples_dir or (cwd / 'data' / 'examples')

    # Load from specific file if requested
    if example_file:
        file_path = (Path(example_file) if Path(example_file).is_absolute() 
                     else examples_dir / example_file)
        
        if file_path.exists():
            if file_path.suffix == '.zip':
                return load_records_from_zip(file_path)
            return load_records_from_json_file(file_path)
        return []

    # Auto-discover from examples folder (newest files first)
    if examples_dir.exists():
        json_files = sorted(
            examples_dir.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for json_file in json_files:
            records = load_records_from_json_file(json_file)
            # Validate that records have URL field
            if records and any('url' in record for record in records):
                return records
    
    return []


# =============================================================================
# SERVER SUBMISSION FUNCTIONS
# =============================================================================

def submit_urls_to_server(
    server_url: str,
    urls: List[str],
    user_email: str,
    ruleset_name: str,
    ports_to_try: Optional[List[int]] = None,
    timeout: int = 240,
    completed_dir: Optional[Path] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Submit URLs to the consent-observatory server for analysis.
    
    Attempts to connect to the server on multiple ports and submits
    URLs for crawling. Polls for completed results within the timeout.
    
    Args:
        server_url: Base server URL (e.g., 'http://localhost:5173')
        urls: List of URLs to analyze
        user_email: Email for job notifications
        ruleset_name: Which analysis ruleset to use
        ports_to_try: List of ports to attempt (default: [5173, 3000, 80])
        timeout: Maximum seconds to wait for results
        completed_dir: Directory to monitor for completed jobs
    
    Returns:
        Tuple of (job_id, completed_zip_name):
            - job_id: Server-assigned job identifier
            - completed_zip_name: Filename of completed results ZIP
        Both may be None if submission fails or times out.
    """
    # Parse server URL components
    parsed = urllib.parse.urlparse(server_url)
    scheme = parsed.scheme or 'http'
    host = parsed.hostname or 'localhost'
    provided_port = parsed.port
    
    # Determine ports to try
    if ports_to_try is None:
        ports = [provided_port] if provided_port else DEFAULT_SERVER_PORTS
    else:
        ports = ports_to_try

    # Setup completed results monitoring
    cwd = Path.cwd()
    completed_dir = completed_dir or (cwd / 'consent-observatory.eu' / 'data' / 'completed')
    latest_mtime = _get_latest_zip_mtime(completed_dir)

    # Build form data with all required parameters
    form_data = _build_submission_form(urls, user_email, ruleset_name)

    # Track results
    job_id: Optional[str] = None
    found_zip: Optional[str] = None

    # Attempt submission on each port
    for port in ports:
        if port is None:
            continue
        
        result = _try_submit_on_port(
            scheme, host, port, form_data, timeout,
            completed_dir, latest_mtime
        )
        
        if result:
            job_id, found_zip = result
            return job_id, found_zip

    return None, None


def _get_latest_zip_mtime(completed_dir: Path) -> float:
    """Get the modification time of the newest ZIP file in directory."""
    if not completed_dir.exists():
        return 0
    
    zips = list(completed_dir.glob('data-*.zip'))
    return max((p.stat().st_mtime for p in zips), default=0)


def _build_submission_form(
    urls: List[str],
    user_email: str,
    ruleset_name: str
) -> Dict[str, str]:
    """
    Build the form data dictionary for server submission.
    
    Includes all required gatherer options for comprehensive analysis.
    """
    return {
        'email': user_email,
        'urls': '\n'.join(urls),
        'rulesetName': ruleset_name,
        # Gatherer options - all enabled for comprehensive data collection
        'rulesetOption.CMPGatherer': 'true',
        'rulesetOption.ButtonGatherer': 'true',
        'rulesetOption.CookieGatherer': 'true',
        'rulesetOption.VisibilityAnalyzer': 'true',
        'rulesetOption.InspectorAnalyzer': 'true',
        'rulesetOption.EventListenerGatherer': 'true',
        'rulesetOption.WordBoxGatherer': 'true',
        'rulesetOption.skipWaiting': 'false',
    }


def _try_submit_on_port(
    scheme: str,
    host: str,
    port: int,
    form_data: Dict[str, str],
    timeout: int,
    completed_dir: Path,
    latest_mtime: float
) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Attempt to submit URLs to server on a specific port.
    
    Returns:
        Tuple of (job_id, zip_name) on success, None if port fails
    """
    # Construct endpoint URL
    port_suffix = f':{port}' if port not in (80, 443) else ''
    origin = f'{scheme}://{host}{port_suffix}'
    endpoint = f'{origin.rstrip("/")}/analysis/new'
    
    # Setup request headers
    headers = {
        'Origin': origin,
        'Referer': f'{origin.rstrip("/")}/analysis/new',
        'User-Agent': 'python-requests/auto',
        'Accept': 'application/json',
    }
    
    try:
        # Submit the request
        request_timeout = max(60, timeout)
        response = requests.post(
            endpoint, 
            data=form_data, 
            headers=headers, 
            timeout=request_timeout
        )
        
        # Extract job ID from response
        job_id = _extract_job_id(response)
        
        if response.status_code not in SUCCESS_STATUS_CODES:
            return None
        
        # Poll for completed results
        found_zip = _poll_for_results(completed_dir, latest_mtime, timeout)
        return job_id, found_zip
        
    except requests.exceptions.RequestException:
        return None


def _extract_job_id(response: requests.Response) -> Optional[str]:
    """
    Extract job ID from server response.
    
    Handles various response formats used by different server versions.
    """
    try:
        resp_json = response.json()
        if not isinstance(resp_json, dict):
            return None
        
        # Try common job ID field names
        for key in ('jobId', 'job_id', 'id', 'job'):
            if key not in resp_json:
                continue
            
            job_value = resp_json[key]
            
            # Handle nested job object
            if isinstance(job_value, dict) and 'id' in job_value:
                return job_value.get('id')
            
            return str(job_value)
            
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None


def _poll_for_results(
    completed_dir: Path,
    latest_mtime: float,
    timeout: int
) -> Optional[str]:
    """
    Poll the completed directory for new result files.
    
    Args:
        completed_dir: Directory to monitor
        latest_mtime: Modification time of newest existing file
        timeout: Maximum seconds to wait
    
    Returns:
        Filename of new ZIP file, or None if timeout reached
    """
    steps = max(1, timeout // POLL_INTERVAL_SECONDS)
    elapsed = 0
    progress_interval = 20  # Log progress every N iterations
    
    print(f"\n[...] Waiting for server to process (max {timeout} seconds)...")
    
    for step in range(steps):
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
        
        # Log progress periodically
        if (step + 1) % progress_interval == 0:
            remaining = timeout - elapsed
            print(f"[...] Still waiting... {elapsed}s elapsed, {remaining}s remaining")
        
        # Check for new completed files
        if completed_dir.exists():
            zips = sorted(
                completed_dir.glob('data-*.zip'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if zips and zips[0].stat().st_mtime > latest_mtime:
                print(f"[OK] Results ready after {elapsed} seconds!")
                return zips[0].name
    
    print(f"[TIMEOUT] Server did not complete within {timeout} seconds")
    return None
