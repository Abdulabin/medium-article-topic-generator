"""Web searcher node - searches DuckDuckGo for trending topics."""

from duckduckgo_search import DDGS
from langchain_core.prompts import ChatPromptTemplate

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.config import settings
from medium_topic_agent.utils.logger import get_logger
from medium_topic_agent.utils.retry import with_retry

logger = get_logger(__name__)

SEARCH_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert content researcher helping find trending topics for Medium articles.

Generate optimized search queries to find:
1. Trending topics and discussions in the user's areas of interest
2. Popular Medium articles and blog content
3. Latest industry news and developments
4. Tutorial and how-to content opportunities
5. Research papers and technical discussions

User Context:
- Background: {background}
- Keywords: {keywords}
- Target Audience: {target_audience}
- Additional Context: {additional_context}

Generate 5-6 highly specific, targeted search queries that will surface:
- Current trending discussions
- Content gaps the user could fill
- Popular topics with engagement potential

Respond with ONLY the search queries, one per line. No numbering, no explanations."""),
    ("human", "Generate search queries for finding trending Medium article topics.")
])


def _parse_search_queries(response_text: str) -> list[str]:
    """Parse LLM response into search queries."""
    queries = []
    for line in response_text.strip().split("\n"):
        query = line.strip()
        if query and not query.startswith(("#", "-", "*")):
            # Remove any numbering like "1." or "1)"
            if len(query) > 2 and query[0].isdigit() and query[1] in ".):":
                query = query[2:].strip()
            elif len(query) > 3 and query[:2].isdigit() and query[2] in ".):":
                query = query[3:].strip()
            if query:
                queries.append(query)
    return queries[:6]  # Limit to 6 queries


@with_retry(max_attempts=3, min_wait=1.0, max_wait=5.0)
def _search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Execute DuckDuckGo search with retry logic."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


def _build_fallback_queries(keywords: list[str]) -> list[str]:
    """Build fallback search queries when LLM is not available."""
    queries = []
    keyword_str = " ".join(keywords[:3])
    
    queries.append(f"{keyword_str} trending topics 2024 2025")
    queries.append(f"Medium blog {keyword_str} popular articles")
    queries.append(f"{keyword_str} tutorial guide best practices")
    queries.append(f"{keyword_str} latest news developments")
    
    for keyword in keywords[:2]:
        queries.append(f"{keyword} content ideas blog topics")
    
    return queries[:6]


def web_searcher_node(state: AgentState, llm=None) -> AgentState:
    """Search DuckDuckGo for trending topics using LLM-generated queries.
    
    This node uses LLM to generate context-aware search queries based on
    user's background and keywords, then executes searches and aggregates results.
    
    Args:
        state: Current agent state with keywords.
        llm: Language model for generating search queries.
        
    Returns:
        Updated state with web search results.
    """
    logger.info("web_searcher_start", keywords=state.get("keywords", []))
    
    try:
        keywords = state.get("keywords", [])
        background = state.get("user_background", "")
        target_audience = state.get("target_audience", "")
        additional_context = state.get("additional_context", {})
        user_responses = state.get("user_responses", {})
        
        if not keywords:
            logger.warning("web_searcher_no_keywords")
            return {
                **state,
                "web_search_results": [],
                "error": "No keywords provided for search",
            }
        
        # Generate search queries using LLM
        if llm:
            # Combine additional context with user responses
            context_str = ""
            if additional_context:
                context_str = str(additional_context)
            if user_responses and not user_responses.get("skipped"):
                context_str += f" User clarifications: {user_responses}"
            
            chain = SEARCH_QUERY_PROMPT | llm
            response = chain.invoke({
                "background": background or "Not specified",
                "keywords": ", ".join(keywords),
                "target_audience": target_audience or "General tech audience",
                "additional_context": context_str or "None",
            })
            
            queries = _parse_search_queries(response.content)
            logger.info("llm_generated_queries", num_queries=len(queries))
            
            if not queries:
                queries = _build_fallback_queries(keywords)
        else:
            queries = _build_fallback_queries(keywords)
        
        # Execute searches and collect results
        all_results = []
        seen_urls = set()
        
        for query in queries:
            try:
                logger.debug("executing_search", query=query)
                results = _search_duckduckgo(query, max_results=settings.max_search_results)
                
                for result in results:
                    url = result.get("href", result.get("link", ""))
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": result.get("title", ""),
                            "url": url,
                            "snippet": result.get("body", result.get("snippet", "")),
                            "source": "duckduckgo",
                            "query": query,
                        })
                        
            except Exception as e:
                logger.warning("search_query_failed", query=query, error=str(e))
                continue
        
        logger.info("web_searcher_complete", num_results=len(all_results))
        
        return {
            **state,
            "web_search_results": all_results,
            "current_step": "web_search_complete",
        }
        
    except Exception as e:
        logger.error("web_searcher_error", error=str(e))
        return {
            **state,
            "web_search_results": [],
            "error": f"Web search failed: {str(e)}",
            "current_step": "web_search_error",
        }
