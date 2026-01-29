"""Input collector node - validates and processes user input."""

from langchain_core.prompts import ChatPromptTemplate

from medium_topic_agent.schemas.state import AgentState
from medium_topic_agent.utils.logger import get_logger

logger = get_logger(__name__)

CLARIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert content strategist helping a writer choose the best Medium article topics.

Analyze the user's input and determine if you need more information to generate excellent topic suggestions.

User Input:
- Background: {background}
- Keywords: {keywords}
- Target Audience: {target_audience}

Based on this input, decide:
1. Is the information sufficient to generate high-quality, personalized topic suggestions?
2. If not, what specific questions would help you understand their needs better?

Rules:
- Only ask questions if truly necessary (missing critical context)
- Maximum 3 questions
- Questions should be specific and actionable
- Don't ask if background is detailed (50+ chars), has 2+ keywords, and has target audience

Respond in this exact format:
NEEDS_CLARIFICATION: true/false
QUESTIONS:
- Question 1
- Question 2
- Question 3

If no clarification needed, respond with:
NEEDS_CLARIFICATION: false
QUESTIONS:
"""),
    ("human", "Analyze the input and determine if clarification is needed.")
])


def _parse_clarification_response(response_text: str) -> tuple[bool, list[str]]:
    """Parse the LLM response to extract clarification needs."""
    lines = response_text.strip().split("\n")
    needs_clarification = False
    questions = []
    
    for line in lines:
        line = line.strip()
        if line.upper().startswith("NEEDS_CLARIFICATION:"):
            value = line.split(":", 1)[1].strip().lower()
            needs_clarification = value == "true"
        elif line.startswith("- ") and needs_clarification:
            question = line[2:].strip()
            if question:
                questions.append(question)
    
    return needs_clarification, questions


def input_collector_node(state: AgentState, llm=None) -> AgentState:
    """Validate user input and use LLM to determine if clarification is needed.
    
    This node:
    1. Validates that required fields are present
    2. Uses LLM to intelligently determine if more info is needed
    3. Generates context-aware clarification questions
    
    Args:
        state: Current agent state with user input.
        llm: Language model for generating clarification questions.
        
    Returns:
        Updated state with validation results.
    """
    logger.info("input_collector_start", keywords=state.get("keywords", []))
    
    try:
        background = state.get("user_background", "").strip()
        keywords = state.get("keywords", [])
        target_audience = state.get("target_audience", "")
        
        # Basic validation
        if not keywords or len(keywords) < 1:
            return {
                **state,
                "error": "At least one keyword is required",
                "current_step": "error",
            }
        
        # Trim to max 10 keywords
        if len(keywords) > 10:
            keywords = keywords[:10]
        
        # Use LLM to determine if clarification is needed
        needs_clarification = False
        clarification_questions = []
        
        if llm:
            chain = CLARIFICATION_PROMPT | llm
            response = chain.invoke({
                "background": background or "Not provided",
                "keywords": ", ".join(keywords),
                "target_audience": target_audience or "Not specified",
            })
            
            needs_clarification, clarification_questions = _parse_clarification_response(
                response.content
            )
            
            logger.info(
                "llm_clarification_check",
                needs_clarification=needs_clarification,
                num_questions=len(clarification_questions),
            )
        else:
            # Fallback: simple heuristic if no LLM provided
            if not target_audience or len(background) < 30 or len(keywords) < 2:
                needs_clarification = True
                if not target_audience:
                    clarification_questions.append(
                        "Who is your target audience? (e.g., beginners, professionals)"
                    )
                if len(background) < 30:
                    clarification_questions.append(
                        "Can you share more about your expertise and experience?"
                    )
                if len(keywords) < 2:
                    clarification_questions.append(
                        "Can you provide 1-2 more related keywords?"
                    )
        
        logger.info(
            "input_collector_complete",
            needs_clarification=needs_clarification,
            num_questions=len(clarification_questions),
        )
        
        return {
            **state,
            "keywords": keywords,
            "needs_clarification": needs_clarification,
            "clarification_questions": clarification_questions,
            "current_step": "input_collected",
        }
        
    except Exception as e:
        logger.error("input_collector_error", error=str(e))
        return {
            **state,
            "error": f"Input validation failed: {str(e)}",
            "current_step": "error",
        }
