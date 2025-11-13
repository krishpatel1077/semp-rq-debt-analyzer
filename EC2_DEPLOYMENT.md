# EC2 Deployment Guide for Python 3.6.8

This guide provides instructions for deploying the SEMP Requirements Debt Analyzer on an EC2 instance with Python 3.6.8 and pip 9.0.3.

## Branch Information

**Branch:** `python36-ec2-compatible`

This branch has been specifically configured to work with:
- Python 3.6.8
- pip 9.0.3
- Legacy package versions compatible with Python 3.6

## Prerequisites

- EC2 instance with Python 3.6.8 installed
- pip version 9.0.3
- AWS credentials configured with appropriate permissions
- Access to required AWS services (S3, DynamoDB, Bedrock)

## Installation Steps

### 1. Clone the Repository

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ec2-user@your-ec2-instance

# Clone the repository
git clone <your-repo-url> semp-rq-debt-analyzer
cd semp-rq-debt-analyzer

# Checkout the Python 3.6 compatible branch
git checkout python36-ec2-compatible
```

### 2. Verify Python Version

```bash
python3 --version
# Should output: Python 3.6.8

pip3 --version
# Should output: pip 9.0.3 or similar
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify virtual environment is active
which python
# Should point to venv/bin/python
```

### 4. Upgrade pip (within virtual environment)

```bash
# Upgrade pip to a version that works with Python 3.6
pip install --upgrade "pip>=20.0,<21.0"
```

### 5. Install Dependencies

```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

**Note:** If you encounter installation issues, try installing packages individually:

```bash
# Core dependencies first
pip install python-dotenv==0.19.2
pip install pydantic==1.10.2
pip install click==7.1.2
pip install rich==10.16.2
pip install loguru==0.5.3

# AWS dependencies
pip install boto3==1.20.54
pip install botocore==1.23.54

# Data handling
pip install numpy==1.19.5
pip install pandas==1.1.5
pip install scikit-learn==0.24.2

# Document processing
pip install PyPDF2==1.26.0
pip install python-docx==0.8.11
pip install markdown==3.3.6

# Web framework
pip install flask==1.1.4
pip install flask-cors==3.0.10
pip install werkzeug==1.0.1

# RAG dependencies
pip install faiss-cpu==1.7.1.post2
```

### 6. Configure Environment Variables

```bash
# Copy the environment template
cp .env.template .env

# Edit the .env file with your AWS credentials and configuration
nano .env
```

Required environment variables:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# S3 Configuration
S3_KNOWLEDGE_BASE_BUCKET=your-bucket-name
S3_KNOWLEDGE_BASE_PREFIX=semp-docs/

# DynamoDB Configuration
DYNAMODB_CHAT_HISTORY_TABLE=your-chat-history-table
DYNAMODB_AGENT_INFO_TABLE=your-agent-info-table

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
BEDROCK_REGION=us-east-1

# Application Configuration
APP_NAME=SEMP Requirements Debt Analyzer
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 7. Initialize Knowledge Base (Optional)

```bash
# Initialize the knowledge base from S3 documents
python3 main.py init-knowledge-base
```

## Running the Web Server

### Development Mode

```bash
# Run the Flask development server
python3 web_app.py
```

The server will start on `http://0.0.0.0:5001`

### Production Mode with Gunicorn

For production deployment, use a WSGI server like Gunicorn:

```bash
# Install gunicorn (Python 3.6 compatible version)
pip install "gunicorn>=19.9.0,<20.0"

# Run with gunicorn
gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 300 web_app:app
```

### Running as a Background Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/semp-analyzer.service
```

Add the following content:

```ini
[Unit]
Description=SEMP Requirements Debt Analyzer Web Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/semp-rq-debt-analyzer
Environment="PATH=/home/ec2-user/semp-rq-debt-analyzer/venv/bin"
ExecStart=/home/ec2-user/semp-rq-debt-analyzer/venv/bin/gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 300 web_app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable semp-analyzer
sudo systemctl start semp-analyzer
sudo systemctl status semp-analyzer
```

## Nginx Reverse Proxy Configuration

To expose the application through Nginx:

```bash
# Install Nginx (if not already installed)
sudo yum install nginx -y  # For Amazon Linux
# or
sudo apt-get install nginx -y  # For Ubuntu

