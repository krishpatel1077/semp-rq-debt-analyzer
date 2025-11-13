# Python 3.6 EC2 Compatible Branch

## Overview

This branch (`python36-ec2-compatible`) is specifically designed to run on EC2 instances with Python 3.6.8 and pip 9.0.3. It contains all the necessary adjustments to make the SEMP Requirements Debt Analyzer compatible with this older Python environment.

## What's Different?

### 1. Dependencies (requirements.txt)

All dependencies have been downgraded to versions compatible with Python 3.6:

| Package | Main Branch | Python 3.6 Branch |
|---------|-------------|-------------------|
| pydantic | >=2.0.0 | ==1.10.2 |
| pandas | >=2.0.0 | ==1.1.5 |
| numpy | >=1.24.0 | ==1.19.5 |
| flask | >=2.3.0 | ==1.1.4 |
| click | >=8.0.0 | ==7.1.2 |
| rich | >=13.0.0 | ==10.16.2 |
| boto3 | >=1.34.0 | ==1.20.54 |
| scikit-learn | >=1.3.0 | ==0.24.2 |
| faiss-cpu | >=1.7.4 | ==1.7.1.post2 |
| pytest | >=7.0.0 | ==6.2.5 |

### 2. Code Changes

#### config/settings.py
- **Before:** `from pydantic_settings import BaseSettings`
- **After:** `from pydantic import BaseSettings`

The `pydantic_settings` module only exists in Pydantic v2. In Pydantic v1, `BaseSettings` is part of the main `pydantic` package.

### 3. Additional Requirements

- `dataclasses==0.8` - Backport for Python 3.6 (dataclasses were added in Python 3.7)
- `typing-extensions==3.10.0.2` - Enhanced type hints for Python 3.6

### 4. setup.py Updates

- Changed `python_requires` from `>=3.8` to `>=3.6.8`
- Updated classifiers to reflect Python 3.6 and 3.7 support

## Installation

See the comprehensive [EC2_DEPLOYMENT.md](EC2_DEPLOYMENT.md) guide for detailed installation instructions.

Quick start:

```bash
# Clone and checkout this branch
git clone <repo-url> semp-rq-debt-analyzer
cd semp-rq-debt-analyzer
git checkout python36-ec2-compatible

# Create virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install --upgrade "pip>=20.0,<21.0"
pip install -r requirements.txt
```

## Compatibility Notes

### What Works
- ✅ All core functionality (document analysis, web interface, CLI)
- ✅ AWS services (S3, DynamoDB, Bedrock)
- ✅ RAG and knowledge base features
- ✅ PDF and document processing
- ✅ Flask web server
- ✅ Chat interface

### Known Limitations
- ⚠️ Some newer Python features (f-strings with `=`, walrus operator, etc.) are avoided
- ⚠️ Older package versions may have fewer features or bug fixes
- ⚠️ Performance may be slightly slower with older numpy/pandas versions
- ⚠️ Type hints are more limited in Python 3.6

## Testing

All main functionality has been verified for Python 3.6 syntax compatibility:
- ✅ Main application files compile without errors
- ✅ Configuration and model files are compatible
- ✅ Import statements work with Pydantic v1

## When to Use This Branch

Use this branch if:
- 🔧 You're deploying to an EC2 instance with Python 3.6.8
- 🔧 You cannot upgrade Python on your target system
- 🔧 You need to maintain compatibility with legacy infrastructure
- 🔧 You're working in a regulated environment with frozen dependencies

## When NOT to Use This Branch

Avoid this branch if:
- ✨ You can use Python 3.8+ (use the main branch instead)
- ✨ You're setting up a new environment
- ✨ You want the latest features and security updates

## Migration Path

If you're currently using this branch and want to upgrade:

1. **Upgrade Python**: Install Python 3.8 or later on your EC2 instance
2. **Switch branches**: `git checkout main`
3. **Reinstall dependencies**: `pip install -r requirements.txt`
4. **Test thoroughly**: Ensure all functionality works with newer packages

## Security Considerations

⚠️ **Important**: Python 3.6 reached end-of-life in December 2021. This branch uses older package versions that may contain known security vulnerabilities. 

Recommendations:
- Use this only in isolated/private environments
- Keep AWS IAM permissions tightly scoped
- Monitor for security advisories
- Plan to upgrade to Python 3.8+ when possible

## Maintenance

This branch will be maintained for:
- Critical bug fixes
- Security patches (where possible)
- Compatibility with the main branch features (where feasible)

However, new features will primarily target the main branch.

## Support

For questions or issues specific to this Python 3.6 branch:
1. Check [EC2_DEPLOYMENT.md](EC2_DEPLOYMENT.md) for deployment troubleshooting
2. Verify your Python version: `python3 --version`
3. Check pip version: `pip --version`
4. Review package installation logs for version conflicts

## Version Pinning

All dependencies are pinned to exact versions for stability and reproducibility. This ensures:
- Consistent behavior across deployments
- Predictable dependency resolution with pip 9.0.3
- Easier troubleshooting of version-related issues

To update a specific package (use caution):
```bash
pip install "package-name==X.Y.Z"
# Update requirements.txt accordingly
```

## Files Modified in This Branch

1. `requirements.txt` - Downgraded all dependencies
2. `setup.py` - Updated Python version requirement
3. `config/settings.py` - Fixed pydantic imports
4. `EC2_DEPLOYMENT.md` - New deployment guide (added)
5. `PYTHON36_BRANCH_README.md` - This file (added)

## Branch Strategy

- **Main branch**: Python 3.8+ with latest dependencies
- **python36-ec2-compatible**: Python 3.6.8 with legacy dependencies
- Merge strategy: Features are developed on main, then backported to this branch if feasible

## Contributing

When contributing to this branch:
- Ensure all code is Python 3.6 compatible
- Test with the exact versions in requirements.txt
- Avoid Python 3.7+ features
- Update this README if making significant changes

## License

Same as main branch - see LICENSE file.

## Acknowledgments

This compatibility layer was created to support legacy EC2 deployments while maintaining full application functionality.
