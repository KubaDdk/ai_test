# Website Analysis Agent

An AI-powered tool that analyzes websites to create user flows, user stories, and test requirements.

## Project Structure

```
website-analysis-agent/
│
├── src/                        # Source code
│   ├── crawler/                # Website crawling module
│   ├── analyzer/               # Analysis module
│   ├── generator/              # Output generators
│   └── utils/                  # Utility functions
│
├── config/                     # Configuration files
│
├── data/                       # Data storage
│   ├── raw/                    # Raw crawled data
│   ├── processed/              # Processed analysis data
│   └── output/                 # Final outputs
│
├── tests/                      # Unit and integration tests
│
├── notebooks/                  # Jupyter notebooks
│
└── scripts/                    # Utility scripts
```

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `config/credentials.yaml` file with your API keys.

3. Run the analysis:
   ```
   python scripts/run_analysis.py --url https://example.com
   ```
