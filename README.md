# Consent Observatory Analysis

Analysis of cookie consent mechanisms on websites, comparing EU vs US traffic using Consent Observatory scraper data.

## Data

The data comes from the [Consent Observatory](https://consentobservatory.org/) server, which crawls websites and records cookie consent interfaces. Each record is a JSON object (one per line) with:

- **`url`** – Website URL
- **`time`** – Crawl timestamp
- **`requestStrategy`** – Crawl strategy
- **`data`** – Output from gatherers:
  - **CookieGatherer** – Cookies (`name`, `domain`, `secure`, `httpOnly`, `sameSite`, etc.)
  - **ButtonGatherer** – Consent buttons (`text`, `html`, visibility)
  - **NormalizedWordButtonGatherer** – Normalized button labels with `category` (Accept, Reject, Settings, etc.)
  - **EventListenerGatherer** – Event-bound consent elements
  - **CheckboxGatherer** – Consent checkboxes
  - **WordBoxGatherer** – Text-based consent detections (`hits`, `detections`, etc.)
  - **CMPGatherer** – Consent Management Platforms
  - **IABJSGatherer** – IAB TCF API detection (`tcfapiDetected`, `pingResult`)
  - **ScreenshotGatherer** – Base64 screenshots (`onDomContentLoaded`, `onPageWait`)
  - **DOMGatherer** – Raw HTML (`dom`)
  - **VisibilityAnalyzer** – Visibility metadata (may be empty)

### Data files

- **`data/examples/tranco_germany.json`** – EU traffic (Germany)
- **`data/examples/tranco_us.json`** – US traffic

Websites are drawn from the [Tranco](https://tranco-list.eu/) top-list (`data/websites/`).

## Usage

Run the analysis notebook:

```
notebooks/results_analysis.ipynb
```

It loads the EU and US JSON data, restricts to websites present in both crawls, and produces figures and table values for the Results section of the paper.
