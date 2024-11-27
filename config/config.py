# config/config.py

import os
from typing import List

# DIRECTORIES - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
DATA_DIR: str = "data"    # Input data directory
OUTPUT_DIR: str = "out"   # Output directory

# PROMPTS FILE - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
PROMPTS_FILE: str = os.path.join("config", "prompts.json")

# INPUT-OUTPUT FILES - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
DATA_FILE: str = os.path.join(DATA_DIR, "data.json")
TEST_FILE: str = os.path.join(DATA_DIR, "test.json")
VERIFY_FILE: str = os.path.join(OUTPUT_DIR, "verify.json")
CONFIRMED_FILE: str = os.path.join(OUTPUT_DIR, "confirmed.json")

# MODELS - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
LOCAL_GENERATOR: bool = False
LOCAL_EMBEDDER: bool = False
LOCAL_FOLDER: str = "local-models"

MODEL_GENERATOR_NAME: str = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_EMBEDDER_NAME: str = "Alibaba-NLP/gte-multilingual-base"

# GENERATION TASKS - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
GENERATE: str = "generate few-shot"
GENERATE_WITH_DATASET: str = "generate variations"

# CONSENSUS TASKS - ADD, CHANGE, OR REMOVE AS DESIRED
CONSENSUS_SEMANTIC_COHERENCE: str = "semantic coherence"
CONSENSUS_INFORMATION_LOSS: str = "information loss"
CONSENSUS_REDUNDANT_COHERENCE: str = "redundant coherence"

# List of all consensus tasks - DON'T FORGET TO INCLUDE ALL THE CONSENSUS TASKS HERE
CONSENSUS_TASKS: List[str] = [
    CONSENSUS_SEMANTIC_COHERENCE,
    CONSENSUS_INFORMATION_LOSS,
    CONSENSUS_REDUNDANT_COHERENCE,
]

# PARAMETERS FOR GENERATOR WITHOUT REFERENCES - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED
NUM_RESPONSES_GENERATE: int = 5

# VERIFIER PARAMETERS - DO NOT REMOVE VARIABLES - CHANGE VALUE IF NEEDED

# Semantic distance verifier using embeddings
THRESHOLD: float = 0.90
UPPER_THRESHOLD: float = 0.99

# Consensus verifier
NUM_RESPONSES_CONSENSUS: int = 5
NUM_OK: int = 4
