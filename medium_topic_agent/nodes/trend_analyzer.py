"""Trend analyzer node - analyzes search results using LLM."""

from langchain_core.messages import SystemMessage, HumanMessage

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)


TREND_ANALYSIS_PROMPT = """You are an expert content strategist analyzing market trends for Medium articles.

Analyze the following search results and research papers to identify:

1. **Hot Topics**: Currently trending topics with high engagement potential
2. **Content Gaps**: Underserved niches where there's demand but limited quality content
3. **Emerging Trends**: New trends that are gaining momentum
4. **Evergreen Topics**: Timeless topics with consistent interest
5. **Research Frontiers**: Cutting-edge research that could be translated into accessible content

User's Background: {background}
Target Audience: {target_audience}
Keywords: {keywords}

=== WEB SEARCH RESULTS ===
{web_results}

=== ARXIV RESEARCH PAPERS ===
{arxiv_papers}

Provide your analysis in the following JSON format:
{{
    "hot_topics": ["topic1", "topic2", "topic3"],
    "content_gaps": ["gap1", "gap2"],
    "emerging_trends": ["trend1", "trend2"],
    "evergreen_topics": ["evergreen1", "evergreen2"],
    "research_frontiers": ["frontier1", "frontier2"],
    "key_insights": "A brief summary of the most important findings",
    "opportunity_score": 85
}}

Focus on actionable insights that will help create high-performing Medium articles."""


def _format_web_results(results: list[dict]) -> str:
    """Format web search results for the prompt."""
    if not results:
        return "No web search results available."
    
    formatted = []
    for i, result in enumerate(results[:15], 1):  # Limit to 15 results
        formatted.append(
            f"{i}. {result.get('title', 'No title')}\n"
            f"   URL: {result.get('url', 'N/A')}\n"
            f"   Snippet: {result.get('snippet', 'No snippet')[:200]}"
        )
    return "\n\n".join(formatted)


def _format_arxiv_papers(papers: list[dict]) -> str:
    """Format ArXiv papers for the prompt."""
    if not papers:
        return "No research papers available."
    
    formatted = []
    for i, paper in enumerate(papers[:10], 1):  # Limit to 10 papers
        authors = ", ".join(paper.get("authors", [])[:2])
        formatted.append(
            f"{i}. {paper.get('title', 'No title')}\n"
            f"   Authors: {authors}\n"
            f"   Published: {paper.get('published', 'N/A')}\n"
            f"   Summary: {paper.get('summary', 'No summary')[:300]}..."
        )
    return "\n\n".join(formatted)


def _parse_trend_response(response_text: str) -> dict:
    """Parse the LLM response into structured trend insights."""
    import json
    import re
    
    # Try to extract JSON from the response
    try:
        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    # Fallback: Return a basic structure
    return {
        "hot_topics": [],
        "content_gaps": [],
        "emerging_trends": [],
        "evergreen_topics": [],
        "research_frontiers": [],
        "key_insights": response_text[:500],
        "opportunity_score": 50,
    }


def trend_analyzer_node(state: AgentState, llm) -> AgentState:
    """Analyze search results and papers to identify trends.
    
    Args:
        state: Current agent state with search results.
        llm: Language model instance.
        
    Returns:
        Updated state with trend insights.
    """
    logger.info("trend_analyzer_start")
    
    try:
        # Format inputs for prompt
        web_results = _format_web_results(state.get("web_search_results", []))
        arxiv_papers = _format_arxiv_papers(state.get("arxiv_papers", []))
        
        prompt = TREND_ANALYSIS_PROMPT.format(
            background=state.get("user_background", "Not provided"),
            target_audience=state.get("target_audience", "General audience"),
            keywords=", ".join(state.get("keywords", [])),
            web_results=web_results,
            arxiv_papers=arxiv_papers,
        )
        
        messages = [
            SystemMessage(content="You are an expert content strategist. Always respond with valid JSON."),
            HumanMessage(content=prompt),
        ]
        
        response = llm.invoke(messages)
        trend_insights = _parse_trend_response(response.content)
        
        logger.info(
            "trend_analyzer_complete",
            num_hot_topics=len(trend_insights.get("hot_topics", [])),
            num_gaps=len(trend_insights.get("content_gaps", [])),
        )
        
        return {
            **state,
            "trend_insights": trend_insights,
            "current_step": "trend_analysis_complete",
        }
        
    except Exception as e:
        logger.error("trend_analyzer_error", error=str(e))
        return {
            **state,
            "trend_insights": {
                "hot_topics": [],
                "content_gaps": [],
                "emerging_trends": [],
                "evergreen_topics": [],
                "research_frontiers": [],
                "key_insights": "Analysis failed",
                "opportunity_score": 0,
            },
            "error": f"Trend analysis failed: {str(e)}",
            "current_step": "trend_analysis_error",
        }
