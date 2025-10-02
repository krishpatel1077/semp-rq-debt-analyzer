#!/usr/bin/env python3
"""
SEMP Requirements Debt Analyzer - Main Application
"""
import sys
import json
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from loguru import logger

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import settings
from src.agent.session_manager import SEMPChatSessionManager
from src.rag.knowledge_base import SEMPKnowledgeBase
from src.agent.debt_analyzer import RequirementsDebtAnalyzer
from src.models.debt_models import AnalysisRequest, SeverityLevel

console = Console()

# Configure logging
logger.remove()
logger.add(
    sys.stderr, 
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """SEMP Requirements Debt Analyzer - A proof-of-concept tool for analyzing requirements debt in Systems Engineering Management Plans."""
    pass


@cli.command()
@click.option('--force-refresh', is_flag=True, help='Force reprocessing of all documents')
def init_knowledge_base(force_refresh):
    """Initialize or refresh the knowledge base from S3 documents."""
    console.print(Panel("Initializing Knowledge Base", style="blue"))
    
    try:
        kb = SEMPKnowledgeBase()
        
        with Progress() as progress:
            task = progress.add_task("Processing documents...", total=100)
            
            success = kb.initialize_knowledge_base(force_refresh=force_refresh)
            progress.update(task, completed=100)
        
        if success:
            console.print("✅ Knowledge base initialized successfully!", style="green")
        else:
            console.print("❌ Failed to initialize knowledge base", style="red")
            
    except Exception as e:
        logger.error(f"Knowledge base initialization failed: {e}")
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
@click.argument('document_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file for results')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'summary']), default='table', help='Output format')
@click.option('--severity', type=click.Choice(['Low', 'Medium', 'High', 'Critical']), default='Low', help='Minimum severity threshold')
@click.option('--no-suggestions', is_flag=True, help='Exclude improvement suggestions')
def analyze(document_file, output, output_format, severity, no_suggestions):
    """Analyze a SEMP document for requirements debt."""
    console.print(Panel(f"Analyzing Document: {document_file.name}", style="blue"))
    
    try:
        # Read document content (in binary mode for proper handling of PDFs and other file types)
        with open(document_file, 'rb') as f:
            binary_content = f.read()
        
        # Initialize components
        kb = SEMPKnowledgeBase()
        analyzer = RequirementsDebtAnalyzer(kb)
        
        # Extract text from the document using the document processor
        from src.rag.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        text_content = processor.extract_text(binary_content, document_file.name)
        
        if not text_content:
            console.print(f"❌ Failed to extract text from {document_file.name}", style="red")
            return
        
        # Create analysis request
        request = AnalysisRequest(
            document_content=text_content,
            document_name=document_file.name,
            severity_threshold=SeverityLevel(severity),
            include_suggestions=not no_suggestions
        )
        
        # Perform analysis
        with Progress() as progress:
            task = progress.add_task("Analyzing document...", total=100)
            result = analyzer.analyze_document(request)
            progress.update(task, completed=100)
        
        # Display results
        if output_format == 'table':
            display_results_table(result)
        elif output_format == 'json':
            display_results_json(result)
        else:
            display_results_summary(result)
        
        # Save output if specified
        if output:
            save_results(result, output, output_format)
            console.print(f"✅ Results saved to {output}", style="green")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
