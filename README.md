# SEMP Requirements Technical Debt Analyzer (SRDA)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

> An AI-powered tool for automated detection and analysis of Requirements Debt in Systems Engineering Management Plans (SEMPs)

SRDA leverages Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to automatically identify, classify, and provide remediation recommendations for requirements quality issues in systems engineering documentation. Built on AWS Bedrock with Claude 3 Sonnet, the system provides transparent chain-of-thought reasoning grounded in authoritative standards from INCOSE, NASA, and IEEE.

**This project was developed as part of a Masters Thesis in Systems Engineering, completed and published in 2025. The full thesis can be found at the following link: https://digital.wpi.edu/pdfviewer/mk61rn831**

A demo video can be found at: https://www.dropbox.com/scl/fi/yjp5fuetd70rz7cgom2mp/SRDA-DEMO-VIDEO.mov?rlkey=30kvvzfy1njqr30fyuyckho02&st=w577ixs8&dl=0

---

## Key Features

- **Automated Debt Detection**: Identifies 10 types of requirements debt including ambiguity, incompleteness, inconsistency, traceability gaps, and more
- **Chain-of-Thought Reasoning**: Provides transparent explanations for each finding with confidence scores
- **RAG-Powered Knowledge Base**: Searches curated systems engineering standards (INCOSE, NASA, IEEE) for authoritative guidance
- **Dual Interface**: Command-line tool for automation and web GUI for interactive analysis
- **Structured Output**: Results in tabular format with location, problem, fix, reference, and severity
- **Interactive Chat**: Conversational interface for iterative refinement and detailed explanations
- **Cloud-Native Architecture**: Built on AWS Bedrock, S3, and DynamoDB for scalability

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- AWS account with Bedrock access (Claude 3 Sonnet model enabled)
- AWS credentials configured

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/semp-rq-debt-analyzer.git
   cd semp-rq-debt-analyzer
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.template .env
   # Edit .env with your AWS credentials and configuration
   ```

4. **Set up AWS infrastructure**
   ```bash
   # Create S3 bucket for knowledge base
   aws s3 mb s3://your-semp-knowledge-base-bucket
   
   # Create DynamoDB tables
   python -c "from src.infrastructure.dynamodb_client import DynamoDBChatClient; DynamoDBChatClient().create_tables_if_not_exist()"
   ```

5. **Initialize knowledge base**
   ```bash
   # Upload your SEMP reference documents to S3, then:
   python main.py init-knowledge-base
   ```

For detailed setup instructions, see [INSTALLATION.md](./INSTALLATION.md).

---

## Usage

### Command Line Interface

**Analyze a SEMP document:**
```bash
python main.py analyze path/to/semp_document.pdf --severity Medium --output results.md
```

**Interactive chat mode:**
```bash
python main.py chat
```

**Search knowledge base:**
```bash
python main.py search --query "requirements traceability" --top-k 5
```

**Check system status:**
```bash
python main.py status
```

### Web Interface

Launch the web GUI for a modern, interactive experience:

```bash
./start_web_gui.sh
# Or manually:
# source venv/bin/activate
# python web_app.py
```

Then open your browser to `http://localhost:5000`

**Web Features:**
- Drag-and-drop document upload (PDF, DOCX, TXT, MD)
- Real-time analysis with progress tracking
- Clickable location links to view exact problematic text
- AI chat assistant for detailed explanations
- Export results as structured Markdown

For more examples, see [docs/EXAMPLES.md](./docs/EXAMPLES.md).

---

## Architecture

SRDA uses a four-tier layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│                  (CLI + Web Interface)                       │
├─────────────────────────────────────────────────────────────┤
│                      Agent Layer                             │
│  • Requirements Debt Analyzer (Chain-of-Thought)            │
│  • Session Manager (Chat & Context)                         │
├─────────────────────────────────────────────────────────────┤
│                      RAG Layer                               │
│  • Knowledge Base (FAISS Vector Search)                     │
│  • Document Processor (Multi-format parsing)                │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                        │
│  • AWS Bedrock (Claude 3 Sonnet + Titan Embeddings)        │
│  • S3 (Knowledge Base Storage)                              │
│  • DynamoDB (Session & Chat History)                        │
└─────────────────────────────────────────────────────────────┘
```

**Analysis Pipeline:**
1. Document decomposition into sections
2. RAG context retrieval from knowledge base
3. Chain-of-thought analysis via Claude 3 Sonnet
4. Issue extraction and validation
5. Structured output generation

For detailed architecture documentation, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## Example Output

| Location in Text | Debt Type / Problem | Recommended Fix | Reference | Severity |
|------------------|--------------------|-----------------|-----------|---------
| Section 3.1.2 "The system shall be reliable" | **Vague Terminology**: Undefined term "reliable" without measurable criteria | Define "reliable" with specific metrics (e.g., MTBF ≥ 1000 hours, availability ≥ 99.9%) | IEEE 830-1998 Requirements Specification | High |
| Section 4.2 Requirements table | **Traceability Gap**: No clear mapping to higher-level requirements | Implement traceability matrix linking each requirement to parent requirements and verification methods | INCOSE Systems Engineering Handbook | Medium |

---

## Documentation

- **[INSTALLATION.md](./INSTALLATION.md)** - Complete setup and configuration guide
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System architecture and design patterns
- **[docs/EXAMPLES.md](./docs/EXAMPLES.md)** - Usage examples and tutorials

---

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

