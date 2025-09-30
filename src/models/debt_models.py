"""
Data models for Requirements Debt analysis
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DebtType(str, Enum):
    """Types of Requirements Debt"""
    AMBIGUITY = "Ambiguity"
    INCOMPLETENESS = "Incompleteness"
    INCONSISTENCY = "Inconsistency"
    TRACEABILITY_GAP = "Traceability Gap"
    VAGUE_TERMINOLOGY = "Vague Terminology"
    MISSING_CONSTRAINTS = "Missing Constraints"
    UNCLEAR_ACCEPTANCE_CRITERIA = "Unclear Acceptance Criteria"
    CONFLICTING_REQUIREMENTS = "Conflicting Requirements"
    OUTDATED_REQUIREMENTS = "Outdated Requirements"
    UNTESTABLE_REQUIREMENTS = "Untestable Requirements"


class SeverityLevel(str, Enum):
    """Severity levels for debt issues"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class DebtIssue(BaseModel):
    """Individual requirements debt issue"""
    id: str = Field(..., description="Unique identifier for the issue")
    location_in_text: str = Field(..., description="Exact location where the issue was found")
    debt_type: DebtType = Field(..., description="Type of requirements debt")
    problem_description: str = Field(..., description="Detailed description of the problem")
    recommended_fix: str = Field(..., description="Recommended solution or improvement")
    reference: str = Field(..., description="Citation from knowledge base supporting the evaluation")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="Severity of the issue")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for the detection")
    
    # Additional metadata
    section: Optional[str] = Field(None, description="Document section where issue was found")
    line_number: Optional[int] = Field(None, description="Line number in document")
    context: Optional[str] = Field(None, description="Surrounding context of the issue")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AnalysisResult(BaseModel):
    """Complete analysis result for a SEMP document"""
    document_name: str = Field(..., description="Name of the analyzed document")
    document_id: str = Field(..., description="Unique identifier for the document")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    
    # Analysis results
    issues: List[DebtIssue] = Field(default_factory=list, description="List of identified debt issues")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Analysis summary statistics")
    
    # Quality metrics
    total_issues: int = Field(default=0, description="Total number of issues found")
    severity_distribution: Dict[str, int] = Field(default_factory=dict, description="Count of issues by severity")
    debt_type_distribution: Dict[str, int] = Field(default_factory=dict, description="Count of issues by type")
    
    # Analysis metadata
    analyzer_version: str = Field(default="1.0.0", description="Version of the analyzer used")
    analysis_duration: Optional[float] = Field(None, description="Time taken for analysis in seconds")
    knowledge_base_version: Optional[str] = Field(None, description="Version of knowledge base used")


class ChatSession(BaseModel):
    """Chat session for interactive analysis"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(default="default", description="User identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    
    # Session state
    current_document: Optional[str] = Field(None, description="Currently analyzed document")
    last_analysis: Optional[AnalysisResult] = Field(None, description="Last analysis result")
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context and state")


class AnalysisRequest(BaseModel):
    """Request for document analysis"""
    document_content: str = Field(..., description="Document content to analyze")
    document_name: str = Field(..., description="Name of the document")
    analysis_type: str = Field(default="full", description="Type of analysis to perform")
    
    # Analysis options
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")
    severity_threshold: SeverityLevel = Field(default=SeverityLevel.LOW, description="Minimum severity to report")
    include_suggestions: bool = Field(default=True, description="Include improvement suggestions")
    
    # Context
    session_id: Optional[str] = Field(None, description="Associated chat session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional request metadata")


class KnowledgeBaseReference(BaseModel):
    """Reference to knowledge base content"""
    document_name: str = Field(..., description="Source document name")
    document_type: str = Field(..., description="Type of source document")
    chunk_index: int = Field(..., description="Chunk index in document")
    relevance_score: float = Field(..., description="Relevance score for the reference")
    text_excerpt: str = Field(..., description="Relevant text excerpt")
    
    def to_citation(self) -> str:
        """Convert to citation format"""
        return f"{self.document_name} (chunk {self.chunk_index}, relevance: {self.relevance_score:.2f})"


class ChainOfThoughtStep(BaseModel):
    """Individual step in chain-of-thought reasoning"""
    step_number: int = Field(..., description="Step number in the reasoning chain")
    description: str = Field(..., description="Description of this reasoning step")
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting this step")
    conclusion: str = Field(..., description="Conclusion drawn from this step")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this step")


class ChainOfThoughtAnalysis(BaseModel):
    """Chain-of-thought reasoning for a debt detection"""
    issue_id: str = Field(..., description="ID of the associated debt issue")
    reasoning_steps: List[ChainOfThoughtStep] = Field(..., description="Steps in the reasoning chain")
    final_conclusion: str = Field(..., description="Final conclusion from the chain")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in the analysis")
    knowledge_base_references: List[KnowledgeBaseReference] = Field(
        default_factory=list, 
        description="References from knowledge base used in reasoning"
    )