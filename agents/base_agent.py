"""Base agent class — Hermes-inspired LLM agent with tools, memory, and skills."""

from __future__ import annotations

import structlog

from tools.llm_client import LLMClient
from memory.memory_manager import MemoryManager
from memory.skills_manager import SkillsManager

logger = structlog.get_logger(__name__)


class BaseAgent:
    """Hermes-inspired agent with conversation history, memory, and skills.

    Core patterns from Hermes Agent framework:
    - Tool registration: agents can register callable tools
    - Skill awareness: loads relevant skill files for context
    - Persistent memory: reads/writes to memory store
    - Conversation history: maintains sliding window of past messages

    Usage:
        agent = BaseAgent(name="greeter", system_prompt="You are helpful.")
        reply = agent.run("Hello!")
    """

    def __init__(self, name: str, system_prompt: str, tools: list | None = None):
        self.name = name
        self.system_prompt = system_prompt
        self.client = LLMClient()
        self.conversation_history: list[dict] = []
        self.logger = logger.bind(agent=name)
        self.max_history = 10

        # Hermes-inspired additions
        self.tools = tools or []
        self.memory = MemoryManager()
        self.skills = SkillsManager()

    def run(self, user_message: str) -> str:
        """Process a user message and return the assistant's reply.

        Flow (Hermes-inspired):
            1. Load relevant skills into context
            2. Load relevant memories
            3. Build message list (system + skills + memories + history + user msg)
            4. Call LLM
            5. Append user + assistant messages to history
            6. Return reply text
        """
        self.logger.info("agent_run", input=user_message[:100])

        # Build messages for this call
        messages = self._build_messages(user_message)

        # Call LLM
        reply = self.client.chat(messages)
        reply = reply.strip()

        # Update conversation history ONLY if success
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": reply})

        self.logger.info("agent_done", output_chars=len(reply))
        return reply

    def _build_messages(self, user_message: str) -> list[dict]:
        """Assemble the full message list for the LLM call.

        Injects relevant skills and memories into the system prompt
        for context-aware responses (Hermes pattern).
        """
        # Start with system prompt
        system_content = self.system_prompt

        # Inject relevant skills (Hermes skill awareness)
        relevant_skills = self.skills.find_relevant_skills(user_message, limit=2)
        if relevant_skills:
            skills_text = "\n\n".join(relevant_skills)
            system_content += (
                "\n\n--- RELEVANT SKILLS ---\n"
                f"{skills_text}\n"
                "--- END SKILLS ---"
            )

        # Inject relevant memories
        relevant_memories = self.memory.search_memory(user_message, limit=3)
        if relevant_memories:
            mem_text = "\n".join(
                f"- [{m['category']}] {m['content']}" for m in relevant_memories
            )
            system_content += (
                "\n\n--- RELEVANT MEMORIES ---\n"
                f"{mem_text}\n"
                "--- END MEMORIES ---"
            )

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversation_history[-self.max_history:])
        messages.append({"role": "user", "content": user_message})
        return messages

    def remember(self, content: str, category: str = "observation", tags: list[str] | None = None):
        """Save a notable observation to persistent memory."""
        self.memory.save_memory(content, category=category, tags=tags or [self.name])

    def reset(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.logger.info("history_cleared")
