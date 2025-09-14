"""
Field-level encryption and tokenization utilities.
"""

import os
import base64
import json
import uuid
from typing import Dict, Any, Optional, Tuple, Union, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import boto3
from botocore.exceptions import ClientError
import hashlib
import hmac

from security.models import EncryptionKey, AuditLog


@dataclass
class EncryptedData:
    """Represents encrypted data with metadata."""
    ciphertext: str
    key_id: str
    algorithm: str
    version: int
    metadata: Dict[str, Any]
    created_at: datetime


class KMSProvider:
    """Abstract base class for Key Management Service providers."""
    
    def generate_data_key(self, key_id: str) -> Tuple[str, str]:
        """Generate a data encryption key. Returns (plaintext_key, encrypted_key)."""
        raise NotImplementedError
    
    def decrypt_data_key(self, encrypted_key: str, key_id: str) -> str:
        """Decrypt a data encryption key."""
        raise NotImplementedError
    
    def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data using KMS."""
        raise NotImplementedError
    
    def decrypt_data(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data using KMS."""
        raise NotImplementedError


class AWSKMSProvider(KMSProvider):
    """AWS KMS provider implementation."""
    
    def __init__(self, region_name: str = None):
        self.region_name = region_name or getattr(settings, 'AWS_REGION', 'us-east-1')
        self.client = boto3.client('kms', region_name=self.region_name)
    
    def generate_data_key(self, key_id: str) -> Tuple[str, str]:
        """Generate data key using AWS KMS."""
        try:
            response = self.client.generate_data_key(
                KeyId=key_id,
                KeySpec='AES_256'
            )
            
            plaintext_key = base64.b64encode(response['Plaintext']).decode()
            encrypted_key = base64.b64encode(response['CiphertextBlob']).decode()
            
            return plaintext_key, encrypted_key
            
        except ClientError as e:
            raise Exception(f"KMS data key generation failed: {e}")
    
    def decrypt_data_key(self, encrypted_key: str, key_id: str = None) -> str:
        """Decrypt data key using AWS KMS."""
        try:
            response = self.client.decrypt(
                CiphertextBlob=base64.b64decode(encrypted_key)
            )
            
            return base64.b64encode(response['Plaintext']).decode()
            
        except ClientError as e:
            raise Exception(f"KMS data key decryption failed: {e}")
    
    def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data directly with KMS (for small data)."""
        try:
            response = self.client.encrypt(
                KeyId=key_id,
                Plaintext=data
            )
            
            return response['CiphertextBlob']
            
        except ClientError as e:
            raise Exception(f"KMS encryption failed: {e}")
    
    def decrypt_data(self, encrypted_data: bytes, key_id: str = None) -> bytes:
        """Decrypt data with KMS."""
        try:
            response = self.client.decrypt(
                CiphertextBlob=encrypted_data
            )
            
            return response['Plaintext']
            
        except ClientError as e:
            raise Exception(f"KMS decryption failed: {e}")


class HashiCorpVaultProvider(KMSProvider):
    """HashiCorp Vault provider implementation."""
    
    def __init__(self, vault_url: str = None, vault_token: str = None):
        import hvac
        
        self.vault_url = vault_url or getattr(settings, 'VAULT_URL', 'http://localhost:8200')
        self.vault_token = vault_token or getattr(settings, 'VAULT_TOKEN', '')
        
        self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
        
        if not self.client.is_authenticated():
            raise Exception("Vault authentication failed")
    
    def generate_data_key(self, key_id: str) -> Tuple[str, str]:
        """Generate data key using Vault transit engine."""
        try:
            # Generate plaintext key
            plaintext_key = base64.b64encode(os.urandom(32)).decode()
            
            # Encrypt with Vault
            response = self.client.secrets.transit.encrypt_data(
                name=key_id,
                plaintext=plaintext_key
            )
            
            encrypted_key = response['data']['ciphertext']
            
            return plaintext_key, encrypted_key
            
        except Exception as e:
            raise Exception(f"Vault data key generation failed: {e}")
    
    def decrypt_data_key(self, encrypted_key: str, key_id: str) -> str:
        """Decrypt data key using Vault."""
        try:
            response = self.client.secrets.transit.decrypt_data(
                name=key_id,
                ciphertext=encrypted_key
            )
            
            return response['data']['plaintext']
            
        except Exception as e:
            raise Exception(f"Vault data key decryption failed: {e}")
    
    def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data with Vault."""
        try:
            plaintext = base64.b64encode(data).decode()
            
            response = self.client.secrets.transit.encrypt_data(
                name=key_id,
                plaintext=plaintext
            )
            
            return response['data']['ciphertext'].encode()
            
        except Exception as e:
            raise Exception(f"Vault encryption failed: {e}")
    
    def decrypt_data(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data with Vault."""
        try:
            response = self.client.secrets.transit.decrypt_data(
                name=key_id,
                ciphertext=encrypted_data.decode()
            )
            
            return base64.b64decode(response['data']['plaintext'])
            
        except Exception as e:
            raise Exception(f"Vault decryption failed: {e}")


class LocalKMSProvider(KMSProvider):
    """Local key management for development/testing."""
    
    def __init__(self, master_key: str = None):
        self.master_key = (master_key or getattr(settings, 'ENCRYPTION_MASTER_KEY', settings.SECRET_KEY))[:32].ljust(32, '0').encode()
        self.cipher = Fernet(base64.urlsafe_b64encode(self.master_key))
    
    def generate_data_key(self, key_id: str) -> Tuple[str, str]:
        """Generate data key locally."""
        # Generate random data key
        data_key = os.urandom(32)
        plaintext_key = base64.b64encode(data_key).decode()
        
        # Encrypt with master key
        encrypted_key = self.cipher.encrypt(data_key).decode()
        
        return plaintext_key, encrypted_key
    
    def decrypt_data_key(self, encrypted_key: str, key_id: str = None) -> str:
        """Decrypt data key locally."""
        try:
            data_key = self.cipher.decrypt(encrypted_key.encode())
            return base64.b64encode(data_key).decode()
        except Exception as e:
            raise Exception(f"Local data key decryption failed: {e}")
    
    def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data locally."""
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes, key_id: str = None) -> bytes:
        """Decrypt data locally."""
        return self.cipher.decrypt(encrypted_data)


