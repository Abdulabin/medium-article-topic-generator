"""CLI entry point for the Medium Topic Suggestion Agent."""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from medium_topic_agent.agent import MediumTopicAgent
from medium_topic_agent.utils import setup_logging, save_topics_to_markdown

console = Console()


def display_welcome():
    """Display welcome message."""
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]📝 Medium Article Topic Suggestion Agent[/bold blue]\n\n"
            "I'll help you find the best topics for your Medium articles\n"
            "based on your background, trending topics, and research insights.",
            border_style="blue",
        )
    )
    console.print()


def get_user_input() -> tuple[str, list[str], str]:
    """Collect user input interactively."""
    console.print("[bold cyan]Let's gather some information about you:[/bold cyan]\n")
    
    background = Prompt.ask(
        "[yellow]📋 Your professional background[/yellow]\n"
        "   (e.g., 'Software engineer with 5 years experience in Python and ML')"
    )
    console.print()
    
    keywords_str = Prompt.ask(
        "[yellow]🔑 Keywords/topics of interest[/yellow]\n"
        "   (comma-separated, e.g., 'python, machine learning, fastapi')"
    )
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    console.print()
    
    target_audience = Prompt.ask(
        "[yellow]👥 Target audience[/yellow]\n"
        "   (e.g., 'beginner developers', 'data scientists', 'tech managers')",
        default="general tech audience"
    )
    
    return background, keywords, target_audience


def display_clarification_questions(questions: list[str]) -> dict:
    """Display clarification questions and collect responses."""
    console.print()
    console.print("[bold yellow]🤔 I need a bit more information:[/bold yellow]\n")
    
    responses = {}
    for i, question in enumerate(questions, 1):
        response = Prompt.ask(f"[cyan]{i}. {question}[/cyan]")
        responses[f"q{i}"] = response
        console.print()
    
    return responses


def display_results(result: dict):
    """Display the final topic suggestions."""
    console.print()
    console.print(Panel.fit("[bold green]✨ Topic Suggestions Ready![/bold green]", border_style="green"))
    console.print()
    
    # Display trend summary
    trend_insights = result.get("trend_insights", {})
    if trend_insights.get("key_insights"):
        console.print("[bold cyan]📊 Trend Insights:[/bold cyan]")
        console.print(Markdown(trend_insights["key_insights"]))
        console.print()
    
    topics = result.get("topics", [])
    
    if not topics:
        console.print("[red]No topics were generated. Please try again with different keywords.[/red]")
        return
    
    for i, scored_topic in enumerate(topics, 1):
        topic = scored_topic.get("topic", scored_topic)
        scores = scored_topic.get("scores", {})
        overall_score = scored_topic.get("overall_score", 0)
        rank = scored_topic.get("rank", i)
        
        title = topic.get("title", "Untitled")
        hook = topic.get("hook", "")
        description = topic.get("description", "")
        unique_angle = topic.get("unique_angle", "")
        article_type = topic.get("article_type", "article")
        read_time = topic.get("estimated_read_time", "5 min")
        
        score_bar = "█" * int(overall_score / 10) + "░" * (10 - int(overall_score / 10))
        
        content = f"""[bold]{title}[/bold]

[italic]"{hook}"[/italic]

{description}

[cyan]Unique Angle:[/cyan] {unique_angle}
[cyan]Type:[/cyan] {article_type} | [cyan]Read Time:[/cyan] {read_time}

[bold]Score:[/bold] {score_bar} {overall_score:.1f}/100
"""
        
        if scores:
            score_details = (
                f"📈 Trend: {scores.get('trend_score', 0)} | "
                f"✨ Unique: {scores.get('uniqueness_score', 0)} | "
                f"💬 Engage: {scores.get('engagement_score', 0)} | "
                f"👤 Fit: {scores.get('author_fit_score', 0)} | "
                f"📚 Research: {scores.get('research_depth_score', 0)}"
            )
            content += f"\n[dim]{score_details}[/dim]"
        
        reasoning = scored_topic.get("reasoning", "")
        if reasoning:
            content += f"\n\n[yellow]Why this topic:[/yellow] {reasoning}"
        
        recommendations = scored_topic.get("recommendations", [])
        if recommendations:
            content += "\n\n[green]Recommendations:[/green]"
            for rec in recommendations[:2]:
                content += f"\n  • {rec}"
        
        border_color = "green" if rank == 1 else "yellow" if rank <= 3 else "blue"
        
        console.print(Panel(content, title=f"[bold]#{rank}[/bold]", border_style=border_color))
        console.print()
    
    metadata = result.get("metadata", {})
    console.print(
        f"[dim]📊 Analyzed {metadata.get('web_results_count', 0)} web results and "
        f"{metadata.get('arxiv_papers_count', 0)} research papers[/dim]"
    )


def run_with_spinner(func, message: str):
    """Run a function with a progress spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(message, total=None)
        return func()


def main():
    """Main entry point for the CLI."""
    setup_logging()
    display_welcome()
    
    try:
        background, keywords, target_audience = get_user_input()
        
        if not keywords:
            console.print("[red]Error: At least one keyword is required.[/red]")
            sys.exit(1)
        
        console.print()
        
        agent = MediumTopicAgent()
        
        # Run agent
        result = run_with_spinner(
            lambda: agent.run(
                background=background,
                keywords=keywords,
                target_audience=target_audience,
            ),
            "Analyzing trends and generating topics..."
        )
        
        # Handle clarification if needed
        if result.get("status") == "needs_clarification":
            questions = result.get("questions", [])
            if questions:
                responses = display_clarification_questions(questions)
                console.print()
                result = run_with_spinner(
                    lambda: agent.continue_with_responses(
                        state=result.get("state", {}),
                        responses=responses,
                    ),
                    "Continuing analysis with your responses..."
                )
        
        # Display and save results
        if result.get("status") == "success":
            display_results(result)
            
            # Save to markdown file
            console.print()
            if Confirm.ask("[cyan]Would you like to save the results to a markdown file?[/cyan]", default=True):
                filepath = save_topics_to_markdown(
                    result=result,
                    background=background,
                    keywords=keywords,
                )
                console.print(f"\n[green]✅ Results saved to:[/green] [bold]{filepath}[/bold]")
        else:
            error = result.get("error", "Unknown error occurred")
            console.print(f"[red]Error: {error}[/red]")
            sys.exit(1)
        
        # Ask to continue
        console.print()
        if Confirm.ask("[cyan]Would you like to generate more topics with different parameters?[/cyan]"):
            main()
        else:
            console.print("\n[green]Thank you for using Medium Topic Agent! Happy writing! 📝[/green]\n")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]An error occurred: {str(e)}[/red]")
        console.print("[dim]Please check your configuration and try again.[/dim]")
        raise


if __name__ == "__main__":
    main()
