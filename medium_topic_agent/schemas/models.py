"""Pydantic models for input/output validation."""

from pydantic import BaseModel, Field
from typing import Optional


class UserInput(BaseModel):
    """Validated user input for topic generation."""
    
    background: str = Field(
        ...,
        min_length=10,
        description="User's professional background and expertise"
    )
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Keywords/topics of interest (1-10 keywords)"
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Target audience for the articles"
    )
    preferred_style: Optional[str] = Field(
        default=None,
        description="Preferred writing style (tutorial, opinion, case study, etc.)"
    )
    expertise_level: Optional[str] = Field(
        default="intermediate",
        description="Target expertise level (beginner, intermediate, advanced)"
    )


class SearchResult(BaseModel):
    """Web search result from DuckDuckGo."""
    
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"


class ResearchPaper(BaseModel):
    """Research paper from ArXiv."""
    
    title: str
    authors: list[str]
    summary: str
    published: str
    arxiv_url: str
    categories: list[str] = Field(default_factory=list)


class TrendInsights(BaseModel):
    """Analyzed trend insights from search results."""
    
    hot_topics: list[str] = Field(
        description="Currently trending topics with high engagement"
    )
    content_gaps: list[str] = Field(
        description="Underserved niches with opportunity"
    )
    emerging_trends: list[str] = Field(
        description="New trends gaining momentum"
    )
    evergreen_topics: list[str] = Field(
        description="Timeless topics with consistent interest"
    )
    research_frontiers: list[str] = Field(
        description="Cutting-edge research topics from ArXiv"
    )


class Topic(BaseModel):
    """Generated topic idea."""
    
    title: str = Field(description="Catchy article title")
    hook: str = Field(description="Opening hook to grab attention")
    description: str = Field(description="Brief description of what the article covers")
    unique_angle: str = Field(description="What makes this topic unique")
    target_audience: str = Field(description="Who this article is for")
    article_type: str = Field(description="Type: tutorial, opinion, case study, etc.")
    estimated_read_time: str = Field(default="5-7 min", description="Estimated reading time")


class TopicScore(BaseModel):
    """Individual score components for a topic."""
    
    trend_score: int = Field(ge=0, le=100, description="How trending is this topic")
    uniqueness_score: int = Field(ge=0, le=100, description="How differentiated from existing content")
    engagement_score: int = Field(ge=0, le=100, description="Likelihood of engagement (claps/shares)")
    author_fit_score: int = Field(ge=0, le=100, description="Match with author's background")
    research_depth_score: int = Field(ge=0, le=100, description="Backed by research/data")


class ScoredTopic(BaseModel):
    """Topic with scores and ranking."""
    
    topic: Topic
    scores: TopicScore
    overall_score: float = Field(ge=0, le=100, description="Weighted average score")
    rank: int = Field(ge=1, description="Rank among all topics")
    reasoning: str = Field(description="Explanation for the scores")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions to improve the topic"
    )


class AgentOutput(BaseModel):
    """Final output from the agent."""
    
    topics: list[ScoredTopic] = Field(description="Ranked list of topic suggestions")
    trend_summary: str = Field(description="Summary of current trends in the domain")
    research_highlights: list[str] = Field(
        default_factory=list,
        description="Key insights from research papers"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (search count, papers analyzed, etc.)"
    )
