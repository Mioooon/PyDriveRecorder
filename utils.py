import logging
import yaml
import os
from typing import Any, Dict
from exceptions import ConfigError

# ロガーの設定
def setup_logger(name: str) -> logging.Logger:
    """アプリケーションロガーのセットアップ"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger('PyDriveRecorder')

class Config:
    """設定管理クラス"""
    DEFAULT_CONFIG = {
        'camera': {
            'default_device': 0,
            'frame_width': 640,
            'frame_height': 480,
            'fps': 30
        },
        'recording': {
            'default_before_time': 5,
            'default_after_time': 5,
            'max_time': 30,
            'min_time': 1
        },
        'trigger': {
            'default_type': 'keyboard',
            'available_types': ['keyboard', 'gpio', 'http', 'websocket'],
            'http_port': 8080,
            'websocket_port': 8081,
            'gpio_pin': 17  # Raspberry Pi GPIO pin number
        },
        'buffer': {
            'max_size_mb': 1024,
            'compression_quality': 90
        }
    }

    def __init__(self, config_path: str = None):
        self._config = self.DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    self._merge_config(user_config)
            except Exception as e:
                raise ConfigError(f"設定ファイルの読み込みに失敗: {e}")

    def _merge_config(self, user_config: Dict[str, Any]):
        """ユーザー設定とデフォルト設定のマージ"""
        for section, values in user_config.items():
            if section in self._config:
                self._config[section].update(values)

    def get(self, section: str, key: str) -> Any:
        """設定値の取得"""
        try:
            return self._config[section][key]
        except KeyError:
            raise ConfigError(f"設定が見つかりません: {section}.{key}")

    def save(self, config_path: str):
        """設定の保存"""
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self._config, f)
        except Exception as e:
            raise ConfigError(f"設定の保存に失敗: {e}")

class FrameBuffer:
    """最適化されたフレームバッファ"""
    def __init__(self, max_bytes: int, compression_quality: int = 90):
        self.max_bytes = max_bytes
        self.compression_quality = compression_quality
        self._buffer = []
        self._current_size = 0

    def add_frame(self, frame):
        """フレームの追加（サイズ制限付き）"""
        import cv2
        import numpy as np

        # フレームの圧縮
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.compression_quality]
        result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
        
        if not result:
            raise ResourceError("フレームの圧縮に失敗しました")

        frame_size = len(encoded_frame)

        # バッファサイズの管理
        while self._buffer and self._current_size + frame_size > self.max_bytes:
            self._current_size -= len(self._buffer.pop(0))

        self._buffer.append(encoded_frame)
        self._current_size += frame_size

    def get_frames(self, count: int = None):
        """フレームの取得"""
        import cv2
        import numpy as np

        frames = self._buffer[-count:] if count else self._buffer
        return [cv2.imdecode(frame, cv2.IMREAD_COLOR) for frame in frames]

    def clear(self):
        """バッファのクリア"""
        self._buffer.clear()
        self._current_size = 0

    @property
    def frame_count(self):
        """現在のフレーム数"""
        return len(self._buffer)
