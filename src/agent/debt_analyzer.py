"""
Core Requirements Debt Detection Agent with chain-of-thought reasoning
"""
import uuid
import time
import json
from typing import List, Dict, Optional, Any
import openai
from loguru import logger

from config.settings import get_openai_config, settings
from src.models.debt_models import (
    DebtIssue, AnalysisResult, DebtType, SeverityLevel,
    ChainOfThoughtAnalysis, ChainOfThoughtStep, KnowledgeBaseReference,
    AnalysisRequest
)
from src.rag.knowledge_base import SEMPKnowledgeBase


class RequirementsDebtAnalyzer:
    """Expert assistant for detecting Requirements Debt in SEMPs"""
    
    def __init__(self, knowledge_base: SEMPKnowledgeBase):
        self.knowledge_base = knowledge_base
        
        # Initialize OpenAI
        openai_config = get_openai_config()
        openai.api_key = openai_config["api_key"]
        self.model = openai_config["model"]
        
        logger.info("Requirements Debt Analyzer initialized")
    
    def analyze_document(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze a SEMP document for requirements debt"""
        start_time = time.time()
        
        logger.info(f"Starting analysis of document: {request.document_name}")
        
        try:
            # Initialize result
            result = AnalysisResult(
                document_name=request.document_name,
                document_id=str(uuid.uuid4())
            )
            
            # Split document into analyzable sections
            sections = self._split_document_into_sections(request.document_content)
            
            # Analyze each section for debt issues
            all_issues = []
            for section_name, section_content in sections.items():
                section_issues = self._analyze_section(
                    section_content, section_name, request
                )
                all_issues.extend(section_issues)
            
            # Filter by severity threshold
            filtered_issues = [
                issue for issue in all_issues
                if self._severity_meets_threshold(issue.severity, request.severity_threshold)
            ]
            
            # Update result with findings
            result.issues = filtered_issues
            result.total_issues = len(filtered_issues)
            result.severity_distribution = self._calculate_severity_distribution(filtered_issues)
            result.debt_type_distribution = self._calculate_debt_type_distribution(filtered_issues)
            result.analysis_duration = time.time() - start_time
            
            # Generate summary
            result.summary = self._generate_analysis_summary(result)
            
            logger.info(f"Analysis completed. Found {result.total_issues} issues in {result.analysis_duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze document {request.document_name}: {e}")
            raise
    
    def _analyze_section(self, content: str, section_name: str, request: AnalysisRequest) -> List[DebtIssue]:
        """Analyze a document section for debt issues"""
        try:
            # Get relevant knowledge base context
            kb_context = self._get_relevant_context(content, section_name)
            
            # Generate chain-of-thought analysis
            cot_analysis = self._perform_chain_of_thought_analysis(
                content, section_name, kb_context
            )
            
            # Extract debt issues from analysis
            issues = self._extract_issues_from_analysis(
                cot_analysis, content, section_name, kb_context
            )
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to analyze section {section_name}: {e}")
            return []
    
    def _get_relevant_context(self, content: str, section_name: str) -> List[Dict]:
        """Get relevant context from knowledge base"""
        # Create search query based on content and section
        search_queries = [
            f"requirements debt {section_name}",
            f"SEMP best practices {section_name}",
            content[:200]  # First 200 chars for context
        ]
        
        all_context = []
        for query in search_queries:
            results = self.knowledge_base.search_knowledge_base(
                query, top_k=3, score_threshold=0.6
            )
            all_context.extend(results)
        
        # Remove duplicates and return top results
        unique_context = {}
        for ctx in all_context:
            key = f"{ctx['document']}_{ctx['chunk_index']}"
            if key not in unique_context or ctx['score'] > unique_context[key]['score']:
                unique_context[key] = ctx
        
        return list(unique_context.values())[:5]  # Top 5 most relevant
    
    def _perform_chain_of_thought_analysis(
        self, content: str, section_name: str, context: List[Dict]
    ) -> Dict[str, Any]:
        """Perform chain-of-thought analysis on the content"""
        
        # Prepare context text
        context_text = "\n".join([
            f"Reference: {ctx['document']} (score: {ctx['score']:.2f})\n{ctx['text']}\n"
            for ctx in context
        ])
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._create_analysis_prompt(content, section_name, context_text)
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse the structured response
            return self._parse_analysis_response(analysis_text)
            
        except Exception as e:
            logger.error(f"Failed to perform chain-of-thought analysis: {e}")
            return {}
    
    def _extract_issues_from_analysis(
        self, analysis: Dict[str, Any], content: str, section_name: str, context: List[Dict]
    ) -> List[DebtIssue]:
        """Extract debt issues from the chain-of-thought analysis"""
        issues = []
        
        try:
            analysis_results = analysis.get('issues', [])
            
            for issue_data in analysis_results:
                # Create knowledge base references
                references = []
                for ctx in context:
                    if ctx['score'] > 0.7:  # High relevance threshold
                        references.append(KnowledgeBaseReference(
                            document_name=ctx['document'],
                            document_type=ctx.get('document_type', 'unknown'),
                            chunk_index=ctx['chunk_index'],
                            relevance_score=ctx['score'],
                            text_excerpt=ctx['text'][:200] + "..."
                        ))
                
                # Create the debt issue
                issue = DebtIssue(
                    id=str(uuid.uuid4()),
                    location_in_text=issue_data.get('location', section_name),
                    debt_type=DebtType(issue_data.get('type', 'Ambiguity')),
                    problem_description=issue_data.get('problem', ''),
                    recommended_fix=issue_data.get('fix', ''),
                    reference=self._format_references(references),
                    severity=SeverityLevel(issue_data.get('severity', 'Medium')),
                    confidence=float(issue_data.get('confidence', 0.8)),
                    section=section_name,
                    context=issue_data.get('context', '')
                )
                
                issues.append(issue)
                
        except Exception as e:
            logger.error(f"Failed to extract issues from analysis: {e}")
        
        return issues
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the analyzer"""
        return """You are an expert assistant specializing in Requirements Engineering, Systems Engineering, and the detection of Requirements Debt (RQ Debt). Your primary task is to evaluate Systems Engineering Management Plans (SEMPs) for potential instances of RQ Debt.

When analyzing a SEMP section, you must:
1. Apply Chain-of-Thought reasoning to explain your findings
2. Identify specific debt types: ambiguity, incompleteness, inconsistency, traceability gaps, vague terminology, missing constraints, unclear acceptance criteria, conflicting requirements, outdated requirements, untestable requirements
3. Provide practical improvements aligned with Systems Engineering standards
4. Use the provided knowledge base references to support your evaluation
5. Assess severity (Low, Medium, High, Critical) and confidence (0.0-1.0)

Your analysis should be thorough yet precise, highlighting uncertainty where human review is necessary.

Respond in JSON format with this structure:
{
  "reasoning_steps": [
    {
      "step": 1,
      "description": "Step description",
      "evidence": ["evidence1", "evidence2"],
      "conclusion": "Step conclusion"
    }
  ],
  "issues": [
    {
      "location": "specific text or section",
      "type": "debt type",
      "problem": "detailed problem description",
      "fix": "recommended solution",
      "severity": "Low|Medium|High|Critical",
      "confidence": 0.8,
      "context": "surrounding context"
    }
  ],
  "overall_assessment": "Summary of findings"
}"""
    
    def _create_analysis_prompt(self, content: str, section_name: str, context_text: str) -> str:
        """Create the analysis prompt for a section"""
        return f"""Please analyze the following SEMP section for requirements debt:

SECTION: {section_name}

CONTENT TO ANALYZE:
{content[:3000]}  # Limit content length

KNOWLEDGE BASE CONTEXT:
{context_text}

Apply chain-of-thought reasoning to identify potential requirements debt issues. For each issue found, provide:
1. The exact location in the text
2. The specific debt type and problem
3. A recommended fix aligned with systems engineering best practices
4. Severity and confidence assessment
5. Reference to supporting knowledge base content

Focus on actionable findings that would help improve the SEMP's quality and reduce requirements debt."""
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured analysis response"""
        try:
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.warning("Could not extract JSON from analysis response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response JSON: {e}")
            return {}
    
    def _split_document_into_sections(self, content: str) -> Dict[str, str]:
        """Split document into analyzable sections"""
        sections = {}
        
        # Simple section splitting based on headers
        import re
        
        # Look for numbered sections, headers, etc.
        section_pattern = r'(\d+\..*?(?=\d+\.|$))'
        matches = re.split(section_pattern, content, flags=re.DOTALL)
        
        if len(matches) > 1:
            for i in range(1, len(matches), 2):
                if i + 1 < len(matches):
                    header = matches[i].strip()[:100]  # First 100 chars as header
                    section_content = matches[i + 1].strip()
                    if section_content:
                        sections[header] = section_content
        else:
            # If no clear sections, split into chunks
            chunk_size = 2000
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    sections[f"Section {i//chunk_size + 1}"] = chunk
        
        return sections or {"Main Content": content}
    
    def _format_references(self, references: List[KnowledgeBaseReference]) -> str:
        """Format knowledge base references into citation string"""
        if not references:
            return "General systems engineering best practices"
        
        citations = [ref.to_citation() for ref in references[:3]]  # Limit to top 3
        return "; ".join(citations)
    
    def _severity_meets_threshold(self, severity: SeverityLevel, threshold: SeverityLevel) -> bool:
        """Check if severity meets the minimum threshold"""
        severity_order = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4
        }
        return severity_order[severity] >= severity_order[threshold]
    
    def _calculate_severity_distribution(self, issues: List[DebtIssue]) -> Dict[str, int]:
        """Calculate distribution of issues by severity"""
        distribution = {level.value: 0 for level in SeverityLevel}
        for issue in issues:
            distribution[issue.severity.value] += 1
        return distribution
    
    def _calculate_debt_type_distribution(self, issues: List[DebtIssue]) -> Dict[str, int]:
        """Calculate distribution of issues by debt type"""
        distribution = {debt_type.value: 0 for debt_type in DebtType}
        for issue in issues:
            distribution[issue.debt_type.value] += 1
        return distribution
    
    def _generate_analysis_summary(self, result: AnalysisResult) -> Dict[str, Any]:
        """Generate a summary of the analysis results"""
        return {
            "total_issues": result.total_issues,
            "high_severity_issues": result.severity_distribution.get("High", 0) + result.severity_distribution.get("Critical", 0),
            "most_common_debt_type": max(result.debt_type_distribution.items(), key=lambda x: x[1])[0] if result.debt_type_distribution else "None",
            "average_confidence": sum(issue.confidence for issue in result.issues) / len(result.issues) if result.issues else 0.0,
            "sections_analyzed": len(set(issue.section for issue in result.issues if issue.section)),
            "recommendations_provided": len([issue for issue in result.issues if issue.recommended_fix])
        }