"""
Website Submission Module

Reads websites from a file and submits them to the server for analysis.
Retrieves generated JSON data files.
"""

from pathlib import Path
from typing import List, Tuple, Optional
import pandas as pd
from .generate_data import generate_data


def read_websites_from_file(file_path: str) -> List[str]:
    """
    Read websites from a file (CSV format).
    
    Expected file format: rank, domain (or just domain names)
    
    Args:
        file_path: Path to the file
        
    Returns:
        List of domain names
    """
    try:
        df = pd.read_csv(file_path, header=None)
        
        # If file has multiple columns, try to find the domain column
        if len(df.columns) > 1:
            # Assume second column is the domain
            domains = df.iloc[:, 1].tolist()
        else:
            # Single column - assume it's the domain
            domains = df.iloc[:, 0].tolist()
        
        # Convert to https URLs
        urls = [f"https://{domain.strip()}" for domain in domains if domain]
        return urls
    except Exception as e:
        print(f"Error reading file: {e}")
        return []


def submit_websites(
    file_path: str,
    server_url: str = 'http://localhost:5173/',
    user_email: str = 'researcher@example.com',
    ruleset_name: str = 'Scrape-O-Matic Data Gatherers',
    limit: Optional[int] = None,
    timeout: int = 240
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Submit websites from a file to the server for analysis.
    
    Args:
        file_path: Path to file with websites
        server_url: Server endpoint
        user_email: Email for submission
        ruleset_name: Which analysis ruleset to use
        limit: Max number of websites to submit (None = all)
        timeout: Wait timeout in seconds
        
    Returns:
        (job_id, completed_zip_name, websites_submitted)
    """
    # Read websites from file
    print(f"Reading websites from {file_path}...")
    urls = read_websites_from_file(file_path)
    
    if not urls:
        print("No websites found in file!")
        return None, None, []
    
    # Limit if specified
    if limit:
        urls = urls[:limit]
    
    print(f"[+] Found {len(urls)} websites")
    print(f"[+] Sample URLs: {urls[:3]}")
    
    # Submit to server
    print(f"\nSubmitting to server...")
    job_id, zip_file = generate_data(
        server_url=server_url,
        urls=urls,
        user_email=user_email,
        ruleset_name=ruleset_name,
        timeout=timeout
    )
    
    if job_id:
        print(f"[+] Job submitted: {job_id}")
    if zip_file:
        print(f"[+] Results found: {zip_file}")
    
    return job_id, zip_file, urls


def validate_file(file_path: str) -> bool:
    """
    Check if file exists and is readable.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if valid, False otherwise
    """
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return False
    if not path.suffix.lower() == '.csv':
        print(f"File is not a CSV: {file_path}")
        return False
    return True


def list_available_files(folder: str = 'websites') -> List[str]:
    """
    List all available website files in a folder.
    
    Args:
        folder: Folder path to search
        
    Returns:
        List of filenames
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        print(f"Folder not found: {folder}")
        return []
    
    files = list(folder_path.glob('*.csv'))
    return [f.name for f in files]
