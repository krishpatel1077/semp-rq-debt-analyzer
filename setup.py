#!/usr/bin/env python3
"""
Setup script for SEMP Requirements Debt Analyzer
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() 
        for line in requirements_path.read_text().splitlines() 
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="semp-rq-debt-analyzer",
    version="1.0.0",
    description="A proof-of-concept tool for analyzing Requirements Debt in Systems Engineering Management Plans (SEMPs)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Requirements Engineering Team",
    author_email="team@example.com",
    url="https://github.com/example/semp-rq-debt-analyzer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "semp-analyzer=main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="requirements engineering, systems engineering, debt analysis, SEMP, quality assurance",
    project_urls={
        "Bug Reports": "https://github.com/example/semp-rq-debt-analyzer/issues",
        "Source": "https://github.com/example/semp-rq-debt-analyzer",
        "Documentation": "https://github.com/example/semp-rq-debt-analyzer/wiki",
    },
)