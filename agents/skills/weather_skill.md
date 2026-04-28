# Weather Market Research

When analyzing weather prediction markets:

1. Identify the exact location (city, country) from the market question
2. Identify the exact date from the market question
3. Use OpenWeatherMap or WeatherAPI to fetch the forecast
4. Report: temperature, conditions, precipitation probability
5. Note forecast reliability (24h vs 7-day forecasts differ in accuracy)

## Tools
- `curl` for API requests
- `jq` for JSON parsing

## API Key
Use env var `OPENWEATHER_API_KEY`

## Example
```bash
curl -s "https://api.openweathermap.org/data/2.5/forecast?q=Seoul&appid=$OPENWEATHER_API_KEY&units=metric"
```

## Output Format
Provide your findings as structured data before the final probability.
