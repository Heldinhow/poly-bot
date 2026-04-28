# Commodity Market Research

When analyzing commodity markets (oil, gold, etc.):

1. Identify the exact commodity and benchmark (WTI, Brent, spot, etc.)
2. Use Yahoo Finance or Alpha Vantage for current spot price
3. Check recent trend (24h, 7d)
4. Note relevant news (OPEC decisions, geopolitical events)

## Tools
- `curl` for API requests
- `jq` for JSON parsing

## API Key
Use env var `ALPHA_VANTAGE_API_KEY`

## Example
```bash
# Yahoo Finance
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1d&range=7d"
```

## Output Format
Provide your findings as structured data before the final probability.
