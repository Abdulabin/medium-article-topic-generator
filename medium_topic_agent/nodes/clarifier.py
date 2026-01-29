"""Clarifier node - generates follow-up questions using LLM."""

from langchain_core.messages import SystemMessage, HumanMessage

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)


CLARIFICATION_PROMPT = """You are helping a content creator decide on the best Medium article topics.

Based on the user's input, generate 2-3 specific follow-up questions to better understand:
1. Their unique expertise and perspective
2. Their target audience's needs and pain points
3. The specific angle or approach they want to take
4. Any constraints (time, depth, controversy level)

User's Background: {background}
Keywords: {keywords}
Target Audience: {target_audience}

Existing questions to avoid repeating: {existing_questions}

Generate concise, actionable questions that will help create better topic suggestions.
Format: Return only the questions, one per line, without numbering."""


def clarifier_node(state: AgentState, llm) -> AgentState:
    """Generate intelligent follow-up questions using LLM.
    
    Args:
        state: Current agent state.
        llm: Language model instance.
        
    Returns:
        Updated state with clarification questions.
    """
    logger.info("clarifier_start")
    
    try:
        background = state.get("user_background", "Not provided")
        keywords = state.get("keywords", [])
        target_audience = state.get("target_audience", "Not specified")
        existing_questions = state.get("clarification_questions", [])
        
        prompt = CLARIFICATION_PROMPT.format(
            background=background,
            keywords=", ".join(keywords),
            target_audience=target_audience,
            existing_questions="\n".join(existing_questions) if existing_questions else "None",
        )
        
        messages = [
            SystemMessage(content="You are an expert content strategist for Medium articles."),
            HumanMessage(content=prompt),
        ]
        
        response = llm.invoke(messages)
        
        # Parse questions from response
        new_questions = [
            q.strip() 
            for q in response.content.strip().split("\n") 
            if q.strip() and not q.strip().startswith("#")
        ]
        
        # Combine with existing questions, avoid duplicates
        all_questions = list(set(existing_questions + new_questions))[:5]  # Max 5 questions
        
        logger.info("clarifier_complete", num_questions=len(all_questions))
        
        return {
            **state,
            "clarification_questions": all_questions,
            "current_step": "clarification_ready",
        }
        
    except Exception as e:
        logger.error("clarifier_error", error=str(e))
        # Don't fail the whole pipeline, just continue without additional questions
        return {
            **state,
            "current_step": "clarification_skipped",
        }
