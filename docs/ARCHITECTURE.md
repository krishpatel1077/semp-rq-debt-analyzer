# System Architecture

Comprehensive architectural documentation for the SEMP Requirements Technical Debt Analyzer (SRDA).

---

## Overview

SRDA employs a **layered architecture** pattern with four distinct tiers, separating concerns and enabling maintainability, testability, and scalability.

---

## Four-Tier Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│                   (CLI + Web Interface)                          │
│  • Command parsing and validation                                │
│  • Formatted output rendering (tables, JSON, markdown)           │
│  • Interactive chat interface                                    │
│  • Web GUI with drag-and-drop upload                            │
├──────────────────────────────────────────────────────────────────┤
│                       AGENT LAYER                                │
│  ┌─────────────────────────┐  ┌────────────────────────────┐    │
│  │ RequirementsDebtAnalyzer│  │  SEMPChatSessionManager    │    │
│  │ • Section decomposition │  │  • Request classification  │    │
│  │ • Chain-of-thought      │  │  • Context management      │    │
│  │   reasoning             │  │  • Multi-turn dialogue     │    │
│  │ • Issue extraction      │  │  • Results formatting      │    │
│  └─────────────────────────┘  └────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│                         RAG LAYER                                │
│  ┌─────────────────────────┐  ┌────────────────────────────┐    │
│  │  SEMPKnowledgeBase      │  │  DocumentProcessor         │    │
│  │  • Vector search (FAISS)│  │  • Multi-format parsing    │    │
│  │  • Embedding generation │  │  • Text chunking           │    │
│  │  • Context retrieval    │  │  • Coordinate tracking     │    │
│  └─────────────────────────┘  └────────────────────────────┘    │
│  ┌─────────────────────────┐                                     │
│  │  SimpleVectorStore      │                                     │
│  │  • FAISS IndexFlatIP    │                                     │
│  │  • Metadata management  │                                     │
│  │  • Persistence layer    │                                     │
│  └─────────────────────────┘                                     │
├──────────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                           │
│  ┌─────────────────────────┐  ┌────────────────────────────┐    │
│  │  BedrockClient          │  │  S3KnowledgeBaseClient     │    │
│  │  • Claude 3 Sonnet LLM  │  │  • Document storage        │    │
│  │  • Titan embeddings     │  │  • Version tracking        │    │
│  │  • Request/response     │  │  • Metadata caching        │    │
│  │    handling             │  └────────────────────────────┘    │
│  └─────────────────────────┘                                     │
│  ┌─────────────────────────┐                                     │
│  │  DynamoDBChatClient     │                                     │
│  │  • Chat history storage │                                     │
│  │  • Session management   │                                     │
│  │  • Analysis persistence │                                     │
│  └─────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer Details

### 1. Presentation Layer

**Responsibility:** User interaction and output formatting

**Components:**
- **CLI Interface** (`main.py`): Click-based command-line interface with Rich console formatting
- **Web Interface** (`web_app.py`): Flask-based web GUI with Bootstrap 5 UI

**Key Functions:**
- Command parsing and validation
- Output rendering (tables, JSON, markdown, HTML)
- Error handling and user feedback
- Progress tracking and status updates

### 2. Agent Layer

**Responsibility:** Core business logic and AI orchestration

**Components:**

#### RequirementsDebtAnalyzer (`src/agent/debt_analyzer.py`)
- **Purpose**: Core debt detection engine with chain-of-thought reasoning
- **Key Methods**:
  - `analyze_document()`: Main analysis pipeline
  - `_split_document_into_sections()`: Document decomposition
  - `_get_relevant_context()`: RAG context retrieval
  - `_perform_chain_of_thought_analysis()`: LLM-based analysis
  - `_extract_issues_from_analysis()`: Issue extraction and validation

#### SEMPChatSessionManager (`src/agent/session_manager.py`)
- **Purpose**: Conversational interface and context management
- **Key Methods**:
  - `create_session()`: Initialize new chat session
  - `process_user_message()`: Handle user queries
  - `_classify_request()`: Determine intent (analysis, search, chat)
  - `_generate_response()`: Orchestrate appropriate handler

