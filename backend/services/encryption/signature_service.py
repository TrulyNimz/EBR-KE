"""
Digital Signature Service for FDA 21 CFR Part 11 Compliance.

Provides RSA key pair generation, digital signing, and signature verification.
Electronic signatures must be unique to one individual and not reusable.
"""
import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature


class SignatureService:
    """
    Service for generating and verifying digital signatures.

    Implements FDA 21 CFR Part 11 compliant electronic signatures:
    - Unique to one individual
    - Not reused or reassigned
    - Linked to the electronic record
    - Includes meaning of signature (e.g., approval, review)
    """

    # RSA key size for signing (2048 is minimum for compliance)
    KEY_SIZE = 2048

    # Public exponent for RSA
    PUBLIC_EXPONENT = 65537

    @classmethod
    def generate_key_pair(cls) -> Tuple[bytes, bytes]:
        """
        Generate a new RSA key pair for digital signing.

        Returns:
            Tuple of (private_key_pem, public_key_pem) as bytes.
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=cls.PUBLIC_EXPONENT,
            key_size=cls.KEY_SIZE,
            backend=default_backend()
        )

        # Serialize private key (encrypted with password in production)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()  # Add password in production
        )

        # Get public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    @classmethod
    def sign_data(
        cls,
        private_key_pem: bytes,
        data: Dict[str, Any],
        signer_id: str,
        signer_name: str,
        signature_meaning: str = 'approval'
    ) -> Dict[str, Any]:
        """
        Create a digital signature for the given data.

        Args:
            private_key_pem: The signer's private key in PEM format.
            data: The data to sign (will be serialized to JSON).
            signer_id: The unique identifier of the signer.
            signer_name: The full name of the signer.
            signature_meaning: The meaning of the signature (approval, review, etc.).

        Returns:
            Dictionary containing the signature details.
        """
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,  # Add password support in production
            backend=default_backend()
        )

        # Create the signature payload
        timestamp = datetime.now(timezone.utc).isoformat()

        signature_payload = {
            'data_hash': cls._hash_data(data),
            'signer_id': signer_id,
            'signer_name': signer_name,
            'signature_meaning': signature_meaning,
            'timestamp': timestamp,
        }

        # Serialize payload for signing
        payload_bytes = json.dumps(signature_payload, sort_keys=True).encode('utf-8')

        # Sign the payload
        signature = private_key.sign(
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return {
            'signature': base64.b64encode(signature).decode('utf-8'),
            'payload': signature_payload,
            'algorithm': 'RSA-PSS-SHA256',
            'key_size': cls.KEY_SIZE,
        }

    @classmethod
    def verify_signature(
        cls,
        public_key_pem: bytes,
        signature_data: Dict[str, Any],
        original_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Verify a digital signature.

        Args:
            public_key_pem: The signer's public key in PEM format.
            signature_data: The signature data returned by sign_data().
            original_data: Optional original data to verify hash against.

        Returns:
            True if signature is valid, False otherwise.
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )

            # Decode signature
            signature = base64.b64decode(signature_data['signature'])

            # Reconstruct payload
            payload = signature_data['payload']
            payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')

            # Verify signature
            public_key.verify(
                signature,
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Optionally verify data hash
            if original_data is not None:
                expected_hash = cls._hash_data(original_data)
                if payload['data_hash'] != expected_hash:
                    return False

            return True

        except (InvalidSignature, KeyError, ValueError):
            return False

    @classmethod
    def create_signature_manifest(
        cls,
        record_id: str,
        record_type: str,
        signatures: list
    ) -> Dict[str, Any]:
        """
        Create a signature manifest for an electronic record.

        FDA 21 CFR Part 11 requires linking signatures to records.

        Args:
            record_id: The unique identifier of the record.
            record_type: The type of record (batch, step, etc.).
            signatures: List of signature data.

        Returns:
            Signature manifest dictionary.
        """
        manifest = {
            'record_id': record_id,
            'record_type': record_type,
            'signatures': signatures,
            'signature_count': len(signatures),
            'manifest_created_at': datetime.now(timezone.utc).isoformat(),
            'manifest_hash': '',
        }

        # Calculate manifest hash (excluding manifest_hash field)
        manifest_for_hash = {k: v for k, v in manifest.items() if k != 'manifest_hash'}
        manifest['manifest_hash'] = cls._hash_data(manifest_for_hash)

        return manifest

    @staticmethod
    def _hash_data(data: Dict[str, Any]) -> str:
        """
        Create a SHA-256 hash of the data.

        Args:
            data: Dictionary to hash.

        Returns:
            Hexadecimal hash string.
        """
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    @classmethod
    def get_signature_meanings(cls) -> Dict[str, str]:
        """
        Get available signature meanings per FDA 21 CFR Part 11.

        Returns:
            Dictionary of signature meaning codes and descriptions.
        """
        return {
            'approval': 'Approved - I approve this record',
            'review': 'Reviewed - I have reviewed this record',
            'verification': 'Verified - I have verified this information',
            'creation': 'Created - I created this record',
            'modification': 'Modified - I modified this record',
            'rejection': 'Rejected - I reject this record',
            'completion': 'Completed - I completed this step/task',
            'witness': 'Witnessed - I witnessed this action',
        }
