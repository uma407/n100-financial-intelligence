-- Query 1
SELECT COUNT(*) AS total_companies
FROM companies;

-- Query 2
SELECT COUNT(*) AS total_profit_records
FROM profitandloss;

-- Query 3
SELECT COUNT(*) AS total_balance_records
FROM balancesheet;

-- Query 4
SELECT COUNT(*) AS total_cashflow_records
FROM cashflow;

-- Query 5
SELECT company_id,
       COUNT(DISTINCT year) AS years_available
FROM profitandloss
GROUP BY company_id
ORDER BY years_available DESC;

-- Query 6
SELECT company_id,
       sales
FROM profitandloss
ORDER BY sales DESC
LIMIT 10;

-- Query 7
SELECT company_id,
       net_profit
FROM profitandloss
ORDER BY net_profit DESC
LIMIT 10;

-- Query 8
SELECT company_id,
       market_cap
FROM financial_ratios
ORDER BY market_cap DESC
LIMIT 10;

-- Query 9
SELECT sector,
       COUNT(*) AS companies
FROM sectors
GROUP BY sector
ORDER BY companies DESC;

-- Query 10
SELECT COUNT(*)
FROM stock_prices;