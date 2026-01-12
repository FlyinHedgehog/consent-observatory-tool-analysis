"""
Data Analysis Runner
====================

Command-line interface for analyzing consent-observatory data files.
Loads JSON records and generates Excel reports with cookie and button analysis.

Output Structure:
    data/output/analysis/{dataset_name}/
        ├── cookies.xlsx      - All cookies found
        ├── buttons.xlsx      - Consent button detections
        └── sites_summary.xlsx - Per-site statistics

Usage:
    python runners/run_analysis.py
    
    Then select a data file from the interactive menu.
"""

import sys
from pathlib import Path

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cookie_analysis import analyze_cookies_and_buttons, save_analysis
from src.generate_data import load_data


# =============================================================================
# CONSTANTS
# =============================================================================

# Directory containing input JSON/JSONL data files
EXAMPLES_DIR = 'data/examples'

# Base directory for analysis output
OUTPUT_BASE_DIR = 'data/output/analysis'


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def list_available_json_files(examples_dir: str = EXAMPLES_DIR) -> list:
    """
    List available JSON files, sorted by modification time (newest first).
    
    Args:
        examples_dir: Directory to search for JSON files
    
    Returns:
        List of JSON filenames
    """
    examples_path = Path(examples_dir)
    
    if not examples_path.exists():
        return []
    
    # Sort by modification time, newest first
    files = sorted(
        examples_path.glob('*.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    return [f.name for f in files]


# =============================================================================
# USER INTERFACE
# =============================================================================

def show_menu() -> list:
    """
    Display interactive menu for selecting data files.
    
    Returns:
        List of available data files, or None if none found
    """
    _print_header("CONSENT OBSERVATORY - DATA ANALYSIS")
    
    data_files = list_available_json_files(EXAMPLES_DIR)
    
    if not data_files:
        print(f"[ERROR] No JSON files found in '{EXAMPLES_DIR}/' folder!")
        return None
    
    print("\nAvailable data files:")
    for i, data_file in enumerate(data_files, 1):
        print(f"  {i}. {data_file}")
    
    return data_files


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
# ANALYSIS PIPELINE
# =============================================================================

def run_analysis(data_file: str, dataset_name: str) -> bool:
    """
    Execute the full analysis pipeline for a dataset.
    
    Pipeline Steps:
        1. Load records from JSON file
        2. Extract cookies and buttons
        3. Save results to Excel files
    
    Args:
        data_file: Filename of the JSON data file (in examples dir)
        dataset_name: Name for the output folder (usually file stem)
    
    Returns:
        True if analysis completed successfully, False otherwise
    """
    # -------------------------------------------------------------------------
    # Step 1: Load Data
    # -------------------------------------------------------------------------
    _print_step(1, "LOAD DATA")
    
    print(f"[...] Loading: {data_file}")
    records = load_data(data_file)
    
    if not records:
        print("[ERROR] No data found!")
        return False
    
    print(f"[OK] ✓ Loaded {len(records)} records")
    
    # -------------------------------------------------------------------------
    # Step 2: Analyze Cookies and Buttons
    # -------------------------------------------------------------------------
    _print_step(2, "ANALYZE COOKIES AND BUTTONS")
    
    print("[...] Extracting cookie and button data...")
    df_cookies, df_buttons, df_sites = analyze_cookies_and_buttons(records)
    
    print(f"[OK] ✓ Analysis complete:")
    print(f"     - {len(df_sites)} sites analyzed")
    print(f"     - {len(df_cookies)} cookies found")
    print(f"     - {len(df_buttons)} consent buttons found")
    
    # -------------------------------------------------------------------------
    # Step 3: Save Results
    # -------------------------------------------------------------------------
    _print_step(3, "SAVE RESULTS")
    
    # Create dataset-specific output folder
    output_dir = f'{OUTPUT_BASE_DIR}/{dataset_name}'
    print(f"[...] Saving to: {output_dir}/")
    
    save_analysis(df_cookies, df_buttons, df_sites, output_dir)
    
    print(f"[OK] ✓ Results saved:")
    print(f"     - cookies.xlsx")
    print(f"     - buttons.xlsx")
    print(f"     - sites_summary.xlsx")
    
    # -------------------------------------------------------------------------
    # Complete
    # -------------------------------------------------------------------------
    print("\n[COMPLETE] ✓ Analysis finished!")
    print("=" * 60)
    
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """
    Main entry point for the analysis runner.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n[START] Analysis Module")
    
    # Show menu and get available files
    data_files = show_menu()
    if not data_files:
        return 1
    
    # Get user selection
    choice = input("\nEnter data file number (or 'q' to quit): ").strip()
    
    if choice.lower() == 'q':
        print("[CANCELLED] Exiting...")
        return 0
    
    # Validate selection
    try:
        idx = int(choice) - 1
        if not 0 <= idx < len(data_files):
            print("[ERROR] Invalid choice!")
            return 1
        
        data_file = data_files[idx]
        dataset_name = Path(data_file).stem  # Filename without extension
        
    except ValueError:
        print("[ERROR] Invalid input!")
        return 1
    
    # Run analysis
    success = run_analysis(data_file, dataset_name)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
