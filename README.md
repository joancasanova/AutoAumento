# AutoAumento

AutoAumento is a project designed to generate and verify synthetic sentences using AI models. It leverages language models to produce variations of sentences and uses embedding models and consensus verification to ensure the quality and coherence of the generated data. This tool is particularly useful for data augmentation in natural language processing tasks.

## Table of Contents

- [AutoAumento](#autoaumento)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Running the CLI](#running-the-cli)
    - [Data Generation](#data-generation)
    - [Model Benchmarking](#model-benchmarking)
  - [Configuration](#configuration)
    - [Config File](#config-file)
    - [Prompt File](#prompt-file)
      - [Format](#format)
  - [Data Files](#data-files)
    - [Format](#format-1)
  - [System Architecture](#system-architecture)
    - [Overview](#overview)
    - [Components](#components)
      - [Data Generation Module](#data-generation-module)
      - [Verification Module](#verification-module)
      - [Consensus Verification Process](#consensus-verification-process)
      - [Embedding Similarity Verification](#embedding-similarity-verification)
      - [CLI Interface](#cli-interface)
    - [Workflow](#workflow)
  - [Consensus Method and Rationale](#consensus-method-and-rationale)
    - [Why Choose Consensus Verification?](#why-choose-consensus-verification)
      - [Human Assessment Inspiration](#human-assessment-inspiration)
      - [Consistency Testing](#consistency-testing)
      - [Implementation in AutoAumento](#implementation-in-autoaumento)
  - [Use Case: Generating and Verifying Spanish Sentences](#use-case-generating-and-verifying-spanish-sentences)
    - [Why Focus on Redundant Phrases, Pleonasms, and Circumlocutions?](#why-focus-on-redundant-phrases-pleonasms-and-circumlocutions)
    - [Prompts for Generation and Verification](#prompts-for-generation-and-verification)
      - [Example Prompts](#example-prompts)
    - [How They Are Used](#how-they-are-used)
  - [Benchmark Results](#benchmark-results)
    - [Semantic Similarity with Embeddings](#semantic-similarity-with-embeddings)
    - [Redundance Verification with LLaMa 3.1 8B Instruct](#redundance-verification-with-llama-31-8b-instruct)
    - [Information Loss Evaluation](#information-loss-evaluation)
    - [Semantic Coherence Evaluation](#semantic-coherence-evaluation)
  - [Examples](#examples)
    - [Generating Data Without References](#generating-data-without-references)
    - [Generating Data Using a Reference Dataset](#generating-data-using-a-reference-dataset)
    - [Benchmarking the Model](#benchmarking-the-model)
  - [Contributing](#contributing)

## Introduction

AutoAumento provides a streamlined way to generate synthetic datasets and verify their quality using state-of-the-art AI models. By automating the generation and verification process, it helps in creating high-quality datasets for training machine learning models, reducing redundancy, and ensuring semantic coherence.

## Features

- **Synthetic Data Generation**: Generate new sentences with or without references.
- **Consensus Verification**: Use an LLM instruct model to verify generated data through consensus tasks.
- **Embedding Sentence Similarity**: Evaluate semantic similarity between sentences using embedding models.
- **Customizable Configurations**: Easily configure models, thresholds, and tasks via config files.
- **Flexible Prompting**: Define custom prompts for data generation and verification.
- **Multi-Language Support**: Use any prompts and models optimized for multi-language processing.

## Installation

To set up AutoAumento, follow these steps:

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/joancasanova/AutoAumento.git
   cd AutoAumento
   ```

2. **Install Dependencies**:

   Ensure you have Python 3.7 or higher installed. Install the required packages using pip:

   ```bash
   pip install -r requirements.txt
   ```

   Alternatively, if you have the `pyproject.toml` file, you can install dependencies via:

   ```bash
   pip install .
   ```

3. **Set Up Prompts (`config/prompts.json`)**:

   Define the prompts used for consensus verification and data generation tasks.

   Details: [Prompt File](#prompt-file).

4. **Set Up Configuration File (`config/config.py`)**:

   - Choose the generation and embedding models.
   - Configure consensus tasks.

   Details: [Config File](#config-file)

5. **Set Up Local Models** (Optional):

   If you are using local models, place them in the directory specified by `LOCAL_FOLDER` in the config file, and set the `LOCAL_GENERATOR` or `LOCAL_EMBEDDER` values to `True` in the `config/config.py` file.

## Usage

AutoAumento provides a command-line interface (CLI) for interacting with the tool.

### Running the CLI

Start the CLI by running:

```bash
python -m autoaumento.cli
```

You will be presented with a menu to select different actions.

### Data Generation

1. **Normal Data Generation**:

   Generate synthetic data without any reference dataset.

2. **Data Generation Using Support JSON File**:

   Generate data based on an existing dataset. Ensure your data file is placed in the `data` directory.

### Model Benchmarking

1. **Evaluate Verification Model (Benchmark)**:

   Benchmark the verification models using different methods:

   - **Semantic Distance between Embeddings**:
     - Find the optimal similarity threshold.
     - Evaluate using a specific similarity threshold.

   - **Consensus Verification**:
     - Evaluate using consensus tasks defined in the prompt file.

## Configuration

AutoAumento uses configuration files to manage settings for models, tasks, and thresholds.

### Config File

The `config.py` file located in the `config` directory contains all the configuration settings.

Key configurations include:

- **Directories**:

  ```python
  DATA_DIR = "data"
  OUTPUT_DIR = "out"
  ```

- **Model Settings**:

  ```python
  LOCAL_GENERATOR = True
  LOCAL_EMBEDDER = False
  LOCAL_FOLDER = "local-models"

  MODEL_GENERATOR_NAME = "Llama-3.1-8B-Instruct"
  MODEL_EMBEDDER_NAME = "Alibaba-NLP/gte-multilingual-base"
  ```

- **Tasks**:

  ```python
  GENERATE = "generate few-shot"
  GENERATE_WITH_DATASET = "generate variations"
  ```

- **Consensus Tasks**:

  These variables can be altered, removed, or new ones added.

  ```python
  CONSENSUS_SEMANTIC_COHERENCE = "semantic coherence"
  CONSENSUS_INFORMATION_LOSS = "information loss"
  CONSENSUS_REDUNDANT_COHERENCE = "redundant coherence"

  CONSENSUS_TASKS = [
      CONSENSUS_SEMANTIC_COHERENCE,
      CONSENSUS_INFORMATION_LOSS,
      CONSENSUS_REDUNDANT_COHERENCE,
  ]
  ```

- **Verifier Parameters**:

  ```python
  THRESHOLD = 0.90
  UPPER_THRESHOLD = 0.99
  ```

### Prompt File

The prompt file, `prompts.json`, is stored in the `config` directory. It defines the prompts used for consensus verification and data generation tasks.

#### Format

The prompt file is a JSON object where each key is a task name, and the value is another object containing `context` and `instruction` entries.

Example:

```json
{
    "generate variations": {
        "context": "Your task is to review a dataset of sentences to apply easy reading guidelines: redundancies, repetitive structures, or circumlocutions should be avoided to make sentences easier to understand. Given a redundant sentence or one with a repetitive structure (original_input) and its correction (original_output), generate THREE variants of the sentence using the format shown in the examples...",
        "instruction": "Generate variations according to the above format:\noriginal_input: {input_text}\noriginal_output: {output_text}"
    },
    "redundant coherence": {
        "context": "Given two redundant sentences, with repetitive structures, pleonasms, or circumlocutions relative to each other in the format 'sentence1' -> 'sentence2', where sentence1 is a redundant version or circumlocution of sentence2:\nVerify and confirm that sentence1 is a redundancy of sentence2 by answering 'Yes' or 'No'.",
        "instruction": "'{input_text}' -> '{output_text}'"
    }
    // Add other tasks as needed
}
```

- **Task Names**: Must match **exactly** with the task names specified in the config file (e.g., `GENERATE`, `GENERATE_WITH_DATASET`, and tasks in `CONSENSUS_TASKS`).
- **Context**: Acts as the system prompt for the instruct model.
- **Instruction**: The user message for the instruct model. You can include `{input_text}` and `{output_text}` placeholders, which will be replaced by the actual input and output from the selected data files.

## Data Files

Data files should be placed in the `data` directory. They are used for both testing and generating data with references.

### Format

Data files are JSON files containing a list of data points. Each data point should have at least `input` and `output` keys. For benchmarking, a `label` key is also required.

Example:

```json
[
    {
        "input": "",
        "output": "The house is big and bright.",
        "label": "correct"
    },
    {
        "input": "",
        "output": "Eat the bright sun.",
        "label": "incorrect"
    },
    {
        "input": "",
        "output": "She runs quickly towards the goal.",
        "label": "correct"
    },
    {
        "input": "",
        "output": "The cat sings at night.",
        "label": "incorrect"
    }
]
```

- **input**: The input sentence (can be empty if not used).
- **output**: The output sentence.
- **label**: The label indicating correctness, used in benchmarking.

## System Architecture

### Overview

AutoAumento is designed with a modular architecture to facilitate flexibility and scalability. The system consists of several key components that work together to generate and verify synthetic data:

- **Data Generation Module**: Handles the creation of synthetic sentences using language models.
- **Verification Module**: Verifies the generated sentences using embedding similarity and consensus verification.
- **CLI Interface**: Provides a user-friendly command-line interface for interacting with the system.
- **Configuration and Prompts**: Manages customizable settings and prompts for different tasks.

### Components

#### Data Generation Module

- **Purpose**: Generates synthetic sentences based on provided prompts and, optionally, reference datasets.
- **Functionality**:
  - Uses language models (e.g., LLaMa 3.1 8B Instruct) to generate sentences.
  - Supports both unguided generation and generation based on reference data.
  - Utilizes prompts defined in the `prompts.json` file to guide the generation process.

#### Verification Module

- **Purpose**: Ensures the quality and coherence of generated sentences.
- **Sub-components**:
  - **Consensus Verification Process**: Uses an instruct model to verify sentences through repeated questioning.
  - **Embedding Similarity Verification**: Uses embedding models to calculate semantic similarity between sentences.

#### Consensus Verification Process

- **Mechanism**:
  - The verification model is prompted multiple times with the same question regarding a sentence or sentence pair.
  - Responses are aggregated to determine a consensus.
- **Workflow**:
  1. **Prompting**: The model is given a prompt from the `prompts.json` file, with placeholders replaced by actual data.
  2. **Multiple Iterations**: The model is queried multiple times (e.g., 5 times) to account for stochastic variability.
  3. **Aggregation**: Responses are collected, and a consensus is reached if a predefined threshold (e.g., 80% agreement) is met.
- **Benefits**:
  - Reduces the impact of random variations in model outputs.
  - Enhances reliability by confirming consistent responses.

#### Embedding Similarity Verification

- **Mechanism**:
  - Calculates the semantic similarity between pairs of sentences using embedding models (e.g., Alibaba-NLP/gte-multilingual-base).
- **Workflow**:
  1. **Embedding Generation**: Sentences are converted into vector representations (embeddings).
  2. **Similarity Calculation**: The cosine similarity between sentence embeddings is computed.
  3. **Thresholding**: The similarity score is compared against predefined thresholds to determine if sentences are semantically similar.
- **Benefits**:
  - Provides a quantitative measure of semantic similarity.
  - Effective in detecting redundancies and ensuring semantic coherence.

#### CLI Interface

- **Purpose**: Facilitates user interaction with the system through a command-line interface.
- **Features**:
  - Menu-driven options for data generation and model benchmarking.
  - Input prompts for selecting tasks, models, and configurations.
  - Output of results and saving of generated data.

### Workflow

1. **Configuration**:
   - Users set up the `config.py` file to specify models, tasks, and parameters.
   - Prompts are defined in the `prompts.json` file.

2. **Data Generation**:
   - The Data Generation Module uses the specified language model and prompts to generate synthetic sentences.
   - If reference data is provided, the generation is guided accordingly.

3. **Verification**:
   - The Verification Module evaluates the generated sentences.
   - **Consensus Verification**:
     - The instruct model is queried multiple times per sentence.
     - Responses are aggregated to reach a consensus.
   - **Embedding Similarity Verification**:
     - Embeddings are generated for sentence pairs.
     - Similarity scores are calculated and compared against thresholds.

4. **Output and Storage**:
   - Verified sentences are saved to the output directory.
   - Misclassified cases and benchmarking results are recorded.

5. **Benchmarking (Optional)**:
   - Users can evaluate the performance of verification methods using test datasets.
   - Optimal thresholds and parameters can be determined.

## Consensus Method and Rationale

### Why Choose Consensus Verification?

In the realm of natural language processing, especially when dealing with generative models, ensuring the reliability and consistency of model outputs is crucial. The consensus method was chosen for verification in AutoAumento to address the inherent variability and stochastic nature of language models.

#### Human Assessment Inspiration

According to research literature, such as Stajner et al. (2016), human assessments for evaluating text quality often involve:

- **Grammaticality (Fluency)**: Evaluators rate sentences based on grammatical correctness.
- **Meaning Preservation (Adequacy)**: Evaluators assess how well the text preserves meaning.

These evaluations are typically done using Likert scales, and the criteria are not strictly fixed, offering flexibility in assessment methods.

#### Consistency Testing

The consensus method in AutoAumento is inspired by the concept of **Consistency Testing**:

- **Purpose**: To verify if the model provides similar or identical responses when presented with the same input multiple times.
- **Application**:
  - **Basic Consistency**: Checking if the model generates the same response consistently.
  - **Controlled Variability**: Analyzing minor differences in responses that do not affect the core content.
- **Scenarios**:
  - **Deterministic Models**: Models with fixed parameters should produce identical outputs.
  - **Stochastic Models**: Models with randomness (e.g., temperature > 0) may vary, and consistency testing helps understand the range of variations.

By asking the model the same question multiple times and aggregating the responses, we can mitigate random errors and obtain a more reliable verification.

#### Implementation in AutoAumento

- **Multiple Responses**: For consensus tasks, the model is queried multiple times (e.g., 5 times).
- **Consensus Threshold**: A consensus is considered achieved if a certain percentage (e.g., 80%) of the responses agree.
- **Benefits**:
  - **Reduces Variability**: Minimizes the impact of random variations in model outputs.
  - **Enhances Reliability**: Provides a more stable and trustworthy verification mechanism.

## Use Case: Generating and Verifying Spanish Sentences

AutoAumento is particularly tailored to work with the Spanish language, providing specialized generation and verification prompts.

### Why Focus on Redundant Phrases, Pleonasms, and Circumlocutions?

Redundant phrases, pleonasms, and circumlocutions in Spanish are linguistic structures that are not solely dependent on grammar or syntax but are heavily influenced by context and semantics. This characteristic makes them ideal candidates for verifying synthetic data generation for several reasons:

1. **Extra-linguistic Dependency**:

   - These structures often require understanding beyond formal language rules.
   - They depend on the context in which they are used and the semantic content they convey.

2. **Semantic Nuance**:

   - Detecting redundancies and pleonasms involves recognizing subtle semantic differences.
   - This challenges AI models to go beyond surface-level analysis, ensuring deeper language understanding.

3. **Ideal for Verification**:

   - Since these structures are context-dependent, they provide a robust test for verifying the model's ability to generate semantically coherent and contextually appropriate sentences.
   - They help in assessing whether the model can maintain the essential meaning while simplifying or altering the sentence.

4. **Data Augmentation**:

   - By focusing on these complex structures, synthetic data generation can enrich datasets with nuanced examples.
   - This can improve model training, leading to better performance in tasks like text simplification and semantic analysis.

### Prompts for Generation and Verification

The prompts are defined in the `prompts.json` file and are crucial for guiding the model in both generation and verification tasks.

#### Example Prompts

- **Generate Variations**:

  ```json
  {
      "generate variations": {
          "context": "Tu tarea es revisar un conjunto de oraciones para aplicar pautas de lectura fácil: se deben evitar redundancias, estructuras repetitivas o circunloquios para hacer las frases más fáciles de entender. Dada una frase redundante o con una estructura repetitiva (original_input) y su corrección (original_output), genera TRES variantes de la frase utilizando el formato mostrado en los ejemplos: \n    original_input: Me dije a mí mismo\n    original_output: Me dije\n    input1: El anciano se dijo a sí mismo\n    output1: Se dijo el anciano\n    ...\n\nLas variantes generadas deben ser semánticamente correctas y coherentes.",
          "instruction": "Genera variaciones según el formato anterior:\noriginal_input: {input_text}\noriginal_output: {output_text}"
      }
  }
  ```

  This prompt instructs the model to generate three variants of a given redundant sentence and its correction, following a specific format.

- **Consensus Verification (e.g., Redundant Coherence)**:

  ```json
  {
      "redundant coherence": {
          "context": "Dadas dos frases, donde una es una versión redundante o circunloquio de la otra en el formato 'frase1' -> 'frase2':\nVerifica y confirma que frase1 es una redundancia de frase2 contestando con 'Sí' o 'No'.",
          "instruction": "'{input_text}' -> '{output_text}'"
      }
  }
  ```

  This prompt asks the model to verify if one sentence is a redundant version of another by answering 'Sí' (Yes) or 'No'.

### How They Are Used

- **Generation**:

  - The model uses the generation prompts to create new sentence pairs.
  - Placeholders like `{input_text}` and `{output_text}` are replaced with actual sentences from the data files.

- **Verification**:

  - The model is prompted multiple times with the same verification task to achieve consensus.
  - The consensus method ensures that the model's verification is reliable.

## Benchmark Results

AutoAumento has been benchmarked using different datasets for each verification method. Below is a summary of the results obtained for each method.

### Semantic Similarity with Embeddings

**Model**: Alibaba-NLP/gte-multilingual-base

**Methodology**:

- **Selection of Redundant Structures**: The focus on redundant phrases, pleonasms, and circumlocutions in Spanish is intentional because these structures require semantic understanding and context awareness. They are not strictly governed by grammar or syntax, making them ideal for testing the model's deeper language comprehension.
- **Dataset**:
  - 500 sentence pairs labeled into four categories:
    - **Redundant**: Correctly corrected redundant sentences.
    - **Non-redundant**: Sentences without redundancies.
    - **Redundant-bad**: Redundant sentences with incorrect corrections.
    - **Non-redundant-bad**: Non-redundant sentences modified incorrectly.
- **Optimal Threshold**:
  - Determined the optimal lower threshold for semantic similarity to be **0.91**.

**Results**:

- **Overall Accuracy**: High accuracy, especially in negative categories.
- **Precision per Category**:
  - **Redundant**: 79.23%
  - **Non-redundant**: 100.00%
  - **Redundant-bad**: 96.03%
  - **Non-redundant-bad**: 95.28%

**Conclusions**:

- The embedding model effectively detects redundancies.
- High accuracy in negative categories indicates low false positives.
- **Importance**: The ability to handle extra-linguistic structures like redundancies demonstrates the model's proficiency in semantic understanding, essential for verifying synthetic data generation.

### Redundance Verification with LLaMa 3.1 8B Instruct

**Model**: LLaMa 3.1 8B Instruct

**Methodology**:

- **Focus on Context and Semantics**: By targeting redundant phrases and circumlocutions, the model is tested on structures that require contextual and semantic analysis rather than mere grammatical checks.
- **Consensus Threshold**:
  - Used a consensus threshold of 80% (at least 4 out of 5 affirmative responses).
- **Evaluation**:
  - Assessed the model's ability to detect redundant coherence.

**Results**:

- **Overall Accuracy**: 87.65%
- **Precision per Category**:
  - **Redundant**: 94.62%
  - **Non-redundant**: 66.93%
  - **Redundant-bad**: 91.27%
  - **Non-redundant-bad**: 97.64%

**Conclusions**:

- Effective in detecting redundancies and corrections.
- Lower precision in the 'Non-redundant' category suggests some false positives.
- **Significance**: The model's capacity to handle extra-linguistic features validates its suitability for verifying the generation of synthetic data that involves complex semantic structures.

### Information Loss Evaluation

**Model**: LLaMa 3.1 8B Instruct

**Methodology**:

- Evaluated whether the simplified sentence maintains the essential message.
- Used the same consensus threshold of 80%.
- **Relevance**: Ensuring no loss of information when simplifying redundant structures is critical, as it tests the model's understanding of semantic content beyond surface-level text.

**Results**:

- **Overall Accuracy**: 90.98%
- **Precision per Category**:
  - **Correct**: 84.44%
  - **Incorrect**: 97.63%

**Conclusions**:

- High accuracy in detecting loss of information.
- Some tendency towards false negatives in the 'Correct' category.
- **Relevance**: Demonstrates the model's proficiency in semantic preservation, crucial for generating high-quality synthetic data.

### Semantic Coherence Evaluation

**Model**: LLaMa 3.1 8B Instruct

**Methodology**:

- Verified if a sentence is well-formed and semantically coherent.
- Used a dataset with sentences labeled as 'Correct' or 'Incorrect'.

**Results**:

- **Overall Accuracy**: 96.67%
- **Precision per Category**:
  - **Correct**: 100.00%
  - **Incorrect**: 93.33%

**Conclusions**:

- Highly effective in evaluating semantic coherence.
- Perfect precision in the 'Correct' category.
- **Relevance**: Validates the model's capability to assess extra-linguistic aspects, reinforcing its suitability for tasks involving context-dependent structures.

## Examples

### Generating Data Without References

1. Run the CLI:

   ```bash
   python -m main.cli
   ```

2. Choose **Data Generation** > **Normal Data Generation**.

3. The system will generate synthetic data and save it to the output directory.

### Generating Data Using a Reference Dataset

1. Place your reference data file in the `data` directory.

2. Run the CLI and choose **Data Generation** > **Data Generation Using Support JSON File**.

3. Enter the name of your data file when prompted.

### Benchmarking the Model

1. Place your test data file in the `data` directory.

2. Run the CLI and choose **Evaluate Verification Model (Benchmark)**.

3. Select the verification method and follow the prompts to configure thresholds and methods.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

---

Feel free to customize the prompts and configuration to suit your specific needs. The flexibility of AutoAumento allows for a wide range of applications in data augmentation and AI-driven text processing.
