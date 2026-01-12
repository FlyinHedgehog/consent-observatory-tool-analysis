"""
Website Submission Module
=========================

Provides utilities for reading website lists from CSV files and
submitting them to the consent-observatory server for analysis.

Workflow:
    1. Read domains from CSV file (Tranco list format)
    2. Convert domains to HTTPS URLs
    3. Submit to consent-observatory server
    4. Monitor for completed results

Expected CSV Format:
    - Single column: domain names only
    - Two columns: rank, domain (Tranco list format)
"""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from .generate_data import generate_data


# =============================================================================
# CONSTANTS
# =============================================================================

# Default server configuration
DEFAULT_SERVER_URL = 'http://localhost:5173/'
DEFAULT_USER_EMAIL = 'researcher@example.com'
DEFAULT_RULESET = 'Scrape-O-Matic Data Gatherers'
DEFAULT_TIMEOUT = 240  # seconds


# =============================================================================
# FILE READING FUNCTIONS
# =============================================================================

def read_websites_from_file(file_path: str) -> List[str]:
    """
    Read website domains from a CSV file and convert to URLs.
    
    Supports two CSV formats:
        - Single column: domain names only
        - Two columns: rank, domain (e.g., Tranco list)
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        List of HTTPS URLs (e.g., ['https://google.com', ...])
    
    Example:
        >>> urls = read_websites_from_file('data/websites/tranco_QWJY4.csv')
        >>> print(urls[:3])
        ['https://google.com', 'https://facebook.com', 'https://youtube.com']
    """
    try:
        # Read CSV without headers (raw data)
        df = pd.read_csv(file_path, header=None)
        
        # Determine which column contains domains
        if len(df.columns) > 1:
            # Multiple columns: assume second column is domain (Tranco format)
            domains = df.iloc[:, 1].tolist()
        else:
            # Single column: assume it's the domain
            domains = df.iloc[:, 0].tolist()
        
        # Convert domains to full HTTPS URLs
        urls = [
            f"https://{domain.strip()}" 
            for domain in domains 
            if domain and str(domain).strip()
        ]
        
        return urls
        
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return []


# =============================================================================
# SUBMISSION FUNCTIONS
# =============================================================================

def submit_websites(
    file_path: str,
    server_url: str = DEFAULT_SERVER_URL,
    user_email: str = DEFAULT_USER_EMAIL,
    ruleset_name: str = DEFAULT_RULESET,
    limit: Optional[int] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Read websites from file and submit them for analysis.
    
    This is the main entry point for batch website submission.
    It handles file reading, URL limiting, and server submission.
    
    Args:
        file_path: Path to CSV file containing website domains
        server_url: Consent-observatory server URL
        user_email: Email for job notifications
        ruleset_name: Which analysis ruleset to use
        limit: Maximum number of websites to submit (None = all)
        timeout: Seconds to wait for results
    
    Returns:
        Tuple of (job_id, completed_zip_name, submitted_urls):
            - job_id: Server-assigned job identifier
            - completed_zip_name: Filename of results ZIP
            - submitted_urls: List of URLs that were submitted
    
    Example:
        >>> job_id, zip_file, urls = submit_websites(
        ...     file_path='data/websites/tranco_QWJY4.csv',
        ...     limit=10  # Only analyze first 10 websites
        ... )
    """
    # --- Step 1: Read URLs from file ---
    print(f"[...] Reading websites from {file_path}...")
    urls = read_websites_from_file(file_path)
    
    if not urls:
        print("[ERROR] No websites found in file!")
        return None, None, []
    
    # --- Step 2: Apply limit if specified ---
    if limit:
        urls = urls[:limit]
    
    print(f"[+] Found {len(urls)} websites")
    print(f"[+] Sample URLs: {urls[:3]}")
    
    # --- Step 3: Submit to server ---
    print(f"\n[...] Submitting to server...")
    job_id, zip_file = generate_data(
        server_url=server_url,
        urls=urls,
        user_email=user_email,
        ruleset_name=ruleset_name,
        timeout=timeout
    )
    
    # --- Step 4: Report results ---
    if job_id:
        print(f"[+] Job submitted: {job_id}")
    if zip_file:
        print(f"[+] Results found: {zip_file}")
    
    return job_id, zip_file, urls


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_file(file_path: str) -> bool:
    """
    Validate that a CSV file exists and is readable.
    
    Args:
        file_path: Path to the file to validate
    
    Returns:
        True if file is valid, False otherwise
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return False
    
    if path.suffix.lower() != '.csv':
        print(f"[ERROR] File is not a CSV: {file_path}")
        return False
    
    return True


def list_available_files(folder: str = 'websites') -> List[str]:
    """
    List all CSV files in a specified folder.
    
    Args:
        folder: Folder path to search for CSV files
    
    Returns:
        List of CSV filenames (not full paths)
    
    Example:
        >>> files = list_available_files('data/websites')
        >>> print(files)
        ['tranco_QWJY4.csv', 'custom_list.csv']
    """
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"[ERROR] Folder not found: {folder}")
        return []
    
    csv_files = list(folder_path.glob('*.csv'))
    return [f.name for f in csv_files]
