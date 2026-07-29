# N100 Financial Intelligence Platform

## Overview

The N100 Financial Intelligence Platform is a Streamlit-based analytics dashboard for analyzing Nifty 100 companies. It provides financial ratio analysis, company profiling, peer comparison, valuation insights, trend analysis, sector analytics, capital allocation analysis, and annual report access using SQLite and Excel datasets.

---

## Features

- Company Profile
- Financial Screener
- Peer Comparison
- Trend Analysis
- Sector Analysis
- Capital Allocation
- Annual Reports
- Valuation Module

---

## Technology Stack

- Python
- Streamlit
- SQLite
- Pandas
- Plotly
- OpenPyXL

---

## Project Structure

```text
N100-Financial-Intelligence
│
├── pages/
├── src/
│   ├── analytics/
│   └── dashboard/
├── data/
├── output/
├── reports/
└── README.md
```

---

## Run the Dashboard

```bash
streamlit run src/dashboard/app.py
```

---

## Run Valuation Module

```bash
python src/analytics/valuation.py
```

---

## Output Files

- `output/valuation_summary.xlsx`
- `output/valuation_flags.csv`

---

## Dashboard Screens

### 1. Home
Displays summary KPIs, sector distribution, and top-performing companies.

### 2. Company Profile
Displays company information, financial KPIs, historical trends, and company strengths and weaknesses.

### 3. Screener
Filters companies using multiple financial metrics and supports CSV export.

### 4. Peer Comparison
Compares companies within the same sector using KPI tables and radar charts.

### 5. Trend Analysis
Shows historical financial metrics and year-over-year changes using interactive charts.

### 6. Sector Analysis
Displays sector performance through bubble charts and KPI comparisons.

### 7. Capital Allocation
Visualizes company capital allocation patterns using treemaps.

### 8. Annual Reports
Shows financial summaries and available annual report records for selected companies.

---

## Sprint 4 Retrospective

### Completed

- Built all 8 Streamlit dashboard screens.
- Implemented the valuation module.
- Added CSV export functionality.
- Added cached SQLite data access.
- Integrated financial analytics and interactive visualizations.

### Challenges

- Handling missing financial data.
- Database integration.
- Chart rendering and responsiveness.
- Streamlit page integration.

### Outcome

Successfully completed all Sprint 4 deliverables with a fully functional Streamlit dashboard and valuation module.