# Create Nginx configuration
sudo nano /etc/nginx/conf.d/semp-analyzer.conf
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or use your EC2 public IP

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for long-running analysis
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files
    location /static {
        alias /home/ec2-user/semp-rq-debt-analyzer/static;
    }
}
```

Enable and start Nginx:

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

## Security Considerations

### 1. EC2 Security Group

Ensure your EC2 security group allows inbound traffic:
- Port 80 (HTTP) from your desired IP ranges
- Port 443 (HTTPS) if using SSL
- Port 22 (SSH) for administration (restrict to your IP)

### 2. IAM Role

Instead of using AWS credentials in `.env`, use an IAM role for your EC2 instance:

```bash
# Remove AWS credentials from .env
# AWS will automatically use the instance role
```

Required IAM permissions:
- S3: `s3:GetObject`, `s3:ListBucket` for knowledge base bucket
- DynamoDB: `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query` for tables
- Bedrock: `bedrock:InvokeModel` for AI operations

### 3. SSL/TLS Configuration (Recommended for Production)

Use Let's Encrypt for free SSL certificates:

```bash
# Install certbot
sudo yum install certbot python2-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured by default
```

## Monitoring and Logs

### View Application Logs

```bash
# Systemd service logs
sudo journalctl -u semp-analyzer -f

# Application log files (if configured)
tail -f /var/log/semp-analyzer/app.log
```

### Nginx Logs

```bash
# Access logs
tail -f /var/log/nginx/access.log

# Error logs
tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Issue: pip install fails with SSL errors

```bash
# Try using --trusted-host flags
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Issue: numpy installation fails

```bash
# Install system dependencies first
sudo yum install gcc gcc-c++ python3-devel -y
# Then retry pip install
pip install numpy==1.19.5
```

### Issue: faiss-cpu installation fails

```bash
# Ensure you have the correct version
pip install faiss-cpu==1.7.1.post2

# If still failing, try installing from source or skip faiss
# The application will work but RAG features may be limited
```

### Issue: Module import errors

```bash
# Ensure PYTHONPATH includes src directory
export PYTHONPATH="${PYTHONPATH}:/home/ec2-user/semp-rq-debt-analyzer/src"

# Add to .bashrc for persistence
echo 'export PYTHONPATH="${PYTHONPATH}:/home/ec2-user/semp-rq-debt-analyzer/src"' >> ~/.bashrc
```

### Issue: Permission errors

```bash
# Ensure proper ownership
sudo chown -R ec2-user:ec2-user /home/ec2-user/semp-rq-debt-analyzer

# Fix permissions
chmod +x web_app.py
chmod +x main.py
```

## Testing the Deployment

### 1. Test CLI Interface

```bash
# Activate virtual environment
source venv/bin/activate

# Run help command
python3 main.py --help

# Test knowledge base initialization
python3 main.py init-knowledge-base
```

### 2. Test Web Interface

```bash
# Using curl
curl http://localhost:5001/

# Or access from browser
# http://your-ec2-public-ip/
```

### 3. Test Document Analysis

```bash
# Upload and analyze a test document
curl -X POST -F "document=@test_document.pdf" http://localhost:5001/upload
```

## Performance Optimization

### 1. Worker Configuration

Adjust Gunicorn workers based on your EC2 instance type:

```bash
# Formula: (2 × CPU_CORES) + 1
# For t2.micro (1 vCPU): 3 workers
# For t2.medium (2 vCPU): 5 workers

gunicorn --bind 0.0.0.0:5001 --workers 5 --timeout 300 web_app:app
```

### 2. Caching

The application uses a cache directory for processed documents:

```bash
# Ensure cache directory exists
mkdir -p /home/ec2-user/semp-rq-debt-analyzer/cache
chmod 755 /home/ec2-user/semp-rq-debt-analyzer/cache
```

### 3. Memory Considerations

For smaller EC2 instances (t2.micro/small), consider:
- Reducing max file upload size in `web_app.py`
- Limiting concurrent workers
- Using swap space if memory is tight

## Upgrading

To upgrade to a newer version:

```bash
# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin python36-ec2-compatible

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Restart the service
sudo systemctl restart semp-analyzer
```

## Differences from Main Branch

This Python 3.6 compatible branch includes:

1. **Downgraded dependencies:**
   - pydantic 1.10.2 (instead of 2.x)
   - pandas 1.1.5 (instead of 2.x)
   - numpy 1.19.5 (instead of 1.24.x)
   - flask 1.1.4 (instead of 2.3.x)
   - And many others...

2. **Code changes:**
   - Fixed `pydantic_settings` import (now uses `pydantic.BaseSettings`)
   - All dependencies pinned to specific versions for stability

3. **Additional requirements:**
   - `dataclasses` backport for Python 3.6
   - `typing-extensions` for enhanced type hints

## Support

For issues specific to this Python 3.6 deployment:
- Check the EC2 instance system logs
- Verify Python version compatibility
- Ensure all environment variables are set correctly
- Review AWS IAM permissions

## Next Steps

After successful deployment:
1. Set up automated backups for DynamoDB tables
2. Configure CloudWatch monitoring for the EC2 instance
3. Implement log rotation for application logs
4. Set up automated deployment pipeline (optional)
5. Configure auto-scaling (for production workloads)
