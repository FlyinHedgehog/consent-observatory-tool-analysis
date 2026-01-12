"""
Data Generation Runner
======================

Command-line interface for submitting website lists to the consent-observatory
server and saving the resulting analysis data.

Workflow:
    1. Check if consent-observatory server is running
    2. Read website domains from CSV file
    3. Submit URLs to server for analysis
    4. Extract JSON data from completed ZIP
    5. Save to data/examples/ for later analysis

Prerequisites:
    - Consent-observatory server must be running locally
    - CSV file with website domains in data/websites/

Usage:
    python runners/run_generation.py
    
    Then follow the interactive prompts.
"""

import json
import sys
import zipfile
from pathlib import Path
from typing import List, Optional

import requests

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.website_submitter import (
    list_available_files,
    submit_websites,
    validate_file,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Server configuration
DEFAULT_PORTS = [5173, 3000, 80]
HEALTH_CHECK_TIMEOUT = 5  # seconds

# Directory paths
WEBSITES_DIR = 'data/websites'
COMPLETED_DIR = Path('consent-observatory.eu') / 'data' / 'completed'
EXAMPLES_DIR = Path('data/examples')

# Submission settings
DEFAULT_TIMEOUT = 600  # 10 minutes for large batches


# =============================================================================
# SERVER HEALTH CHECKS
# =============================================================================

def check_server_health(ports: Optional[List[int]] = None, timeout: int = HEALTH_CHECK_TIMEOUT) -> bool:
    """
    Check if the consent-observatory server is running on any known port.
    
    Args:
        ports: List of ports to try (default: [5173, 3000, 80])
        timeout: Connection timeout in seconds
    
    Returns:
        True if server is reachable, False otherwise
    """
    if ports is None:
        ports = DEFAULT_PORTS
    
    for port in ports:
        if _is_port_responsive(port, timeout):
            return True
    
    return False


def find_server_port(ports: Optional[List[int]] = None, timeout: int = HEALTH_CHECK_TIMEOUT) -> Optional[int]:
    """
    Find which port the server is running on.
    
    Args:
        ports: List of ports to check
        timeout: Connection timeout in seconds
    
    Returns:
        The port number if found, None otherwise
    """
    if ports is None:
        ports = DEFAULT_PORTS
    
    for port in ports:
        if _is_port_responsive(port, timeout):
            return port
    
    return None


def _is_port_responsive(port: int, timeout: int) -> bool:
    """Check if a specific port responds to HTTP requests."""
    try:
        url = f'http://localhost:{port}/'
        response = requests.get(url, timeout=timeout)
        # Any response (even 404) means server is running
        return response.status_code in (200, 301, 302, 404)
    except (requests.exceptions.ConnectionError, 
            requests.exceptions.Timeout):
        return False


# =============================================================================
# DATA EXTRACTION
# =============================================================================

def extract_json_from_zip(zip_path: Path) -> List[dict]:
    """
    Extract JSON data from a completed results ZIP file.
    
    Handles both standard JSON arrays and JSONL (newline-delimited) formats.
    
    Args:
        zip_path: Path to the ZIP file
    
    Returns:
        List of record dictionaries
    """
    all_data: List[dict] = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            json_files = [f for f in archive.namelist() if f.endswith('.json')]
            
            if not json_files:
                return all_data
            
            for json_file in json_files:
                records = _extract_json_file(archive, json_file)
                all_data.extend(records)
                
    except (zipfile.BadZipFile, FileNotFoundError, OSError):
        return []
    
    return all_data


def _extract_json_file(archive: zipfile.ZipFile, filename: str) -> List[dict]:
    """
    Extract records from a single JSON file within an archive.
    
    Tries standard JSON first, falls back to JSONL format.
    """
    records: List[dict] = []
    
    try:
        with archive.open(filename) as file:
            content = file.read().decode('utf-8')
            
            # Try standard JSON first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    records.extend(data)
                else:
                    records.append(data)
                    
            except json.JSONDecodeError as e:
                # Fall back to JSONL format if JSON fails
                if "Extra data" in str(e):
                    records.extend(_parse_jsonl(content))
                else:
                    raise
                    
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    
    return records


def _parse_jsonl(content: str) -> List[dict]:
    """Parse newline-delimited JSON content."""
    records = []
    for line in content.strip().split('\n'):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def save_json_to_examples(zip_filename: str, csv_filename: str) -> bool:
    """
    Extract JSON from ZIP and save to examples folder.
    
    Saves as JSONL format with the same base name as the source CSV.
    
    Args:
        zip_filename: Name of the completed ZIP file
        csv_filename: Name of the source CSV file (for output naming)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Locate source ZIP
        source_zip = COMPLETED_DIR / zip_filename
        
        if not source_zip.exists():
            print(f"[ERROR] ZIP file not found: {source_zip}")
            return False
        
        # Extract data
        print(f"[...] Extracting JSON data from ZIP...")
        all_data = extract_json_from_zip(source_zip)
        
        if not all_data:
            print(f"[ERROR] No data found in ZIP file")
            return False
        
        # Save as JSONL with CSV base name
        csv_base = Path(csv_filename).stem
        EXAMPLES_DIR.mkdir(exist_ok=True)
        
        json_output = EXAMPLES_DIR / f"{csv_base}.json"
        
        with open(json_output, 'w', encoding='utf-8') as file:
            for record in all_data:
                file.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"[OK] ✓ JSON saved to: {json_output}")
        print(f"[OK] ✓ Records: {len(all_data)}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")
        return False


# =============================================================================
# USER INTERFACE
# =============================================================================

def show_menu() -> Optional[List[str]]:
    """
    Display interactive menu for selecting CSV files.
    
    Returns:
        List of available CSV files, or None if none found
    """
    _print_header("CONSENT OBSERVATORY - DATA GENERATION")
    
    csv_files = list_available_files(WEBSITES_DIR)
    
    if not csv_files:
        print(f"[ERROR] No CSV files found in '{WEBSITES_DIR}/' folder!")
        return None
    
    print("\nAvailable CSV files:")
    for i, csv_file in enumerate(csv_files, 1):
        print(f"  {i}. {csv_file}")
    
    return csv_files


def _print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def _print_step(step_number: int, title: str) -> None:
    """Print a formatted step header."""
    print("\n" + "-" * 60)
    print(f"STEP {step_number}: {title}")
    print("-" * 60)


# =============================================================================
# GENERATION PIPELINE
# =============================================================================

def run_generation(csv_file: str, num_websites: Optional[int] = None) -> bool:
    """
    Execute the full data generation pipeline.
    
    Pipeline Steps:
        0. Check server availability
        1. Validate CSV file
        2. Submit URLs to server
        3. Save extracted JSON data
    
    Args:
        csv_file: CSV filename (in data/websites/)
        num_websites: Optional limit on number of websites to submit
    
    Returns:
        True if generation completed successfully, False otherwise
    """
    # -------------------------------------------------------------------------
    # Step 0: Check Server
    # -------------------------------------------------------------------------
    _print_step(0, "CHECK SERVER")
    
    print(f"[...] Checking if server is running (ports: {DEFAULT_PORTS})...")
    server_port = find_server_port()
    
    if not server_port:
        print("[ERROR] ✗ Server is NOT running!")
        print("\nTo start the server:")
        print("  cd consent-observatory.eu && npm run dev")
        return False
    
    print(f"[OK] ✓ Server is running on port {server_port}!")
    
    # -------------------------------------------------------------------------
    # Step 1: Validate CSV
    # -------------------------------------------------------------------------
    _print_step(1, "VALIDATE CSV")
    
    csv_path = f"{WEBSITES_DIR}/{csv_file}"
    
    if not validate_file(csv_path):
        print("[ERROR] CSV validation failed!")
        return False
    
    print(f"[OK] ✓ CSV validated: {csv_path}")
    
    # -------------------------------------------------------------------------
    # Step 2: Submit to Server
    # -------------------------------------------------------------------------
    _print_step(2, "SUBMIT TO SERVER")
    
    print(f"[...] Submitting websites to server...")
    
    try:
        job_id, zip_file, urls = submit_websites(
            file_path=csv_path,
            server_url=f'http://localhost:{server_port}/',
            user_email='researcher@example.com',
            ruleset_name='Scrape-O-Matic Data Gatherers',
            limit=num_websites,
            timeout=DEFAULT_TIMEOUT
        )
    except Exception as e:
        print(f"[ERROR] Submission failed: {e}")
        return False
    
    # Handle submission results
    if not zip_file:
        if job_id:
            print(f"[WARN] Job submitted (ID: {job_id}) but results not ready yet")
            print("[WARN] The server is still processing. Results will appear in:")
            print(f"[WARN] {COMPLETED_DIR}")
        else:
            print("[ERROR] Server did not accept the submission")
            print("[HINT] Try with fewer URLs (e.g., 10-20) first")
        return False
    
    print(f"[OK] ✓ Job ID: {job_id}")
    
    # -------------------------------------------------------------------------
    # Step 3: Save JSON
    # -------------------------------------------------------------------------
    _print_step(3, "SAVE JSON")
    
    if not save_json_to_examples(zip_file, csv_file):
        return False
    
    # -------------------------------------------------------------------------
    # Complete
    # -------------------------------------------------------------------------
    print("\n[COMPLETE] ✓ Data generation finished!")
    print("=" * 60)
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """
    Main entry point for the generation runner.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n[START] Data Generation Module")
    
    # Show menu and get available files
    csv_files = show_menu()
    if not csv_files:
        return 1
    
    # Get user selection
    choice = input("\nEnter CSV file number (or 'q' to quit): ").strip()
    
    if choice.lower() == 'q':
        print("[CANCELLED] Exiting...")
        return 0
    
    # Validate selection
    try:
        idx = int(choice) - 1
        if not 0 <= idx < len(csv_files):
            print("[ERROR] Invalid choice!")
            return 1
        csv_file = csv_files[idx]
    except ValueError:
        print("[ERROR] Invalid input!")
        return 1
    
    # Get website limit (optional)
    limit_input = input("How many websites to submit? (press Enter for all): ").strip()
    num_websites = None
    
    if limit_input:
        try:
            num_websites = int(limit_input)
        except ValueError:
            print("[ERROR] Invalid number!")
            return 1
    
    # Run generation
    success = run_generation(csv_file, num_websites)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
