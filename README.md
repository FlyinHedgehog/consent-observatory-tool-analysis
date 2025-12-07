# consent-observatory-tool-analysis

Jupyter notebook and helper utilities for analyzing consent popups collected by the Consent Observatory tooling.

Contents
- `consent_observatory_run.ipynb` — analysis notebook (run after installing requirements).
- `notebook_utils.py` — helper functions for loading records, categorization, and submission helper.

Quick start
1. Create and activate a Python environment (Python 3.8+ recommended).
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Open `consent_observatory_run.ipynb` in Jupyter or VS Code and run cells in order.

Notes
- Example data is intentionally excluded from the repository to keep the repo small. Place any small example zips or JSONs in an `examples/` folder if needed.
# Consent Observatory — Shareable Full Setup

This repository contains Jupyter notebooks and helper scripts for running the Consent Observatory analysis locally. 

**Quick Overview**
- `consent_observatory_run.ipynb`: notebook to submit jobs or analyze results.
- `examples/`: contains a small sample `data.json` and a script to make `data-example.zip` that matches the format the notebook expects.

**Project Setup**
- Clone this repository:

```
git clone <your-repo-url>
cd <repo-folder>
```

- Create a Python virtual environment and activate it (Windows PowerShell example):

```
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

- Install requirements:

```
pip install -r requirements.txt
```

**Generate Example ZIP (so you can run the notebook without a running server)**

1. Create a sample zip used by the notebook:

```
python examples/make_example_zip.py
```

This writes `examples/data-example.zip` containing a file named `data.json` with newline-delimited JSON records (the format `consent_observatory_run.ipynb` expects).

2. Run the notebook (`consent_observatory_run.ipynb`) in Jupyter or VS Code. Two ways to let the notebook find the example zip:

- Option A (easy): copy the example zip into the expected completed directory the notebook uses:

```
mkdir -p consent-observatory.eu\data\completed
copy examples\data-example.zip consent-observatory.eu\data\completed\data-example.zip
```

- Option B (no file copy): before running the Analysis cell, set the `COMPLETED_DIR` variable in the notebook to the `examples/` folder. In a code cell insert and run:

```python
from pathlib import Path
COMPLETED_DIR = Path.cwd() / 'examples'
```

**Notes about external tools & paths**
- The notebook is mostly self-contained and requires only standard Python packages (`pandas`, `requests`, `jupyter`). If your workflow requires additional tools, mention them here and provide install steps.
- Watch out for absolute paths. If you see hard-coded paths like `C:\Users\YourName\...`, change them to relative paths or update the README so contributors edit paths to match their machines.

**How the example zip is structured**
- The notebook's `load_records_from_zip` looks for a file with a name ending in `data.json` inside the zip and expects newline-delimited JSON records.
- `examples/make_example_zip.py` creates that exact structure.

**How to run a quick analysis from the example zip**
1. Generate the zip as above.
2. Start Jupyter: `jupyter notebook` or open `consent_observatory_run.ipynb` in VS Code and run cells.
3. Ensure the Analysis cell locates `data-example.zip` (either via copy or by setting `COMPLETED_DIR`).

**If you want to run the entire server/submission flow**
- The notebook uses `SERVER_URL` (default `http://localhost:5173/`) in the Submission cell. Update that if your dev server runs at a different host/port.
- If POST submission fails, use the fallback writer cell to create a job JSON in `jobs_root_test/pending`.
