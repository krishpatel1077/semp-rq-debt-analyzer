"""
Chat session manager for interactive SEMP analysis
"""
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

from src.infrastructure.dynamodb_client import DynamoDBChatClient
from src.models.debt_models import ChatSession, AnalysisResult, AnalysisRequest
from src.agent.debt_analyzer import RequirementsDebtAnalyzer
from src.rag.knowledge_base import SEMPKnowledgeBase
from config.settings import settings


class SEMPChatSessionManager:
    """Manages chat sessions for SEMP analysis"""
    
    def __init__(self):
        self.db_client = DynamoDBChatClient()
        self.knowledge_base = SEMPKnowledgeBase()
        self.analyzer = RequirementsDebtAnalyzer(self.knowledge_base)
        
        logger.info("SEMP Chat Session Manager initialized")
    
    def create_session(self, user_id: str = "default") -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        try:
            # Create session in DynamoDB
            success = self.db_client.create_chat_session(session_id, user_id)
            
            if success:
                logger.info(f"Created chat session: {session_id}")
                
                # Add welcome message
                self.add_message(
                    session_id,
                    "assistant",
                    "Hello! I'm your SEMP Requirements Debt Analyzer. I can help you identify and analyze requirements debt in Systems Engineering Management Plans. You can upload a SEMP document for analysis or ask questions about requirements engineering best practices.",
                    {"type": "welcome"}
                )
                
                return session_id
            else:
                logger.error("Failed to create chat session in database")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            return None
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Add a message to the chat session"""
        try:
            return self.db_client.add_message(session_id, role, content, metadata)
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            return False
    
    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get chat history for a session"""
        try:
            limit = limit or settings.max_chat_history
            return self.db_client.get_chat_history(session_id, limit) or []
        except Exception as e:
            logger.error(f"Failed to get chat history for session {session_id}: {e}")
            return []
    
    def process_user_message(self, session_id: str, user_message: str) -> str:
        """Process a user message and generate a response"""
        try:
            # Add user message to session
            self.add_message(session_id, "user", user_message)
            
            # Get chat history for context
            chat_history = self.get_chat_history(session_id, limit=10)
            
            # Determine the type of request
            request_type = self._classify_user_request(user_message, chat_history)
            
            # Process based on request type
            if request_type == "analyze_document":
                response = self._handle_document_analysis(session_id, user_message, chat_history)
            elif request_type == "ask_question":
                response = self._handle_question(session_id, user_message, chat_history)
            elif request_type == "view_results":
                response = self._handle_results_query(session_id, user_message, chat_history)
            else:
                response = self._handle_general_conversation(session_id, user_message, chat_history)
            
            # Add assistant response to session
            self.add_message(session_id, "assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process user message in session {session_id}: {e}")
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            self.add_message(session_id, "assistant", error_response)
            return error_response
    
    def analyze_document(
        self, 
        session_id: str, 
        document_content: str, 
        document_name: str,
        analysis_options: Dict = None
    ) -> AnalysisResult:
        """Analyze a SEMP document and store results in session"""
        try:
            # Create analysis request
            options = analysis_options or {}
            request = AnalysisRequest(
                document_content=document_content,
                document_name=document_name,
                session_id=session_id,
                **options
            )
            
            # Perform analysis
            result = self.analyzer.analyze_document(request)
            
            # Store analysis result in session context
            session_info = self.db_client.get_session_info(session_id)
            if session_info:
                # Update session with current analysis
                self.db_client.store_agent_info(
                    f"session_analysis_{session_id}",
                    {
                        "current_document": document_name,
                        "last_analysis": result.dict(),
                        "analysis_timestamp": result.analysis_timestamp.isoformat()
                    }
                )
            
            # Add analysis summary message to chat
            summary_message = self._create_analysis_summary_message(result)
            self.add_message(
                session_id, 
                "assistant", 
                summary_message,
                {"type": "analysis_summary", "analysis_id": result.document_id}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze document in session {session_id}: {e}")
            raise
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context and state"""
        try:
            # Get session info
            session_info = self.db_client.get_session_info(session_id)
            
            # Get analysis info if available
            analysis_info = self.db_client.get_agent_info(f"session_analysis_{session_id}")
            
            context = {
                "session_info": session_info,
                "current_analysis": analysis_info,
                "chat_history_length": len(self.get_chat_history(session_id))
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get session context for {session_id}: {e}")
            return {}
    
    def _classify_user_request(self, message: str, chat_history: List[Dict]) -> str:
        """Classify the type of user request"""
        message_lower = message.lower()
        
        # Check for explicit document analysis requests (must contain action + document reference)
        analysis_patterns = [
            "analyze this document", "analyze my semp", "check this document", "review this semp",
            "analyze document", "process this semp", "upload document", "upload file",
            "analyze the document", "check my semp", "review document"
        ]
        if any(phrase in message_lower for phrase in analysis_patterns):
            return "analyze_document"
        
        # Check for results/findings queries (asking about existing analysis)
        results_patterns = [
            "show results", "view findings", "analysis results", "show issues", 
            "view results", "display results", "last analysis", "previous analysis",
            "show summary", "analysis summary", "show findings", "latest results"
        ]
        if any(phrase in message_lower for phrase in results_patterns):
            return "view_results"
        
        # Prioritize general questions (educational/conceptual queries)
        question_patterns = [
            "what is", "what are", "how does", "how do", "explain", "define", 
            "tell me about", "describe", "why", "when", "where", "help me understand",
            "best practices", "methodology", "standard", "approach", "difference between",
            "advantages of", "disadvantages of", "benefits of", "challenges of"
        ]
        if any(pattern in message_lower for pattern in question_patterns):
            return "ask_question"
        
        # If message contains SE/requirements terms without action words, treat as question
        se_terms = [
            'requirements debt', 'technical debt', 'requirements engineering',
            'systems engineering', 'verification', 'validation', 'traceability', 
            'requirements management', 'semp standards', 'semp best practices'
        ]
        
        action_words = [
            'analyze', 'upload', 'process', 'check', 'review', 'show', 'view', 'display'
        ]
        
        if (any(term in message_lower for term in se_terms) and 
            not any(action in message_lower for action in action_words)):
            return "ask_question"
        
        # Default to general question for everything else (be more inclusive)
        return "ask_question"
    
    def _handle_document_analysis(self, session_id: str, message: str, chat_history: List[Dict]) -> str:
        """Handle document analysis requests"""
        return """I'm ready to analyze your SEMP document for requirements debt. Please provide the document content in one of these ways:

1. **Paste the text directly** into the chat
2. **Upload a file** (if using the file upload feature)
3. **Provide a document URL** or S3 key if it's already in the knowledge base

Once you provide the document, I'll analyze it for potential requirements debt issues including:
- Ambiguity and vague terminology
- Incompleteness and missing constraints  
- Inconsistency and conflicting requirements
- Traceability gaps
- Unclear acceptance criteria
- Untestable requirements

The analysis will include specific locations, problem descriptions, recommended fixes, and references to best practices from my knowledge base."""
    
    def _handle_question(self, session_id: str, message: str, chat_history: List[Dict]) -> str:
        """Handle general questions about requirements engineering"""
        try:
            # Search knowledge base for relevant information
            search_results = self.knowledge_base.search_knowledge_base(
                message, top_k=5, score_threshold=0.3
            )
            
            if search_results:
                # Prepare context from search results
                context = "\n".join([
                    f"From {result['document']}: {result['text'][:300]}..."
                    for result in search_results
                ])
                
                # Generate response using the knowledge base context
                response = f"""Based on systems engineering best practices and standards:

{self._generate_contextual_response(message, context)}

**References:**
{'; '.join([f"{r['document']} (relevance: {r['score']:.2f})" for r in search_results[:2]])}

Would you like me to elaborate on any specific aspect or analyze a SEMP document related to this topic?"""
            else:
                # Try to provide a general answer based on common knowledge
                response = self._provide_general_answer(message)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle question: {e}")
            return "I encountered an error processing your question. Please try rephrasing it or ask about a specific SEMP analysis topic."
    
    def _handle_results_query(self, session_id: str, message: str, chat_history: List[Dict]) -> str:
        """Handle queries about analysis results"""
        try:
            # Get current analysis from session
            analysis_info = self.db_client.get_agent_info(f"session_analysis_{session_id}")
            
            if not analysis_info or "last_analysis" not in analysis_info:
                return "I don't have any recent analysis results to show. Please analyze a SEMP document first by providing the document content."
            
            # Parse the stored analysis
            analysis_data = analysis_info["last_analysis"]
            
            # Create a formatted response based on what user is asking
            if "summary" in message.lower():
                return self._format_analysis_summary(analysis_data)
            elif "table" in message.lower() or "format" in message.lower():
                return self._format_analysis_table(analysis_data)
            elif "high" in message.lower() or "critical" in message.lower():
                return self._format_high_severity_issues(analysis_data)
            else:
                return self._format_general_results(analysis_data)
                
        except Exception as e:
            logger.error(f"Failed to handle results query: {e}")
            return "I encountered an error retrieving the analysis results. Please try your request again."
    
    def _handle_general_conversation(self, session_id: str, message: str, chat_history: List[Dict]) -> str:
        """Handle general conversation"""
        # If it seems like a question, try to provide a useful answer
        if any(word in message.lower() for word in ['?', 'what', 'how', 'why', 'when', 'where']):
            return self._provide_general_answer(message)
        
        # Otherwise provide the standard welcome/help message
        return """I'm specialized in analyzing Systems Engineering Management Plans (SEMPs) for requirements debt. I can help you with:

🔍 **Document Analysis**: Identify debt issues like ambiguity, incompleteness, and inconsistencies
📊 **Results Review**: View analysis findings in structured tables with recommendations  
❓ **Q&A**: Answer questions about requirements engineering best practices
📚 **Knowledge Base**: Reference authoritative sources and standards

How would you like to proceed? You can:
- Share a SEMP document for analysis
- Ask about specific requirements engineering topics
- Request help with understanding requirements debt types"""
    
    def _create_analysis_summary_message(self, result: AnalysisResult) -> str:
        """Create a summary message for analysis results"""
        summary = result.summary
        
        message = f"""## Analysis Complete: {result.document_name}

**Summary:**
- **Total Issues Found:** {result.total_issues}
- **High/Critical Issues:** {summary.get('high_severity_issues', 0)}
- **Analysis Duration:** {result.analysis_duration:.2f} seconds
- **Average Confidence:** {summary.get('average_confidence', 0.0):.2f}

**Issue Distribution:**
"""
        
        # Add severity distribution
        for severity, count in result.severity_distribution.items():
            if count > 0:
                message += f"- **{severity}:** {count} issues\n"
        
        message += f"""
**Most Common Debt Type:** {summary.get('most_common_debt_type', 'N/A')}

Would you like to see the detailed results in a table format or focus on specific types of issues?"""
        
        return message
    
    def _generate_contextual_response(self, question: str, context: str) -> str:
        """Generate a response using knowledge base context and Bedrock"""
        try:
            # Create a prompt for Bedrock to generate a comprehensive answer
            system_prompt = "You are an expert in Requirements Engineering and Systems Engineering. Answer questions clearly and concisely based on the provided context from authoritative sources."
            
            user_prompt = f"""Question: {question}

Context from authoritative systems engineering documents:
{context}

Please provide a clear, comprehensive answer to the question based on the context provided. Focus on practical guidance and best practices."""
            
            # Generate response using Bedrock
            from src.infrastructure.bedrock_client import BedrockClient
            bedrock_client = BedrockClient()
            
            response = bedrock_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate contextual response: {e}")
            # Fallback to simple context presentation
            return f"Based on the available documentation:\n\n{context[:800]}..."
    
    def _format_analysis_table(self, analysis_data: Dict) -> str:
        """Format analysis results as a table"""
        issues = analysis_data.get("issues", [])
        
        if not issues:
            return "No issues were found in the analysis."
        
        table = """## Requirements Debt Analysis Results

| Location in Text | Debt Type / Problem | Recommended Fix | Reference | Severity |
|-----------------|-------------------|-----------------|-----------|----------|
"""
        
        for issue in issues[:10]:  # Limit to first 10 issues
            location = issue.get("location_in_text", "")[:50] + "..." if len(issue.get("location_in_text", "")) > 50 else issue.get("location_in_text", "")
            debt_type = issue.get("debt_type", "")
            problem = issue.get("problem_description", "")[:100] + "..." if len(issue.get("problem_description", "")) > 100 else issue.get("problem_description", "")
            fix = issue.get("recommended_fix", "")[:100] + "..." if len(issue.get("recommended_fix", "")) > 100 else issue.get("recommended_fix", "")
            reference = issue.get("reference", "")[:50] + "..." if len(issue.get("reference", "")) > 50 else issue.get("reference", "")
            severity = issue.get("severity", "")
            
            table += f"| {location} | {debt_type}: {problem} | {fix} | {reference} | {severity} |\n"
        
        if len(issues) > 10:
            table += f"\n*Showing first 10 of {len(issues)} total issues*"
        
        return table
    
    def _format_analysis_summary(self, analysis_data: Dict) -> str:
        """Format a summary of analysis results"""
        summary = analysis_data.get("summary", {})
        
        return f"""## Analysis Summary

**Overall Results:**
- Total Issues: {analysis_data.get('total_issues', 0)}
- High/Critical Issues: {summary.get('high_severity_issues', 0)}
- Sections Analyzed: {summary.get('sections_analyzed', 0)}
- Average Confidence: {summary.get('average_confidence', 0.0):.2f}

**Issue Breakdown:**
- Most Common Issue: {summary.get('most_common_debt_type', 'N/A')}
- Recommendations Provided: {summary.get('recommendations_provided', 0)}

Would you like to see the detailed table or focus on specific severity levels?"""
    
    def _format_high_severity_issues(self, analysis_data: Dict) -> str:
        """Format high severity issues only"""
        issues = analysis_data.get("issues", [])
        high_severity_issues = [
            issue for issue in issues 
            if issue.get("severity") in ["High", "Critical"]
        ]
        
        if not high_severity_issues:
            return "No high or critical severity issues were found in the analysis."
        
        result = f"## High Priority Issues ({len(high_severity_issues)} found)\n\n"
        
        for i, issue in enumerate(high_severity_issues, 1):
            result += f"""**Issue {i}: {issue.get('debt_type', 'Unknown')}** (Severity: {issue.get('severity', 'Unknown')})
- **Location:** {issue.get('location_in_text', 'Not specified')}
- **Problem:** {issue.get('problem_description', 'No description')}
- **Recommended Fix:** {issue.get('recommended_fix', 'No recommendation')}
- **Reference:** {issue.get('reference', 'No reference')}

"""
        
        return result
    
    def _format_general_results(self, analysis_data: Dict) -> str:
        """Format general results overview"""
        return f"""## Analysis Results Overview

The analysis found **{analysis_data.get('total_issues', 0)} total issues** in the document.

**Severity Breakdown:**
"""
        + "\n".join([
            f"- **{severity}:** {count} issues" 
            for severity, count in analysis_data.get('severity_distribution', {}).items()
            if count > 0
        ]) + """

**Debt Type Breakdown:**
"""
        + "\n".join([
            f"- **{debt_type}:** {count} issues"
            for debt_type, count in analysis_data.get('debt_type_distribution', {}).items()
            if count > 0
        ]) + """

Would you like to see:
1. Detailed table format
2. Only high/critical issues  
3. Issues of a specific type
4. Analysis summary

Just let me know what you'd prefer!"""

    def _provide_general_answer(self, question: str) -> str:
        """Provide a general answer using Bedrock for common SE concepts"""
        try:
            from src.infrastructure.bedrock_client import BedrockClient
            bedrock_client = BedrockClient()
            
            system_prompt = """You are an expert in Requirements Engineering, Systems Engineering, and Requirements Debt analysis. 
            Provide clear, comprehensive answers about systems engineering concepts, best practices, and methodologies. 
            Focus on practical guidance that would be valuable for systems engineers and requirements analysts."""
            
            user_prompt = f"""Please explain: {question}
            
            Provide a clear, educational answer covering:
            - Definition and key concepts
            - Why this is important in systems engineering
            - Best practices and common approaches
            - How it relates to requirements debt (if applicable)
            
            Keep the response practical and actionable."""
            
            response = bedrock_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            return response + "\n\n💡 *Would you like me to help you apply these concepts to a specific SEMP document, or do you have any follow-up questions?*"
            
        except Exception as e:
            logger.error(f"Failed to generate general answer: {e}")
            return """I'd be happy to help with your question about requirements engineering and systems engineering concepts. 
            
            I can assist with topics like:
            - Requirements debt and technical debt
            - SEMP analysis and best practices  
            - Requirements engineering methodologies
            - Systems engineering standards and processes
            
            Could you rephrase your question or provide more specific details about what you'd like to know?"""
    
    def close_session(self, session_id: str) -> bool:
        """Close a chat session"""
        try:
            return self.db_client.update_session_status(session_id, "completed")
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            return False