class FieldEncryptor:
    """Main field-level encryption utility."""
    
    def __init__(self, kms_provider: KMSProvider = None):
        self.kms_provider = kms_provider or self._get_default_kms_provider()
        self.cache_ttl = 3600  # Cache keys for 1 hour
    
    def _get_default_kms_provider(self) -> KMSProvider:
        """Get default KMS provider based on configuration."""
        provider_type = getattr(settings, 'KMS_PROVIDER', 'local')
        
        if provider_type == 'aws':
            return AWSKMSProvider()
        elif provider_type == 'vault':
            return HashiCorpVaultProvider()
        else:
            return LocalKMSProvider()
    
    def encrypt_field(self, value: Union[str, bytes], key_id: str, 
                     deterministic: bool = False, context: Dict[str, str] = None) -> EncryptedData:
        """
        Encrypt a field value.
        
        Args:
            value: Value to encrypt
            key_id: KMS key identifier
            deterministic: If True, same value always produces same ciphertext (for searchability)
            context: Additional context for encryption
        """
        if isinstance(value, str):
            value = value.encode('utf-8')
        
        # Get or generate data encryption key
        data_key = self._get_data_key(key_id)
        
        if deterministic:
            # Use HMAC-based deterministic encryption
            ciphertext = self._encrypt_deterministic(value, data_key, context)
            algorithm = 'AES-256-HMAC-DET'
        else:
            # Use standard Fernet encryption
            fernet = Fernet(data_key.encode())
            ciphertext = fernet.encrypt(value).decode()
            algorithm = 'FERNET'
        
        # Get key version
        key_obj = EncryptionKey.objects.filter(key_id=key_id, is_active=True).first()
        version = key_obj.version if key_obj else 1
        
        # Create encrypted data object
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            key_id=key_id,
            algorithm=algorithm,
            version=version,
            metadata=context or {},
            created_at=timezone.now()
        )
        
        # Update key usage
        if key_obj:
            key_obj.increment_usage()
        
        return encrypted_data
    
    def decrypt_field(self, encrypted_data: EncryptedData) -> str:
        """Decrypt field value."""
        try:
            # Get data key
            data_key = self._get_data_key(encrypted_data.key_id)
            
            if encrypted_data.algorithm == 'AES-256-HMAC-DET':
                # Deterministic decryption
                plaintext = self._decrypt_deterministic(
                    encrypted_data.ciphertext, 
                    data_key, 
                    encrypted_data.metadata
                )
            elif encrypted_data.algorithm == 'FERNET':
                # Standard Fernet decryption
                fernet = Fernet(data_key.encode())
                plaintext = fernet.decrypt(encrypted_data.ciphertext.encode())
            else:
                raise Exception(f"Unsupported algorithm: {encrypted_data.algorithm}")
            
            # Update key usage
            key_obj = EncryptionKey.objects.filter(
                key_id=encrypted_data.key_id, 
                version=encrypted_data.version
            ).first()
            if key_obj:
                key_obj.increment_usage()
            
            return plaintext.decode('utf-8') if isinstance(plaintext, bytes) else plaintext
            
        except Exception as e:
            # Log decryption failure
            AuditLog.objects.create(
                action='SECURITY_EVENT',
                severity='HIGH',
                resource_type='encryption',
                resource_id=encrypted_data.key_id,
                description=f'Field decryption failed: {str(e)}',
                success=False,
                metadata={
                    'algorithm': encrypted_data.algorithm,
                    'version': encrypted_data.version
                }
            )
            raise Exception(f"Field decryption failed: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any], field_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary to encrypt
            field_config: Configuration for each field to encrypt
                Format: {
                    'field_name': {
                        'key_id': 'encryption_key_id',
                        'deterministic': False,
                        'context': {...}
                    }
                }
        """
        encrypted_data = data.copy()
        
        for field_name, config in field_config.items():
            if field_name in encrypted_data and encrypted_data[field_name] is not None:
                try:
                    encrypted_field = self.encrypt_field(
                        encrypted_data[field_name],
                        config['key_id'],
                        config.get('deterministic', False),
                        config.get('context', {})
                    )
                    
                    # Store as JSON with metadata
                    encrypted_data[field_name] = {
                        'encrypted': True,
                        'ciphertext': encrypted_field.ciphertext,
                        'key_id': encrypted_field.key_id,
                        'algorithm': encrypted_field.algorithm,
                        'version': encrypted_field.version,
                        'metadata': encrypted_field.metadata,
                        'created_at': encrypted_field.created_at.isoformat(),
                    }
                    
                except Exception as e:
                    # Log encryption failure but continue
                    AuditLog.objects.create(
                        action='SECURITY_EVENT',
                        severity='HIGH',
                        resource_type='encryption',
                        description=f'Field encryption failed for {field_name}: {str(e)}',
                        success=False,
                        metadata={'field': field_name, 'config': config}
                    )
        
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any], fields: List[str] = None) -> Dict[str, Any]:
        """Decrypt encrypted fields in a dictionary."""
        decrypted_data = data.copy()
        
        for field_name, field_value in data.items():
            if fields and field_name not in fields:
                continue
            
            if isinstance(field_value, dict) and field_value.get('encrypted'):
                try:
                    encrypted_data = EncryptedData(
                        ciphertext=field_value['ciphertext'],
                        key_id=field_value['key_id'],
                        algorithm=field_value['algorithm'],
                        version=field_value['version'],
                        metadata=field_value['metadata'],
                        created_at=datetime.fromisoformat(field_value['created_at'])
                    )
                    
                    decrypted_value = self.decrypt_field(encrypted_data)
                    decrypted_data[field_name] = decrypted_value
                    
                except Exception as e:
                    # Log decryption failure
                    AuditLog.objects.create(
                        action='SECURITY_EVENT',
                        severity='HIGH',
                        resource_type='encryption',
                        description=f'Field decryption failed for {field_name}: {str(e)}',
                        success=False,
                        metadata={'field': field_name}
                    )
                    # Keep encrypted data as is
                    continue
        
        return decrypted_data
    
    def _get_data_key(self, key_id: str) -> str:
        """Get or generate data encryption key."""
        cache_key = f"data_key_{key_id}"
        
        # Try to get from cache first
        data_key = cache.get(cache_key)
        if data_key:
            return data_key
        
        # Get key from database
        key_obj = EncryptionKey.objects.filter(key_id=key_id, is_active=True).first()
        if not key_obj:
            raise Exception(f"Encryption key not found: {key_id}")
        
        if not key_obj.is_valid():
            raise Exception(f"Encryption key expired or invalid: {key_id}")
        
        # Generate or decrypt data key using KMS
        if key_obj.kms_key_id:
            # Use external KMS
            plaintext_key, encrypted_key = self.kms_provider.generate_data_key(key_obj.kms_key_id)
        else:
            # Use local key derivation
            plaintext_key = self._derive_data_key(key_id)
        
        # Cache the key
        cache.set(cache_key, plaintext_key, self.cache_ttl)
        
        return plaintext_key
    
    def _derive_data_key(self, key_id: str) -> str:
        """Derive data key from master key and key ID."""
        master_key = getattr(settings, 'ENCRYPTION_MASTER_KEY', settings.SECRET_KEY).encode()
        
        # Use PBKDF2 to derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_id.encode(),
            iterations=100000,
        )
        
        derived_key = kdf.finalize(master_key)
        return base64.urlsafe_b64encode(derived_key).decode()
    
    def _encrypt_deterministic(self, value: bytes, key: str, context: Dict[str, str] = None) -> str:
        """Encrypt with deterministic output for searchability."""
        # Create deterministic key from base key and context
        context_str = json.dumps(context or {}, sort_keys=True)
        det_key = hmac.new(
            key.encode(),
            f"deterministic:{context_str}".encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Use AES-GCM with zero IV for determinism (less secure but searchable)
        cipher = Cipher(
            algorithms.AES(det_key.encode()),
            modes.ECB()  # ECB mode is deterministic but less secure
        )
        
        encryptor = cipher.encryptor()
        
        # Pad to block size
        block_size = 16
        padding_length = block_size - (len(value) % block_size)
        padded_value = value + bytes([padding_length]) * padding_length
        
        ciphertext = encryptor.update(padded_value) + encryptor.finalize()
        
        return base64.b64encode(ciphertext).decode()
    
    def _decrypt_deterministic(self, ciphertext: str, key: str, context: Dict[str, str] = None) -> bytes:
        """Decrypt deterministic encryption."""
        # Recreate deterministic key
        context_str = json.dumps(context or {}, sort_keys=True)
        det_key = hmac.new(
            key.encode(),
            f"deterministic:{context_str}".encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        cipher = Cipher(
            algorithms.AES(det_key.encode()),
            modes.ECB()
        )
        
        decryptor = cipher.decryptor()
        
        encrypted_bytes = base64.b64decode(ciphertext)
        padded_plaintext = decryptor.update(encrypted_bytes) + decryptor.finalize()
        
        # Remove padding
        padding_length = padded_plaintext[-1]
        return padded_plaintext[:-padding_length]


class TokenizationService:
    """Tokenization service for sensitive data."""
    
    def __init__(self):
        self.token_cache_ttl = 86400  # 24 hours
    
    def tokenize(self, value: str, token_type: str = 'generic') -> str:
        """
        Create a token for sensitive value.
        
        Returns a token that can be used to retrieve the original value.
        """
        # Generate unique token
        token = f"tok_{token_type}_{uuid.uuid4().hex[:16]}"
        
        # Store mapping in secure cache
        cache_key = f"token_{token}"
        cache.set(cache_key, value, self.token_cache_ttl)
        
        # Also store reverse mapping for deduplication
        value_hash = hashlib.sha256(value.encode()).hexdigest()
        reverse_cache_key = f"token_reverse_{value_hash}"
        cache.set(reverse_cache_key, token, self.token_cache_ttl)
        
        # Log tokenization
        AuditLog.objects.create(
            action='DATA_ACCESS',
            severity='MEDIUM',
            resource_type='tokenization',
            description=f'Value tokenized with {token}',
            success=True,
            metadata={'token_type': token_type}
        )
        
        return token
    
    def detokenize(self, token: str) -> Optional[str]:
        """Retrieve original value from token."""
        cache_key = f"token_{token}"
        value = cache.get(cache_key)
        
        if value:
            # Log detokenization
            AuditLog.objects.create(
                action='PII_ACCESS',
                severity='MEDIUM',
                resource_type='tokenization',
                description=f'Token {token} detokenized',
                success=True
            )
        
        return value
    
    def get_existing_token(self, value: str) -> Optional[str]:
        """Get existing token for value if it exists."""
        value_hash = hashlib.sha256(value.encode()).hexdigest()
        reverse_cache_key = f"token_reverse_{value_hash}"
        return cache.get(reverse_cache_key)
    
    def tokenize_dict(self, data: Dict[str, Any], field_config: Dict[str, str]) -> Dict[str, Any]:
        """
        Tokenize specified fields in dictionary.
        
        Args:
            data: Dictionary to tokenize
            field_config: {field_name: token_type}
        """
        tokenized_data = data.copy()
        
        for field_name, token_type in field_config.items():
            if field_name in tokenized_data and tokenized_data[field_name] is not None:
                value = str(tokenized_data[field_name])
                
                # Check for existing token
                existing_token = self.get_existing_token(value)
                if existing_token:
                    token = existing_token
                else:
                    token = self.tokenize(value, token_type)
                
                tokenized_data[field_name] = token
        
        return tokenized_data
    
    def detokenize_dict(self, data: Dict[str, Any], fields: List[str] = None) -> Dict[str, Any]:
        """Detokenize fields in dictionary."""
        detokenized_data = data.copy()
        
        for field_name, field_value in data.items():
            if fields and field_name not in fields:
                continue
            
            if isinstance(field_value, str) and field_value.startswith('tok_'):
                original_value = self.detokenize(field_value)
                if original_value is not None:
                    detokenized_data[field_name] = original_value
        
        return detokenized_data