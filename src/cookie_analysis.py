"""
Cookie and Consent Button Analysis Module
==========================================

This module extracts and analyzes cookie information and consent-related 
button data from consent-observatory server responses.

Key Features:
    - Extracts cookie metadata (name, domain, security flags)
    - Identifies consent buttons and their visibility
    - Generates per-site summaries with aggregated statistics

Data Sources:
    - CookieGatherer: Raw cookie data from browser
    - ButtonGatherer: Detected consent/cookie banner buttons
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple

import pandas as pd


# =============================================================================
# CONSTANTS
# =============================================================================

# Maximum HTML content length to store (prevents bloated output)
MAX_HTML_LENGTH = 500

# Data gatherer keys used in server responses
COOKIE_GATHERER_KEY = 'CookieGatherer'
BUTTON_GATHERER_KEY = 'ButtonGatherer'


# =============================================================================
# CORE ANALYSIS FUNCTIONS
# =============================================================================

def analyze_cookies_and_buttons(
    records: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Analyze cookie data and consent button options from server records.
    
    This function processes raw data collected by the consent-observatory
    server and extracts structured information about cookies and buttons.
    
    Args:
        records: List of record dictionaries from the server, each containing
                 'url' and 'data' fields with gatherer outputs.
    
    Returns:
        Tuple of three DataFrames:
            - cookies_df: Cookie details (name, domain, security flags)
            - buttons_df: Consent button info (text, visibility)
            - sites_df: Per-site summary statistics
    
    Example:
        >>> records = load_data('example.json')
        >>> cookies, buttons, sites = analyze_cookies_and_buttons(records)
        >>> print(f"Found {len(cookies)} cookies across {len(sites)} sites")
    """
    # Accumulator lists for building DataFrames
    cookies_rows: List[Dict[str, Any]] = []
    buttons_rows: List[Dict[str, Any]] = []
    sites_summary: List[Dict[str, Any]] = []
    
    for record in records:
        url = record.get('url', 'unknown')
        data = record.get('data', {})
        
        # --- Extract Cookie Information ---
        cookies_rows.extend(_extract_cookies(url, data))
        
        # --- Extract Button Information ---
        buttons_rows.extend(_extract_buttons(url, data))
        
        # --- Generate Site Summary ---
        sites_summary.append(_create_site_summary(url, data))
    
    # Convert lists to DataFrames for analysis
    return (
        pd.DataFrame(cookies_rows),
        pd.DataFrame(buttons_rows),
        pd.DataFrame(sites_summary)
    )


def _extract_cookies(url: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract cookie information from CookieGatherer data.
    
    Args:
        url: The website URL
        data: The 'data' field from a server record
    
    Returns:
        List of cookie dictionaries with standardized fields
    """
    cookies = []
    
    if COOKIE_GATHERER_KEY not in data:
        return cookies
    
    cookie_data = data[COOKIE_GATHERER_KEY]
    raw_cookies = cookie_data.get('cookies', [])
    
    for cookie in raw_cookies:
        cookies.append({
            'url': url,
            'cookie_name': cookie.get('name', ''),
            'domain': cookie.get('domain', ''),
            'secure': cookie.get('secure', False),      # HTTPS-only flag
            'httpOnly': cookie.get('httpOnly', False),  # JS-inaccessible flag
            'sameSite': cookie.get('sameSite', ''),     # Cross-site policy
            'session': cookie.get('session', False),    # Session vs persistent
        })
    
    return cookies


def _extract_buttons(url: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract consent button information from ButtonGatherer data.
    
    Args:
        url: The website URL
        data: The 'data' field from a server record
    
    Returns:
        List of button dictionaries with text and visibility info
    """
    buttons = []
    
    if BUTTON_GATHERER_KEY not in data:
        return buttons
    
    button_data = data[BUTTON_GATHERER_KEY]
    detections = button_data.get('detectionsArray', [])
    
    for button in detections:
        text = button.get('text', '').strip()
        
        # Skip empty button text
        if not text:
            continue
        
        buttons.append({
            'url': url,
            'button_text': text,
            'html': button.get('html', '')[:MAX_HTML_LENGTH],  # Truncate HTML
            'is_visible': button.get('visibilityAnalysis') is not None,
        })
    
    return buttons


def _create_site_summary(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create aggregated statistics for a single site.
    
    Args:
        url: The website URL
        data: The 'data' field from a server record
    
    Returns:
        Dictionary with site-level metrics
    """
    # Get raw cookie and button lists
    cookies = data.get(COOKIE_GATHERER_KEY, {}).get('cookies', [])
    buttons = data.get(BUTTON_GATHERER_KEY, {}).get('detectionsArray', [])
    
    return {
        'url': url,
        'cookies_found': len(cookies),
        'buttons_found': len(buttons),
        'has_secure_cookies': any(c.get('secure') for c in cookies),
    }


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def save_analysis(
    df_cookies: pd.DataFrame,
    df_buttons: pd.DataFrame,
    df_sites: pd.DataFrame,
    output_dir: str = "data/output/analysis"
) -> None:
    """
    Save analysis DataFrames to Excel files.
    
    Creates the output directory if it doesn't exist and saves each
    non-empty DataFrame to a separate Excel file.
    
    Args:
        df_cookies: Cookie analysis DataFrame
        df_buttons: Button analysis DataFrame
        df_sites: Site summary DataFrame
        output_dir: Directory path for output files
    
    Output Files:
        - cookies.xlsx: All cookie data
        - buttons.xlsx: All button detections
        - sites_summary.xlsx: Per-site statistics
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Map filenames to DataFrames
    output_files = {
        'cookies.xlsx': df_cookies,
        'buttons.xlsx': df_buttons,
        'sites_summary.xlsx': df_sites,
    }
    
    for filename, df in output_files.items():
        if df.empty:
            continue
        
        filepath = output_path / filename
        df.to_excel(filepath, index=False, sheet_name='Data')
        print(f"[+] Saved {len(df)} records to {filename}")
