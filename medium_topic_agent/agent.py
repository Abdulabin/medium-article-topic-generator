"""Main LangGraph agent definition for Medium Topic Suggestion."""

from typing import Literal
from functools import partial

from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.config import settings, get_llm_config
from medium_topic_agent.utils.logger import get_logger
from medium_topic_agent.nodes.input_collector import input_collector_node
from medium_topic_agent.nodes.clarifier import clarifier_node
from medium_topic_agent.nodes.web_searcher import web_searcher_node
from medium_topic_agent.nodes.arxiv_searcher import arxiv_searcher_node
from medium_topic_agent.nodes.trend_analyzer import trend_analyzer_node
from medium_topic_agent.nodes.topic_generator import topic_generator_node
from medium_topic_agent.nodes.scorer import scorer_node

logger = get_logger(__name__)

# Module-level LLM instance for reuse
_llm_instance = None


def _get_llm():
    """Initialize the LLM based on configuration (cached)."""
    global _llm_instance
    
    if _llm_instance is None:
        config = get_llm_config()
        model_string = config["model"]
        logger.info("initializing_llm", model=model_string)
        _llm_instance = init_chat_model(model_string)
    
    return _llm_instance


def _should_clarify(state: AgentState) -> Literal["clarify", "research"]:
    """Determine if clarification is needed or proceed to research."""
    if state.get("needs_clarification") and not state.get("user_responses"):
        return "clarify"
    return "research"


def _build_research_graph(llm) -> StateGraph:
    """Build the research-to-scoring portion of the graph.
    
    This is shared between the main graph and continuation workflow.
    """
    web_searcher_with_llm = partial(web_searcher_node, llm=llm)
    arxiv_searcher_with_llm = partial(arxiv_searcher_node, llm=llm)
    trend_analyzer_with_llm = partial(trend_analyzer_node, llm=llm)
    topic_generator_with_llm = partial(topic_generator_node, llm=llm)
    scorer_with_llm = partial(scorer_node, llm=llm)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("web_searcher", web_searcher_with_llm)
    workflow.add_node("arxiv_searcher", arxiv_searcher_with_llm)
    workflow.add_node("trend_analyzer", trend_analyzer_with_llm)
    workflow.add_node("topic_generator", topic_generator_with_llm)
    workflow.add_node("scorer", scorer_with_llm)
    
    workflow.set_entry_point("web_searcher")
    workflow.add_edge("web_searcher", "arxiv_searcher")
    workflow.add_edge("arxiv_searcher", "trend_analyzer")
    workflow.add_edge("trend_analyzer", "topic_generator")
    workflow.add_edge("topic_generator", "scorer")
    workflow.add_edge("scorer", END)
    
    return workflow.compile()


