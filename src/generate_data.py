"""
Data Generation Module
======================

High-level interface for submitting URLs to the consent-observatory server
and loading analysis results.

This module provides simplified wrapper functions around the lower-level
data_loader module, making it easier to use in scripts and notebooks.

Usage:
    from src.generate_data import generate_data, load_data
    
    # Submit URLs for analysis
    job_id, zip_name = generate_data(
        server_url='http://localhost:5173',
        urls=['https://example.com'],
        user_email='researcher@example.com',
        ruleset_name='Scrape-O-Matic Data Gatherers'
    )
    
    # Load existing data
    records = load_data('my_dataset.json')
"""

from typing import List, Optional, Tuple

from .data_loader import load_any_records, submit_urls_to_server


# =============================================================================
# DATA GENERATION
# =============================================================================

def generate_data(
    server_url: str,
    urls: List[str],
    user_email: str,
    ruleset_name: str,
    timeout: int = 240
) -> Tuple[Optional[str], Optional[str]]:
    """
    Submit URLs to the consent-observatory server for analysis.
    
    This is a convenience wrapper around submit_urls_to_server that
    uses default port detection and timeout settings.
    
    Args:
        server_url: Base URL of the consent-observatory server
                    (e.g., 'http://localhost:5173')
        urls: List of URLs to analyze (should include https://)
        user_email: Email address for job notifications
        ruleset_name: Name of the analysis ruleset to use
                      (e.g., 'Scrape-O-Matic Data Gatherers')
        timeout: Maximum seconds to wait for results (default: 240)
    
    Returns:
        Tuple of (job_id, completed_zip_name):
            - job_id: Server-assigned job identifier (or None)
            - completed_zip_name: Filename of results ZIP (or None)
    
    Example:
        >>> job_id, zip_file = generate_data(
        ...     server_url='http://localhost:5173',
        ...     urls=['https://google.com', 'https://facebook.com'],
        ...     user_email='test@example.com',
        ...     ruleset_name='Scrape-O-Matic Data Gatherers'
        ... )
        >>> if zip_file:
        ...     print(f"Results saved to: {zip_file}")
    """
    return submit_urls_to_server(
        server_url=server_url,
        urls=urls,
        user_email=user_email,
        ruleset_name=ruleset_name,
        timeout=timeout
    )


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data(data_file: Optional[str] = None) -> List[dict]:
    """
    Load consent-observatory records from a data file.
    
    If no file is specified, automatically discovers the most recent
    JSON file in the data/examples folder.
    
    Args:
        data_file: Path to specific data file (ZIP or JSON).
                   Can be relative to data/examples or absolute path.
                   If None, auto-discovers from examples folder.
    
    Returns:
        List of record dictionaries, each containing:
            - 'url': The analyzed website URL
            - 'data': Dictionary of gatherer outputs
    
    Example:
        >>> # Load specific file
        >>> records = load_data('tranco_QWJY4.json')
        >>> print(f"Loaded {len(records)} records")
        
        >>> # Auto-discover newest file
        >>> records = load_data()
    """
    return load_any_records(example_file=data_file)
