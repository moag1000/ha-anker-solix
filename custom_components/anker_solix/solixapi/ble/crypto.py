"""Anker Solix BLE cryptography module.

Implements the ECDH key exchange and AES-128-CBC session encryption
used by Anker Solix devices for secure BLE communication.

Protocol (reverse-engineered from SolixBLE + Anker app v3.18.0):
    1. Use hardcoded ECDH private key (secp256r1 / NIST P-256)
    2. During negotiation stage 5, device sends its public key
    3. Compute ECDH shared secret (32 bytes)
    4. shared_secret[:16] = AES-128 key, shared_secret[16:] = CBC IV
    5. Encrypt/decrypt command payloads with AES-128-CBC + PKCS7 padding

Credits: ECDH flow derived from SolixBLE (@flip-dots), key material from APK RE.
"""

from __future__ import annotations

from typing import NamedTuple

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from . import ECDH_PRIVATE_KEY_HEX


class BleSessionKeys(NamedTuple):
    """Derived AES session keys for BLE communication."""

    aes_key: bytes  # 16 bytes (AES-128)
    aes_iv: bytes  # 16 bytes


def get_ecdh_private_key() -> ec.EllipticCurvePrivateKey:
    """Get the hardcoded ECDH private key for BLE negotiation.

    Returns the private key object on the secp256r1 curve.
    """
    private_value = int.from_bytes(bytes.fromhex(ECDH_PRIVATE_KEY_HEX), byteorder="big")
    return ec.derive_private_key(private_value, ec.SECP256R1())


def get_ecdh_public_key_bytes() -> bytes:
    """Get our public key bytes (uncompressed point format, 64 bytes without 0x04 prefix).

    This is sent to the device during ECDH negotiation.
    """
    private_key = get_ecdh_private_key()
    public_numbers = private_key.public_key().public_numbers()
    return public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")


def compute_session_keys(device_public_key_raw: bytes) -> BleSessionKeys:
    """Compute AES session keys from the device's ECDH public key.

    The Anker BLE protocol uses the raw ECDH shared secret directly:
    - First 16 bytes = AES-128 key
    - Last 16 bytes = CBC initialization vector

    Args:
        device_public_key_raw: Device's public key x+y coordinates (64 bytes, no 0x04 prefix).

    Returns:
        BleSessionKeys with 16-byte AES key and 16-byte IV.

    """
    # Reconstruct uncompressed public key with 0x04 prefix
    device_pub_bytes = b"\x04" + device_public_key_raw
    device_pub_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), device_pub_bytes
    )

    private_key = get_ecdh_private_key()
    shared_secret = private_key.exchange(ec.ECDH(), device_pub_key)

    return BleSessionKeys(aes_key=shared_secret[:16], aes_iv=shared_secret[16:])


def aes_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Encrypt data with AES-128-CBC and PKCS7 padding.

    Args:
        data: Plaintext data to encrypt.
        key: 16-byte AES key.
        iv: 16-byte initialization vector.

    Returns:
        Encrypted ciphertext.

    """
    padder = PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def aes_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt AES-128-CBC encrypted data and remove PKCS7 padding.

    Args:
        data: Ciphertext to decrypt.
        key: 16-byte AES key.
        iv: 16-byte initialization vector.

    Returns:
        Decrypted plaintext.

    """
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def aes_decrypt_raw(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt AES-128-CBC without removing padding.

    Used for telemetry data where padding may not be standard PKCS7.

    Args:
        data: Ciphertext to decrypt.
        key: 16-byte AES key.
        iv: 16-byte initialization vector.

    Returns:
        Decrypted data with padding intact.

    """
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()
