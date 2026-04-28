"""Market classifier — matches markets to agents based on keywords."""
import logging
import re

logger = logging.getLogger(__name__)

# Simple keyword-based classification rules
# Maps agent name patterns to lists of keywords
CLASSIFICATION_RULES = {
    "weather": [
        "weather", "temperature", "rain", "snow", "storm", "hurricane",
        "celsius", "fahrenheit", "degrees", "forecast", "sunny", "cloudy",
        "precipitation", "wind", "humidity",
    ],
    "commodity": [
        "oil", "gold", "silver", "bitcoin", "btc", "ethereum", "eth",
        "commodity", "wti", "brent", "crude", "gas", "natural gas",
        "copper", "aluminum", "wheat", "corn", "soybean",
    ],
    "sports": [
        "nba", "nfl", "mlb", "nhl", "fifa", "world cup", "champions league",
        "premier league", "super bowl", "olympics", "tennis", "golf",
        "baseball", "basketball", "football", "soccer", "hockey",
        "match", "game", "team", "player", "score", "win", "lose",
    ],
    "esports": [
        "lol", "league of legends", "dota", "csgo", "counter-strike",
        "valorant", "overwatch", "fortnite", "pubg", "twitch",
        "esports", "gaming", "tournament", "championship",
    ],
    "politics": [
        "election", "president", "congress", "senate", "vote", "ballot",
        "trump", "biden", "democrat", "republican", "gop", "political",
        "campaign", "poll", "primary", "midterm", "referendum",
    ],
    "crypto": [
        "crypto", "cryptocurrency", "blockchain", "defi", "nft",
        "bitcoin", "ethereum", "solana", "cardano", "binance",
        "wallet", "token", "mining", "staking",
    ],
    "tech": [
        "apple", "google", "microsoft", "amazon", "meta", "facebook",
        "tesla", "spacex", "twitter", "x.com", "ai", "artificial intelligence",
        "iphone", "android", "iphone", "macbook", "launch",
    ],
}


class MarketClassifier:
    """Classifies markets based on keywords in the question."""

    def classify(self, question: str) -> list[str]:
        """Return a list of category names that match the market question.

        Categories are ordered by match strength (number of keyword hits).
        """
        question_lower = question.lower()
        scores: dict[str, int] = {}

        for category, keywords in CLASSIFICATION_RULES.items():
            score = 0
            for keyword in keywords:
                # Use word boundaries for more accurate matching
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, question_lower))
                score += matches
            if score > 0:
                scores[category] = score

        # Sort by score descending
        sorted_categories = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        logger.debug(f"Market classified: {question[:60]}... → categories={sorted_categories}, scores={scores}")
        return sorted_categories

    def get_primary_category(self, question: str) -> str | None:
        """Return the single best-matching category, or None if no match."""
        categories = self.classify(question)
        return categories[0] if categories else None
