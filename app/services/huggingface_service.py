"""HuggingFace integration service for fetching tokenizer information."""
import httpx
import logging

logger = logging.getLogger(__name__)


class HuggingFaceService:
    """Service to fetch tokenizer info from HuggingFace repositories."""

    BASE_URL = "https://huggingface.co"

    async def get_tokenizer_info(self, repo_path: str) -> dict:
        """
        Fetch tokenizer_config.json from HuggingFace repo.

        Args:
            repo_path: HuggingFace repository path, e.g., "mistralai/Mistral-Small-3.1-24B-Instruct-2503"

        Returns:
            dict with tokenizer_class, tokenizer_name, repo_path, found status, and optional error
        """
        url = f"{self.BASE_URL}/{repo_path}/raw/main/tokenizer_config.json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0, follow_redirects=True)

                if response.status_code == 404:
                    logger.info(f"Tokenizer config not found for repo: {repo_path}")
                    return {
                        "found": False,
                        "repo_path": repo_path,
                        "tokenizer_class": None,
                        "tokenizer_name": None,
                    }

                response.raise_for_status()
                config = response.json()

                # Extract tokenizer class and name from config
                tokenizer_class = config.get("tokenizer_class")
                tokenizer_name = config.get("name") or config.get("tokenizer_name")

                logger.info(f"Found tokenizer info for {repo_path}: class={tokenizer_class}, name={tokenizer_name}")

                return {
                    "found": True,
                    "repo_path": repo_path,
                    "tokenizer_class": tokenizer_class,
                    "tokenizer_name": tokenizer_name,
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"HuggingFace API HTTP error for {repo_path}: {e}")
                return {
                    "found": False,
                    "repo_path": repo_path,
                    "tokenizer_class": None,
                    "tokenizer_name": None,
                    "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                }
            except httpx.TimeoutException:
                logger.error(f"HuggingFace API timeout for {repo_path}")
                return {
                    "found": False,
                    "repo_path": repo_path,
                    "tokenizer_class": None,
                    "tokenizer_name": None,
                    "error": "Request timed out",
                }
            except Exception as e:
                logger.error(f"HuggingFace API error for {repo_path}: {e}")
                return {
                    "found": False,
                    "repo_path": repo_path,
                    "tokenizer_class": None,
                    "tokenizer_name": None,
                    "error": str(e),
                }


huggingface_service = HuggingFaceService()
