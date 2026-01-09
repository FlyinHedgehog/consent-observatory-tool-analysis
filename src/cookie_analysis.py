"""
Proper cookie and button option analysis.

Extracts real cookie information and cookie-related button options from server data.
"""

import pandas as pd
from typing import List, Dict, Any


def analyze_cookies_and_buttons(records: List[Dict[str, Any]]):
    """
    Analyze cookie data and button options from records.
    
    Returns:
        - cookies_df: Info about cookies found on each site
        - buttons_df: Info about consent/cookie buttons found
        - sites_summary: Summary counts per site
    """
    
    cookies_rows = []
    buttons_rows = []
    sites_summary = []
    
    for record in records:
        url = record.get('url', 'unknown')
        
        # ===== COOKIES =====
        if 'CookieGatherer' in record.get('data', {}):
            cg = record['data']['CookieGatherer']
            cookies = cg.get('cookies', [])
            
            for cookie in cookies:
                cookies_rows.append({
                    'url': url,
                    'cookie_name': cookie.get('name', ''),
                    'domain': cookie.get('domain', ''),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': cookie.get('sameSite', ''),
                    'session': cookie.get('session', False),
                })
        
        # ===== BUTTONS =====
        if 'ButtonGatherer' in record.get('data', {}):
            bg = record['data']['ButtonGatherer']
            buttons = bg.get('detectionsArray', [])
            
            for button in buttons:
                text = button.get('text', '').strip()
                if text:
                    buttons_rows.append({
                        'url': url,
                        'button_text': text,
                        'html': button.get('html', '')[:500],  # Limit HTML
                        'is_visible': button.get('visibilityAnalysis', {}) is not None,
                    })
        
        # ===== SITE SUMMARY =====
        cookie_count = len(record.get('data', {}).get('CookieGatherer', {}).get('cookies', []))
        button_count = len(record.get('data', {}).get('ButtonGatherer', {}).get('detectionsArray', []))
        
        sites_summary.append({
            'url': url,
            'cookies_found': cookie_count,
            'buttons_found': button_count,
            'has_secure_cookies': any(
                c.get('secure') for c in record.get('data', {}).get('CookieGatherer', {}).get('cookies', [])
            ),
        })
    
    # Convert to DataFrames
    df_cookies = pd.DataFrame(cookies_rows)
    df_buttons = pd.DataFrame(buttons_rows)
    df_sites = pd.DataFrame(sites_summary)
    
    return df_cookies, df_buttons, df_sites


def save_analysis(df_cookies, df_buttons, df_sites, output_dir: str = "analysis_output"):
    """Save the analysis dataframes to Excel files."""
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save all dataframes in one loop
    dfs = {
        'cookies.xlsx': df_cookies,
        'buttons.xlsx': df_buttons,
        'sites_summary.xlsx': df_sites,
    }
    
    for filename, df in dfs.items():
        if not df.empty:
            df.to_excel(output_path / filename, index=False, sheet_name='Data')
            print(f"[+] Saved {len(df)} records to {filename}")
