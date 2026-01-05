# Installation Guide

Complete guide for setting up the SEMP Requirements Technical Debt Analyzer (SRDA).

---

## Prerequisites

### Required Software

- **Python 3.8 or higher**
  - Check version: `python --version` or `python3 --version`
  - Download from: https://www.python.org/downloads/

- **AWS CLI**
  - Check installation: `aws --version`
  - Install: https://aws.amazon.com/cli/

- **Git** (for cloning the repository)
  - Check installation: `git --version`

### AWS Requirements

- **AWS Account** with the following:
  - AWS Bedrock access enabled in your region
  - Claude 3 Sonnet model access granted
  - Sufficient IAM permissions for:
    - S3 (bucket creation and object management)
    - DynamoDB (table creation and read/write)
    - Bedrock (model invocation)

### AWS Bedrock Model Access

Before proceeding, ensure you have access to:
- **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
- **Titan Embed Text v2** (`amazon.titan-embed-text-v2:0`)

To request model access:
1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Request access for Claude 3 Sonnet and Titan Embed Text v2
4. Wait for approval (typically instant for Titan, may take time for Claude)

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/semp-rq-debt-analyzer.git
cd semp-rq-debt-analyzer
```

### 2. Set Up Python Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

Your prompt should now show `(venv)` indicating the virtual environment is active.

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install all required packages including:
- `boto3` - AWS SDK
- `anthropic` - Anthropic SDK
- `faiss-cpu` - Vector similarity search
- `pydantic` - Data validation
- `click` - CLI framework
- `rich` - Terminal UI
- `flask` - Web framework
- And more...

### 4. Configure AWS Credentials

**Option A: AWS CLI Configuration (Recommended)**

```bash
aws configure
```

You'll be prompted for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Output format (use `json`)

**Option B: Environment Variables**

Create `.env` file from template:
```bash
cp .env.template .env
```

Edit `.env` with your credentials:
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

# AWS Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
BEDROCK_REGION=us-east-1

# Application Configuration
LOG_LEVEL=INFO
```

**Security Note:** Never commit `.env` files to version control. The `.gitignore` file is configured to exclude them.

---

## AWS Infrastructure Setup

### 1. Create S3 Bucket for Knowledge Base

Choose a unique bucket name and create it:

```bash
aws s3 mb s3://your-semp-knowledge-base-bucket --region us-east-1
```

Verify creation:
```bash
aws s3 ls | grep semp-knowledge-base
```

### 2. Create DynamoDB Tables

**Option A: Using Python Script**

```bash
python -c "from src.infrastructure.dynamodb_client import DynamoDBChatClient; DynamoDBChatClient().create_tables_if_not_exist()"
```

**Option B: Using AWS CLI**

Create chat history table:
```bash
aws dynamodb create-table \
    --table-name semp-chat-history \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

Create agent info table:
```bash
aws dynamodb create-table \
    --table-name semp-agent-info \
    --attribute-definitions AttributeName=agent_id,AttributeType=S \
    --key-schema AttributeName=agent_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

Verify tables:
```bash
aws dynamodb list-tables --region us-east-1
```

### 3. Upload Knowledge Base Documents to S3

Upload your systems engineering reference documents (INCOSE handbooks, NASA standards, IEEE standards, etc.) to the S3 bucket:

```bash
aws s3 cp ./your-documents/ s3://your-semp-knowledge-base-bucket/semp-docs/ --recursive
```

Supported document formats:
- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Markdown (`.md`)
- Plain text (`.txt`)
- JSON (`.json`)

### 4. Initialize the Knowledge Base

Process uploaded documents and create vector embeddings:

```bash
python main.py init-knowledge-base
```

For a complete refresh (reprocess all documents):
```bash
python main.py init-knowledge-base --force-refresh
```

This process:
1. Downloads documents from S3
2. Extracts text content
3. Chunks text into semantic segments
4. Generates embeddings using Titan
5. Creates FAISS vector index
6. Caches results locally

**Note:** Initial knowledge base creation can take 5-30 minutes depending on the number and size of documents.

---

## Verification

### 1. Check System Status

```bash
python main.py status
```

Expected output should show:
- ✅ AWS credentials configured
- ✅ Bedrock access available
- ✅ S3 bucket accessible
- ✅ DynamoDB tables exist
- ✅ Knowledge base initialized

### 2. Test Knowledge Base Search

```bash
python main.py search --query "requirements traceability" --top-k 3
```

You should see relevant results from your knowledge base documents.

### 3. Test CLI Analysis

Create a simple test SEMP file (`test_semp.txt`):
```
Section 1: Requirements
The system shall be user-friendly and reliable.
The system must process data quickly.
```

