"""
Field-Level Encryption Service.

Provides AES-256 encryption for sensitive data fields (PII, PHI).
Compliant with Kenya Data Protection Act 2019 and HIPAA (for healthcare module).
"""
import base64
import os
from typing import Optional, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings


class FieldEncryption:
    """
    AES-256 encryption service for sensitive field data.

    Uses AES-256-CBC with PKCS7 padding for field-level encryption.
    Key management should use a proper key management system in production.
    """

    # AES-256 requires 32-byte key
    KEY_SIZE = 32

    # IV size for AES
    IV_SIZE = 16

    # Block size for AES
    BLOCK_SIZE = 128

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize the encryption service.

        Args:
            encryption_key: 32-byte encryption key. If not provided,
                          uses FIELD_ENCRYPTION_KEY from settings.
        """
        if encryption_key:
            self._key = encryption_key
        else:
            key_str = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
            if key_str:
                # Key stored as base64 in settings
                self._key = base64.b64decode(key_str)
            else:
                raise ValueError(
                    'FIELD_ENCRYPTION_KEY not configured in settings. '
                    'Generate with FieldEncryption.generate_key()'
                )

        if len(self._key) != self.KEY_SIZE:
            raise ValueError(f'Encryption key must be {self.KEY_SIZE} bytes')

    @classmethod
    def generate_key(cls) -> str:
        """
        Generate a new AES-256 encryption key.

        Returns:
            Base64-encoded encryption key for storing in settings.
        """
        key = os.urandom(cls.KEY_SIZE)
        return base64.b64encode(key).decode('utf-8')

    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt a field value.

        Args:
            plaintext: The value to encrypt (string or bytes).

        Returns:
            Base64-encoded encrypted value (IV + ciphertext).
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        # Generate random IV
        iv = os.urandom(self.IV_SIZE)

        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Pad plaintext to block size
        padder = padding.PKCS7(self.BLOCK_SIZE).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        # Encrypt
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV and ciphertext, encode as base64
        encrypted = iv + ciphertext
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a field value.

        Args:
            ciphertext: Base64-encoded encrypted value.

        Returns:
            Decrypted string value.
        """
        # Decode from base64
        encrypted = base64.b64decode(ciphertext)

        # Extract IV and ciphertext
        iv = encrypted[:self.IV_SIZE]
        actual_ciphertext = encrypted[self.IV_SIZE:]

        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Decrypt
        padded_data = decryptor.update(actual_ciphertext) + decryptor.finalize()

        # Remove padding
        unpadder = padding.PKCS7(self.BLOCK_SIZE).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()

        return plaintext.decode('utf-8')

    def encrypt_dict_fields(
        self,
        data: dict,
        fields_to_encrypt: list
    ) -> dict:
        """
        Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing data.
            fields_to_encrypt: List of field names to encrypt.

        Returns:
            Dictionary with specified fields encrypted.
        """
        result = data.copy()
        for field in fields_to_encrypt:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result

    def decrypt_dict_fields(
        self,
        data: dict,
        fields_to_decrypt: list
    ) -> dict:
        """
        Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing encrypted data.
            fields_to_decrypt: List of field names to decrypt.

        Returns:
            Dictionary with specified fields decrypted.
        """
        result = data.copy()
        for field in fields_to_decrypt:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(result[field])
                except Exception:
                    # Field might not be encrypted or corrupted
                    pass
        return result


class EncryptedFieldMixin:
    """
    Django model mixin for encrypted fields.

    Usage:
        class Patient(EncryptedFieldMixin, models.Model):
            encrypted_fields = ['national_id', 'phone']
            national_id = models.TextField()
            phone = models.TextField()
    """

    encrypted_fields: list = []
    _encryption_service: Optional[FieldEncryption] = None

    @classmethod
    def get_encryption_service(cls) -> FieldEncryption:
        """Get or create the encryption service singleton."""
        if cls._encryption_service is None:
            cls._encryption_service = FieldEncryption()
        return cls._encryption_service

    def save(self, *args, **kwargs):
        """Encrypt fields before saving."""
        service = self.get_encryption_service()
        for field in self.encrypted_fields:
            value = getattr(self, field, None)
            if value and not self._is_encrypted(value):
                setattr(self, field, service.encrypt(value))
        super().save(*args, **kwargs)

    def get_decrypted_field(self, field_name: str) -> Optional[str]:
        """
        Get a decrypted field value.

        Args:
            field_name: Name of the encrypted field.

        Returns:
            Decrypted value or None.
        """
        if field_name not in self.encrypted_fields:
            raise ValueError(f'{field_name} is not an encrypted field')

        value = getattr(self, field_name, None)
        if value:
            service = self.get_encryption_service()
            return service.decrypt(value)
        return None

    @staticmethod
    def _is_encrypted(value: str) -> bool:
        """
        Check if a value appears to be encrypted.

        Encrypted values are base64 encoded and typically longer.
        """
        try:
            decoded = base64.b64decode(value)
            # Encrypted values will be at least IV_SIZE + 1 block
            return len(decoded) >= 32
        except Exception:
            return False