### 3. RAG Layer

**Responsibility:** Knowledge retrieval and document processing

**Components:**

#### SEMPKnowledgeBase (`src/rag/knowledge_base.py`)
- **Purpose**: RAG implementation with vector similarity search
- **Key Methods**:
  - `initialize_knowledge_base()`: Process S3 documents
  - `search_knowledge_base()`: Vector similarity search
  - `_generate_embeddings()`: Titan embedding generation
  - `_chunk_documents()`: Semantic text segmentation

#### DocumentProcessor (`src/rag/document_processor.py`)
- **Purpose**: Multi-format document parsing with coordinate tracking
- **Supported Formats**: PDF, DOCX, Markdown, TXT, JSON
- **Key Features**:
  - Character-level position tracking
  - Line number mapping
  - Context extraction for highlighting

#### SimpleVectorStore (`src/rag/vector_store.py`)
- **Purpose**: FAISS-based vector storage and retrieval
- **Implementation**: IndexFlatIP for inner product similarity
- **Features**:
  - Persistence to disk
  - Metadata association
  - Efficient similarity search

### 4. Infrastructure Layer

**Responsibility:** Cloud service integration and low-level operations

**Components:**

#### BedrockClient (`src/infrastructure/bedrock_client.py`)
- **Models Used**:
  - Claude 3 Sonnet: Primary LLM for analysis
  - Titan Embed Text v2: Embedding generation
- **Configuration**:
  - Temperature: 0.3 (balanced creativity/precision)
  - Max tokens: 4096
  - Top-p: 0.9

#### S3KnowledgeBaseClient (`src/infrastructure/s3_client.py`)
- **Purpose**: Knowledge base document storage
- **Features**:
  - Document upload/download
  - Version tracking
  - Metadata caching
  - Prefix-based organization

#### DynamoDBChatClient (`src/infrastructure/dynamodb_client.py`)
- **Tables**:
  - `semp-chat-history`: Conversation storage
  - `semp-agent-info`: Agent metadata
- **Features**:
  - Session management
  - TTL-based cleanup
  - Query optimization

---

## Data Flow

### Analysis Pipeline

```
User Input (SEMP Document)
    ↓
[Document Intake & Validation]
    ↓
[Document Decomposition]
    ├─→ Section 1 ─→ [RAG Context Retrieval] ─→ [CoT Analysis] ─→ Issues
    ├─→ Section 2 ─→ [RAG Context Retrieval] ─→ [CoT Analysis] ─→ Issues
    └─→ Section N ─→ [RAG Context Retrieval] ─→ [CoT Analysis] ─→ Issues
    ↓
[Issue Aggregation & Filtering]
    ↓
[Result Compilation]
    ↓
Output (Table/JSON/Markdown)
```

### RAG Knowledge Retrieval Flow

```
User Query / Section Content
    ↓
[Generate Search Queries]
    ↓
[Embedding Generation (Titan)]
    ↓
[FAISS Vector Search]
    ↓
[Similarity Scoring & Ranking]
    ↓
[Top-K Selection]
    ↓
[Context Formatting]
    ↓
Return to Analyzer
```

---

## Design Patterns

### 1. Repository Pattern (RAG Layer)
- `SEMPKnowledgeBase` abstracts vector store operations
- Enables swapping FAISS with alternatives (Pinecone, Weaviate)
- Clean separation of data access logic

### 2. Strategy Pattern (Document Processing)
- `DocumentProcessor` employs different strategies per format
- PDF: pdfplumber extraction
- DOCX: python-docx parsing
- Markdown/TXT: direct text processing
- JSON: structured data parsing

### 3. Chain of Responsibility (Analysis Pipeline)
- Each stage processes and passes to next stage
- Document → Sections → Context → Analysis → Issues → Results
- Stages can be modified independently

### 4. Observer Pattern (Session Management)
- Chat messages trigger analysis workflows
- Session state updates propagate to DynamoDB
- Event-driven architecture

### 5. Factory Pattern (Client Creation)
- Infrastructure clients created via factory methods
- Configuration centralized in `settings.py`
- Easy mocking for testing

