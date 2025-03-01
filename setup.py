"""
Setup script for Home Assistant Agent package.
"""
from setuptools import setup, find_packages
import os

# Get package version from src/ha_agent/__init__.py
with open(os.path.join("src", "ha_agent", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip("'\"")
            break
    else:
        version = "0.1.0"

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Define package requirements
requirements = [
    "crewai>=0.28.0",
    "anthropic>=0.5.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "asyncio>=3.4.3",
    "pydantic>=2.0.0",
    "loguru>=0.7.0",
]

setup(
    name="ha_agent",
    version=version,
    author="Home Assistant Agent Team",
    author_email="your.email@example.com",
    description="Intelligent agent system for Home Assistant using Crew AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ha_agent",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ha-agent=ha_agent.cli:main",
        ],
    },
) 