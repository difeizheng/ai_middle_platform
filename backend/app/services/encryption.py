"""
密码加密服务

用于加密存储敏感信息（如数据库密码、API 密钥等）
"""
import os
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """
    加密服务

    使用 Fernet 对称加密（基于 AES-128-CBC）
    支持基于密码派生密钥
    """

    def __init__(self, encryption_key: Optional[str] = None, salt: Optional[str] = None):
        """
        初始化加密服务

        Args:
            encryption_key: 加密密钥（32 字节 URL-safe base64 编码）
                         如果未提供，将使用密钥管理器中的密钥
                         或从环境变量 ENCRYPTION_KEY 获取
            salt: 盐值（用于密码派生）
        """
        self._key = encryption_key
        self._salt = salt.encode() if salt else None
        self._fernet: Optional[Fernet] = None

        # 1. 尝试从参数获取密钥
        if not self._key:
            # 2. 尝试从密钥管理器获取
            try:
                from .key_manager import get_encryption_key_from_manager
                self._key = get_encryption_key_from_manager()
                logger.info("Using encryption key from key manager")
            except ImportError:
                pass

        # 3. 尝试从环境变量获取密钥
        if not self._key:
            self._key = os.environ.get("ENCRYPTION_KEY")

        # 4. 如果没有密钥，生成一个新密钥（仅用于开发环境）
        if not self._key:
            logger.warning("No encryption key provided. Generating a new one (development only!)")
            self._key = Fernet.generate_key().decode()
            logger.info(f"Generated temporary encryption key: {self._key[:10]}...")

        # 初始化 Fernet
        if isinstance(self._key, str):
            self._key = self._key.encode()

        try:
            self._fernet = Fernet(self._key)
        except Exception as e:
            logger.error(f"Invalid encryption key: {e}")
            raise ValueError(f"Invalid encryption key: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        生成新的加密密钥

        Returns:
            str: 32 字节 URL-safe base64 编码的密钥
        """
        return Fernet.generate_key().decode()

    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """
        从密码派生加密密钥

        Args:
            password: 密码
            salt: 盐值（可选，如果未提供将生成新的）

        Returns:
            tuple: (密钥字符串，盐值字节)
        """
        if salt is None:
            salt = os.urandom(16)

        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP 推荐值
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 明文

        Returns:
            str: 密文（URL-safe base64 编码）
        """
        if not plaintext:
            return ""

        encrypted = self._fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        解密密文

        Args:
            ciphertext: 密文（URL-safe base64 编码）

        Returns:
            str: 明文
        """
        if not ciphertext:
            return ""

        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except InvalidToken:
            logger.error("Invalid token - decryption failed")
            raise ValueError("Invalid encryption key or corrupted data")
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def encrypt_if_needed(self, value: str, is_encrypted: bool = False) -> str:
        """
        条件加密：如果值尚未加密，则加密它

        Args:
            value: 要加密的值
            is_encrypted: 值是否已加密

        Returns:
            str: 加密后的值或原始值
        """
        if is_encrypted:
            return value
        return self.encrypt(value)

    def decrypt_if_needed(self, value: str, is_encrypted: bool = True) -> str:
        """
        条件解密：如果值已加密，则解密它

        Args:
            value: 要解密的值
            is_encrypted: 值是否已加密

        Returns:
            str: 解密后的值或原始值
        """
        if not is_encrypted:
            return value
        try:
            return self.decrypt(value)
        except ValueError:
            # 如果解密失败，可能值未加密
            logger.warning("Decryption failed, returning original value")
            return value


# 全局加密服务实例
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    获取全局加密服务实例

    Returns:
        EncryptionService: 加密服务实例
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def init_encryption_service(encryption_key: str) -> EncryptionService:
    """
    初始化加密服务

    Args:
        encryption_key: 加密密钥

    Returns:
        EncryptionService: 加密服务实例
    """
    global _encryption_service
    _encryption_service = EncryptionService(encryption_key=encryption_key)
    return _encryption_service


def encrypt_password(password: str) -> str:
    """
    加密密码

    Args:
        password: 明文密码

    Returns:
        str: 加密后的密码
    """
    return get_encryption_service().encrypt(password)


def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码

    Args:
        encrypted_password: 加密的密码

    Returns:
        str: 明文密码
    """
    return get_encryption_service().decrypt(encrypted_password)
