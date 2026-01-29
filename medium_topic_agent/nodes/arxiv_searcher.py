"""ArXiv searcher node - fetches latest research papers."""

import arxiv
from langchain_core.prompts import ChatPromptTemplate

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.config import settings
from medium_topic_agent.utils.logger import get_logger
from medium_topic_agent.utils.retry import with_retry

logger = get_logger(__name__)

ARXIV_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert research paper curator helping find relevant academic papers for Medium article topics.

Generate optimized ArXiv search queries to find:
1. Latest research papers relevant to the user's interests
2. Groundbreaking studies that could inspire unique article angles
3. Technical papers with practical applications for the target audience

User Context:
- Background: {background}
- Keywords: {keywords}
- Target Audience: {target_audience}

ArXiv Query Tips:
- Use technical/academic terms for better results
- Combine related concepts with AND
- Use category prefixes like cs.AI, cs.LG, stat.ML when relevant

Generate 3-4 ArXiv search queries that will surface:
- Recent cutting-edge research
- Papers with practical applications
- Studies that could provide unique data/insights for articles

Respond with ONLY the search queries, one per line. No numbering, no explanations.
Keep queries concise and focused on academic/research terminology."""),
    ("human", "Generate ArXiv search queries for finding relevant research papers.")
])


def _parse_arxiv_queries(response_text: str) -> list[str]:
    """Parse LLM response into ArXiv queries."""
    queries = []
    for line in response_text.strip().split("\n"):
        query = line.strip()
        if query and not query.startswith(("#", "-", "*")):
            # Remove any numbering
            if len(query) > 2 and query[0].isdigit() and query[1] in ".):":
                query = query[2:].strip()
            elif len(query) > 3 and query[:2].isdigit() and query[2] in ".):":
                query = query[3:].strip()
            if query:
                queries.append(query)
    return queries[:4]  # Limit to 4 queries


@with_retry(max_attempts=3, min_wait=1.0, max_wait=5.0)
def _search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Execute ArXiv search with retry logic."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    papers = []
    for result in client.results(search):
        papers.append({
            "title": result.title,
            "authors": [author.name for author in result.authors[:3]],
            "summary": result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
            "published": result.published.strftime("%Y-%m-%d"),
            "arxiv_url": result.entry_id,
            "categories": result.categories,
            "pdf_url": result.pdf_url,
        })
    
    return papers


def _build_fallback_queries(keywords: list[str]) -> list[str]:
    """Build fallback ArXiv queries when LLM is not available."""
    queries = []
    
    if keywords:
        main_query = " AND ".join(keywords[:3])
        queries.append(main_query)
    
    for keyword in keywords[:3]:
        queries.append(keyword)
    
    return queries[:4]


def arxiv_searcher_node(state: AgentState, llm=None) -> AgentState:
    """Search ArXiv for research papers using LLM-generated queries.
    
    This node uses LLM to generate context-aware search queries
    for fetching cutting-edge research papers.
    
    Args:
        state: Current agent state with keywords.
        llm: Language model for generating search queries.
        
    Returns:
        Updated state with ArXiv paper results.
    """
    logger.info("arxiv_searcher_start", keywords=state.get("keywords", []))
    
    try:
        keywords = state.get("keywords", [])
        background = state.get("user_background", "")
        target_audience = state.get("target_audience", "")
        
        if not keywords:
            logger.warning("arxiv_searcher_no_keywords")
            return {
                **state,
                "arxiv_papers": [],
            }
        
        # Generate search queries using LLM
        if llm:
            chain = ARXIV_QUERY_PROMPT | llm
            response = chain.invoke({
                "background": background or "Not specified",
                "keywords": ", ".join(keywords),
                "target_audience": target_audience or "General tech audience",
            })
            
            queries = _parse_arxiv_queries(response.content)
            logger.info("llm_generated_arxiv_queries", num_queries=len(queries))
            
            if not queries:
                queries = _build_fallback_queries(keywords)
        else:
            queries = _build_fallback_queries(keywords)
        
        # Execute searches and collect papers
        all_papers = []
        seen_titles = set()
        
        for query in queries:
            try:
                logger.debug("executing_arxiv_search", query=query)
                papers = _search_arxiv(query, max_results=settings.max_arxiv_results)
                
                for paper in papers:
                    title_lower = paper["title"].lower()
                    if title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        all_papers.append(paper)
                        
            except Exception as e:
                logger.warning("arxiv_query_failed", query=query, error=str(e))
                continue
        
        # Sort by date and limit results
        all_papers = sorted(
            all_papers, 
            key=lambda x: x["published"], 
            reverse=True
        )[:settings.max_arxiv_results * 2]
        
        logger.info("arxiv_searcher_complete", num_papers=len(all_papers))
        
        return {
            **state,
            "arxiv_papers": all_papers,
            "current_step": "arxiv_search_complete",
        }
        
    except Exception as e:
        logger.error("arxiv_searcher_error", error=str(e))
        return {
            **state,
            "arxiv_papers": [],
            "current_step": "arxiv_search_error",
        }
