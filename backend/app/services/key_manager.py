"""
密钥管理服务

用于安全存储和管理加密密钥、API 密钥等敏感信息
"""
import os
import json
from typing import Optional, Dict
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class KeyManager:
    """
    密钥管理器

    功能:
    - 从安全位置加载密钥
    - 密钥轮换支持
    - 密钥访问审计
    """

    def __init__(self, key_storage_path: Optional[str] = None):
        """
        初始化密钥管理器

        Args:
            key_storage_path: 密钥存储文件路径
                           默认使用环境变量 KEY_STORAGE_PATH
                           或默认为 ~/.ai_middle_platform/keys.json
        """
        self._keys: Dict[str, str] = {}
        self._key_storage_path = key_storage_path

        if not self._key_storage_path:
            self._key_storage_path = os.environ.get(
                "KEY_STORAGE_PATH",
                str(Path.home() / ".ai_middle_platform" / "keys.json")
            )

        # 确保存储目录存在
        storage_dir = os.path.dirname(self._key_storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, mode=0o700)
            logger.info(f"Created key storage directory: {storage_dir}")

        # 加载密钥
        self._load_keys()

    def _load_keys(self):
        """从存储加载密钥"""
        if os.path.exists(self._key_storage_path):
            try:
                # 检查文件权限（仅限所有者读写）
                file_mode = os.stat(self._key_storage_path).st_mode & 0o777
                if file_mode != 0o600:
                    logger.warning(
                        f"Key storage file has insecure permissions: {oct(file_mode)}. "
                        "Should be 0600."
                    )

                with open(self._key_storage_path, "r", encoding="utf-8") as f:
                    self._keys = json.load(f)
                logger.info(f"Loaded {len(self._keys)} keys from storage")
            except Exception as e:
                logger.error(f"Failed to load keys: {e}")
                self._keys = {}
        else:
            logger.info("No key storage found, starting with empty keys")

    def _save_keys(self):
        """保存密钥到存储"""
        try:
            # 创建临时文件并设置安全权限
            temp_path = self._key_storage_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._keys, f, indent=2)

            # 设置文件权限为仅所有者读写
            os.chmod(temp_path, 0o600)

            # 原子替换原文件
            os.replace(temp_path, self._key_storage_path)
            logger.info("Keys saved to storage")
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_key(self, key_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取密钥

        Args:
            key_name: 密钥名称
            default: 默认值（如果密钥不存在）

        Returns:
            密钥值或 None

        优先级:
        1. 环境变量（AI_MIDDLE_PLATFORM_{key_name}_KEY）
        2. 密钥存储文件
        3. 默认值
        """
        # 1. 尝试从环境变量获取
        env_var_name = f"AI_MIDDLE_PLATFORM_{key_name.upper()}_KEY"
        env_value = os.environ.get(env_var_name)
        if env_value:
            logger.debug(f"Got key '{key_name}' from environment variable")
            return env_value

        # 2. 从存储获取
        if key_name in self._keys:
            logger.debug(f"Got key '{key_name}' from storage")
            return self._keys[key_name]

        # 3. 返回默认值
        if default:
            logger.debug(f"Using default value for key '{key_name}'")
            return default

        logger.warning(f"Key '{key_name}' not found")
        return None

    def set_key(self, key_name: str, key_value: str, save: bool = True) -> None:
        """
        设置密钥

        Args:
            key_name: 密钥名称
            key_value: 密钥值
            save: 是否立即保存到存储
        """
        self._keys[key_name] = key_value
        logger.info(f"Set key '{key_name}'")

        if save:
            self._save_keys()

    def delete_key(self, key_name: str, save: bool = True) -> bool:
        """
        删除密钥

        Args:
            key_name: 密钥名称
            save: 是否立即保存到存储

        Returns:
            是否成功删除
        """
        if key_name in self._keys:
            del self._keys[key_name]
            logger.info(f"Deleted key '{key_name}'")

            if save:
                self._save_keys()
            return True

        logger.warning(f"Key '{key_name}' not found")
        return False

    def list_keys(self) -> list:
        """
        列出所有密钥名称（不显示值）

        Returns:
            密钥名称列表
        """
        return list(self._keys.keys())

    def rotate_key(self, key_name: str) -> str:
        """
        轮换密钥

        Args:
            key_name: 密钥名称

        Returns:
            新生成的密钥值
        """
        from cryptography.fernet import Fernet

        # 生成新密钥
        if key_name.endswith("_ENCRYPTION"):
            # 如果是加密密钥，生成 Fernet 密钥
            new_key = Fernet.generate_key().decode()
        else:
            # 否则生成随机密钥
            import secrets
            new_key = secrets.token_urlsafe(32)

        # 保存新密钥
        self.set_key(key_name, new_key)
        logger.info(f"Rotated key '{key_name}'")

        return new_key

    def get_encryption_key(self) -> str:
        """
        获取加密密钥

        Returns:
            加密密钥
        """
        key = self.get_key("ENCRYPTION")
        if not key:
            # 如果没有存储密钥，生成一个新的
            from cryptography.fernet import Fernet
            key = Fernet.generate_key().decode()
            self.set_key("ENCRYPTION", key)
            logger.info("Generated new encryption key")

        return key


# 全局密钥管理器实例
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """
    获取全局密钥管理器实例

    Returns:
        KeyManager: 密钥管理器
    """
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def get_encryption_key_from_manager() -> str:
    """
    从密钥管理器获取加密密钥

    Returns:
        str: 加密密钥
    """
    return get_key_manager().get_encryption_key()
