# models/embedder.py

"""
EmbeddingModel Module.

This module defines the EmbeddingModel class, which is used to calculate the semantic similarity between two texts
using pre-trained embedding models.
"""

import os

# Import DeviceManager and set CUDA_VISIBLE_DEVICES before importing torch
from main.models.device_manager import DeviceManager

device_manager = DeviceManager()
device_manager.set_cuda_visible_devices_mig()

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer
from config.config import *

class EmbeddingModel:
    """
    EmbeddingModel class to calculate semantic similarity between texts.

    Attributes:
        tokenizer (AutoTokenizer): The tokenizer associated with the embedding model.
        model (AutoModel): The pre-trained embedding model.
        device (torch.device): The device (CPU or GPU) where the model is loaded.
    """
    
    def __init__(self) -> None:
        """
        Initializes the embedding model and tokenizer.
        """
        print("Loading the embedding model for semantic proximity verification...")
        model_name = MODEL_EMBEDDER_NAME
        if LOCAL_EMBEDDER:
            model_path = os.path.join(os.getcwd(), LOCAL_FOLDER, model_name)
        else:
            model_path = model_name
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModel.from_pretrained(model_path, trust_remote_code=True)
        except Exception as e:
            error_msg = f"while loading the embedding model -> {e}"
            raise ValueError(error_msg)

        # Determine the device
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
            print(f"Number of GPUs: {torch.cuda.device_count()}")
            print(f"DEVICE: {self.device}")
        else:
            self.device = torch.device('cpu')
            print("CUDA is not available. Using CPU.")

        # Move the model to the device
        self.model.to(self.device)
        print(f"Embedding model loaded and moved to device: {self.device}")

    def get_embedding(self, text: str) -> torch.Tensor:
        """
        Calculates the embedding of a given text.

        Args:
            text (str): The text for which the embedding will be calculated.

        Returns:
            torch.Tensor: The normalized embedding vector for the text.

        Raises:
            Exception: If an error occurs during embedding calculation.
        """
        try:
            # Tokenize the text
            tokens = self.tokenizer(
                text,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors='pt'
            ).to(self.device)
            
            # Pass the tokens to the model to get the embeddings
            with torch.no_grad():
                output = self.model(**tokens)

            # Extract and normalize the embedding corresponding to the [CLS] token
            embedding = F.normalize(output.last_hidden_state[:, 0], p=2, dim=1)
            return embedding

        except Exception as e:
            error_msg = f"while calculating the embedding -> {e}"
            raise ValueError(error_msg)
