#!/usr/bin/env python3
"""Seed default skills into the database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import init_schema
from db.skill_repository import SkillRepository

SKILLS_DIR = Path(__file__).parent.parent / "agents" / "skills"


def seed_skills():
    init_schema()
    repo = SkillRepository()

    skill_files = [
        ("weather_research", "Weather Market Research", "weather_skill.md"),
        ("commodity_research", "Commodity Market Research", "commodity_skill.md"),
        ("news_research", "News Research", "news_search_skill.md"),
    ]

    for name, description, filename in skill_files:
        filepath = SKILLS_DIR / filename
        if not filepath.exists():
            print(f"Skipping {filename} — not found")
            continue

        content = filepath.read_text(encoding="utf-8")

        # Check if already exists
        existing = repo.list_skills(active_only=True)
        if any(s["name"] == name for s in existing):
            print(f"Skill '{name}' already exists — skipping")
            continue

        skill_id = repo.create_skill(name=name, description=description, content=content)
        print(f"Created skill: {name} (id={skill_id})")

    print("Done seeding skills.")


if __name__ == "__main__":
    seed_skills()
