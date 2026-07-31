
import sqlite3
import pandas as pd
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "reports" / "tearsheets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = PROJECT_ROOT / "nifty100.db"


def load_company_data(company_id="ABB"):

    conn = sqlite3.connect(DB_FILE)

    query = """
    SELECT
        c.id,
        c.company_name,
        f.year,
        p.sales,
        p.net_profit,
        f.return_on_equity_pct,
        f.debt_to_equity,
        f.operating_profit_margin_pct,
        f.composite_quality_score
    FROM companies c
    JOIN financial_ratios f
        ON c.id = f.company_id
    JOIN profitandloss p
        ON c.id = p.company_id
       AND f.year = p.year
    WHERE c.id = ?
    ORDER BY f.year DESC
    LIMIT 1
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(company_id,),
    )

    conn.close()

    return df

def format_number(value, decimals=2):
    if pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f}"


def generate_tearsheet(company_id="ABB"):
    df = load_company_data(company_id)

    if df.empty:
        print(f"No data found for company: {company_id}")
        return

    row = df.iloc[0]

    company_name = row["company_name"]
    year = row["year"]

    safe_name = company_id.replace("/", "_").replace("\\", "_")
    output_file = OUTPUT_DIR / f"{safe_name}_tearsheet.pdf"

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            f"{company_name} Tearsheet",
            styles["Title"],
        )
    )

    story.append(Spacer(1, 20))

    company_data = [
        ["Company ID", company_id],
        ["Company", company_name],
        ["Financial Year", str(year)],
        ["Report Type", "Financial Intelligence Tearsheet"],
    ]

    company_table = Table(
        company_data,
        colWidths=[1.5 * inch, 4.5 * inch],
    )

    company_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(company_table)
    story.append(Spacer(1, 25))

    story.append(
        Paragraph(
            "Key Financial Metrics",
            styles["Heading2"],
        )
    )

    story.append(Spacer(1, 10))

    kpi_data = [
        ["Metric", "Value"],
        ["Revenue (Cr)", format_number(row["sales"])],
        ["Net Profit (Cr)", format_number(row["net_profit"])],
        ["ROE (%)", format_number(row["return_on_equity_pct"])],
        ["Debt to Equity", format_number(row["debt_to_equity"])],
        [
            "Operating Margin (%)",
            format_number(row["operating_profit_margin_pct"]),
        ],
        [
            "Composite Quality Score",
            format_number(row["composite_quality_score"]),
        ],
    ]

    kpi_table = Table(
        kpi_data,
        colWidths=[3 * inch, 3 * inch],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(kpi_table)
    story.append(Spacer(1, 25))

    story.append(
        Paragraph(
            "Summary",
            styles["Heading2"],
        )
    )

    summary_text = (
        f"This report presents the latest available financial metrics "
        f"for {company_name} for the period {year}. "
        f"The company recorded revenue of "
        f"{format_number(row['sales'])} crore and net profit of "
        f"{format_number(row['net_profit'])} crore."
    )

    story.append(
        Paragraph(
            summary_text,
            styles["BodyText"],
        )
    )

    doc.build(story)

    print("Day 33 real-data PDF created successfully.")
    print("Created:", output_file)


if __name__ == "__main__":
    generate_tearsheet("ABB")