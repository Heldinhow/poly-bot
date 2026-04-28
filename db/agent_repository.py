import logging
from typing import Optional
from uuid import UUID

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class AgentRepository:
    """Repository for agent CRUD operations."""

    def create_agent(
        self,
        name: str,
        runtime: str,
        description: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_concurrent_tasks: int = 1,
        max_retries: int = 1,
        custom_args: Optional[list[str]] = None,
        custom_env: Optional[dict] = None,
    ) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agents (
                    name, description, runtime, model, system_prompt,
                    max_concurrent_tasks, max_retries, custom_args, custom_env
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name, description, runtime, model, system_prompt,
                    max_concurrent_tasks, max_retries, custom_args or [], custom_env or {}
                ),
            )
            result = cursor.fetchone()
            agent_id = result["id"]
            logger.info(f"Agent created: id={agent_id}, name={name}, runtime={runtime}")
            return agent_id

    def get_agent_by_id(self, agent_id: UUID) -> Optional[dict]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM agents WHERE id = %s", (str(agent_id),))
            return cursor.fetchone()

    def get_agent_by_name(self, name: str) -> Optional[dict]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM agents WHERE name = %s", (name,))
            return cursor.fetchone()

    def list_agents(self, active_only: bool = False) -> list[dict]:
        with get_db_cursor() as cursor:
            if active_only:
                cursor.execute(
                    "SELECT * FROM agents WHERE is_active = true AND is_archived = false ORDER BY created_at DESC"
                )
            else:
                cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
            return cursor.fetchall()

    def update_agent(self, agent_id: UUID, **fields) -> bool:
        allowed = {
            "name", "description", "runtime", "model", "system_prompt",
            "max_concurrent_tasks", "max_retries", "custom_args", "custom_env",
            "is_active", "is_archived",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [str(agent_id)]

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE agents SET {set_clause} WHERE id = %s RETURNING id",
                values,
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Agent updated: id={agent_id}")
                return True
            return False

    def delete_agent(self, agent_id: UUID) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM agents WHERE id = %s RETURNING id", (str(agent_id),))
            result = cursor.fetchone()
            if result:
                logger.info(f"Agent deleted: id={agent_id}")
                return True
            return False

    def archive_agent(self, agent_id: UUID) -> bool:
        return self.update_agent(agent_id, is_archived=True, is_active=False)
