# main.py

import argparse
import warnings
import os
from typing import Optional, Tuple, Dict

from main.utils.data_manager import DataManager
from main.models.generator import InstructModel
from main.models.embedder import EmbeddingModel
from main.verifier.verifier import Verifier
from main.benchmark.benchmark_evaluator import BenchmarkEvaluator
from config.config import *


# Ignore warnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress INFO and WARNING messages from TensorFlow
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable OneDNN optimizations


def _initialize_models(benchmark: bool, verification_method: str) -> Tuple[Optional[InstructModel], Optional[EmbeddingModel]]:
    """
    Initializes the required models based on the selected verification method.

    Args:
        benchmark (bool): Indicates if benchmarking is being performed.
        verification_method (str): The method of verification to use ('all', 'embedding', 'consensus').

    Returns:
        Tuple[Optional[InstructModel], Optional[EmbeddingModel]]: The generator and embedder models.
    """
    generator = None
    embedder = None

    try:
        if verification_method in ['all', 'consensus'] or not benchmark:
            generator = InstructModel()
        if verification_method in ['all', 'embedding']:
            embedder = EmbeddingModel()
    except Exception as e:
        print(f"An error occurred while initializing models: {e}")
        raise

    return generator, embedder

def _process_generation(
    generation,
    generator,
    verifier,
    verification_method,
    valid_generations,
    to_verify_data,
    processed_inputs  # Conjunto con entradas procesadas
) -> None:
    """
    Processes a single generation by parsing, verifying, and categorizing it.

    Args:
        generation (str): The raw generation output from the generator model.
        generator (InstructModel): The generator model instance.
        verifier (Verifier): The verifier instance.
        verification_method (str): The verification method to use.
        valid_generations (list): List to store valid generations.
        to_verify_data (list): List to store generations that need further verification.
        processed_inputs (set): Set of already processed inputs to avoid duplicates.
    """
    try:
        parsed_generation = generator.parse_generated_response(generation)

        # Verificar que `parsed_generation` sea un diccionario
        if not isinstance(parsed_generation, dict):
            print(f"Invalid generation format: {parsed_generation}")
            return

        # Obtener input_text con un valor predeterminado
        input_text = parsed_generation.get('input', "")
        print(f"input_text: {input_text}")

        # Manejo de cadenas vacías
        if input_text == "":
            print("Empty input detected and discarded.")
            return

        # Verificar duplicados exactos
        if input_text in processed_inputs:
            print(f"Exact duplicate detected and discarded: {input_text}")
            return

        # Añadir la entrada al conjunto de procesados
        processed_inputs.add(input_text)

        # Procesar generaciones
        verdict = verifier.verify(parsed_generation, verification_method)
        if verdict == 0:
            valid_generations.append(parsed_generation)
            print("Added to confirmed list.")
        elif verdict == 1:
            to_verify_data.append(parsed_generation)
            print("Added to verification list.")
    except Exception as e:
        print(f"Error while processing generation: {e}")

