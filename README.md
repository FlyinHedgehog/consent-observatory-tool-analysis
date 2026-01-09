# Consent Observatory Analysis Tools

Analysis and data extraction tools for the Consent Observatory project.

## Overview

This project analyzes cookie consent mechanisms on websites by:
1. **Generating data** - Submitting websites to the Consent Observatory server for analysis 
Important Note: The server component is not included in this repository. You need to set up yourself. oopssie
2. **Processing results** - Extracting cookie and button data from server responses 
3. **Exporting analysis** - Creating Excel files for further analysis

## Quick Start

### Usage

**Run Analysis on JSON Data:**
```bash
python runners/run_analysis.py
```
- Select a dataset file from `examples/` folder
- Generates three Excel files:
  - `cookies.xlsx` - Cookie data with security metadata
  - `buttons.xlsx` - Consent button detections
  - `sites_summary.xlsx` - Per-site summary

**Generate Data from URLs:**
```bash
python runners/run_generation.py
```
important Note: You need to have your own Consent Observatory server running to use this feature.
- Submit websites to Consent Observatory server
- Retrieve and save analysis results

## Data Flow

```
URLs → Server Analysis → ZIP Results → Python Processing → Excel Export
```

## Folder Structure

- `src/` - Core analysis modules
  - `cookie_analysis.py` - Cookie and button extraction
  - `generate_data.py` - Server submission
  - `website_submitter.py` - Website file reader and submitter
  - `notebook_utils.py` - Utilities
- `runners/` - Entry points
  - `run_analysis.py` - Analyze saved data
  - `run_generation.py` - Submit new analysis
- `examples/` - Sample data files
- `notebooks/` - Jupyter notebooks for exploration

## Output Format

### cookies.xlsx
- url, cookie_name, domain, secure, httpOnly, sameSite, session

### buttons.xlsx
- url, button_text, html, is_visible

### sites_summary.xlsx
- url, cookies_found, buttons_found, has_secure_cookies
