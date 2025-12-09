#!/usr/bin/env python3
from cryptography.fernet import Fernet
from typing import Optional


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet symmetric encryption."""

    def __init__(self, encryption_key: str):
        """
        Initialize the encryption service with a Fernet key.

        Args:
            encryption_key: Base64-encoded Fernet key (32 bytes when decoded)
        """
        self.fernet = Fernet(encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        return self.fernet.decrypt(ciphertext.encode()).decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded 32-byte encryption key
    """
    return Fernet.generate_key().decode()


# Global encryption service instance (initialized with settings)
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service(encryption_key: Optional[str] = None) -> EncryptionService:
    """
    Get or create the global encryption service instance.

    Args:
        encryption_key: Optional encryption key (uses existing instance if not provided)

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        if encryption_key is None:
            from .config import settings
            encryption_key = settings.encryption_key
        _encryption_service = EncryptionService(encryption_key)
    return _encryption_service
