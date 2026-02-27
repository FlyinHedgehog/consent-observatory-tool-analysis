import json
import csv
from pathlib import Path

# =====================================================================
# Configuration
# =====================================================================
# We hardcode the input and output directories to make the script simple
# and easy to run without needing complex command-line arguments.
INPUT_DIR = Path('data/examples')
OUTPUT_DIR = Path('data/output')

def process_file(json_path, cookie_writer, button_writer, cmp_writer):
    """
    Reads a JSON file containing scraped website data line by line.
    Extracts Cookies, Buttons, and Consent Management Platform (CMP) info 
    and writes them directly to CSV files.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            # ---------------------------------------------------------
            # 1. load the JSON record for a single website
            # ---------------------------------------------------------
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"  Warning: skipped invalid JSON on line {line_num} in {json_path}")
                continue

            url = record.get("url", "Unknown URL")
            data_block = record.get("data", {})

            # ---------------------------------------------------------
            # 2. Extract Cookies
            # ---------------------------------------------------------
            # we look inside the "CookieGatherer" block of the JSON
            cookie_gatherer = data_block.get("CookieGatherer", {})
            for cookie in cookie_gatherer.get("cookies", []):
                cookie_writer.writerow({
                    'website_url': url,
                    'cookie_name': cookie.get('name', ''),
                    'value': cookie.get('value', ''),
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', ''),
                    'expires': cookie.get('expires', ''),
                    'size': cookie.get('size', ''),
                    'httpOnly': cookie.get('httpOnly', ''),
                    'secure': cookie.get('secure', ''),
                    'session': cookie.get('session', ''),
                    'sameSite': cookie.get('sameSite', ''),
                    'priority': cookie.get('priority', ''),
                    'sameParty': cookie.get('sameParty', ''),
                    'sourceScheme': cookie.get('sourceScheme', ''),
                    'sourcePort': cookie.get('sourcePort', '')
                })

            # ---------------------------------------------------------
            # 3. Extract Buttons (Accept, Reject, etc.)
            # ---------------------------------------------------------
            # we use "NormalizedWordButtonGatherer" because it already 
            # categorizes buttons (1=Accept, 2=Reject, etc.)
            button_gatherer = data_block.get("NormalizedWordButtonGatherer", {})
            for detection in button_gatherer.get("detectionsArray", []):
                # pull out the visual styles to check for patterns
                vis = detection.get("visibilityAnalysis", {})
                button_writer.writerow({
                    'website_url': url,
                    'text': detection.get('text', ''),
                    'normalized': detection.get('normalized', ''),
                    'element': detection.get('element', ''),
                    'category': detection.get('category', ''),
                    'distance': detection.get('distance', ''),
                    'popup': detection.get('popup', ''),
                    'vis_color': vis.get('color', ''),
                    'vis_backgroundColor': vis.get('backgroundColor', ''),
                    'vis_fontSize': vis.get('fontSize', ''),
                    'vis_fontWeight': vis.get('fontWeight', ''),
                    'vis_clickability': vis.get('clickability', ''),
                    'vis_score': vis.get('score', '')
                })

            # ---------------------------------------------------------
            # 4. Extract CMPs (Consent Management Platforms)
            # ---------------------------------------------------------
            # finds out if a third-party tool like OneTrust or Cookiebot is used
            cmp_gatherer = data_block.get("CMPGatherer", {})
            for cmp in cmp_gatherer.get("CMPs", []):
                cmp_writer.writerow({
                    'website_url': url,
                    'cmp_name': cmp.get('CMP_name', '')
                })


def open_region_writers(region, cookie_headers, button_headers, cmp_headers):
    """
    Creates three CSV files for a specific region (e.g. cookies_germany.csv)
    Returns the raw file objects (so we can close them later) and the CSV writers.
    """
    # Open the files in write mode
    fc = open(OUTPUT_DIR / f'cookies_{region}.csv', 'w', newline='', encoding='utf-8')
    fb = open(OUTPUT_DIR / f'buttons_{region}.csv', 'w', newline='', encoding='utf-8')
    fm = open(OUTPUT_DIR / f'cmps_{region}.csv',    'w', newline='', encoding='utf-8')

    # Create DictWriters (standard comma-separated)
    wc = csv.DictWriter(fc, fieldnames=cookie_headers)
    wb = csv.DictWriter(fb, fieldnames=button_headers)
    wm = csv.DictWriter(fm, fieldnames=cmp_headers)

    # Write the header row to each file
    wc.writeheader()
    wb.writeheader()
    wm.writeheader()
    
    return (fc, fb, fm), (wc, wb, wm)


def main():
    # Make sure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting data from '{INPUT_DIR}' into '{OUTPUT_DIR}'...\n")

    # Define what columns we want in our output CSVs
    cookie_headers = [
        'website_url', 'cookie_name', 'value', 'domain', 'path', 'expires',
        'size', 'httpOnly', 'secure', 'session', 'sameSite',
        'priority', 'sameParty', 'sourceScheme', 'sourcePort'
    ]
    button_headers = [
        'website_url', 'text', 'normalized', 'element', 'category', 'distance', 'popup',
        'vis_color', 'vis_backgroundColor', 'vis_fontSize', 'vis_fontWeight',
        'vis_clickability', 'vis_score'
    ]
    cmp_headers   = ['website_url', 'cmp_name']
    error_headers = ['timestamp', 'website_url', 'error_type', 'error_message', 'region']

    # =====================================================================
    # Step A: Process Standard Scrapes (tranco-*.json)
    # =====================================================================
    # find all files that look like 'tranco-germany.json', 'tranco-us.json', etc.
    standard_files = sorted(INPUT_DIR.glob("tranco-*.json"))
    if not standard_files:
        print(f"No standard data files found in {INPUT_DIR}")

    for file_path in standard_files:
        # extract the region name from the filename (e.g. "germany" from "tranco-germany")
        # i am not hardcoding the regions, so that different regions can be added later
        region = file_path.stem.replace('tranco-', '')
        print(f"Processing websites for: {region.upper()}")
        
        # open matched CSVs for this specific region
        file_handles, writers = open_region_writers(region, cookie_headers, button_headers, cmp_headers)
        
        try:
            # Send the file and the three writers to our parsing function
            process_file(file_path, writers[0], writers[1], writers[2])
        finally:
            # Always make sure we close files so data is actually saved to disk
            for fh in file_handles:
                fh.close()

    # =====================================================================
    # Step B: Process Error Logs (errors-*.json)
    # =====================================================================
    print("\nProcessing Error logs...")
    
    # we create a separate error CSV for each region to match the other data types
    for file_path in sorted(INPUT_DIR.glob("errors-*.json")):
        region = file_path.stem.replace('errors-', '')
        print(f"Processing errors for: {region.upper()}")
        
        output_file = OUTPUT_DIR / f'errors_{region}.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f_out:
            writer_errors = csv.DictWriter(f_out, fieldnames=error_headers)
            writer_errors.writeheader()

            with open(file_path, 'r', encoding='utf-8') as f_in:
                for line_num, line in enumerate(f_in, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
                    writer_errors.writerow({
                        'timestamp':     rec.get('timestamp', ''),
                        'website_url':   rec.get('url', ''),
                        'error_type':    rec.get('errorType', ''),
                        'error_message': rec.get('error', ''),
                        'region':        region
                    })

    print("\nExtraction complete! Your CSVs are ready.")


if __name__ == "__main__":
    main()