def main(
    generate_from_dataset: Optional[bool] = None,
    benchmark: Optional[bool] = None,
    data_file: Optional[str] = None,
    verification_method: str = "all",
    positive_label: Optional[str] = None,
    threshold: Optional[float] = None,
    find_optimal_threshold: Optional[bool] = None,
    threshold_range: Optional[Tuple[float, float]] = None,
    consensus_method: Optional[str] = None,
) -> None:
    """
    Main entry point of the program.

    Args:
        generate_from_dataset (bool, optional): If True, generates data using a reference JSON dataset.
        benchmark (bool, optional): If True, performs model benchmarking.
        data_file (str, optional): Path to the JSON data file.
        verification_method (str, optional): Verification method to use ('all', 'embedding', 'consensus').
        positive_label (str, optional): Label to consider as positive in benchmarking.
        threshold (float, optional): Specific threshold for evaluation.
        find_optimal_threshold (bool, optional): If True, searches for the optimal threshold.
        threshold_range (Tuple[float, float], optional): Range of thresholds to search for the optimal (min, max).
        consensus_method (str, optional): Consensus method to evaluate.
    """
    # Use argparse if arguments are not passed directly
    if all(arg is None for arg in [generate_from_dataset, benchmark, data_file, positive_label]):
        parser = argparse.ArgumentParser(description="AutoAumento: Generation and Verification of Synthetic Data")
        
        # Main arguments
        parser.add_argument("--generate_from_dataset", action="store_true", help="Generate data using a reference JSON file")
        parser.add_argument("--benchmark", action="store_true", help="Execute model evaluation benchmark")
        parser.add_argument("--data_file", type=str, default=DATA_FILE, help="JSON data file")
        parser.add_argument("--verification_method", choices=["all", "embedding", "consensus", "None"], default="all", help="Verification method to use")
        
        # Benchmark specific arguments
        parser.add_argument("--positive_label", type=str, help="Label to consider as positive")
        parser.add_argument("--threshold", type=float, help="Specific threshold for evaluation")
        parser.add_argument("--find_optimal_threshold", action="store_true", help="Search for the optimal threshold")
        parser.add_argument("--threshold_range", type=float, nargs=2, metavar=("MIN", "MAX"), help="Range of thresholds to search for the optimal")
        parser.add_argument("--consensus_method", choices=CONSENSUS_METHODS, help="Consensus methods to evaluate")
    
        args = parser.parse_args()

        generate_from_dataset = args.generate_from_dataset
        benchmark = args.benchmark
        data_file = args.data_file
        verification_method = args.verification_method
        positive_label = args.positive_label
        threshold = args.threshold
        find_optimal_threshold = args.find_optimal_threshold
        threshold_range = args.threshold_range
        consensus_method = args.consensus_method
        
    # Ensure directories exist
    for directory in [DATA_DIR, OUTPUT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory '{directory}' created.")
            
    # Initialize models
    try:
        generator, embedder = _initialize_models(benchmark, verification_method)
    except Exception as e:
        print("Failed to initialize models.")
        return
    
    verifier = Verifier(generator, embedder)
    
    # Benchmarking
    if benchmark:
        try:
            # Load testing dataset
            if not data_file:
                print("Using default testing data file.")
                data = DataManager.load_json(TEST_FILE, "testing dataset")
            else:
                data_file_path = os.path.join(DATA_DIR, data_file)
                data = DataManager.load_json(data_file_path, "testing dataset")
            
            benchmark_evaluator = BenchmarkEvaluator(verifier, data, positive_label)
            
            if find_optimal_threshold:
                if not threshold_range or len(threshold_range) != 2:
                    print("Threshold range must be specified as two floats: min and max.")
                    return
                benchmark_evaluator.find_optimal_similarity_threshold(
                    tuple(threshold_range)
                )
            elif verification_method == "embedding":            
                if threshold is None:
                    print("A threshold is required for similarity evaluation.")
                    return
                benchmark_evaluator.evaluate(
                    verifier.is_similar,
                    threshold=threshold
                )
            elif verification_method == "consensus":
                if consensus_method not in CONSENSUS_METHODS:
                    print("An existing consensus method has not been specified.")
                    return
                benchmark_evaluator.evaluate(
                    verifier.verify_with_consensus,
                    consensus_method=consensus_method
                )
            else:
                print("Verification method not implemented for benchmark.")
            return
        except Exception as e:
            print(f"An error occurred during benchmarking: {e}")
            return

    # Data Generation
    else:
        processed_inputs = set()
        valid_generations = []
        to_verify_data = []
        
        try:
            # Generation with reference data from a verified JSON file
            if generate_from_dataset:
                if not data_file:
                    print("Using default reference data file.")
                    data = DataManager.load_json(DATA_FILE, "reference dataset")
                else:
                    data_file_path = os.path.join(DATA_DIR, data_file)
                    data = DataManager.load_json(data_file_path, "reference dataset")
        
                for datapoint in data:
                    input_text = datapoint.get('input', "")
                    output_text = datapoint.get('output', "")

                    print(f"Processing datapoint: {input_text} --> {output_text}")

                    generations = generator.generate(
                        GENERATE_WITH_DATASET,
                        input_text,
                        output_text
                    )
                    
                    for generation in generations:
                        _process_generation(
                            generation,
                            generator,
                            verifier,
                            verification_method,
                            valid_generations,
                            to_verify_data,
                            processed_inputs
                        )

            # Generation of synthetic data without dataset references
            else:
                generations = generator.generate(
                    GENERATE,
                    num_responses=NUM_RESPONSES_GENERATE
                )
                
                for generation in generations:
                    _process_generation(
                        generation,
                        generator,
                        verifier,
                        verification_method,
                        valid_generations,
                        to_verify_data,
                        processed_inputs
                    )
                        
            # Save results
            DataManager.register_data(
                valid_generations,
                to_verify_data,
                CONFIRMED_FILE,
                VERIFY_FILE
            )
            
        except Exception as e:
            print(f"An error occurred during data generation: {e}")

if __name__ == "__main__":
    main()
