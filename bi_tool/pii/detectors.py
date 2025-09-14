"""
PII Detection and Classification utilities.
"""

import re
import hashlib
import hmac
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


class PIILevel(Enum):
    """PII sensitivity levels."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PIIMatch:
    """Represents a PII match found in data."""
    field_name: str
    pii_type: str
    confidence: float
    start_pos: int
    end_pos: int
    value: str
    pii_level: PIILevel
    context: Dict[str, Any]


class PIIDetectionRules:
    """PII detection rules and patterns."""
    
    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    )
    
    # Phone number patterns
    PHONE_PATTERNS = {
        'US': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
        'UK': re.compile(r'(\+44\s?7\d{3}|\(?07\d{3}\)?)\s?\d{3}\s?\d{3}'),
        'GENERIC': re.compile(r'(\+\d{1,3}[-.\s]?)?\d{6,14}'),
    }
    
    # Social Security Number (US)
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    
    # Credit card patterns
    CREDIT_CARD_PATTERNS = {
        'VISA': re.compile(r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'MASTERCARD': re.compile(r'\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'AMEX': re.compile(r'\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b'),
        'DISCOVER': re.compile(r'\b6(?:011|5\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'GENERIC': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
    }
    
    # National ID patterns (examples)
    NATIONAL_ID_PATTERNS = {
        'UK_NI': re.compile(r'\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b'),  # UK National Insurance
        'CANADA_SIN': re.compile(r'\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b'),  # Canadian SIN
        'AUSTRALIA_TFN': re.compile(r'\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b'),  # Australian TFN
    }
    
    # IP Address pattern
    IP_PATTERN = re.compile(
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    )
    
    # MAC Address pattern
    MAC_PATTERN = re.compile(
        r'\b([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})\b'
    )
    
    # IBAN pattern
    IBAN_PATTERN = re.compile(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'
    )
    
    # Date of Birth patterns
    DOB_PATTERNS = {
        'ISO': re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
        'US': re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
        'UK': re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
    }
    
    # Common name patterns (basic)
    NAME_PATTERNS = {
        'FULL_NAME': re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
        'TITLE_NAME': re.compile(r'\b(Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
    }
    
    # Address patterns (basic)
    ADDRESS_PATTERNS = {
        'US_ADDRESS': re.compile(r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}'),
        'UK_POSTCODE': re.compile(r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b'),
        'GENERIC': re.compile(r'\d+\s+[A-Za-z\s]+'),
    }


class PIIDetector:
    """Main PII detection engine."""
    
    def __init__(self):
        self.rules = PIIDetectionRules()
        self.confidence_threshold = 0.7
    
    def detect_email(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect email addresses."""
        matches = []
        for match in self.rules.EMAIL_PATTERN.finditer(text):
            email = match.group()
            confidence = self._validate_email(email)
            
            if confidence >= self.confidence_threshold:
                matches.append(PIIMatch(
                    field_name=field_name or 'unknown',
                    pii_type='email',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    value=email,
                    pii_level=PIILevel.MEDIUM,
                    context={'validated': True}
                ))
        return matches
    
    def detect_phone(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect phone numbers."""
        matches = []
        
        # Try different phone patterns
        for region, pattern in self.rules.PHONE_PATTERNS.items():
            for match in pattern.finditer(text):
                phone = match.group()
                confidence = self._validate_phone(phone, region)
                
                if confidence >= self.confidence_threshold:
                    matches.append(PIIMatch(
                        field_name=field_name or 'unknown',
                        pii_type='phone',
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        value=phone,
                        pii_level=PIILevel.MEDIUM,
                        context={'region': region}
                    ))
        return matches
    
    def detect_ssn(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect Social Security Numbers."""
        matches = []
        for match in self.rules.SSN_PATTERN.finditer(text):
            ssn = match.group()
            confidence = self._validate_ssn(ssn)
            
            if confidence >= self.confidence_threshold:
                matches.append(PIIMatch(
                    field_name=field_name or 'unknown',
                    pii_type='ssn',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    value=ssn,
                    pii_level=PIILevel.HIGH,
                    context={'format': 'xxx-xx-xxxx'}
                ))
        return matches
    
    def detect_credit_card(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect credit card numbers."""
        matches = []
        
        for card_type, pattern in self.rules.CREDIT_CARD_PATTERNS.items():
            for match in pattern.finditer(text):
                card_number = match.group()
                confidence = self._validate_credit_card(card_number)
                
                if confidence >= self.confidence_threshold:
                    matches.append(PIIMatch(
                        field_name=field_name or 'unknown',
                        pii_type='credit_card',
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        value=card_number,
                        pii_level=PIILevel.CRITICAL,
                        context={'card_type': card_type}
                    ))
        return matches
    
    def detect_national_id(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect national ID numbers."""
        matches = []
        
        for id_type, pattern in self.rules.NATIONAL_ID_PATTERNS.items():
            for match in pattern.finditer(text):
                national_id = match.group()
                confidence = 0.8  # Basic pattern matching
                
                matches.append(PIIMatch(
                    field_name=field_name or 'unknown',
                    pii_type='national_id',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    value=national_id,
                    pii_level=PIILevel.HIGH,
                    context={'id_type': id_type}
                ))
        return matches
    
    def detect_ip_address(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect IP addresses."""
        matches = []
        for match in self.rules.IP_PATTERN.finditer(text):
            ip = match.group()
            confidence = self._validate_ip(ip)
            
            if confidence >= self.confidence_threshold:
                matches.append(PIIMatch(
                    field_name=field_name or 'unknown',
                    pii_type='ip_address',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    value=ip,
                    pii_level=PIILevel.LOW,
                    context={'ip_type': 'ipv4'}
                ))
        return matches
    
    def detect_names(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Detect person names (basic implementation)."""
        matches = []
        
        # Check if field name suggests it contains names
        name_field_indicators = ['name', 'first_name', 'last_name', 'full_name', 'customer', 'employee']
        field_suggests_name = field_name and any(indicator in field_name.lower() for indicator in name_field_indicators)
        
        for name_type, pattern in self.rules.NAME_PATTERNS.items():
            for match in pattern.finditer(text):
                name = match.group()
                confidence = 0.6 if field_suggests_name else 0.4  # Lower confidence without context
                
                if confidence >= self.confidence_threshold or field_suggests_name:
                    matches.append(PIIMatch(
                        field_name=field_name or 'unknown',
                        pii_type='name',
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        value=name,
                        pii_level=PIILevel.MEDIUM,
                        context={'name_type': name_type, 'field_context': field_suggests_name}
                    ))
        return matches
    
    def scan_text(self, text: str, field_name: str = None) -> List[PIIMatch]:
        """Comprehensive PII scan of text."""
        all_matches = []
        
        # Run all detectors
        detectors = [
            self.detect_email,
            self.detect_phone,
            self.detect_ssn,
            self.detect_credit_card,
            self.detect_national_id,
            self.detect_ip_address,
            self.detect_names,
        ]
        
        for detector in detectors:
            matches = detector(text, field_name)
            all_matches.extend(matches)
        
        # Sort by position and remove overlaps
        return self._deduplicate_matches(all_matches)
    
    def scan_dict(self, data: Dict[str, Any], prefix: str = '') -> Dict[str, List[PIIMatch]]:
        """Scan dictionary for PII."""
        results = {}
        
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, str):
                matches = self.scan_text(value, field_path)
                if matches:
                    results[field_path] = matches
            elif isinstance(value, dict):
                nested_results = self.scan_dict(value, field_path)
                results.update(nested_results)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        matches = self.scan_text(item, f"{field_path}[{i}]")
                        if matches:
                            results[f"{field_path}[{i}]"] = matches
                    elif isinstance(item, dict):
                        nested_results = self.scan_dict(item, f"{field_path}[{i}]")
                        results.update(nested_results)
        
        return results
    
    def _validate_email(self, email: str) -> float:
        """Validate email address and return confidence."""
        try:
            validate_email(email)
            return 0.95
        except EmailNotValidError:
            return 0.3
    
    def _validate_phone(self, phone: str, region: str) -> float:
        """Validate phone number and return confidence."""
        try:
            if region != 'GENERIC':
                # Clean the phone number
                cleaned = re.sub(r'[^\d+]', '', phone)
                parsed = phonenumbers.parse(cleaned, None)
                if phonenumbers.is_valid_number(parsed):
                    return 0.9
            return 0.6  # Pattern matched but not validated
        except:
            return 0.4
    
    def _validate_ssn(self, ssn: str) -> float:
        """Validate SSN format."""
        # Basic validation - not 000-00-0000, etc.
        parts = ssn.split('-')
        if len(parts) == 3 and parts[0] != '000' and parts[1] != '00' and parts[2] != '0000':
            return 0.8
        return 0.3
    
    def _validate_credit_card(self, card_number: str) -> float:
        """Validate credit card using Luhn algorithm."""
        # Clean the number
        cleaned = re.sub(r'[\s-]', '', card_number)
        
        if not cleaned.isdigit():
            return 0.2
        
        # Luhn algorithm
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        if luhn_checksum(cleaned) == 0:
            return 0.9
        return 0.3
    
    def _validate_ip(self, ip: str) -> float:
        """Validate IP address format."""
        parts = ip.split('.')
        if len(parts) == 4:
            try:
                for part in parts:
                    num = int(part)
                    if not 0 <= num <= 255:
                        return 0.3
                return 0.8
            except ValueError:
                return 0.2
        return 0.2
    
    def _deduplicate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping matches, keeping highest confidence."""
        if not matches:
            return []
        
        # Sort by start position
        sorted_matches = sorted(matches, key=lambda x: x.start_pos)
        deduplicated = []
        
        for match in sorted_matches:
            # Check for overlap with existing matches
            overlaps = False
            for existing in deduplicated:
                if (match.start_pos <= existing.end_pos and 
                    match.end_pos >= existing.start_pos):
                    # There's an overlap
                    if match.confidence > existing.confidence:
                        # Replace with higher confidence match
                        deduplicated.remove(existing)
                        deduplicated.append(match)
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(match)
        
        return deduplicated


class PIIClassifier:
    """Classify PII and assign sensitivity levels."""
    
    PII_CATEGORIES = {
        'IDENTIFIERS': {
            'types': ['email', 'phone', 'ssn', 'national_id', 'name'],
            'default_level': PIILevel.MEDIUM,
        },
        'FINANCIAL': {
            'types': ['credit_card', 'bank_account', 'iban'],
            'default_level': PIILevel.CRITICAL,
        },
        'BIOMETRIC': {
            'types': ['fingerprint', 'facial_recognition', 'voice_print'],
            'default_level': PIILevel.CRITICAL,
        },
        'LOCATION': {
            'types': ['address', 'gps_coordinates', 'ip_address'],
            'default_level': PIILevel.LOW,
        },
        'DEMOGRAPHIC': {
            'types': ['date_of_birth', 'age', 'gender', 'race'],
            'default_level': PIILevel.MEDIUM,
        },
        'BEHAVIORAL': {
            'types': ['browsing_history', 'purchase_history', 'preferences'],
            'default_level': PIILevel.LOW,
        },
    }
    
    @classmethod
    def classify_pii_type(cls, pii_type: str) -> Tuple[str, PIILevel]:
        """Classify PII type and return category with sensitivity level."""
        for category, info in cls.PII_CATEGORIES.items():
            if pii_type in info['types']:
                return category, info['default_level']
        
        return 'UNKNOWN', PIILevel.LOW
    
    @classmethod
    def classify_field(cls, field_name: str, matches: List[PIIMatch]) -> Dict[str, Any]:
        """Classify a field based on its PII matches."""
        if not matches:
            return {
                'pii_level': PIILevel.NONE,
                'categories': [],
                'types': [],
                'confidence': 0.0,
            }
        
        # Get highest confidence match
        highest_match = max(matches, key=lambda x: x.confidence)
        
        # Classify all matches
        categories = set()
        types = set()
        max_level = PIILevel.NONE
        
        for match in matches:
            category, level = cls.classify_pii_type(match.pii_type)
            categories.add(category)
            types.add(match.pii_type)
            
            # Get highest sensitivity level
            level_hierarchy = [PIILevel.NONE, PIILevel.LOW, PIILevel.MEDIUM, PIILevel.HIGH, PIILevel.CRITICAL]
            if level_hierarchy.index(level) > level_hierarchy.index(max_level):
                max_level = level
        
        return {
            'pii_level': max_level,
            'categories': list(categories),
            'types': list(types),
            'confidence': highest_match.confidence,
            'match_count': len(matches),
        }
    
    @classmethod
    def generate_data_map(cls, scan_results: Dict[str, List[PIIMatch]]) -> Dict[str, Any]:
        """Generate a data map showing PII classification across all fields."""
        data_map = {
            'fields': {},
            'summary': {
                'total_fields': len(scan_results),
                'pii_fields': 0,
                'levels': {level.value: 0 for level in PIILevel},
                'categories': {},
                'types': {},
            }
        }
        
        for field_name, matches in scan_results.items():
            classification = cls.classify_field(field_name, matches)
            data_map['fields'][field_name] = classification
            
            if classification['pii_level'] != PIILevel.NONE:
                data_map['summary']['pii_fields'] += 1
                data_map['summary']['levels'][classification['pii_level'].value] += 1
                
                # Count categories and types
                for category in classification['categories']:
                    data_map['summary']['categories'][category] = data_map['summary']['categories'].get(category, 0) + 1
                
                for pii_type in classification['types']:
                    data_map['summary']['types'][pii_type] = data_map['summary']['types'].get(pii_type, 0) + 1
        
        return data_map


class PIIRedactor:
    """Redact or mask PII in data."""
    
    REDACTION_STRATEGIES = {
        'MASK': 'mask',          # Replace with asterisks
        'HASH': 'hash',          # Replace with hash
        'REMOVE': 'remove',      # Remove entirely
        'PARTIAL': 'partial',    # Show partial (e.g., first 3 chars)
        'TOKEN': 'token',        # Replace with token
    }
    
    def __init__(self, strategy: str = 'MASK'):
        self.strategy = strategy
        self.salt = getattr(settings, 'PII_HASH_SALT', 'default_salt').encode()
    
    def redact_text(self, text: str, matches: List[PIIMatch]) -> str:
        """Redact PII matches in text."""
        if not matches:
            return text
        
        # Sort matches by position (reverse order to maintain positions)
        sorted_matches = sorted(matches, key=lambda x: x.start_pos, reverse=True)
        
        redacted_text = text
        for match in sorted_matches:
            replacement = self._get_replacement(match)
            redacted_text = (
                redacted_text[:match.start_pos] + 
                replacement + 
                redacted_text[match.end_pos:]
            )
        
        return redacted_text
    
    def redact_dict(self, data: Dict[str, Any], scan_results: Dict[str, List[PIIMatch]], 
                   level_threshold: PIILevel = PIILevel.LOW) -> Dict[str, Any]:
        """Redact PII in dictionary based on scan results."""
        redacted_data = data.copy()
        
        for field_path, matches in scan_results.items():
            # Check if any match exceeds threshold
            should_redact = any(
                self._get_pii_level_value(match.pii_level) >= self._get_pii_level_value(level_threshold)
                for match in matches
            )
            
            if should_redact:
                # Navigate to the field and redact
                keys = field_path.split('.')
                current = redacted_data
                
                # Navigate to parent
                for key in keys[:-1]:
                    if '[' in key and ']' in key:
                        # Handle list indices
                        field_name, index_part = key.split('[')
                        index = int(index_part.rstrip(']'))
                        current = current[field_name][index]
                    else:
                        current = current[key]
                
                # Redact the final field
                final_key = keys[-1]
                if '[' in final_key and ']' in final_key:
                    field_name, index_part = final_key.split('[')
                    index = int(index_part.rstrip(']'))
                    if isinstance(current[field_name][index], str):
                        current[field_name][index] = self.redact_text(current[field_name][index], matches)
                else:
                    if isinstance(current[final_key], str):
                        current[final_key] = self.redact_text(current[final_key], matches)
        
        return redacted_data
    
    def _get_replacement(self, match: PIIMatch) -> str:
        """Get replacement text for a PII match."""
        if self.strategy == 'MASK':
            return '*' * len(match.value)
        elif self.strategy == 'HASH':
            return f"<HASH_{self._hash_value(match.value)[:8]}>"
        elif self.strategy == 'REMOVE':
            return '[REDACTED]'
        elif self.strategy == 'PARTIAL':
            return self._partial_mask(match.value, match.pii_type)
        elif self.strategy == 'TOKEN':
            return f"<{match.pii_type.upper()}_TOKEN>"
        else:
            return '[PII_REDACTED]'
    
    def _hash_value(self, value: str) -> str:
        """Create consistent hash of value."""
        return hashlib.pbkdf2_hmac('sha256', value.encode(), self.salt, 100000).hex()
    
    def _partial_mask(self, value: str, pii_type: str) -> str:
        """Create partial mask showing some characters."""
        if pii_type == 'email':
            if '@' in value:
                local, domain = value.split('@', 1)
                return f"{local[:2]}***@{domain}"
        elif pii_type == 'phone':
            cleaned = re.sub(r'[^\d]', '', value)
            if len(cleaned) >= 7:
                return f"***-***-{cleaned[-4:]}"
        elif pii_type == 'credit_card':
            cleaned = re.sub(r'[^\d]', '', value)
            if len(cleaned) >= 12:
                return f"****-****-****-{cleaned[-4:]}"
        elif pii_type == 'ssn':
            return f"***-**-{value[-4:]}" if '-' in value else f"*****{value[-4:]}"
        
        # Default: show first 2 and last 2 characters
        if len(value) > 4:
            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
        else:
            return '*' * len(value)
    
    def _get_pii_level_value(self, level: PIILevel) -> int:
        """Get numeric value for PII level comparison."""
        level_values = {
            PIILevel.NONE: 0,
            PIILevel.LOW: 1,
            PIILevel.MEDIUM: 2,
            PIILevel.HIGH: 3,
            PIILevel.CRITICAL: 4,
        }
        return level_values.get(level, 0)


class PIIPseudonymizer:
    """Generate stable pseudonyms for PII data."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = (secret_key or getattr(settings, 'PII_PSEUDONYM_KEY', settings.SECRET_KEY)).encode()
    
    def pseudonymize(self, value: str, pii_type: str = None, context: str = None) -> str:
        """Generate stable pseudonym for a value."""
        # Create context-specific key
        context_key = f"{pii_type or 'default'}:{context or 'global'}"
        
        # Generate HMAC-based pseudonym
        hmac_obj = hmac.new(
            self.secret_key,
            f"{context_key}:{value}".encode(),
            hashlib.sha256
        )
        
        pseudonym_hash = hmac_obj.hexdigest()
        
        # Generate human-readable pseudonym based on PII type
        if pii_type == 'email':
            return f"user_{pseudonym_hash[:8]}@example.com"
        elif pii_type == 'phone':
            # Generate fake phone number
            digits = pseudonym_hash[:10]
            return f"+1-555-{digits[3:6]}-{digits[6:10]}"
        elif pii_type == 'name':
            # Generate fake name
            first_names = ['John', 'Jane', 'Alex', 'Sam', 'Chris', 'Morgan', 'Taylor', 'Jordan']
            last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
            
            first_idx = int(pseudonym_hash[:2], 16) % len(first_names)
            last_idx = int(pseudonym_hash[2:4], 16) % len(last_names)
            
            return f"{first_names[first_idx]} {last_names[last_idx]}"
        elif pii_type == 'ssn':
            # Generate fake SSN format
            return f"123-45-{pseudonym_hash[4:8]}"
        else:
            # Generic pseudonym
            return f"PSEUDO_{pseudonym_hash[:12]}"
    
    def pseudonymize_dict(self, data: Dict[str, Any], scan_results: Dict[str, List[PIIMatch]], 
                         context: str = None) -> Dict[str, Any]:
        """Pseudonymize PII in dictionary."""
        pseudonymized_data = data.copy()
        
        for field_path, matches in scan_results.items():
            # Get the highest confidence PII type
            if matches:
                best_match = max(matches, key=lambda x: x.confidence)
                
                # Navigate to field and pseudonymize
                keys = field_path.split('.')
                current = pseudonymized_data
                
                # Navigate to parent
                for key in keys[:-1]:
                    if '[' in key and ']' in key:
                        field_name, index_part = key.split('[')
                        index = int(index_part.rstrip(']'))
                        current = current[field_name][index]
                    else:
                        current = current[key]
                
                # Pseudonymize the final field
                final_key = keys[-1]
                if '[' in final_key and ']' in final_key:
                    field_name, index_part = final_key.split('[')
                    index = int(index_part.rstrip(']'))
                    if isinstance(current[field_name][index], str):
                        current[field_name][index] = self.pseudonymize(
                            current[field_name][index],
                            best_match.pii_type,
                            f"{context or 'default'}:{field_path}"
                        )
                else:
                    if isinstance(current[final_key], str):
                        current[final_key] = self.pseudonymize(
                            current[final_key],
                            best_match.pii_type,
                            f"{context or 'default'}:{field_path}"
                        )
        
        return pseudonymized_data