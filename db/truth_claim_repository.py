"""Repository for truth_claims — structured facts extracted from agent outputs."""
import logging
from uuid import UUID

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class TruthClaimRepository:
    def create(self, execution_log_id: UUID, claim_type: str, content: str,
               source_reference: str = None, confidence_weight: float = None,
               order_index: int = None) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO truth_claims
                    (execution_log_id, claim_type, content, source_reference,
                     confidence_weight, order_index)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (str(execution_log_id), claim_type, content, source_reference,
                 confidence_weight, order_index),
            )
            return cursor.fetchone()["id"]

    def create_batch(self, execution_log_id: UUID, claims: list[dict]) -> list[UUID]:
        if not claims:
            return []
        ids = []
        with get_db_cursor() as cursor:
            for i, claim in enumerate(claims):
                cursor.execute(
                    """
                    INSERT INTO truth_claims
                        (execution_log_id, claim_type, content, source_reference,
                         confidence_weight, order_index)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        str(execution_log_id),
                        claim.get("claim_type", "fact"),
                        claim.get("content", ""),
                        claim.get("source", claim.get("source_reference")),
                        claim.get("weight", claim.get("confidence_weight")),
                        i,
                    ),
                )
                ids.append(cursor.fetchone()["id"])
        return ids

    def list_by_execution(self, execution_log_id: UUID) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM truth_claims
                WHERE execution_log_id = %s
                ORDER BY order_index ASC NULLS LAST, created_at ASC
                """,
                (str(execution_log_id),),
            )
            return cursor.fetchall()

    def list_by_market(self, market_id: str, since=None) -> list[dict]:
        with get_db_cursor() as cursor:
            if since:
                cursor.execute(
                    """
                    SELECT tc.* FROM truth_claims tc
                    JOIN execution_logs el ON tc.execution_log_id = el.id
                    WHERE el.market_id = %s AND tc.created_at >= %s
                    ORDER BY tc.created_at ASC
                    """,
                    (market_id, since),
                )
            else:
                cursor.execute(
                    """
                    SELECT tc.* FROM truth_claims tc
                    JOIN execution_logs el ON tc.execution_log_id = el.id
                    WHERE el.market_id = %s
                    ORDER BY tc.created_at ASC
                    """,
                    (market_id,),
                )
            return cursor.fetchall()