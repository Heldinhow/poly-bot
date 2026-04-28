"""Extract and parse truth claims from agent Result objects."""
import re
import logging
from typing import Optional

from agents.runtime.models import Result

logger = logging.getLogger(__name__)


class TruthClaimExtractor:
    """Parse structured truth_claims from agent Result objects.

    Supports two paths:
    1. Agent Runtime (new flow): Result.truth_claims is already populated from structured JSON
    2. Legacy/fallback: extract claims from Result.reasoning using lightweight regex patterns
    """

    def extract(self, result: Result) -> list[dict]:
        """Extract truth claims from a Result.

        Returns list of claim dicts ready for TruthClaimRepository.create_batch().

        Args:
            result: The agent Result object.

        Returns:
            List of claim dicts with keys: claim_type, content, source_reference,
            confidence_weight, order_index.
        """
        # Path 1: Already structured from Agent Runtime
        if result.truth_claims:
            return [
                {
                    "claim_type": claim.get("claim_type", "fact"),
                    "content": claim.get("content", ""),
                    "source_reference": claim.get("source", claim.get("source_reference")),
                    "confidence_weight": claim.get("weight", claim.get("confidence_weight")),
                }
                for claim in result.truth_claims
                if claim.get("content")
            ]

        # Path 2: Fallback to reasoning extraction (legacy agents)
        if result.reasoning:
            return self.extract_from_reasoning(result.reasoning)

        return []

    def extract_from_reasoning(self, reasoning: str) -> list[dict]:
        """Lightweight regex extraction for legacy agents.

        Extracts quoted statistics, percentages, team names, scores, and
        other concrete data points from free-text reasoning.

        This is best-effort — not as precise as structured JSON but provides
        some traceability for legacy agent outputs.

        Returns:
            List of claim dicts.
        """
        if not reasoning:
            return []

        claims = []
        claim_type = "fact"

        # Extract quoted strings (likely specific facts)
        quoted_patterns = [
            r'"([^"]{10,150})"',
            r"'([^']{10,150})'",
        ]
        for pattern in quoted_patterns:
            for match in re.finditer(pattern, reasoning):
                content = match.group(1).strip()
                if len(content) > 15:
                    claims.append({
                        "claim_type": claim_type,
                        "content": content,
                        "source_reference": "reasoning_text",
                        "confidence_weight": 0.5,
                    })

        # Extract percentages (e.g., "60%", "3 of last 5 games (60%)")
        pct_pattern = r'(\d+(?:\.\d+)?)\s*%'
        for match in re.finditer(pct_pattern, reasoning):
            pct = float(match.group(1))
            if 0 < pct <= 100:
                start = max(0, match.start() - 30)
                end = min(len(reasoning), match.end() + 30)
                context = reasoning[start:end].strip()
                claims.append({
                    "claim_type": "data_point",
                    "content": f"Statistic: {context}",
                    "source_reference": "reasoning_text",
                    "confidence_weight": 0.6,
                })

        # Extract team/st player names with status keywords
        status_keywords = [
            "injury", "injured", "suspended", "missing",
            "out", "doubtful", "questionable", "available",
        ]
        for keyword in status_keywords:
            pattern = rf'(\b[A-Z][a-zA-Z\s]{{2,30}}\b)\s+{keyword}'
            for match in re.finditer(pattern, reasoning, re.IGNORECASE):
                entity = match.group(1).strip()
                if len(entity) > 2:
                    claims.append({
                        "claim_type": "assertion",
                        "content": f"{entity} — {keyword}",
                        "source_reference": "reasoning_text",
                        "confidence_weight": 0.7,
                    })

        # Extract score ratios (e.g., "3-2", "won 3 of last 5")
        score_pattern = r'(\d+)\s*[-:]\s*(\d+)'
        for match in re.finditer(score_pattern, reasoning):
            m1, m2 = int(match.group(1)), int(match.group(2))
            if 0 < m1 < 50 and 0 < m2 < 50:
                start = max(0, match.start() - 20)
                end = min(len(reasoning), match.end() + 20)
                context = reasoning[start:end].strip()
                claims.append({
                    "claim_type": "data_point",
                    "content": f"Score: {context}",
                    "source_reference": "reasoning_text",
                    "confidence_weight": 0.6,
                })

        # Deduplicate by content
        seen = set()
        unique = []
        for c in claims:
            key = c["content"][:80]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        logger.debug(f"Extracted {len(unique)} truth claims from reasoning")
        return unique