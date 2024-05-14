from config import createParser
from summary import summarized_text

def main():
    """
    This function reads the configuration and calls the summarized_text function.
    """
    parser = createParser()
    args = parser.parse_args()

    summarized_text(
        api_key=args.api_key,
        base_url=args.api_base,
        prompt_file=args.prompt_file,
        input_file=args.input_file,
        output_file=args.output_file,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_tokens_llm=args.max_tokens_llm,
        max_tokens=args.max_tokens
    )

if __name__ == "__main__":
    main()
