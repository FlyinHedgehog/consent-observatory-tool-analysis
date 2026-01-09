"""
Data Generation Runner

Reads websites from CSV and submits them to the server for analysis.
Saves extracted JSON data to examples folder with the CSV filename.
"""

import sys
import requests
import json
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.website_submitter import (
    submit_websites,
    list_available_files,
    validate_file
)


def check_server_health(ports: list = None, timeout: int = 5) -> bool:
    """Check if consent-observatory server is running on any of the ports."""
    if ports is None:
        ports = [5173, 3000, 80]
    
    for port in ports:
        try:
            url = f'http://localhost:{port}/'
            response = requests.get(url, timeout=timeout)
            if response.status_code in (200, 301, 302, 404):
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, Exception):
            continue
    
    return False


def extract_json_from_zip(zip_path: Path) -> list:
    """Extract JSON data from the completed ZIP file. Handles both JSON and JSONL formats."""
    all_data = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
            
            if not json_files:
                return all_data
            
            for json_file in json_files:
                try:
                    with zip_ref.open(json_file) as f:
                        content = f.read().decode('utf-8')
                        
                        # Try standard JSON first
                        try:
                            data = json.loads(content)
                            if isinstance(data, list):
                                all_data.extend(data)
                            else:
                                all_data.append(data)
                        except json.JSONDecodeError as e:
                            # Try JSONL format if standard JSON fails
                            if "Extra data" in str(e):
                                for line in content.strip().split('\n'):
                                    if line.strip():
                                        try:
                                            all_data.append(json.loads(line))
                                        except json.JSONDecodeError:
                                            continue
                            else:
                                raise e
                except Exception:
                    continue
    except Exception:
        return []
    
    return all_data


def save_json_to_examples(zip_filename: str, csv_filename: str) -> bool:
    """Extract JSON from ZIP and save to data/examples folder with CSV filename in JSONL format."""
    try:
        source_zip = Path('consent-observatory.eu') / 'data' / 'completed' / zip_filename
        
        if not source_zip.exists():
            print(f"[ERROR] ZIP file not found: {source_zip}")
            return False
        
        print(f"[...] Extracting JSON data from ZIP...")
        all_data = extract_json_from_zip(source_zip)
        
        if not all_data:
            print(f"[ERROR] No data found in ZIP file")
            return False
        
        # Save JSON as JSONL (newline-delimited) with CSV filename
        csv_base = Path(csv_filename).stem
        output_dir = Path('data/examples')
        output_dir.mkdir(exist_ok=True)
        
        json_output = output_dir / f"{csv_base}.json"
        with open(json_output, 'w', encoding='utf-8') as f:
            for record in all_data:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"[OK] ✓ JSON saved to: {json_output}")
        print(f"[OK] ✓ Records: {len(all_data)}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")
        return False


def show_menu():
    """Display available CSV files and let user choose."""
    print("\n" + "="*60)
    print("CONSENT OBSERVATORY - DATA GENERATION")
    print("="*60)
    
    csv_files = list_available_files('data/websites')
    if not csv_files:
        print("[ERROR] No CSV files found in 'data/websites/' folder!")
        return None
    
    print("\nAvailable CSV files:")
    for i, csv_file in enumerate(csv_files, 1):
        print(f"  {i}. {csv_file}")
    
    return csv_files


def run_generation(csv_file: str, num_websites: int = None) -> bool:
    """Run data generation from CSV."""
    
    print("\n" + "-"*60)
    print("STEP 0: CHECK SERVER")
    print("-"*60)
    
    print("[...] Checking if server is running (ports: 5173, 3000, 80)...")
    if not check_server_health():
        print("[ERROR] ✗ Server is NOT running!")
        print("\nTo start the server:")
        print("  cd consent-observatory.eu && npm run dev")
        return False
    
    print("[OK] ✓ Server is running!")
    
    print("\n" + "-"*60)
    print("STEP 1: VALIDATE CSV")
    print("-"*60)
    
    csv_path = f"data/websites/{csv_file}"
    if not validate_file(csv_path):
        print("[ERROR] CSV validation failed!")
        return False
    print(f"[OK] ✓ CSV validated: {csv_path}")
    
    print("\n" + "-"*60)
    print("STEP 2: SUBMIT TO SERVER")
    print("-"*60)
    
    print(f"[...] Submitting websites to server...")
    print(f"[...] This may take a few minutes for {len(urls) if 'urls' in locals() else 'N'} websites...")
    
    try:
        job_id, zip_file, urls = submit_websites(
            file_path=csv_path,
            server_url='http://localhost:5173/',
            user_email='researcher@example.com',
            ruleset_name='Scrape-O-Matic Data Gatherers',
            limit=num_websites,
            timeout=600  # Increased to 10 minutes for large batches
        )
    except Exception as e:
        print(f"[ERROR] Submission failed: {e}")
        return False
    
    if not zip_file:
        if job_id:
            print(f"[WARN] Job submitted (ID: {job_id}) but results not ready yet")
            print("[WARN] The server is still processing. Results will appear in:")
            print(f"[WARN] {Path('consent-observatory.eu') / 'data' / 'completed'}")
        else:
            print("[ERROR] Server did not accept the submission")
            print("[HINT] Try with fewer URLs (e.g., 10-20) first")
        return False
    
    print(f"[OK] ✓ Job ID: {job_id}")
    
    print("\n" + "-"*60)
    print("STEP 3: SAVE JSON")
    print("-"*60)
    
    if not save_json_to_examples(zip_file, csv_file):
        return False
    
    print("\n[COMPLETE] ✓ Data generation finished!")
    print("="*60)
    return True


if __name__ == '__main__':
    print("\n[START] Data Generation Module")
    
    csv_files = show_menu()
    if not csv_files:
        exit(1)
    
    choice = input("\nEnter CSV file number (or 'q' to quit): ").strip()
    if choice.lower() == 'q':
        print("[CANCELLED] Exiting...")
        exit(0)
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(csv_files):
            csv_file = csv_files[idx]
        else:
            print("[ERROR] Invalid choice!")
            exit(1)
    except ValueError:
        print("[ERROR] Invalid input!")
        exit(1)
    
    limit_input = input("How many websites to submit? (press Enter for all): ").strip()
    num_websites = None
    if limit_input:
        try:
            num_websites = int(limit_input)
        except ValueError:
            print("[ERROR] Invalid number!")
            exit(1)
    
    success = run_generation(csv_file, num_websites)
    exit(0 if success else 1)
