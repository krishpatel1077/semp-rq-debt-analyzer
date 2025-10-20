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
            # First check if we have analysis context for this session
            analysis_info = self.db_client.get_agent_info(f"session_analysis_{session_id}")
            
            # If we have analysis context and the question seems related to specific issues
            if analysis_info and self._is_analysis_specific_question(message):
                return self._handle_analysis_specific_question(message, analysis_info, session_id)
            
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
    
    def _is_analysis_specific_question(self, message: str) -> bool:
        """Check if the question is about specific analysis results"""
        analysis_indicators = [
            'this issue', 'this problem', 'this debt', 'this requirement',
            'vague terminology', 'ambiguity', 'incompleteness', 'inconsistency',
            'traceability gap', 'unclear acceptance', 'untestable', 'conflicting',
            'reliability', 'measurable terms', 'verify compliance', 'problematic',
            'should it be addressed', 'how should', 'what makes this',
            'why is this', 'how to fix', 'recommended fix',
            'ambiguity issue', 'requirements management process', 'change control',
            'lack of a clear', 'lack of a defined', 'does not describe',
            'explain more about', 'tell me about', 'what is problematic'
        ]
        
        # Also check for quoted text (indicates reference to specific issue)
        has_quotes = '"' in message and message.count('"') >= 2
        
        return any(indicator in message.lower() for indicator in analysis_indicators) or has_quotes
    
    def _handle_analysis_specific_question(self, message: str, analysis_info: Dict, session_id: str) -> str:
        """Handle questions about specific analysis issues"""
        try:
            analysis_data = analysis_info.get("last_analysis", {})
            issues = analysis_data.get("issues", [])
            
            if not issues:
                return "I don't have any specific issues to reference from the recent analysis."
            
            # Try to find the specific issue being asked about
            relevant_issues = []
            message_lower = message.lower()
            
            # Extract quoted text if present
            quoted_text = ""
            if '"' in message:
                import re
                quotes = re.findall(r'"([^"]+)"', message)
                if quotes:
                    quoted_text = quotes[0].lower()
            
            for issue in issues:
                issue_type = issue.get('debt_type', '').lower()
                problem_desc = issue.get('problem_description', '').lower()
                location = issue.get('location_in_text', '').lower()
                
                # Calculate relevance score
                relevance_score = 0
                
                # High relevance: exact issue type match
                if issue_type in message_lower:
                    relevance_score += 10
                
                # Medium relevance: quoted text matches problem description
                if quoted_text and quoted_text in problem_desc:
                    relevance_score += 8
                    
                # Medium relevance: key words from issue type
                for word in issue_type.split():
                    if len(word) > 3 and word in message_lower:
                        relevance_score += 3
                
                # Low relevance: key words from problem description  
                for word in problem_desc.split()[:10]:  # First 10 words are most important
                    if len(word) > 4 and word in message_lower:
                        relevance_score += 1
                
                # Add issue if it has any relevance
                if relevance_score > 0:
                    issue['_relevance_score'] = relevance_score
                    relevant_issues.append(issue)
            
            # Sort by relevance score
            relevant_issues.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)
            
            if relevant_issues:
                # Focus on the most relevant issue
                issue = relevant_issues[0]
                return self._explain_specific_issue(issue, message)
            else:
                # If no specific issue found, provide general guidance
                return self._provide_general_analysis_guidance(message, analysis_data)
                
        except Exception as e:
            logger.error(f"Failed to handle analysis-specific question: {e}")
            return "I encountered an error analyzing your question about the specific issue. Please try rephrasing your question."
    
    def _explain_specific_issue(self, issue: Dict, original_question: str) -> str:
        """Provide detailed AI-powered explanation of a specific issue"""
        try:
            issue_type = issue.get('debt_type', 'Unknown')
            problem = issue.get('problem_description', '')
            location = issue.get('location_in_text', '')
            fix = issue.get('recommended_fix', '')
            severity = issue.get('severity', '')
            confidence = issue.get('confidence', 0)
            reference = issue.get('reference', '')
            
            # Create a contextual prompt for the AI
            system_prompt = """You are an expert Requirements Engineering consultant. Provide clear, educational explanations about requirements debt issues. Be conversational, helpful, and focus on practical guidance that helps the user understand both the problem and the solution."""
            
            user_prompt = f"""I found this {issue_type} issue in a SEMP document analysis:

Problem: {problem}

Location: {location}

Recommended Fix: {fix}

Severity: {severity} | Confidence: {confidence*100:.0f}%

The user asked: "{original_question}"

Please provide a comprehensive, conversational explanation that addresses:
1. What makes this specific issue problematic in systems engineering
2. Why this type of requirements debt matters
3. How to implement the recommended fix practically
4. What could happen if this isn't addressed
5. Any additional insights or best practices

Be specific to this exact issue, not generic. Make it educational and actionable."""
            
            # Generate AI response using Bedrock
            from src.infrastructure.bedrock_client import BedrockClient
            bedrock_client = BedrockClient()
            
            ai_response = bedrock_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1200,
                temperature=0.3
            )
            
            # Add reference information
            response = f"{ai_response}\n\n---\n**Supporting References:** {reference}\n**Document Location:** {location}"
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate AI explanation: {e}")
            # Fallback to basic explanation
            issue_type = issue.get('debt_type', 'Unknown')
            problem = issue.get('problem_description', '')
            fix = issue.get('recommended_fix', '')
            
            return f"""## {issue_type} Issue

**The Problem:** {problem}

**Recommended Fix:** {fix}

I encountered an error generating a detailed explanation. Please try asking your question again, or ask about a different aspect of this issue."""
    
    def _provide_general_analysis_guidance(self, message: str, analysis_data: Dict) -> str:
        """Provide AI-powered general guidance when no specific issue is identified"""
        try:
            total_issues = analysis_data.get('total_issues', 0)
            severity_dist = analysis_data.get('severity_distribution', {})
            debt_types = analysis_data.get('debt_type_distribution', {})
            
            # Create summary of the analysis for AI context
            analysis_summary = f"""Analysis found {total_issues} total issues with this distribution:
Severity: {', '.join([f'{k}: {v}' for k, v in severity_dist.items() if v > 0])}
Debt Types: {', '.join([f'{k}: {v}' for k, v in debt_types.items() if v > 0])}"""
            
            system_prompt = """You are an expert Requirements Engineering consultant. Provide actionable guidance about requirements debt analysis results. Be conversational, helpful, and focus on practical next steps."""
            
            user_prompt = f"""I just completed a SEMP requirements debt analysis:

{analysis_summary}

The user asked: "{message}"

Please provide helpful guidance that:
1. Interprets what these results mean
2. Suggests practical next steps prioritized by impact
3. Explains why certain types of issues matter more
4. Offers specific advice for improving the SEMP document
5. Answers the user's question in this context

Be specific to these results, not generic. Make it actionable and educational."""
            
            # Generate AI response using Bedrock
            from src.infrastructure.bedrock_client import BedrockClient
            bedrock_client = BedrockClient()
            
            response = bedrock_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate analysis guidance: {e}")
            # Simple fallback
            total_issues = analysis_data.get('total_issues', 0)
            return f"Based on your analysis that found {total_issues} issues, I'd recommend focusing on the highest severity items first. Would you like me to explain a specific issue or concept in more detail?"
    
    def _provide_general_answer(self, message: str) -> str:
        """Provide general answers for common requirements engineering questions"""
        message_lower = message.lower()
        
        if 'requirements debt' in message_lower:
            return """Requirements debt refers to the accumulation of shortcuts, compromises, or deficiencies in requirements engineering that create future costs and risks. Common types include:

• **Technical Debt**: Poor requirements documentation or processes
• **Ambiguity Debt**: Vague or unclear requirements language
• **Completeness Debt**: Missing or incomplete requirements
• **Consistency Debt**: Conflicting or contradictory requirements
• **Traceability Debt**: Poor links between requirements and other artifacts

Addressing requirements debt early reduces project risk and long-term costs."""
        
        elif 'vague terminology' in message_lower or 'ambiguity' in message_lower:
            return """Vague terminology in requirements is problematic because:

• **Subjectivity**: Terms like "reliable," "fast," or "user-friendly" mean different things to different people
• **Untestable**: You can't verify requirements that aren't measurably defined
• **Implementation Risk**: Developers must make assumptions, leading to mismatched expectations
• **Compliance Issues**: Auditors cannot objectively assess compliance

**Solutions:**
• Replace subjective terms with quantitative metrics
• Define acceptance criteria with measurable thresholds
• Use standard terminology and units
• Include examples and boundary conditions"""
        
        elif 'semp' in message_lower or 'systems engineering' in message_lower:
            return """A Systems Engineering Management Plan (SEMP) defines how systems engineering activities will be conducted throughout a project lifecycle. Key components include:

• **Technical processes**: Requirements analysis, design, verification, validation
• **Management processes**: Planning, risk management, configuration control
• **Organizational structure**: Roles, responsibilities, and reporting relationships
• **Tools and methodologies**: Standards, procedures, and supporting tools
• **Lifecycle management**: Phase gates, reviews, and decision points

A well-written SEMP provides clear, measurable guidance for all stakeholders."""
        
        else:
            return """I specialize in requirements engineering and SEMP analysis. I can help with:

• **Requirements Debt Analysis**: Identifying and fixing quality issues
• **SEMP Document Review**: Analyzing management plans for completeness
• **Best Practices**: Guidance on systems engineering standards
• **Problem Resolution**: Specific advice on requirements challenges

What specific aspect of requirements engineering would you like to explore?"""
    
    def _handle_results_query(self, session_id: str, message: str, chat_history: List[Dict]) -> str:
        """Handle queries about analysis results"""
        try:
            # Get current analysis from session
            analysis_info = self.db_client.get_agent_info(f"session_analysis_{session_id}")
            
            if not analysis_info or "last_analysis" not in analysis_info:
                return "I don't have any recent analysis results to show. Please analyze a SEMP document first by providing the document content."
            
            # Check if this is a specific issue question rather than general results request
            if self._is_analysis_specific_question(message):
                return self._handle_analysis_specific_question(message, analysis_info, session_id)
            
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
