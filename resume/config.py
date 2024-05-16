import argparse
import os

__all__ = ["create_parser"]


def create_parser() -> argparse.ArgumentParser:
    """
    Creates a parser for the command line arguments.
    The parser is created with the following arguments:
    --api_key: OpenAI API Token
    --api_base: OpenAI API Base URL
    --prompt_file: Path to the prompt file
    --input_file: Path to the input text file
    --output_file: Path to the output text file
    --chunk_size: The size of each chunk
    --chunk_overlap: The overlap between chunks
    --max_tokens: The maximum number of tokens for reduction
    """
    parser = argparse.ArgumentParser()

    # OpenAI settings
    parser.add_argument(
        "--api_key",
        type=str,
        help="OpenAI API Token",
        default=os.getenv("API_KEY"),
    )
    parser.add_argument(
        "--api_base",
        type=str,
        help="OpenAI API Base URL",
        default=os.getenv("BASE_URL"),
    )

    # File paths
    parser.add_argument(
        "--prompt_file",
        type=str,
        help="Path to the prompt file",
        default=os.getenv("PROMPT"),
    )
    parser.add_argument(
        "--input_file",
        type=str,
        help="Path to the input text file",
        default=os.getenv("INPUT_TEXT")
    )
    parser.add_argument(
        "--output_file",
        type=str,
        help="Path to the output text file",
        default=os.getenv("OUTPUT")
    )

    # Parameters
    parser.add_argument(
        "--chunk_size",
        type=int,
        help="The size of each chunk",
        default=2000,
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        help="The overlap between chunks",
        default=200,
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        help="The maximum number of tokens for reduction",
        default=1000,
    )

    return parser
