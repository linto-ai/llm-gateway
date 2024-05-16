from config import create_parser
from summary import summarized_text

def main():
    """
    This function reads the configuration and calls the summarized_text function.
    """
    parser = create_parser()
    args = parser.parse_args()

    summarized_text(
        api_key=args.api_key,
        base_url=args.api_base,
        prompts_file=args.prompt_file,
        input_file=args.input_file,
        output_file=args.output_file,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_tokens=args.max_tokens
    )

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    summarized_text(
        api_key=args.api_key,
        base_url=args.api_base,
        prompts_file="prompts.json",
        input_file="input_text.txt",
        output_file="resume.txt",
        chunk_size=1000,
        chunk_overlap=100,
        max_tokens=5000
    )
