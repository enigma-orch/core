from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.config import settings


def build_agent(
    *,
    name: str,
    description: str,
    instructions: list[str],
    tools: list | None = None,
    markdown: bool = True,
) -> Agent:
    return Agent(
        name=name,
        description=description,
        instructions=instructions,
        tools=tools or [],
        model=OpenAIChat(id="gpt-4o", api_key=settings.openai_api_key),
        markdown=markdown,
        show_tool_calls=True,
    )
