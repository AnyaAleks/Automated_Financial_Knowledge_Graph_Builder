from setuptools import setup, find_packages

setup(
    name="kg-finance-pipeline",
    version="1.0.0",
    description="Automated Knowledge Graph Construction from Financial News",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "neo4j>=5.0.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "nltk>=3.8.0",
        "tqdm>=4.66.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "kg-pipeline=run_pipeline:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)