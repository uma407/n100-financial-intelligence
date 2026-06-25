-- Query 1: Total companies
SELECT COUNT(*) FROM companies;

-- Query 2: Five random companies
SELECT id, name
FROM companies
ORDER BY RANDOM()
LIMIT 5;

-- Query 3: Year coverage for every company
SELECT company_id,
       MIN(year) AS first_year,
       MAX(year) AS last_year,
       COUNT(DISTINCT year) AS total_years
FROM profitandloss
GROUP BY company_id
ORDER BY total_years;