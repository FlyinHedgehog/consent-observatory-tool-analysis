# Consent Observatory Analysis

Analysis of cookie consent mechanisms on websites, comparing Germany vs USA traffic using Consent Observatory scraper data.

## Data

The data comes from the [Consent Observatory Tool](https://consentobservatory.org/) run from local machine, which crawls websites and records cookie consent interfaces. Each record is a JSON object (one per line) with:

- **`url`** – Website URL
- **`time`** – Crawl timestamp
- **`requestStrategy`** – Crawl strategy
- **`data`** – Output from gatherers:
  - **CookieGatherer** – Cookies (`name`, `domain`, `secure`, `httpOnly`, `sameSite`, etc.)
  - **ButtonGatherer** – Consent buttons (`text`, `html`, visibility)
  - **NormalizedWordButtonGatherer** – Has normalized button labels with `category`
  - **EventListenerGatherer** – Event-bound consent elements
  - **CheckboxGatherer** – Consent checkboxes
  - **WordBoxGatherer** – Text-based consent detections (`hits`, `detections`, etc.)
  - **CMPGatherer** – Consent Management Platforms
  - **IABJSGatherer** – IAB TCF API detection (`tcfapiDetected`, `pingResult`)
  - **ScreenshotGatherer** – Base64 screenshots (`onDomContentLoaded`, `onPageWait`)
  - **DOMGatherer** – Raw HTML (`dom`)
  - **VisibilityAnalyzer** – Visibility metadata

### Data files

- **`data/examples/tranco-germany.json`** – Germany traffic
- **`data/examples/tranco-us.json`** – USA traffic
- **`data/examples/errors-germany.json`** – Germany traffic errors
- **`data/examples/errors-us.json`** – USA traffic errors

Websites are drawn from the [Tranco](https://tranco-list.eu/) top-list. You can find them under `data/websites/`.
