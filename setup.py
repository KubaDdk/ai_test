from setuptools import setup, find_packages

setup(
    name="website_analysis_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.0.0",
        "webdriver-manager>=3.5.2",
        "openai>=0.27.0",
        "pyyaml>=6.0",
        "pandas>=1.3.0",
        "tqdm>=4.62.0",
    ],
    entry_points={
        "console_scripts": [
            "website-analyzer=scripts.run_analysis:main",
        ],
    },
)
