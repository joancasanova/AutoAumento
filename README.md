# AutoAumento

**AutoAumento** is a command-line application that orchestrates text generation, parsing, and verification workflows using a Large Language Model (LLM). The codebase demonstrates a well-structured Python project with a clear separation between domain models, application use cases, and infrastructure services. This README provides installation and usage instructions.

---

## Table of Contents
1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Installation](#installation)
4. [Usage](#usage)
   - [Generate Text](#generate-text)
   - [Parse Text](#parse-text)
   - [Verify](#verify)
   - [Pipeline & Benchmark](#pipeline--benchmark)
5. [Logging](#logging)
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

- **application/use_cases**: Contains the core logic for generating, parsing, and verifying text.
- **domain/model/entities**: Data classes representing different aspects (generation, parsing, verification).
- **domain/ports**: Abstract interfaces (ports) that define how external services (like LLMs) should behave.
- **domain/services**: Internal domain logic (placeholder replacement, verification strategies, etc.).
- **infrastructure/external**: Integrations with external systems, such as the Hugging Face LLM (`InstructModel`).
- **main.py**: Entry-point script with a CLI interface.

---

## Installation

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/your-org/autoaumento.git
   cd autoaumento
   ```

2. **Create a Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or on Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   If you prefer a PEP 517/518 approach, install via `pyproject.toml`:
   ```bash
   pip install build
   python -m build
   pip install dist/*.whl
   ```
---

## Usage

The CLI tool is invoked via:
```bash
python main.py <command> [options]
```
Use `--help` on any command to see its usage.

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
**Options**:
- `--gen-model-name`: Model name on Hugging Face Hub.
- `--system-prompt`: System-level instructions or context.
- `--user-prompt`: User query or prompt.
- `--num-sequences`: Number of outputs to generate.
- `--max-tokens`: Max tokens per sequence.
- `--temperature`: Sampling temperature.
- `--reference-data`: Optional JSON file for placeholder substitutions.

**Output**: A `GenerateTextResponse` object printed in the console.

---

### Parse Text
Parses text using a set of **rules** (regex or keyword). The parse result can be filtered (all, successful, or first_n).

**Example**:
```bash
python main.py parse \
  --text "User: Alice, Age: 30. User: Bob, Age: 25." \
  --rules "rules.json" \
  --output-filter "all"
```
**Options**:
- `--text`: The raw text to parse.
- `--rules`: JSON file containing parse rules.
- `--output-filter`: Filter type: `all`, `successful`, `first_n`.
- `--output-limit`: If `output-filter` is `first_n`, how many entries to return.

**Rules Example** (`rules.json`):
```json
[
  {"name": "User", "pattern": "User:\\s*", "mode": "keyword", "secondary_pattern": ", Age:"},
  {"name": "Age", "pattern": "Age:\\s*(\\d+)", "mode": "regex"}
]
```

**Output**: A JSON-serialized list of dictionaries representing parsed entries.

---

### Verify
Checks correctness or consistency by generating multiple responses from the model and comparing them to a set of **valid responses**.

**Example**:
```bash
python main.py verify \
  --verify-model-name "Qwen/Qwen2.5-3B-Instruct" \
  --methods "methods.json" \
  --required-confirmed 2 \
  --required-review 1 \
  --reference-data "verify_data.json"
```

**Options**:
- `--verify-model-name`: Model name for verification tasks.
- `--methods`: JSON file describing verification methods.
- `--required-confirmed`: Minimum passing methods for final status = “confirmed.”
- `--required-review`: Threshold for final status = “review.”
- `--reference-data`: JSON for placeholder substitution in prompts.

**Methods Example** (`methods.json`):
```json
[
  {
    "mode": "eliminatory",
    "name": "CheckKeyword",
    "system_prompt": "System verification prompt",
    "user_prompt": "Does the text contain 'Alice'?",
    "valid_responses": ["yes", "indeed"],
    "num_sequences": 3,
    "required_matches": 2
  }
]
```
**Output**: A JSON with final status (`confirmed`, `review`, or `discarded`), success rate, and method-specific details.

---

### Pipeline & Benchmark
Currently **placeholders** for further expansions.

---

## License
Distributed under the **MIT License**. See `LICENSE` for details.