def build_agent_graph() -> StateGraph:
    """Build the complete LangGraph agent workflow.
    
    Workflow:
    1. Input Collection → Check if clarification needed
    2. If clarification needed → Ask questions → END (caller handles responses)
    3. Research Phase → Web Search → ArXiv Search
    4. Analysis Phase → Trend Analysis
    5. Generation Phase → Topic Generation → Scoring
    6. Output → Return ranked topics
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    logger.info("building_agent_graph")
    
    llm = _get_llm()
    
    # Create partial functions with LLM bound
    input_collector_with_llm = partial(input_collector_node, llm=llm)
    clarifier_with_llm = partial(clarifier_node, llm=llm)
    web_searcher_with_llm = partial(web_searcher_node, llm=llm)
    arxiv_searcher_with_llm = partial(arxiv_searcher_node, llm=llm)
    trend_analyzer_with_llm = partial(trend_analyzer_node, llm=llm)
    topic_generator_with_llm = partial(topic_generator_node, llm=llm)
    scorer_with_llm = partial(scorer_node, llm=llm)
    
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("input_collector", input_collector_with_llm)
    workflow.add_node("clarifier", clarifier_with_llm)
    workflow.add_node("web_searcher", web_searcher_with_llm)
    workflow.add_node("arxiv_searcher", arxiv_searcher_with_llm)
    workflow.add_node("trend_analyzer", trend_analyzer_with_llm)
    workflow.add_node("topic_generator", topic_generator_with_llm)
    workflow.add_node("scorer", scorer_with_llm)
    
    # Set entry point and edges
    workflow.set_entry_point("input_collector")
    
    workflow.add_conditional_edges(
        "input_collector",
        _should_clarify,
        {"clarify": "clarifier", "research": "web_searcher"}
    )
    
    workflow.add_edge("clarifier", END)
    workflow.add_edge("web_searcher", "arxiv_searcher")
    workflow.add_edge("arxiv_searcher", "trend_analyzer")
    workflow.add_edge("trend_analyzer", "topic_generator")
    workflow.add_edge("topic_generator", "scorer")
    workflow.add_edge("scorer", END)
    
    compiled = workflow.compile()
    logger.info("agent_graph_built")
    
    return compiled


def _build_result(final_state: dict) -> dict:
    """Build the result dictionary from final state."""
    return {
        "status": "success",
        "topics": final_state.get("scored_topics", []),
        "trend_insights": final_state.get("trend_insights", {}),
        "metadata": {
            "web_results_count": len(final_state.get("web_search_results", [])),
            "arxiv_papers_count": len(final_state.get("arxiv_papers", [])),
            "topics_generated": len(final_state.get("generated_topics", [])),
        },
        "error": final_state.get("error"),
    }


class MediumTopicAgent:
    """High-level interface for the Medium Topic Suggestion Agent."""
    
    def __init__(self):
        """Initialize the agent."""
        self._graph = None
        self._research_graph = None
    
    @property
    def graph(self):
        """Lazy-load the main graph."""
        if self._graph is None:
            self._graph = build_agent_graph()
            logger.info("agent_initialized")
        return self._graph
    
    @property
    def research_graph(self):
        """Lazy-load the research continuation graph."""
        if self._research_graph is None:
            self._research_graph = _build_research_graph(_get_llm())
        return self._research_graph
    
    def run(
        self,
        background: str,
        keywords: list[str],
        target_audience: str = "",
        additional_context: dict = None,
        skip_clarification: bool = False,
    ) -> dict:
        """Run the agent to generate topic suggestions.
        
        Args:
            background: User's professional background.
            keywords: Keywords/topics of interest.
            target_audience: Target audience for articles.
            additional_context: Extra context or preferences.
            skip_clarification: Skip follow-up questions.
            
        Returns:
            Result dict with topics, insights, and metadata.
        """
        logger.info("agent_run_start", num_keywords=len(keywords))
        
        initial_state: AgentState = {
            "user_background": background,
            "keywords": keywords,
            "target_audience": target_audience,
            "additional_context": additional_context or {},
            "needs_clarification": False,
            "clarification_questions": [],
            "user_responses": {"skipped": True} if skip_clarification else None,
            "web_search_results": [],
            "arxiv_papers": [],
            "trend_insights": {},
            "generated_topics": [],
            "scored_topics": [],
            "error": None,
            "current_step": "start",
        }
        
        final_state = self.graph.invoke(initial_state)
        
        # Check if clarification is needed
        if final_state.get("needs_clarification") and not skip_clarification:
            logger.info("clarification_needed", questions=final_state.get("clarification_questions", []))
            return {
                "status": "needs_clarification",
                "questions": final_state.get("clarification_questions", []),
                "state": final_state,
            }
        
        logger.info("agent_run_complete", num_topics=len(final_state.get("scored_topics", [])))
        return _build_result(final_state)
    
    def continue_with_responses(self, state: dict, responses: dict) -> dict:
        """Continue after clarification questions are answered.
        
        Args:
            state: State from previous run.
            responses: User's responses to questions.
            
        Returns:
            Result dict with topics, insights, and metadata.
        """
        logger.info("agent_continue", num_responses=len(responses))
        
        continued_state = {
            **state,
            "user_responses": responses,
            "needs_clarification": False,
        }
        
        final_state = self.research_graph.invoke(continued_state)
        return _build_result(final_state)
