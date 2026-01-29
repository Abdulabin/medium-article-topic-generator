"""Scorer node - scores and ranks generated topics."""

from langchain_core.messages import SystemMessage, HumanMessage

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)


SCORING_PROMPT = """You are an expert content strategist specializing in Medium article performance.

Score each topic on the following criteria (0-100 scale):

1. **Trend Score**: How trending/timely is this topic? (Higher = more current interest)
2. **Uniqueness Score**: How differentiated is this from existing content? (Higher = more unique)
3. **Engagement Score**: How likely to get claps, shares, comments? (Higher = more engaging)
4. **Author Fit Score**: How well does this match the author's background? (Higher = better fit)
5. **Research Depth Score**: Is this backed by research/data? (Higher = more credible)

=== AUTHOR PROFILE ===
Background: {background}
Keywords of Expertise: {keywords}

=== TREND CONTEXT ===
Hot Topics: {hot_topics}
Content Gaps: {content_gaps}

=== TOPICS TO SCORE ===
{topics_json}

Return a JSON array with scored topics:
[
    {{
        "topic": {{original topic object}},
        "scores": {{
            "trend_score": 85,
            "uniqueness_score": 72,
            "engagement_score": 88,
            "author_fit_score": 90,
            "research_depth_score": 65
        }},
        "overall_score": 80.0,
        "reasoning": "Brief explanation of the scores",
        "recommendations": ["Suggestion to improve topic 1", "Suggestion 2"]
    }}
]

Calculate overall_score as: (trend*0.2 + uniqueness*0.2 + engagement*0.25 + author_fit*0.2 + research*0.15)

Sort the results by overall_score in descending order and assign ranks (1 = best)."""


def _parse_scored_topics(response_text: str) -> list[dict]:
    """Parse the LLM response into scored topics list."""
    import json
    import re
    
    try:
        # Look for JSON array
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            topics = json.loads(json_match.group())
            if isinstance(topics, list):
                # Ensure proper ranking
                topics = sorted(
                    topics,
                    key=lambda x: x.get("overall_score", 0),
                    reverse=True
                )
                for i, topic in enumerate(topics, 1):
                    topic["rank"] = i
                return topics
    except json.JSONDecodeError:
        pass
    
    logger.warning("scored_topics_parse_failed", response_preview=response_text[:200])
    return []


def scorer_node(state: AgentState, llm) -> AgentState:
    """Score and rank generated topics.
    
    Args:
        state: Current agent state with generated topics.
        llm: Language model instance.
        
    Returns:
        Updated state with scored and ranked topics.
    """
    logger.info("scorer_start", num_topics=len(state.get("generated_topics", [])))
    
    try:
        generated_topics = state.get("generated_topics", [])
        trend_insights = state.get("trend_insights", {})
        
        if not generated_topics:
            logger.warning("scorer_no_topics")
            return {
                **state,
                "scored_topics": [],
                "error": "No topics to score",
            }
        
        import json
        
        prompt = SCORING_PROMPT.format(
            background=state.get("user_background", "Not provided"),
            keywords=", ".join(state.get("keywords", [])),
            hot_topics=", ".join(trend_insights.get("hot_topics", [])),
            content_gaps=", ".join(trend_insights.get("content_gaps", [])),
            topics_json=json.dumps(generated_topics, indent=2),
        )
        
        messages = [
            SystemMessage(content="You are an expert content strategist. Always respond with valid JSON."),
            HumanMessage(content=prompt),
        ]
        
        response = llm.invoke(messages)
        scored_topics = _parse_scored_topics(response.content)
        
        logger.info("scorer_complete", num_scored=len(scored_topics))
        
        return {
            **state,
            "scored_topics": scored_topics,
            "current_step": "scoring_complete",
        }
        
    except Exception as e:
        logger.error("scorer_error", error=str(e))
        return {
            **state,
            "scored_topics": [],
            "error": f"Scoring failed: {str(e)}",
            "current_step": "scoring_error",
        }