Analyze it:
```bash
python main.py analyze test_semp.txt --severity Low
```

You should see detected requirements debt issues.

### 4. Test Web Interface

```bash
./start_web_gui.sh
```

Open browser to `http://localhost:5000` and verify the interface loads.

---

## Troubleshooting

### Python Environment Issues

**Error:** `python: command not found`
- Try `python3` instead
- Ensure Python is installed and in PATH

**Error:** `No module named 'venv'`
- Install: `python3 -m pip install virtualenv`
- Or use system package manager: `apt-get install python3-venv` (Ubuntu/Debian)

### AWS Credentials Issues

**Error:** `Unable to locate credentials`
- Run `aws configure` to set up credentials
- Verify credentials file exists: `~/.aws/credentials`
- Check environment variables are set if using `.env`

**Error:** `An error occurred (AccessDeniedException) when calling the InvokeModel operation`
- Verify Bedrock model access is granted in AWS Console
- Check IAM permissions include `bedrock:InvokeModel`
- Ensure you're using the correct AWS region

### AWS Bedrock Issues

**Error:** `Model not found` or `ValidationException`
- Verify model ID in `.env` matches available models
- Check region supports Bedrock (e.g., `us-east-1`, `us-west-2`)
- Request model access in Bedrock console

### S3 Issues

**Error:** `Bucket does not exist`
- Verify bucket name in `.env` matches created bucket
- Check bucket region matches configured region
- Ensure IAM permissions include S3 read/write

**Error:** `Access Denied` when accessing S3
- Check IAM policy includes `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`
- Verify bucket policy doesn't block access

### DynamoDB Issues

**Error:** `Table does not exist`
- Run table creation commands again
- Verify table names in `.env` match created tables
- Check correct region

**Error:** `ProvisionedThroughputExceededException`
- This shouldn't happen with PAY_PER_REQUEST billing
- If using provisioned capacity, increase WCU/RCU

### Knowledge Base Issues

**Error:** `No documents found in S3`
- Verify documents were uploaded: `aws s3 ls s3://your-bucket/semp-docs/`
- Check S3 prefix in `.env` matches upload location

**Error:** `FAISS index creation failed`
- Ensure sufficient memory available (embeddings require RAM)
- Try with fewer/smaller documents initially
- Check disk space for cache directory

### Web Interface Issues

**Error:** `Address already in use`
- Another process is using port 5000
- Kill process: `lsof -ti:5000 | xargs kill -9` (macOS/Linux)
- Or change port in `web_app.py`

**Error:** `Session cookie too large`
- This is a warning, not an error
- Large analysis results cause this
- Results are still saved correctly

---

## Optional: Production Deployment

For deploying to production (EC2, cloud servers):

### 1. Use Production WSGI Server

Replace Flask development server with Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

### 2. Set Up Reverse Proxy (nginx)

Install nginx and configure:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Use IAM Roles (EC2)

Instead of credentials in `.env`, attach IAM role to EC2 instance with:
- Bedrock access
- S3 read/write
- DynamoDB read/write

### 4. Environment Variables

Set production environment:
```bash
export FLASK_ENV=production
```

### 5. Process Management

Use systemd or supervisor to manage the application as a service.

---

## Next Steps

After successful installation:

1. **Read the documentation:**
   - [docs/EXAMPLES.md](./docs/EXAMPLES.md) - Usage examples
   - [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System architecture
   - [docs/TECHNICAL_DOCUMENTATION.md](./docs/TECHNICAL_DOCUMENTATION.md) - Implementation details

2. **Customize the knowledge base:**
   - Add your organization's standards and templates
   - Include project-specific requirements guidelines

3. **Run analysis on real SEMPs:**
   - Start with smaller documents to understand output
   - Adjust severity thresholds based on your needs

4. **Explore the web interface:**
   - Upload documents and experiment with different settings
   - Use the chat assistant to understand findings

---

## Support

For installation issues:
1. Check this troubleshooting guide first
2. Review error messages carefully
3. Verify all prerequisites are met
4. Open an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version, AWS region)

---

## Uninstallation

To remove SRDA:

```bash
# Deactivate virtual environment
deactivate

# Delete virtual environment
rm -rf venv/

# Delete AWS resources (optional)
aws s3 rb s3://your-semp-knowledge-base-bucket --force
aws dynamodb delete-table --table-name semp-chat-history
aws dynamodb delete-table --table-name semp-agent-info

# Delete repository
cd ..
rm -rf semp-rq-debt-analyzer/
```

---

**Installation Complete!** You're ready to start analyzing SEMP documents.
