import logging
from typing import Optional
from uuid import UUID

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class SkillRepository:
    """Repository for skill CRUD operations."""

    def create_skill(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
    ) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO skills (name, description, content)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (name, description, content),
            )
            result = cursor.fetchone()
            skill_id = result["id"]
            logger.info(f"Skill created: id={skill_id}, name={name}")
            return skill_id

    def get_skill_by_id(self, skill_id: UUID) -> Optional[dict]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM skills WHERE id = %s", (str(skill_id),))
            return cursor.fetchone()

    def list_skills(self, active_only: bool = False) -> list[dict]:
        with get_db_cursor() as cursor:
            if active_only:
                cursor.execute(
                    "SELECT * FROM skills WHERE is_active = true ORDER BY created_at DESC"
                )
            else:
                cursor.execute("SELECT * FROM skills ORDER BY created_at DESC")
            return cursor.fetchall()

    def update_skill(self, skill_id: UUID, **fields) -> bool:
        allowed = {"name", "description", "content", "is_active"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [str(skill_id)]

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE skills SET {set_clause} WHERE id = %s RETURNING id",
                values,
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Skill updated: id={skill_id}")
                return True
            return False

    def delete_skill(self, skill_id: UUID) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM skills WHERE id = %s RETURNING id", (str(skill_id),))
            result = cursor.fetchone()
            if result:
                logger.info(f"Skill deleted: id={skill_id}")
                return True
            return False