@click.option('--user-id', default='default', help='User ID for the session')
def chat(user_id):
    """Start an interactive chat session for SEMP analysis."""
    console.print(Panel("SEMP Requirements Debt Analyzer - Chat Mode", style="blue"))
    console.print("Type 'quit' or 'exit' to end the session\n")
    
    try:
        # Initialize session manager
        session_manager = SEMPChatSessionManager()
        
        # Create new session
        session_id = session_manager.create_session(user_id)
        if not session_id:
            console.print("❌ Failed to create chat session", style="red")
            return
        
        console.print(f"Chat session created: {session_id[:8]}...", style="green")
        console.print("Hello! I'm ready to help analyze SEMP documents for requirements debt.\n")
        
        while True:
            try:
                user_input = console.input("[bold blue]You:[/bold blue] ")
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                
                if not user_input.strip():
                    continue
                
                # Process message
                response = session_manager.process_user_message(session_id, user_input)
                
                # Display response
                console.print(f"[bold green]Assistant:[/bold green] {response}\n")
                
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        # Close session
        session_manager.close_session(session_id)
        console.print("\n👋 Chat session ended. Goodbye!", style="blue")
        
    except Exception as e:
        logger.error(f"Chat session failed: {e}")
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
@click.option('--query', required=True, help='Search query')
@click.option('--top-k', default=5, help='Number of results to return')
@click.option('--threshold', default=0.6, help='Minimum relevance score')
def search(query, top_k, threshold):
    """Search the knowledge base for relevant information."""
    console.print(Panel(f"Searching Knowledge Base: '{query}'", style="blue"))
    
    try:
        kb = SEMPKnowledgeBase()
        results = kb.search_knowledge_base(query, top_k=top_k, score_threshold=threshold)
        
        if not results:
            console.print("No relevant results found", style="yellow")
            return
        
        # Display results
        table = Table(title="Search Results")
        table.add_column("Document", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Score", style="green")
        table.add_column("Content Preview", style="white")
        
        for result in results:
            preview = result['text'][:100] + "..." if len(result['text']) > 100 else result['text']
            table.add_row(
                result['document'],
                result['document_type'],
                f"{result['score']:.3f}",
                preview
            )
        
        console.print(table)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
def status():
    """Show system status and configuration."""
    console.print(Panel("System Status", style="blue"))
    
    # Configuration info
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Environment", settings.environment)
    config_table.add_row("AWS Region", settings.aws_region)
    config_table.add_row("S3 Bucket", settings.s3_knowledge_base_bucket)
    config_table.add_row("Chat History Table", settings.dynamodb_chat_history_table)
    config_table.add_row("Bedrock Model", settings.bedrock_model_id)
    config_table.add_row("Log Level", settings.log_level)
    
    console.print(config_table)
    
    # Test connections
    console.print("\n🔍 Testing Connections...")
    
    try:
        from src.infrastructure.s3_client import S3KnowledgeBaseClient
        from src.infrastructure.dynamodb_client import DynamoDBChatClient
        from src.infrastructure.bedrock_client import BedrockClient
        
        # Test S3
        try:
            s3_client = S3KnowledgeBaseClient()
            docs = s3_client.list_documents()
            console.print(f"✅ S3 Connection: {len(docs)} documents found", style="green")
        except Exception as e:
            console.print(f"❌ S3 Connection: {e}", style="red")
        
        # Test DynamoDB
        try:
            db_client = DynamoDBChatClient()
            # Try to get info for a non-existent session (should not error)
            db_client.get_session_info("test-session")
            console.print("✅ DynamoDB Connection: OK", style="green")
        except Exception as e:
            console.print(f"❌ DynamoDB Connection: {e}", style="red")
        
        # Test Bedrock
        try:
            bedrock_client = BedrockClient()
            if bedrock_client.test_connection():
                console.print("✅ Bedrock Connection: OK", style="green")
            else:
                console.print("❌ Bedrock Connection: Failed", style="red")
        except Exception as e:
            console.print(f"❌ Bedrock Connection: {e}", style="red")
        
        # Test Knowledge Base
        try:
            kb = SEMPKnowledgeBase()
            all_chunks = kb.get_all_chunks()
            console.print(f"✅ Knowledge Base: {len(all_chunks)} chunks loaded", style="green")
        except Exception as e:
            console.print(f"❌ Knowledge Base: {e}", style="red")
            
    except Exception as e:
        console.print(f"❌ Status check failed: {e}", style="red")


def display_results_table(result):
    """Display analysis results in table format."""
    if not result.issues:
        console.print("No issues found in the analysis.", style="yellow")
        return
    
    # Summary panel
    summary_text = f"""Total Issues: {result.total_issues}
Analysis Duration: {result.analysis_duration:.2f}s
High/Critical Issues: {result.summary.get('high_severity_issues', 0)}
Average Confidence: {result.summary.get('average_confidence', 0.0):.2f}"""
    
    console.print(Panel(summary_text, title="Analysis Summary", style="blue"))
    
    # Results table - no width restrictions to show full content
    table = Table(title="Requirements Debt Analysis Results", show_lines=True, expand=True)
    table.add_column("Location in Text", style="cyan", no_wrap=False, max_width=50)
    table.add_column("Debt Type / Problem", style="red", no_wrap=False)
    table.add_column("Recommended Fix", style="green", no_wrap=False)
    table.add_column("Reference", style="yellow", no_wrap=False, max_width=30)
    table.add_column("Severity", style="bold", width=10)
    
    for issue in result.issues[:20]:  # Limit to first 20
        # Show full content, let Rich handle text wrapping
        location = issue.location_in_text
        problem = f"{issue.debt_type.value}: {issue.problem_description}"
        fix = issue.recommended_fix
        reference = issue.reference
        
        severity_style = {
            "Low": "dim",
            "Medium": "yellow",
            "High": "red",
            "Critical": "bold red"
        }.get(issue.severity.value, "white")
        
        table.add_row(location, problem, fix, reference, f"[{severity_style}]{issue.severity.value}[/{severity_style}]")
    
    console.print(table)
    
    if len(result.issues) > 20:
        console.print(f"\n[dim]Showing first 20 of {len(result.issues)} total issues[/dim]")


def display_results_json(result):
    """Display analysis results in JSON format."""
    console.print(json.dumps(result.dict(), indent=2, default=str))


def display_results_summary(result):
    """Display analysis results summary."""
    summary_text = f"""
Analysis Complete: {result.document_name}

📊 Summary Statistics:
• Total Issues: {result.total_issues}
• Analysis Duration: {result.analysis_duration:.2f} seconds
• High/Critical Issues: {result.summary.get('high_severity_issues', 0)}
• Average Confidence: {result.summary.get('average_confidence', 0.0):.2f}

📈 Issue Distribution by Severity:"""
    
    for severity, count in result.severity_distribution.items():
        if count > 0:
            summary_text += f"\n  • {severity}: {count} issues"
    
    summary_text += f"\n\n🎯 Most Common Debt Type: {result.summary.get('most_common_debt_type', 'N/A')}"
    summary_text += f"\n💡 Recommendations Provided: {result.summary.get('recommendations_provided', 0)}"
    
    console.print(Panel(summary_text, title="Analysis Summary", style="blue"))


def save_results(result, output_path, format_type):
    """Save analysis results to file."""
    if format_type == 'json':
        with open(output_path, 'w') as f:
            json.dump(result.dict(), f, indent=2, default=str)
    else:
        # Save as text/markdown
        with open(output_path, 'w') as f:
            f.write(f"# SEMP Requirements Debt Analysis Results\n\n")
            f.write(f"**Document:** {result.document_name}\n")
            f.write(f"**Analysis Date:** {result.analysis_timestamp}\n")
            f.write(f"**Total Issues:** {result.total_issues}\n")
            f.write(f"**Analysis Duration:** {result.analysis_duration:.2f} seconds\n\n")
            
            f.write("## Issues Found\n\n")
            f.write("| Location | Debt Type / Problem | Recommended Fix | Reference | Severity |\n")
            f.write("|----------|-------------------|-----------------|-----------|----------|\n")
            
            for issue in result.issues:
                # Escape pipe characters but don't truncate content
                location = issue.location_in_text.replace('|', '\\|').replace('\n', ' ')
                problem = f"{issue.debt_type.value}: {issue.problem_description}".replace('|', '\\|').replace('\n', ' ')
                fix = issue.recommended_fix.replace('|', '\\|').replace('\n', ' ')
                reference = issue.reference.replace('|', '\\|').replace('\n', ' ')
                
                f.write(f"| {location} | {problem} | {fix} | {reference} | {issue.severity.value} |\n")


if __name__ == '__main__':
    cli()