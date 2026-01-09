"""
Utilities for loading consent-observatory records and building option/category views.

Functions exposed for the notebook:
- load_any_records: find records from in-memory, examples/, or completed job zips.
- build_options_dataframe: produce a wide table of options per site with category flags.
- build_option_views: return wide table, long-form options, and category summaries for visualization.
"""
from pathlib import Path
import json
import zipfile
import time
import requests
import urllib.parse
from typing import List, Any, Dict, Set, Tuple, Optional

import pandas as pd


# -------------------------
# Record loading helpers
# -------------------------
def load_records_from_zip(zip_path: Path) -> List[Dict[str, Any]]:
    """Read newline-delimited JSON records from the first data.json inside a zip."""
    records_local = []
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as z:
            names = [n for n in z.namelist() if n.endswith('data.json')]
            if not names:
                return records_local
            with z.open(names[0]) as f:
                for raw in f:
                    try:
                        line = raw.decode('utf-8').strip()
                    except Exception:
                        continue
                    if not line:
                        continue
                    try:
                        records_local.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []
    return records_local


def load_records_from_json_file(json_path: Path) -> List[Dict[str, Any]]:
    """Load newline-delimited JSON records from a file."""
    recs = []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    recs.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return recs


def load_any_records(existing_records: List[Dict[str, Any]] = None,
                     examples_dir: Path = None,
                     completed_dir: Path = None,
                     example_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load records from specified file or fall back to examples.
    
    If `example_file` is provided, ONLY load from that file (no fallback).
    If no file is specified, try examples/ folder.
    """
    if existing_records:
        return existing_records
    
    cwd = Path.cwd()
    examples_dir = examples_dir or cwd / 'examples'
    completed_dir = completed_dir or cwd / 'consent-observatory.eu' / 'data' / 'completed'

    # If an explicit file was requested, ONLY load from that file
    if example_file:
        ef = Path(example_file)
        if not ef.is_absolute():
            ef = examples_dir / ef
        
        if ef.exists():
            if ef.suffix == '.zip':
                recs = load_records_from_zip(ef)
                if recs:
                    return recs
            elif ef.suffix in ('.json', '.ndjson'):
                recs = load_records_from_json_file(ef)
                if recs:
                    return recs
        
        # Requested file not found or couldn't be loaded
        return []

    # No specific file requested - try examples folder
    ex_json_candidates = sorted(examples_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for cand in ex_json_candidates:
        recs = load_records_from_json_file(cand)
        if recs and any(('url' in r or 'pageUrl' in r or 'requestedUrl' in r) for r in recs):
            return recs

    return []


def list_example_files(examples_dir: Path = None) -> List[str]:
    """Return a sorted list of example filenames found in `examples/`.

    Useful for interactive notebooks to present choices to the user.
    """
    cwd = Path.cwd()
    examples_dir = examples_dir or cwd / 'examples'
    if not examples_dir.exists():
        return []
    files = [p.name for p in examples_dir.iterdir() if p.is_file()]
    return sorted(files)


# -------------------------
# Submission helpers
# -------------------------
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
            # Use the provided timeout parameter, but at least 60 seconds
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
                # Always wait for completed zip, even if job_id is returned
                # Poll for up to the timeout duration
                steps = max(1, timeout // 3)
                elapsed = 0
                progress_interval = 20  # Print every 20 * 3 = 60 seconds (1 minute)
                
                print(f"\n[...] Waiting for server to process (max {timeout} seconds)...")
                
                for step in range(steps):
                    time.sleep(3)
                    elapsed += 3
                    
                    # Print progress every minute
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


# -------------------------
# Option extraction & categorization
# -------------------------
# Revised category mapping: include common phrases and translations to reduce the 'other' bucket.
# Categories: accept, reject, reject_all, customize, info, confirm, essential, dismiss
_CATEGORY_KEYWORDS = {
    'accept': [
        'accept', 'accept all', 'accept cookies', 'agree', 'allow', 'allow all', 'allow cookies',
        'consent', 'agree and continue', 'accept and continue', 'accepter', 'aceptar', 'akzeptieren', 'einverstanden', 'accetta', 'accepteren'
    ],
    'reject': [
        'reject', 'decline', 'deny', 'no thanks', 'opt-out', 'do not accept', 'no, thanks', 'ablehnen', 'nein', 'rechazar', 'refuser', 'rifiuta', 'weigeren'
    ],
    'reject_all': [
        'reject all', 'decline all', 'deny all', 'decline all cookies', 'reject all cookies', 'ablehnen alle', 'rechazar todo', 'rifiuta tutto'
    ],
    'customize': [
        'settings', 'preferences', 'manage', 'customize', 'configure', 'cookie settings', 'cookie preferences',
        'einstellungen', 'paramètres', 'configurar', 'impostazioni', 'instellingen', 'view preferences'
    ],
    'info': [
        'more', 'details', 'learn more', 'more info', 'about', 'info', 'why', 'read more', 'weitere informationen', 'mehr erfahren'
    ],
    'confirm': [
        'save', 'apply', 'speichern', 'confirm', 'save preferences', 'save settings', 'confirm selection', 'guardar', 'enregistrer', 'salva'
    ],
    'essential': [
        'only necessary', 'essential only', 'necessary cookies', 'only essential', 'essential cookies', 'nur notwendige', 'solo los necesarios'
    ],
    'dismiss': [
        'close', 'dismiss', 'got it', 'ok thanks', 'weiter', 'schliessen', 'schließen', 'cerrar', 'chiudi'
    ],
}


def _collect_strings(obj: Any) -> List[str]:
    out: List[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_strings(v))
    elif isinstance(obj, list):
        for i in obj:
            out.extend(_collect_strings(i))
    return out


def _is_noise(text: str) -> bool:
    """Filter out noise, empty values, CSS, HTML fragments, numbers, special chars."""
    st = (text or '').strip()
    if not st or len(st) == 0:
        return True
    # Numbers, special patterns, HTML/CSS noise
    if st in ('none', 'None', '400', '0px', 'primary', 'Medium', 'Secure', '/', '/'):
        return True
    # URLs (contain ://)
    if '://' in st:
        return True
    if st.startswith('<') or st.endswith('>'):  # HTML fragment
        return True
    if st.startswith('0') and st[1:].replace('px', '').isdigit():  # CSS pixel values
        return True
    if len(st) <= 2:  # Too short
        return True
    if not any(c.isalpha() for c in st):  # No alphabetic chars
        return True
    return False


def _extract_options_from_record(record: Dict[str, Any]) -> List[str]:
    """Heuristically gather short strings that look like button/option labels from a record."""
    opts: Set[str] = set()
    button_like_fields = (
        'buttons', 'buttonList', 'buttonsFound', 'buttonTexts', 'detectedButtons', 'cta',
        'actionButtons', 'controls', 'options', 'consentOptions', 'nodeText', 'innerText',
        'textContent', 'menu'
    )
    for key in button_like_fields:
        v = record.get(key)
        if isinstance(v, str):
            st = v.strip()
            if not _is_noise(st):
                opts.add(st)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    st = item.strip()
                    if not _is_noise(st):
                        opts.add(st)
                elif isinstance(item, dict):
                    for tk in ('text', 'label', 'value', 'title', 'ariaLabel'):
                        if item.get(tk):
                            st = str(item.get(tk)).strip()
                            if not _is_noise(st):
                                opts.add(st)
        elif isinstance(v, dict):
            for tk in ('text', 'label', 'value', 'title', 'ariaLabel'):
                if v.get(tk):
                    st = str(v.get(tk)).strip()
                    if not _is_noise(st):
                        opts.add(st)

    for s in _collect_strings(record):
        st = s.strip()
        if _is_noise(st):
            continue
        if len(st) <= 60 and len(st.split()) <= 6:
            opts.add(st)

    return sorted(x for x in opts if x)


def _categorize_option(text: str) -> Set[str]:
    """Categorize an option text; prioritize more specific matches over generic ones."""
    s = (text or '').lower().strip()
    if not s:
        return {'other'}
    
    cats: Set[str] = set()
    
    # Prioritize specific multi-word phrases first
    specific_phrases = {
        'reject_all': ['reject all', 'decline all', 'deny all', 'decline all cookies', 'reject all cookies', 'ablehnen alle', 'rechazar todo', 'rifiuta tutto'],
        'reject': ['reject', 'decline', 'deny', 'ablehnen', 'rechazar', 'refuser', 'rifiuta', 'weigeren'],
        'accept': ['accept all', 'accept cookies', 'agree and', 'akzeptieren', 'accepteren'],
        'essential': ['only necessary', 'essential only', 'necessary cookies', 'only essential', 'essential cookies', 'nur notwendige', 'solo los necesarios'],
        'dismiss': ['got it', 'ok thanks', 'weiter', 'schliessen', 'schließen', 'cerrar', 'chiudi'],
        'confirm': ['save preferences', 'save settings', 'confirm selection', 'guardar', 'enregistrer', 'salva'],
    }
    
    for category, phrases in specific_phrases.items():
        for phrase in phrases:
            if phrase in s:
                cats.add(category)
                break
    
    # If a specific category matched, return it (avoid generic overlaps)
    if cats:
        return cats
    
    # Fall back to broader keywords
    broader_keywords = {
        'accept': ['accept', 'agree', 'allow', 'consent', 'accepter', 'aceptar', 'accetta'],
        'reject': ['reject', 'decline', 'deny', 'nein'],
        'customize': ['settings', 'preferences', 'manage', 'customize', 'configure', 'cookie', 'einstellungen', 'paramètres', 'configurar', 'impostazioni', 'instellingen'],
        'info': ['more', 'details', 'learn more', 'about', 'info', 'why', 'weitere informationen', 'mehr erfahren'],
        'confirm': ['save', 'apply', 'confirm', 'speichern'],
        'dismiss': ['close', 'dismiss', 'ok'],
    }
    
    for category, keywords in broader_keywords.items():
        for kw in keywords:
            if kw in s:
                cats.add(category)
                break
    
    if not cats:
        cats.add('other')
    return cats


# -------------------------
# Public analysis helpers
# -------------------------
def build_options_dataframe(recs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Wide table with options and category flags per URL."""
    rows = []
    for r in recs:
        url = r.get('url') or r.get('pageUrl') or r.get('requestedUrl') or r.get('id')
        opts_list = _extract_options_from_record(r)
        
        # Deduplicate options by category; if an option matches multiple categories,
        # assign it to the first (most specific) one
        cats_map = {
            'accept': [], 'reject': [], 'reject_all': [], 'customize': [],
            'info': [], 'confirm': [], 'essential': [], 'dismiss': [], 'other': []
        }
        assigned = set()
        
        for o in opts_list:
            if o in assigned:
                continue
            # Get all matching categories, sorted by priority
            cats_priority = ['reject_all', 'essential', 'accept', 'reject', 'customize', 'confirm', 'info', 'dismiss', 'other']
            matched_cats = _categorize_option(o)
            primary_cat = next((c for c in cats_priority if c in matched_cats), 'other')
            if primary_cat in cats_map:
                cats_map[primary_cat].append(o)
                assigned.add(o)
        
        rows.append({
            'url': url,
            'options': opts_list,
            'n_options': len(opts_list),
            'accept_opts': cats_map['accept'],
            'reject_opts': cats_map['reject'],
            'reject_all_opts': cats_map['reject_all'],
            'customize_opts': cats_map['customize'],
            'info_opts': cats_map['info'],
            'confirm_opts': cats_map['confirm'],
            'essential_opts': cats_map['essential'],
            'dismiss_opts': cats_map['dismiss'],
            'other_opts': cats_map['other'],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df['has_accept'] = df['accept_opts'].apply(bool)
    df['has_reject'] = df['reject_opts'].apply(bool)
    df['has_reject_all'] = df['reject_all_opts'].apply(bool)
    df['has_customize'] = df['customize_opts'].apply(bool)
    df['has_info'] = df['info_opts'].apply(bool)
    df['has_confirm'] = df['confirm_opts'].apply(bool)
    df['has_essential'] = df['essential_opts'].apply(bool)
    df['has_dismiss'] = df['dismiss_opts'].apply(bool)
    df['accept_preview'] = df['accept_opts'].apply(lambda l: ', '.join(l[:3]))
    df['reject_preview'] = df['reject_opts'].apply(lambda l: ', '.join(l[:3]))
    df['customize_preview'] = df['customize_opts'].apply(lambda l: ', '.join(l[:3]))
    df['reject_all_preview'] = df['reject_all_opts'].apply(lambda l: ', '.join(l[:3]))
    df['essential_preview'] = df['essential_opts'].apply(lambda l: ', '.join(l[:3]))
    return df


def build_option_views(recs: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Produce wide table, long-form table, per-site summary, and overall category counts.
    Returns (df_wide, df_long, summary_by_site, summary_overall).
    """
    df_wide = build_options_dataframe(recs)
    if df_wide.empty:
        return df_wide, pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=int)

    long_rows = []
    for _, row in df_wide.iterrows():
        url = row['url']
        for category in ('accept', 'reject', 'reject_all', 'customize', 'info', 'confirm', 'essential', 'dismiss', 'other'):
            for option in row.get(f'{category}_opts', []):
                long_rows.append({'url': url, 'option': option, 'category': category})
    df_long = pd.DataFrame(long_rows)

    if df_long.empty:
        summary_by_site = pd.DataFrame()
        summary_overall = pd.Series(dtype=int)
    else:
        summary_by_site = df_long.pivot_table(index='url', columns='category', aggfunc='size', fill_value=0)
        summary_overall = df_long['category'].value_counts().sort_index()

    return df_wide, df_long, summary_by_site, summary_overall
