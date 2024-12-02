# autoaumento/verifier/verifier.py

from typing import List, Optional
from main.utils.data_manager import DataManager
from config.config import *

class Verifier:
    """
    Verifier class to check pairs of phrases using various methods.

    Attributes:
        generator (InstructModel): Instructional language model to generate responses.
        embedder (EmbeddingModel): Embedding model to calculate semantic similarity.
    """

    def __init__(self, generator=None, embedder=None):
        """
        Initializes an instance of the Verifier class.

        Args:
            generator (InstructModel, optional): The language model used for generation.
            embedder (EmbeddingModel, optional): The embedding model used for semantic similarity.
        """
        self.generator = generator
        self.embedder = embedder

    def is_similar(self, input_text: str, output_text: str, threshold: float = THRESHOLD) -> bool:
        """
        Verifies if two phrases are semantically similar but not identical.

        If the similarity is too high (close to 1), the phrases are considered identical and False is returned.

        Args:
            input_text (str): The input phrase.
            output_text (str): The output phrase.
            threshold (float, optional): The lower threshold for similarity. Defaults to THRESHOLD.

        Returns:
            bool: True if the phrases are similar but not identical, False otherwise.
        """
        try:
            # Obtain embeddings for both texts
            embedding_input = self.embedder.get_embedding(input_text)
            embedding_output = self.embedder.get_embedding(output_text)

            # Calculate cosine similarity
            similarity = (embedding_input @ embedding_output.T).item()

            # Determine if the phrases are too similar (identical)
            if similarity >= UPPER_THRESHOLD:
                print(f"-- SEMANTIC SIMILARITY: {similarity} - IDENTICAL PHRASES (NEGATIVE)")
                return False  # Phrases are identical; no redundancy to correct

            # Check if similarity is above the threshold but below the upper threshold
            if threshold < similarity < UPPER_THRESHOLD:
                print(f"-- SEMANTIC SIMILARITY: {similarity} - POSITIVE")
                return True  # Phrases are similar but not identical; redundancy to correct
            else:
                print(f"-- SEMANTIC SIMILARITY: {similarity} - NEGATIVE")
                return False  # Phrases are not sufficiently similar

        except Exception as e:
            error_msg = f"similarity verification -> {e}"
            
            raise ValueError(error_msg)

    def verify_with_consensus(self, input_text: str = "", output_text: str = "", consensus_method: str = "") -> bool:
        """
        Verifies a specific consensus method using consensus from the instructional language model's responses.

        Args:
            consensus_method (str): The consensus method to evaluate.
            input_text (str, optional): The input phrase.
            output_text (str, optional): The output phrase.

        Returns:
            bool: True if consensus is achieved, False otherwise.
        """
        print(f"Verifying input: {input_text} | output: {output_text}")

        try:
            # Generate responses using the instructional model
            responses = self.generator.generate(
                consensus_method,
                input_text,
                output_text,
                num_responses= NUM_RESPONSES_CONSENSUS
            )

            # Count how many responses contain the positive response to determine consensus
            num_positive_responses = 0
            for response in responses:
                if any(word in response for word in POSITIVE_RESPONSES):
                    num_positive_responses += 1
                    
            consensus = num_positive_responses >= NUM_OK

            # Log the responses and consensus result
            print(f"-- {consensus_method.upper()}: {'POSITIVE' if consensus else 'NEGATIVE'}")
            print(f"  - Positive responses: {num_positive_responses} out of {NUM_RESPONSES_CONSENSUS}")

            return consensus

        except Exception as e:
            error_msg = f"consensus verification -> {e}"
            
            raise ValueError(error_msg)
        
    def verify(self, generation: str, verification_method: str) -> int:
        """
        Analyzes if a pair of phrases (input and output) meets the specified conditions.

        Args:
            input_text (str): The input phrase.
            output_text (str): The output phrase.
            methods (List[str], optional): List of verification methods to use. Defaults to None.

        Returns:
            int:
                0 if the variation is confirmed,
                1 if it requires additional verification,
                -1 if it is discarded.
        """
        print(f"- VERIFYING GENERATION:\t{input_text} --> {output_text}")

        input_text = generation.get('input', "")
        output_text = generation.get('output', "")
        
        
        methods=[] 
        if verification_method == 'embedding' or verification_method == 'consensus':
            methods=[verification_method] 
        elif verification_method == 'all':
            methods=["embedding", "consensus"]
        elif verification_method == 'None':
            methods=["None"]

        conditions_met = 0
        total_conditions = 0

        # Verification using embeddings
        if "embedding" in methods and self.embedder:
            # Check if input or output is empty
            if not input_text or not output_text:
                print("WARNING: Either 'input_text' or 'output_text' is an empty string. Semantic similarity verification with embeddings will be skipped.\n")
            else:
                total_conditions += 1
                is_similar = self.is_similar(input_text, output_text)
                if not is_similar:
                    print("CONCLUSION -- DISCARDED: The input phrase is not semantically similar to the output.\n")
                    return -1
                else:
                    conditions_met += 1

        # Verification using consensus
        if "consensus" in methods and self.generator:
            methods_to_use = CONSENSUS_METHODS
            total_conditions += len(methods_to_use)
            consensus_results = []
            for method in methods_to_use:
                result = self.verify_with_consensus(input_text, output_text, method)
                consensus_results.append(result)

            conditions_met += sum(consensus_results)

        # Determine the verdict based on the conditions met
        if total_conditions == 0 or conditions_met == 0:
            print(f"CONCLUSION -- DISCARDED: No tests passed\n")
            return -1  # Discarded
        if conditions_met == total_conditions:
            print(f"CONCLUSION -- CONFIRMED: {input_text} -> {output_text}\n")
            return 0  # Confirmed
        elif conditions_met >= total_conditions - 1:
            print(f"CONCLUSION -- TO VERIFY: {input_text} -> {output_text}\n")
            return 1  # Requires additional verification
        else:
            print("CONCLUSION -- DISCARDED\n")
            return -1  # Discarded