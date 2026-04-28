import logging
from uuid import UUID

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class AgentSkillRepository:
    """Repository for agent-skill many-to-many relationships."""

    def link_skill(self, agent_id: UUID, skill_id: UUID) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_skills (agent_id, skill_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                RETURNING agent_id
                """,
                (str(agent_id), str(skill_id)),
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Skill linked: agent={agent_id}, skill={skill_id}")
                return True
            return False

    def unlink_skill(self, agent_id: UUID, skill_id: UUID) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM agent_skills
                WHERE agent_id = %s AND skill_id = %s
                RETURNING agent_id
                """,
                (str(agent_id), str(skill_id)),
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Skill unlinked: agent={agent_id}, skill={skill_id}")
                return True
            return False

    def get_skills_for_agent(self, agent_id: UUID) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT s.* FROM skills s
                JOIN agent_skills ASJ ON s.id = ASJ.skill_id
                WHERE ASJ.agent_id = %s
                ORDER BY s.name
                """,
                (str(agent_id),),
            )
            return cursor.fetchall()

    def get_agents_for_skill(self, skill_id: UUID) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT a.* FROM agents a
                JOIN agent_skills ASJ ON a.id = ASJ.agent_id
                WHERE ASJ.skill_id = %s
                ORDER BY a.name
                """,
                (str(skill_id),),
            )
            return cursor.fetchall()

    def set_skills_for_agent(self, agent_id: UUID, skill_ids: list[UUID]) -> None:
        """Replace all skills for an agent with the given list."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM agent_skills WHERE agent_id = %s",
                (str(agent_id),),
            )
            for skill_id in skill_ids:
                cursor.execute(
                    "INSERT INTO agent_skills (agent_id, skill_id) VALUES (%s, %s)",
                    (str(agent_id), str(skill_id)),
                )
            logger.info(f"Skills set for agent {agent_id}: {len(skill_ids)} skills")
