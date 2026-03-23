"""
加密服务测试
"""
import pytest
from app.services.encryption import (
    EncryptionService,
    generate_key,
    encrypt_password,
    decrypt_password,
    init_encryption_service,
    get_encryption_service,
)


class TestEncryptionService:
    """加密服务测试"""

    def test_generate_key(self):
        """测试生成密钥"""
        key = generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_create_service_with_key(self):
        """测试创建加密服务"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)
        assert service is not None

    def test_encrypt_decrypt(self):
        """测试加密和解密"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "Hello, World!"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert encrypted != plaintext
        assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        encrypted = service.encrypt("")
        assert encrypted == ""

    def test_decrypt_empty_string(self):
        """测试解密空字符串"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        decrypted = service.decrypt("")
        assert decrypted == ""

    def test_encrypt_special_characters(self):
        """测试加密特殊字符"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "你好，世界！@#$%^&*()"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_newline(self):
        """测试加密换行符"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "Line 1\nLine 2\nLine 3"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_decrypt_with_wrong_key(self):
        """测试使用错误的密钥解密"""
        key1 = generate_key()
        key2 = generate_key()

        service1 = EncryptionService(encryption_key=key1)
        service2 = EncryptionService(encryption_key=key2)

        plaintext = "Secret message"
        encrypted = service1.encrypt(plaintext)

        with pytest.raises(ValueError):
            service2.decrypt(encrypted)

    def test_derive_key_from_password(self):
        """测试从密码派生密钥"""
        password = "my_secure_password"
        key, salt = EncryptionService.derive_key_from_password(password)

        assert isinstance(key, str)
        assert isinstance(salt, bytes)
        assert len(salt) == 16

        # 相同的密码和盐应该生成相同的密钥
        key2, salt2 = EncryptionService.derive_key_from_password(password, salt)
        assert key == key2

    def test_encrypt_if_needed(self):
        """测试条件加密"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "Secret"

        # 未加密时应该加密
        encrypted = service.encrypt_if_needed(plaintext, is_encrypted=False)
        assert encrypted != plaintext

        # 已加密时不应该再次加密
        result = service.encrypt_if_needed(encrypted, is_encrypted=True)
        assert result == encrypted

    def test_decrypt_if_needed(self):
        """测试条件解密"""
        key = generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "Secret"
        encrypted = service.encrypt(plaintext)

        # 已加密时应该解密
        decrypted = service.decrypt_if_needed(encrypted, is_encrypted=True)
        assert decrypted == plaintext

        # 未加密时不应该解密
        result = service.decrypt_if_needed(plaintext, is_encrypted=False)
        assert result == plaintext


class TestGlobalEncryptionService:
    """全局加密服务测试"""

    def test_get_encryption_service_auto_init(self):
        """测试自动初始化全局服务"""
        # 清除全局实例（如果存在）
        from app.services import encryption
        encryption._encryption_service = None

        service = get_encryption_service()
        assert service is not None

    def test_init_encryption_service(self):
        """测试手动初始化全局服务"""
        key = generate_key()

        from app.services import encryption
        encryption._encryption_service = None

        service = init_encryption_service(key)
        assert service is not None

        # 再次获取应该是同一个实例
        service2 = get_encryption_service()
        assert service is service2

    def test_encrypt_password_helper(self):
        """测试加密密码辅助函数"""
        key = generate_key()

        from app.services import encryption
        encryption._encryption_service = None
        init_encryption_service(key)

        password = "my_secret_password"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert encrypted != password
        assert decrypted == password
