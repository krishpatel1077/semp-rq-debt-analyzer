# Deployment Guide

This guide provides instructions for deploying the SEMP Requirements Debt Analyzer to a government cloud environment.

## Quick Start

The project is designed for easy lift-and-shift deployment. All configuration is handled through environment variables, making it simple to move between environments.

### 1. Package the Project

```bash
# Create a deployment package
tar -czf semp-analyzer.tar.gz \
    --exclude=".env" \
    --exclude="cache/" \
    --exclude="__pycache__/" \
    --exclude="*.pyc" \
    .
```

### 2. Transfer to Target Environment

Transfer the `semp-analyzer.tar.gz` file to your target government cloud environment.

### 3. Extract and Setup

```bash
# Extract the package
tar -xzf semp-analyzer.tar.gz
cd semp-rq-debt-analyzer

# Copy environment template
cp .env.template .env

# Edit configuration with your environment-specific values
nano .env
```

### 4. Environment-Specific Configuration

Update `.env` with your government cloud credentials and resources:

```bash
# AWS GovCloud Configuration
AWS_ACCESS_KEY_ID=your_govcloud_access_key
AWS_SECRET_ACCESS_KEY=your_govcloud_secret_key
AWS_REGION=us-gov-west-1

# S3 Configuration (GovCloud bucket)
S3_KNOWLEDGE_BASE_BUCKET=your-govcloud-semp-bucket
S3_KNOWLEDGE_BASE_PREFIX=semp-docs/

# DynamoDB Configuration (GovCloud tables)
DYNAMODB_CHAT_HISTORY_TABLE=govcloud-semp-chat-history
DYNAMODB_AGENT_INFO_TABLE=govcloud-semp-agent-info

# AWS Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
BEDROCK_REGION=us-gov-west-1
```

### 5. Create AWS Resources

```bash
# Create S3 bucket
aws s3 mb s3://your-govcloud-semp-bucket --region us-gov-west-1

# Create DynamoDB tables
aws dynamodb create-table \
    --table-name govcloud-semp-chat-history \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-gov-west-1

aws dynamodb create-table \
    --table-name govcloud-semp-agent-info \
    --attribute-definitions AttributeName=agent_id,AttributeType=S \
    --key-schema AttributeName=agent_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-gov-west-1
```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Upload Knowledge Base Documents

Upload your SEMP documents and reference materials to the S3 bucket:

```bash
aws s3 cp local-documents/ s3://your-govcloud-semp-bucket/semp-docs/ --recursive
```

### 8. Initialize and Test

```bash
# Initialize the knowledge base
python main.py init-knowledge-base

# Check system status
python main.py status

# Run a test analysis
python main.py analyze sample-semp.txt --format summary
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `secret123...` |
| `AWS_REGION` | AWS region | `us-gov-west-1` |
| `S3_KNOWLEDGE_BASE_BUCKET` | S3 bucket for documents | `my-semp-docs` |
| `S3_KNOWLEDGE_BASE_PREFIX` | S3 prefix for organization | `semp-docs/` |
| `DYNAMODB_CHAT_HISTORY_TABLE` | DynamoDB table for chat history | `semp-chat-history` |
| `DYNAMODB_AGENT_INFO_TABLE` | DynamoDB table for agent data | `semp-agent-info` |
| `BEDROCK_MODEL_ID` | Bedrock model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `BEDROCK_EMBEDDING_MODEL_ID` | Bedrock embedding model | `amazon.titan-embed-text-v1` |
| `BEDROCK_REGION` | Bedrock region | `us-gov-west-1` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `prod` |

## Security Considerations

### For Government Cloud Deployment

1. **Credentials Management**: 
   - Use IAM roles instead of access keys when possible
   - Store secrets in AWS Secrets Manager or Parameter Store
   - Never commit credentials to version control

2. **Network Security**:
   - Deploy in private subnets with VPC endpoints for AWS services
   - Use security groups to restrict access
   - Consider using AWS PrivateLink for S3 and DynamoDB access

3. **Data Classification**:
   - Ensure all SEMP documents are properly classified
   - Use appropriate S3 bucket policies and encryption
   - Enable CloudTrail for audit logging

4. **Compliance**:
   - Follow FedRAMP guidelines for cloud deployments
   - Implement appropriate data retention policies
   - Ensure all components meet security requirements

### Environment-Specific Modifications

For different government cloud environments, you may need to modify:

```python
# config/settings.py - Add environment-specific endpoints
if settings.environment == "govcloud":
    # Use GovCloud specific Bedrock region
    bedrock_region = "us-gov-west-1"
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**:
   ```bash
   # Check AWS configuration
   aws sts get-caller-identity
   
   # Verify .env file is properly configured
   cat .env | grep AWS
   ```

2. **S3 Permissions Issues**:
   ```bash
   # Test S3 access
   aws s3 ls s3://your-bucket-name/
   
   # Check bucket policy and IAM permissions
   ```

3. **DynamoDB Access Issues**:
   ```bash
   # Test DynamoDB access
   aws dynamodb list-tables
   
   # Verify table exists and permissions are correct
   aws dynamodb describe-table --table-name semp-chat-history
   ```

4. **Bedrock API Issues**:
   ```bash
   # Test Bedrock connectivity
   python main.py status
   
   # Or test directly with AWS CLI
   aws bedrock list-foundation-models --region $BEDROCK_REGION
   ```

### Performance Tuning

For production deployments:

1. **Knowledge Base Optimization**:
   - Adjust chunk sizes based on document types
   - Optimize embedding batch sizes
   - Consider using vector database alternatives for large datasets

2. **AWS Resource Optimization**:
   - Use DynamoDB auto-scaling for variable workloads
   - Configure S3 lifecycle policies for document archival
   - Monitor CloudWatch metrics for resource utilization

3. **Application Scaling**:
   - Deploy behind a load balancer for multiple instances
   - Use AWS Lambda for serverless deployment option
   - Consider containerization with ECS or EKS

## Monitoring and Maintenance

### Health Checks

```bash
# Regular health checks
python main.py status

# Monitor knowledge base state
aws s3 ls s3://your-bucket/semp-docs/ --recursive | wc -l

# Check DynamoDB table status
aws dynamodb describe-table --table-name semp-chat-history \
  --query 'Table.TableStatus'
```

### Backup Strategy

```bash
# Backup DynamoDB tables
aws dynamodb create-backup --table-name semp-chat-history \
  --backup-name "semp-chat-$(date +%Y%m%d)"

aws dynamodb create-backup --table-name semp-agent-info \
  --backup-name "semp-agent-$(date +%Y%m%d)"

# S3 versioning should be enabled for document protection
aws s3api put-bucket-versioning \
  --bucket your-bucket-name \
  --versioning-configuration Status=Enabled
```

### Updates and Maintenance

```bash
# Update knowledge base after adding new documents
python main.py init-knowledge-base --force-refresh

# Clean up old chat sessions (if needed)
# Implement based on your retention policy
```

This deployment approach ensures the system can be easily moved between environments with minimal configuration changes, making it suitable for government cloud deployments where environment isolation and security are critical.