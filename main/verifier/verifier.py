# autoaumento/verifier/verifier.py

from typing import List, Dict, Optional
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
            print(f"An error occurred during similarity verification: {e}")
            return False

    def verify_with_consensus(self, task: str, input_text: str = "", output_text: str = "") -> bool:
        """
        Verifies a specific task using consensus from the instructional language model's responses.

        Args:
            task (str): The consensus task to evaluate.
            input_text (str, optional): The input phrase.
            output_text (str, optional): The output phrase.

        Returns:
            bool: True if consensus is achieved, False otherwise.
        """
        print(f"Verifying input: {input_text} | output: {output_text}")

        try:
            # Generate responses using the instructional model
            responses = self.generator.generate(
                task,
                input_text,
                output_text,
                num_responses= NUM_RESPONSES_CONSENSUS
            )

            # Count how many responses contain "Yes" to determine consensus
            positive_responses = sum("Yes" in response for response in responses)
            consensus = positive_responses >= NUM_OK

            # Log the responses and consensus result
            print(f"-- {task.upper()}: {'Yes' if consensus else 'No'}")
            print(f"  - Positive responses: {positive_responses} out of {NUM_RESPONSES_CONSENSUS}")

            return consensus

        except Exception as e:
            print(f"An error occurred during consensus verification: {e}")
            return False

    def _analyze(self, input_text: str, output_text: str, methods: Optional[List[str]] = None) -> int:
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

        methods = methods or ["embedding", "consensus"]
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
            tasks_to_use = CONSENSUS_TASKS
            total_conditions += len(tasks_to_use)
            consensus_results = []
            for task in tasks_to_use:
                result = self.verify_with_consensus(task, input_text, output_text)
                consensus_results.append(result)

            conditions_met += sum(consensus_results)

        # Determine the verdict based on the conditions met
        if conditions_met == total_conditions:
            print(f"CONCLUSION -- CONFIRMED: {input_text} -> {output_text}\n")
            return 0  # Confirmed
        elif conditions_met >= total_conditions - 1:
            print(f"CONCLUSION -- TO VERIFY: {input_text} -> {output_text}\n")
            return 1  # Requires additional verification
        else:
            print("CONCLUSION -- DISCARDED\n")
            return -1  # Discarded

    @staticmethod
    def _parse_generated_responses(responses: List[str]) -> List[Dict[str, str]]:
        """
        Parses the model's responses to extract input-output pairs.

        Args:
            responses (List[str]): List of responses from the model.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing 'input' and 'output' keys.
        """
        variation_pairs = []
        temp_pair = {}

        for response in responses:
            for line in response.splitlines():
                line = line.strip()

                if "input" in line.lower() and ":" in line:
                    if 'input' in temp_pair and 'output' not in temp_pair:
                        # Add a pair with the existing input and empty output if we encounter another input
                        variation_pairs.append({'input': temp_pair['input'], 'output': ''})
                    # Start a new pair with the new input
                    temp_pair['input'] = line.split(":", 1)[1].strip()
                    temp_pair.pop('output', None)  # Clear any existing output in temp_pair

                elif "output" in line.lower() and ":" in line:
                    temp_pair['output'] = line.split(":", 1)[1].strip()

                if 'input' in temp_pair and 'output' in temp_pair:
                    # Add the complete pair to variation_pairs
                    variation_pairs.append(temp_pair.copy())
                    temp_pair = {}  # Reset temp_pair for the next pair

            # Handle case where there's a leftover input without an output
            if 'input' in temp_pair and 'output' not in temp_pair:
                variation_pairs.append({'input': temp_pair['input'], 'output': ''})

        return variation_pairs


    def verify(self, generations: List[str], verification_method: str) -> None:
        """
        Processes and verifies the generations.

        Args:
            generations (List[str]): List of generated responses to verify.
            verification_method (str): The verification method to use.
        """
        unique_inputs = set()
        valid_generations = []
        to_verify_data = []

        try:
            parsed_generations = self._parse_generated_responses(generations)

            for generation in parsed_generations:                    
                input_text = generation.get('input', "")
                output_text = generation.get('output', "")

                if 'input' not in generation:
                    print("The 'input' key is not present in the datapoint. An empty string ('') is assigned")
                if 'output' not in generation:
                    print("The 'output' key is not present in the datapoint. An empty string ('') is assigned")
     

                if input_text in unique_inputs:
                    print("Duplicate input discarded.")
                    continue
                unique_inputs.add(input_text)

                verdict = self._analyze(
                    input_text,
                    output_text,
                    methods=[verification_method] if verification_method != 'all' else None
                )
                
                # Prepare the entry dynamically based on non-empty values
                generation_entry = {}
                if input_text:
                    generation_entry["input"] = input_text
                if output_text:
                    generation_entry["output"] = output_text

                if verdict == 0:
                    valid_generations.append(generation_entry)
                    print("Added to confirmed list.")
                elif verdict == 1:
                    to_verify_data.append(generation_entry)
                    print("Added to verification list.")
        
            # Save results
            DataManager.register_data(
                valid_generations,
                to_verify_data,
                CONFIRMED_FILE,
                VERIFY_FILE
            )

        except Exception as e:
            print(f"An error occurred during verification: {e}")
