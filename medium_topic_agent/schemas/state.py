"""Agent state definition for LangGraph."""

from typing import TypedDict, Annotated
from operator import add


class AgentState(TypedDict, total=False):
    """State maintained throughout the agent workflow.
    
    This TypedDict defines all state fields that flow through the LangGraph nodes.
    Each node can read from and write to this state.
    """
    
    # User Input Phase
    user_background: str
    """User's professional background, expertise, and domain knowledge."""
    
    keywords: list[str]
    """Keywords and topics of interest provided by the user."""
    
    target_audience: str
    """Intended audience for the Medium articles."""
    
    additional_context: dict
    """Any extra context gathered from user (preferences, constraints, etc.)."""
    
    # Clarification Phase
    needs_clarification: bool
    """Flag indicating if more information is needed from the user."""
    
    clarification_questions: list[str]
    """Questions to ask the user for better topic suggestions."""
    
    user_responses: dict
    """User's responses to clarification questions."""
    
    # Research Phase
    web_search_results: Annotated[list[dict], add]
    """Results from DuckDuckGo web search on trending topics."""
    
    arxiv_papers: Annotated[list[dict], add]
    """Research papers from ArXiv related to the keywords."""
    
    # Analysis Phase
    trend_insights: dict
    """Analyzed trends including hot topics, gaps, and opportunities."""
    
    # Topic Generation Phase
    generated_topics: list[dict]
    """Raw generated topic ideas before scoring."""
    
    # Scoring Phase
    scored_topics: list[dict]
    """Final ranked topics with scores and explanations."""
    
    # Error Handling
    error: str | None
    """Error message if any step fails."""
    
    # Workflow Control
    current_step: str
    """Current step in the workflow for tracking."""
