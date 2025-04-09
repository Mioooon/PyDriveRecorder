class VideoError(Exception):
    """ビデオ処理関連の例外基底クラス"""
    pass

class CameraError(VideoError):
    """カメラ関連の例外"""
    pass

class TriggerError(Exception):
    """トリガー処理関連の例外基底クラス"""
    pass

class ConfigError(Exception):
    """設定関連の例外基底クラス"""
    pass

class ResourceError(Exception):
    """リソース関連の例外基底クラス"""
    pass
