import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Get encryption key from environment or generate one for development
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key for development (should be stored securely in production)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning(
        "Generated temporary encryption key. Set ENCRYPTION_KEY in environment for production."
    )

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key using Fernet encryption"""
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an encrypted API key"""
    return fernet.decrypt(encrypted_key.encode()).decode()
