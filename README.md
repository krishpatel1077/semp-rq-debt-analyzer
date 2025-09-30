# SEMP Requirements Debt Analyzer

A proof-of-concept tool for analyzing Requirements Debt in Systems Engineering Management Plans (SEMPs). This tool serves as a demonstration of an agent model specialized in Requirements Engineering, Systems Engineering, and the detection of Requirements Debt (RQ Debt).

## Features

- **Document Analysis**: Analyze SEMP documents for various types of requirements debt including ambiguity, incompleteness, inconsistency, traceability gaps, vague terminology, missing constraints, unclear acceptance criteria, conflicting requirements, outdated requirements, and untestable requirements.

- **Chain-of-Thought Reasoning**: Apply structured reasoning to explain debt detection findings and provide transparent analysis.

- **RAG-Powered Knowledge Base**: Search curated Systems Engineering documents and standards stored in S3 for relevant information and best practices.

- **Interactive Chat**: Maintain conversational context for iterative analysis and refinement through DynamoDB-backed chat sessions.

- **Structured Output**: Present findings in tabular format with specific columns: Location in Text, Debt Type/Problem, Recommended Fix, Reference, and Severity.

- **Severity Assessment**: Classify issues by severity (Low, Medium, High, Critical) and confidence levels (0.0-1.0).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend/CLI                           │
│                    (Rich Console)                           │
├─────────────────────────────────────────────────────────────┤
│                   Agent Layer                               │
│  ┌─────────────────────┐  ┌─────────────────────────────────┤
│  │ Requirements Debt   │  │    Session Manager              │
│  │     Analyzer        │  │   (Chat History)               │
│  └─────────────────────┘  └─────────────────────────────────┤
├─────────────────────────────────────────────────────────────┤
│                    RAG Layer                               │
│  ┌─────────────────────┐  ┌─────────────────────────────────┤
│  │ Knowledge Base      │  │  Document Processor             │
│  │ (vecclean + OpenAI) │  │  (PDF/DOCX/MD/TXT)             │
│  └─────────────────────┘  └─────────────────────────────────┤
├─────────────────────────────────────────────────────────────┤
│                Infrastructure Layer                         │
│  ┌─────────────────────┐  ┌─────────────────────────────────┤
│  │  S3 Knowledge Base  │  │   DynamoDB Chat Storage        │
│  │     (Documents)     │  │   (Sessions & History)         │
│  └─────────────────────┘  └─────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Environment Setup

Copy the environment template and configure your settings:

```bash
cp .env.template .env
```

Edit `.env` with your AWS credentials and configuration:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Configuration for Knowledge Base
S3_KNOWLEDGE_BASE_BUCKET=your-semp-knowledge-base-bucket
S3_KNOWLEDGE_BASE_PREFIX=semp-docs/

# DynamoDB Configuration
DYNAMODB_CHAT_HISTORY_TABLE=semp-chat-history
DYNAMODB_AGENT_INFO_TABLE=semp-agent-info

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### 2. AWS Resources Setup

Create the required AWS resources:

**S3 Bucket:**
```bash
aws s3 mb s3://your-semp-knowledge-base-bucket
```

**DynamoDB Tables:**
```bash
# Chat history table
aws dynamodb create-table \
    --table-name semp-chat-history \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

# Agent info table
aws dynamodb create-table \
    --table-name semp-agent-info \
    --attribute-definitions AttributeName=agent_id,AttributeType=S \
    --key-schema AttributeName=agent_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Knowledge Base

Upload your SEMP documents and reference materials to the S3 bucket, then initialize the knowledge base:

```bash
python main.py init-knowledge-base
```

## Usage

### Command Line Interface

**Check system status:**
```bash
python main.py status
```

**Analyze a SEMP document:**
```bash
python main.py analyze path/to/semp_document.txt --severity Medium --output results.md
```

**Search the knowledge base:**
```bash
python main.py search --query "requirements traceability" --top-k 5
```

**Interactive chat mode:**
```bash
python main.py chat
```

### Example Analysis Output

The tool produces structured output in the requested tabular format:

| Location in Text | Debt Type / Problem | Recommended Fix | Reference | Severity |
|------------------|--------------------|-----------------|-----------|---------
| Section 3.1.2 "The system shall be reliable" | Vague Terminology: Undefined term "reliable" without measurable criteria | Define "reliable" with specific metrics (e.g., MTBF ≥ 1000 hours, availability ≥ 99.9%) | IEEE 830-1998 Requirements Specification | High |
| Section 4.2 Requirements table | Traceability Gap: No clear mapping to higher-level requirements | Implement traceability matrix linking each requirement to parent requirements and verification methods | INCOSE Systems Engineering Handbook | Medium |

### Chat Interface Example

```
You: Analyze this SEMP section for requirements debt