"""Topic generator node - generates topic ideas using LLM."""

from langchain_core.messages import SystemMessage, HumanMessage

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.config import settings
from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)


TOPIC_GENERATION_PROMPT = """You are an expert Medium content strategist helping create viral article ideas.

Based on the trend analysis and user's expertise, generate {num_topics} unique article topic ideas.

=== USER PROFILE ===
Background: {background}
Keywords: {keywords}
Target Audience: {target_audience}
Additional Context: {additional_context}

=== TREND INSIGHTS ===
Hot Topics: {hot_topics}
Content Gaps: {content_gaps}
Emerging Trends: {emerging_trends}
Research Frontiers: {research_frontiers}
Key Insights: {key_insights}

=== REQUIREMENTS ===
Each topic should:
1. Have a compelling, click-worthy title (not clickbait)
2. Leverage the user's unique background and expertise
3. Address audience pain points or curiosity
4. Stand out from existing content
5. Be actionable and valuable

Generate topics as a JSON array with this structure:
[
    {{
        "title": "Compelling Article Title Here",
        "hook": "Opening line that grabs attention",
        "description": "Brief description of what the article covers (2-3 sentences)",
        "unique_angle": "What makes this unique compared to existing content",
        "target_audience": "Specific audience segment this is for",
        "article_type": "tutorial|opinion|case_study|listicle|deep_dive|comparison",
        "key_takeaways": ["takeaway1", "takeaway2", "takeaway3"],
        "estimated_read_time": "X min read"
    }}
]

Generate exactly {num_topics} diverse topics covering different angles and formats."""


def _parse_topics_response(response_text: str) -> list[dict]:
    """Parse the LLM response into topic list."""
    import json
    import re
    
    # Try to extract JSON array from the response
    try:
        # Look for JSON array
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            topics = json.loads(json_match.group())
            if isinstance(topics, list):
                return topics
    except json.JSONDecodeError:
        pass
    
    # Fallback: Return empty list
    logger.warning("topic_parse_failed", response_preview=response_text[:200])
    return []


def topic_generator_node(state: AgentState, llm) -> AgentState:
    """Generate topic ideas based on trends and user profile.
    
    Args:
        state: Current agent state with trend insights.
        llm: Language model instance.
        
    Returns:
        Updated state with generated topics.
    """
    logger.info("topic_generator_start")
    
    try:
        trend_insights = state.get("trend_insights", {})
        
        prompt = TOPIC_GENERATION_PROMPT.format(
            num_topics=settings.max_topics,
            background=state.get("user_background", "Not provided"),
            keywords=", ".join(state.get("keywords", [])),
            target_audience=state.get("target_audience", "General audience"),
            additional_context=state.get("additional_context", {}),
            hot_topics=", ".join(trend_insights.get("hot_topics", [])),
            content_gaps=", ".join(trend_insights.get("content_gaps", [])),
            emerging_trends=", ".join(trend_insights.get("emerging_trends", [])),
            research_frontiers=", ".join(trend_insights.get("research_frontiers", [])),
            key_insights=trend_insights.get("key_insights", "No insights available"),
        )
        
        messages = [
            SystemMessage(content="You are an expert Medium content strategist. Always respond with valid JSON."),
            HumanMessage(content=prompt),
        ]
        
        response = llm.invoke(messages)
        topics = _parse_topics_response(response.content)
        
        logger.info("topic_generator_complete", num_topics=len(topics))
        
        return {
            **state,
            "generated_topics": topics,
            "current_step": "topic_generation_complete",
        }
        
    except Exception as e:
        logger.error("topic_generator_error", error=str(e))
        return {
            **state,
            "generated_topics": [],
            "error": f"Topic generation failed: {str(e)}",
            "current_step": "topic_generation_error",
        }
