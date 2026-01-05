# Usage Examples

Practical examples for using the SEMP Requirements Technical Debt Analyzer (SRDA).

---

## Table of Contents

1. [Command Line Interface (CLI) Examples](#command-line-interface-cli-examples)
2. [Web Interface Examples](#web-interface-examples)
3. [Advanced Use Cases](#advanced-use-cases)
4. [Integration Examples](#integration-examples)

---

## Command Line Interface (CLI) Examples

### Basic Document Analysis

**Analyze a PDF SEMP:**
```bash
python main.py analyze documents/my_semp.pdf
```

**Analyze with severity threshold:**
```bash
python main.py analyze documents/my_semp.pdf --severity High
```

**Save results to file:**
```bash
python main.py analyze documents/my_semp.pdf --output analysis_results.md
```

**Output in JSON format:**
```bash
python main.py analyze documents/my_semp.pdf --format json --output results.json
```

**Summary format (overview only):**
```bash
python main.py analyze documents/my_semp.pdf --format summary
```

**Exclude suggestions:**
```bash
python main.py analyze documents/my_semp.pdf --no-suggestions
```

### Knowledge Base Operations

**Initialize knowledge base:**
```bash
# First time setup or after adding new documents to S3
python main.py init-knowledge-base
```

**Force refresh (rebuild from scratch):**
```bash
python main.py init-knowledge-base --force-refresh
```

**Search knowledge base:**
```bash
python main.py search --query "requirements traceability" --top-k 5
```

**Search with relevance threshold:**
```bash
python main.py search --query "verification methods" --top-k 10 --threshold 0.7
```

### Interactive Chat Mode

**Start chat session:**
```bash
python main.py chat
```

**Chat with custom user ID:**
```bash
python main.py chat --user-id john_doe
```

**Example chat session:**
```
$ python main.py chat

Chat session created: a7b3c2d1...
Hello! I'm ready to help analyze SEMP documents for requirements debt.

You: Analyze section 3.2 of my SEMP for ambiguity issues
Assistant: I'll analyze section 3.2 for ambiguity. Please paste the section content...

You: "The system shall be reliable and user-friendly. Performance must be adequate."
Assistant: I've identified 3 ambiguity issues in this text:

1. **"reliable"** - Vague term without quantitative metrics
   Recommended fix: Define reliability with MTBF ≥ 1000 hours, availability ≥ 99.9%
   
2. **"user-friendly"** - Subjective term lacking measurable criteria
   Recommended fix: Specify task completion time, error rate, user satisfaction score
   
3. **"adequate"** - Undefined performance standard
   Recommended fix: Specify response time < 500ms, throughput > 1000 TPS

You: quit
```

### System Status

**Check configuration:**
```bash
python main.py status
```

Example output:
```
✅ AWS credentials configured
✅ Bedrock access available
✅ S3 bucket accessible (semp-knowledge-base)
✅ DynamoDB tables exist
✅ Knowledge base initialized (47 documents, 1,234 chunks)
```

---

## Web Interface Examples

### Starting the Web Interface

**Using the startup script:**
```bash
./start_web_gui.sh
```

**Manual start:**
```bash
source venv/bin/activate
python web_app.py
```

Access at `http://localhost:5000`

### Web Workflow

1. **Upload Document**
   - Drag and drop SEMP file onto upload area
   - Or click to browse and select file
   - Supported: PDF, DOCX, TXT, MD (up to 50MB)

2. **Configure Analysis**
   - Select severity threshold: Low, Medium, High, Critical
   - Toggle "Include Suggestions" checkbox

3. **Run Analysis**
   - Click "Analyze Document" button
   - Progress bar shows processing status
   - Typically completes in 10-60 seconds

4. **Review Results**
   - View summary statistics (total issues, high-severity count, analysis time)
   - Browse detected issues with severity badges
   - Click location links to see exact problematic text
   - Each issue shows: problem, fix, reference, severity, confidence

5. **Use AI Assistant**
   - Click "Ask AI About This" on any issue for detailed explanation
   - Or use chat panel for general questions

6. **Export Results**
   - Click "Export Results" button
   - Downloads structured Markdown file

---

## Advanced Use Cases

### Batch Processing Multiple Documents

Create a shell script to analyze multiple SEMPs:

```bash
#!/bin/bash
# analyze_all.sh

for file in semp_documents/*.pdf; do
    echo "Analyzing $file..."
    python main.py analyze "$file" \
        --severity Medium \
        --output "results/$(basename "$file" .pdf)_analysis.md"
done

echo "Batch analysis complete!"
```

Run with:
```bash
chmod +x analyze_all.sh
./analyze_all.sh
```

### Comparing Two SEMP Versions

```bash
# Analyze version 1
python main.py analyze semp_v1.pdf --format json --output semp_v1_results.json

# Analyze version 2
python main.py analyze semp_v2.pdf --format json --output semp_v2_results.json

# Compare results (using jq or custom script)
diff <(jq '.issues | sort_by(.location_in_text)' semp_v1_results.json) \
     <(jq '.issues | sort_by(.location_in_text)' semp_v2_results.json)
```

### Filtering Results by Debt Type

Using `jq` to filter JSON output:

```bash
# Analyze and get JSON
python main.py analyze my_semp.pdf --format json --output results.json

# Extract only "Vague Terminology" issues
jq '.issues[] | select(.debt_type == "Vague Terminology")' results.json

# Count issues by debt type
jq '.debt_type_distribution' results.json

# Get only high-severity issues
jq '.issues[] | select(.severity == "High")' results.json
```

### Knowledge Base Management

**Upload new standards to S3:**
```bash
# Upload entire directory
aws s3 cp standards/ s3://your-semp-knowledge-base-bucket/semp-docs/ --recursive

# Upload single document
aws s3 cp IEEE830-1998.pdf s3://your-semp-knowledge-base-bucket/semp-docs/

# Refresh knowledge base
python main.py init-knowledge-base --force-refresh
```

**View knowledge base contents:**
```bash
aws s3 ls s3://your-semp-knowledge-base-bucket/semp-docs/ --recursive
```

**Test knowledge base effectiveness:**
```bash
# Search for specific topics
python main.py search --query "requirements verification" --top-k 10

# Compare relevance scores
python main.py search --query "traceability matrix" --threshold 0.5
python main.py search --query "traceability matrix" --threshold 0.7
```

---

## Tips and Best Practices

### Analysis Quality

1. **Start with High Severity**
   - Use `--severity High` to focus on critical issues first
   - Review lower severity after addressing high-priority items

2. **Iterative Analysis**
   - Use chat mode for interactive refinement
   - Ask follow-up questions about specific findings

3. **Context Matters**
   - Larger document sections provide better context for LLM
   - Well-structured SEMPs (numbered sections) analyze better

### Knowledge Base Optimization

1. **Quality over Quantity**
   - Curate authoritative sources (INCOSE, NASA, IEEE)
   - Remove outdated or contradictory standards

2. **Regular Updates**
   - Refresh knowledge base when adding new standards
   - Use `--force-refresh` after significant KB changes

3. **Test Searches**
   - Verify KB effectiveness with search queries
   - Adjust document chunking if results are poor

### Performance

1. **Document Size**
   - Large documents (100+ pages) may take several minutes
   - Consider splitting very large SEMPs into sections

2. **Batch Processing**
   - Use shell scripts for multiple documents
   - Avoid parallel analysis (Bedrock quotas)

3. **Caching**
   - Knowledge base is cached after first initialization
   - Delete cache files to force rebuild

---

## Troubleshooting Examples

**Issue: Analysis returns no results**
```bash
# Check knowledge base
python main.py search --query "requirements" --top-k 1

# If empty, reinitialize
python main.py init-knowledge-base --force-refresh
```

**Issue: Low confidence scores**
```bash
# Verify knowledge base quality
python main.py search --query "your domain terms" --threshold 0.5

# Add more domain-specific documents to S3 and refresh
```

**Issue: Slow analysis**
```bash
# Check AWS Bedrock quotas
aws service-quotas list-service-quotas \
    --service-code bedrock \
    --query 'Quotas[?QuotaName==`Invoke Model requests per minute`]'

# Consider implementing rate limiting or request batching
```

---

For more details on architecture and implementation, see:
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [../INSTALLATION.md](../INSTALLATION.md) - Setup guide
