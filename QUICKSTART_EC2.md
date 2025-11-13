# Quick Start Guide - EC2 Python 3.6 Deployment

## TL;DR

This is the Python 3.6.8 compatible branch for deploying to legacy EC2 instances.

## One-Command Setup

```bash
# On your EC2 instance (Python 3.6.8, pip 9.0.3)
git clone <your-repo> && cd semp-rq-debt-analyzer && \
git checkout python36-ec2-compatible && \
python3 -m venv venv && source venv/bin/activate && \
pip install --upgrade "pip>=20.0,<21.0" && \
pip install -r requirements.txt
```

## Configure

```bash
cp .env.template .env
nano .env  # Add your AWS credentials
```

## Run

```bash
# Development
python3 web_app.py

# Production
pip install "gunicorn>=19.9.0,<20.0"
gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 300 web_app:app
```

## Access

Open `http://your-ec2-ip:5001` in your browser.

## Full Documentation

- **Detailed deployment**: See [EC2_DEPLOYMENT.md](EC2_DEPLOYMENT.md)
- **Branch details**: See [PYTHON36_BRANCH_README.md](PYTHON36_BRANCH_README.md)

## Key Differences from Main Branch

| Component | Main Branch | This Branch |
|-----------|-------------|-------------|
| Python | 3.8+ | 3.6.8 |
| pydantic | 2.x | 1.10.2 |
| pandas | 2.x | 1.1.5 |
| flask | 2.3+ | 1.1.4 |

## Troubleshooting

### Installation fails?
```bash
# Install system dependencies first
sudo yum install gcc gcc-c++ python3-devel -y
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Import errors?
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Need help?
Check [EC2_DEPLOYMENT.md](EC2_DEPLOYMENT.md) for comprehensive troubleshooting.
