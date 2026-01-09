"""
Data Generation Module

Handles submitting URLs to the consent-observatory server and retrieving results.
"""

from typing import Optional, Tuple, List
from .data_loader import submit_urls_to_server, load_any_records


def generate_data(
    server_url: str,
    urls: List[str],
    user_email: str,
    ruleset_name: str,
    timeout: int = 240
) -> Tuple[Optional[str], Optional[str]]:
    """
    Submit URLs to server and retrieve job results.
    
    Returns (job_id, completed_zip_name).
    """
    return submit_urls_to_server(
        server_url=server_url,
        urls=urls,
        user_email=user_email,
        ruleset_name=ruleset_name,
        timeout=timeout
    )


def load_data(data_file: Optional[str] = None) -> List[dict]:
    """
    Load records from file or fall back to examples.
    
    Args:
        data_file: Path to specific data file (zip or json)
        
    Returns:
        List of record dictionaries
    """
    return load_any_records(example_file=data_file)
