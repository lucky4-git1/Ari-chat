import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Optional, Dict, Any
from app.core.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    )
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against the stored salt:hash string."""
    try:
        salt, stored_hash = hashed_password.split(":")
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100_000
        )
        return hmac.compare_digest(new_key.hex(), stored_hash)
    except Exception:
        return False

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(payload: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Creates a signed HMAC-SHA256 token."""
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + (expires_delta_seconds if expires_delta_seconds else ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    full_payload = {**payload, "exp": exp, "iat": int(time.time())}
    
    encoded_header = _b64_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    encoded_payload = _b64_encode(json.dumps(full_payload, separators=(',', ':')).encode('utf-8'))
    
    message = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
    encoded_signature = _b64_encode(signature)
    
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and verifies an HMAC-SHA256 token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        encoded_header, encoded_payload, encoded_signature = parts
        
        message = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
        actual_sig = _b64_decode(encoded_signature)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload = json.loads(_b64_decode(encoded_payload).decode('utf-8'))
        if "exp" in payload and time.time() > payload["exp"]:
            return None  # Expired
            
        return payload
    except Exception:
        return None
