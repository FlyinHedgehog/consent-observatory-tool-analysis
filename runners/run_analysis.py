"""
Data Analysis Runner

Loads consent records from JSON files and performs analysis.
Saves results to analysis_output/{dataset_name}/ folder.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generate_data import load_data
from src.cookie_analysis import analyze_cookies_and_buttons, save_analysis


def list_available_json_files(examples_dir: str = 'data/examples') -> list:
    """List available JSON files in examples folder, sorted by modification time (newest first)."""
    examples_path = Path(examples_dir)
    if not examples_path.exists():
        return []
    
    files = sorted(examples_path.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    return [f.name for f in files]


def show_menu():
    """Display available JSON files and let user choose."""
    print("\n" + "="*60)
    print("CONSENT OBSERVATORY - DATA ANALYSIS")
    print("="*60)
    
    data_files = list_available_json_files('data/examples')
    if not data_files:
        print("[ERROR] No JSON files found in 'data/examples/' folder!")
        return None
    
    print("\nAvailable data files:")
    for i, data_file in enumerate(data_files, 1):
        print(f"  {i}. {data_file}")
    
    return data_files


def run_analysis(data_file: str, dataset_name: str) -> bool:
    """Run full analysis pipeline and save to dataset-specific folder."""
    
    print("\n" + "-"*60)
    print("STEP 1: LOAD DATA")
    print("-"*60)
    
    print(f"[...] Loading: {data_file}")
    records = load_data(data_file)
    
    if not records:
        print("[ERROR] No data found!")
        return False
    
    print(f"[OK] ✓ Loaded {len(records)} records")
    
    print("\n" + "-"*60)
    print("STEP 2: ANALYZE COOKIES AND BUTTONS")
    print("-"*60)
    
    print("[...] Extracting cookie and button data...")
    df_cookies, df_buttons, df_sites = analyze_cookies_and_buttons(records)
    
    print(f"[OK] ✓ Analysis complete:")
    print(f"     - {len(df_sites)} sites analyzed")
    print(f"     - {len(df_cookies)} cookies found")
    print(f"     - {len(df_buttons)} consent buttons found")
    
    print("\n" + "-"*60)
    print("STEP 3: SAVE RESULTS")
    print("-"*60)
    
    # Create dataset-specific output folder
    output_dir = f'data/output/analysis/{dataset_name}'
    print(f"[...] Saving to: {output_dir}/")
    save_analysis(df_cookies, df_buttons, df_sites, output_dir)
    
    print(f"[OK] ✓ Results saved")
    print(f"     - cookies.xlsx")
    print(f"     - buttons.xlsx")
    print(f"     - sites_summary.xlsx")
    
    print("\n[COMPLETE] ✓ Analysis finished!")
    print("="*60)
    
    return True


if __name__ == '__main__':
    print("\n[START] Analysis Module")
    
    data_files = show_menu()
    if not data_files:
        exit(1)
    
    choice = input("\nEnter data file number (or 'q' to quit): ").strip()
    if choice.lower() == 'q':
        print("[CANCELLED] Exiting...")
        exit(0)
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(data_files):
            data_file = data_files[idx]  # Just the filename, not full path
            dataset_name = Path(data_files[idx]).stem  # filename without extension
        else:
            print("[ERROR] Invalid choice!")
            exit(1)
    except ValueError:
        print("[ERROR] Invalid input!")
        exit(1)
    
    success = run_analysis(data_file, dataset_name)
    exit(0 if success else 1)
