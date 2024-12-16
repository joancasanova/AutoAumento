# AutoAumento

**AutoAumento** is a command-line application that orchestrates text generation, parsing, and verification workflows using a Large Language Model (LLM). The codebase demonstrates a well-structured Python project with a clear separation between domain models, application use cases, and infrastructure services.

---

## Table of Contents
1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Development Setup](#development-setup)
   - [VSCode Configuration](#vscode-configuration)
   - [Python Environment](#python-environment)
4. [Installation](#installation)
5. [Usage](#usage)
   - [Generate Text](#generate-text)
   - [Parse Text](#parse-text)
   - [Verify](#verify)
   - [Pipeline & Benchmark](#pipeline--benchmark)
6. [Contributing](#contributing)
7. [License](#license)

---

## Features
- **Generate**: Invoke a Hugging Face language model to generate multiple text sequences using system and user prompts.
- **Parse**: Extract structured information from generated or raw text using custom parse rules (regex or keyword modes).
- **Verify**: Run verification methods (consensus checks) on text outputs to determine if they meet success criteria.
- **Placeholders**: Perform placeholder substitution in prompts with reference data.
- **Logging**: A simple logging system that logs errors, warnings, and debug messages to the console.

---

## Project Structure

```
.
├── app/
│   ├── application/
│   │   └── use_cases/
│   │       ├── generate_text_use_case.py
│   │       ├── parse_generated_output_use_case.py
│   │       └── verify_use_case.py
│   ├── domain/
│   │   ├── model/
│   │   │   └── entities/
│   │   │       ├── generation.py
│   │   │       ├── parsing.py
│   │   │       └── verification.py
│   │   ├── ports/
│   │   │   └── llm_port.py
│   │   └── services/
│   │       ├── parse_service.py
│   │       ├── placeholder_service.py
│   │       └── verifier_service.py
│   └── infrastructure/
│       └── external/
│           └── llm/
│               └── instruct_model.py
├── main.py
├── pyproject.toml
└── README.md
```

## Development Setup

### VSCode Configuration

1. **Install Required Extensions**:
   - Python (ms-python.python)
   - Pylance (ms-python.vscode-pylance)
   - Black Formatter (ms-python.black-formatter)
   - isort (ms-python.isort)
   - Python Type Hint (njpwerner.autodocstring)

2. **Workspace Settings**:
   Create a `.vscode/settings.json` file:
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
     "python.analysis.typeCheckingMode": "basic",
     "python.formatting.provider": "black",
     "editor.formatOnSave": true,
     "editor.codeActionsOnSave": {
       "source.organizeImports": true
     },
     "python.linting.enabled": true,
     "python.linting.pylintEnabled": true
   }
   ```

3. **Debug Configuration**:
   Create a `.vscode/launch.json` file:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Generate Text",
         "type": "python",
         "request": "launch",
         "program": "${workspaceFolder}/main.py",
         "args": [
           "generate",
           "--gen-model-name", "Qwen/Qwen2.5-1.5B-Instruct",
           "--system-prompt", "You are a helpful assistant.",
           "--user-prompt", "Explain quantum computing in simple terms.",
           "--num-sequences", "2"
         ],
         "console": "integratedTerminal"
       }
     ]
   }
   ```

### Python Environment

1. **Create Virtual Environment**:
   ```bash
   python -m venv .venv
   # On Linux/macOS:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

2. **Install Development Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-org/autoaumento.git
   cd autoaumento
   ```

2. **Setup with pyproject.toml**:
   ```toml
   [project]
   name = "autoaumento"
   version = "0.1.0"
   description = "Text generation and validation pipeline using LLMs"
   authors = [
       {name = "Your Name", email = "your.email@example.com"}
   ]
   dependencies = [
       "torch>=2.0.0",
       "transformers>=4.30.0",
       "pydantic>=2.0.0",
       "typer>=0.9.0"
   ]

   [project.optional-dependencies]
   dev = [
       "black>=23.0.0",
       "isort>=5.12.0",
       "pylint>=2.17.0",
       "pytest>=7.3.0",
       "pytest-cov>=4.1.0"
   ]

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [tool.black]
   line-length = 88

   [tool.isort]
   profile = "black"

   [tool.pylint]
   max-line-length = 88
   ```

3. **Install the Package**:
   ```bash
   pip install -e ".[dev]"
   ```

## Usage

The CLI tool is invoked via:
```bash
python main.py <command> [options]
```

### Generate Text
Generates multiple text sequences from a specified Hugging Face model.

**Example**:
```bash
python main.py generate \
  --gen-model-name "Qwen/Qwen2.5-1.5B-Instruct" \
  --system-prompt "You are a helpful assistant." \
  --user-prompt "Explain quantum computing in simple terms." \
  --num-sequences 2 \
  --max-tokens 50 \
  --temperature 0.9 \
  --reference-data "reference.json"
```

### Parse Text
Parses text using a set of rules (regex or keyword).

**Example**:
```bash
python main.py parse \
  --text "User: Alice, Age: 30. User: Bob, Age: 25." \
  --rules "rules.json" \
  --output-filter "all"
```

**Rules Example** (`rules.json`):
```json
[
  {"name": "User", "pattern": "User:\\s*", "mode": "keyword", "secondary_pattern": ", Age:"},
  {"name": "Age", "pattern": "Age:\\s*(\\d+)", "mode": "regex"}
]
```

### Verify
Checks correctness or consistency using multiple LLM responses.

**Example**:
```bash
python main.py verify \
  --verify-model-name "Qwen/Qwen2.5-3B-Instruct" \
  --methods "methods.json" \
  --required-confirmed 2 \
  --required-review 1 \
  --reference-data "verify_data.json"
```

### VSCode Development Tips

1. **Running Tests**:
   - Use the Testing sidebar (beaker icon)
   - Or run in terminal: `pytest tests/`

2. **Debugging**:
   - Set breakpoints by clicking left of line numbers
   - Use the Run and Debug sidebar (bug icon)
   - Use the predefined launch configurations

3. **Code Navigation**:
   - `F12` or `Ctrl+Click`: Go to definition
   - `Alt+F12`: Peek definition
   - `Shift+F12`: Find all references

4. **Refactoring**:
   - `F2`: Rename symbol
   - `Ctrl+.`: Quick fixes and refactorings

5. **Terminal Integration**:
   - `` Ctrl+` ``: Toggle integrated terminal
   - Terminal automatically activates virtual environment

## License
Distributed under the **MIT License**. See `LICENSE` for details.