# Installation Guide

## Prerequisites

- Python 3.9 or higher
- uv (modern Python package manager)
- Git

## Installing uv

If you don't have uv installed:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

## Quick Installation

### 1. Clone the Repository

```bash
git clone https://github.com/coairesearch/hierarchical-safety-governor.git
cd hierarchical-safety-governor
```

### 2. Set Up Environment with uv

```bash
# Create a new virtual environment
uv venv

# Activate the environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all dependencies using uv
uv pip install -r requirements.txt

# Install the project in development mode
uv pip install -e .
```

## Using uvx for Quick Commands

You can run tools without installation using uvx:

```bash
# Example: Run streamlit without installing globally
uvx streamlit run stream_ui.py
```

## Verifying Installation

Run a simple test to ensure everything is working:

```bash
python run_once.py --config configs/demo.yaml
```

You should see agents interacting in a price game environment.

## Optional: Install LLM Backends

### Ollama (Local LLMs)

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull llama2
   ```

### OpenAI API

Set your API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Managing Dependencies with uv

### Adding new dependencies

```bash
# Add a new package
uv pip install package-name

# Add to requirements.txt
uv pip freeze > requirements.txt
```

### Updating dependencies

```bash
# Update all packages
uv pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure your virtual environment is activated
   ```bash
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. **uv not found**: Add uv to your PATH or reinstall
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Permission errors**: uv handles permissions automatically, but ensure you have write access to the project directory

## Benefits of Using uv

- **Fast**: 10-100x faster than pip
- **Reliable**: Built-in dependency resolution
- **Modern**: Supports modern Python packaging standards
- **Convenient**: uvx allows running tools without installation

## Next Steps

- Read the [Quick Start Tutorial](./quickstart.md)
- Explore [example configurations](../configs/)
- Learn about [core concepts](./concepts.md)