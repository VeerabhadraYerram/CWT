"""Skills manager — Hermes-inspired skill extraction and retrieval system."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)


class SkillsManager:
    """Manages reusable skill files extracted from agent experiences.

    Implements Hermes' skills pattern:
    - Extract successful procedures as markdown skill files
    - Store skills with YAML frontmatter (name, description, tags)
    - Retrieve relevant skills for new queries

    Storage: memory/store/skills/*.md
    """

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or settings.SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def save_skill(
        self,
        name: str,
        content: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> Path:
        """Save a skill as a markdown file with YAML frontmatter.

        Args:
            name: Skill name (used as filename).
            content: Skill content in markdown.
            description: Brief description of what the skill does.
            tags: Searchable tags.

        Returns:
            Path to the saved skill file.
        """
        # Sanitize filename
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
        filepath = self.skills_dir / f"{safe_name}.md"

        tags_str = ", ".join(tags) if tags else ""
        now = datetime.now(timezone.utc).isoformat()

        frontmatter = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"tags: [{tags_str}]\n"
            f"created: {now}\n"
            f"---\n\n"
        )

        full_content = frontmatter + content

        filepath.write_text(full_content, encoding="utf-8")
        logger.info("skill_saved", name=name, path=str(filepath))
        return filepath

    def load_skill(self, name: str) -> str | None:
        """Load a skill file by name.

        Args:
            name: Skill name (without .md extension).

        Returns:
            Skill content string, or None if not found.
        """
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
        filepath = self.skills_dir / f"{safe_name}.md"

        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return None

    def list_skills(self) -> list[dict]:
        """List all available skills with their metadata.

        Returns:
            List of dicts with name, description, tags, path.
        """
        skills = []
        for filepath in sorted(self.skills_dir.glob("*.md")):
            content = filepath.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(content)
            metadata["path"] = str(filepath)
            metadata["filename"] = filepath.stem
            skills.append(metadata)
        return skills

    def find_relevant_skills(self, query: str, limit: int = 3) -> list[str]:
        """Find skills relevant to a query by keyword matching.

        Args:
            query: Search query.
            limit: Max skills to return.

        Returns:
            List of skill content strings.
        """
        query_lower = query.lower()
        scored: list[tuple[int, str]] = []

        for filepath in self.skills_dir.glob("*.md"):
            content = filepath.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(content)

            # Score by keyword matches
            score = 0
            name = metadata.get("name", "").lower()
            desc = metadata.get("description", "").lower()
            tags = metadata.get("tags", "").lower()

            for word in query_lower.split():
                if word in name:
                    score += 3
                if word in desc:
                    score += 2
                if word in tags:
                    score += 2
                if word in content.lower():
                    score += 1

            if score > 0:
                scored.append((score, content))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:limit]]

    def delete_skill(self, name: str) -> bool:
        """Delete a skill file.

        Args:
            name: Skill name.

        Returns:
            True if deleted, False if not found.
        """
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
        filepath = self.skills_dir / f"{safe_name}.md"

        if filepath.exists():
            filepath.unlink()
            logger.info("skill_deleted", name=name)
            return True
        return False

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        """Extract YAML frontmatter from a markdown file."""
        metadata = {"name": "", "description": "", "tags": ""}
        match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
        if match:
            for line in match.group(1).split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()
        return metadata
