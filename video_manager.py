import cv2
import numpy as np
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Tuple
from contextlib import contextmanager

from exceptions import VideoError, CameraError, ResourceError
from utils import logger, FrameBuffer, Config

class VideoManager:
    def __init__(self, config: Config):
        """
        ビデオマネージャーの初期化
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self._running = False
        self.camera = None
        self.frame_width = config.get('camera', 'frame_width')
        self.frame_height = config.get('camera', 'frame_height')
        self.fps = config.get('camera', 'fps')
        
        # フレームバッファの初期化
        max_bytes = config.get('buffer', 'max_size_mb') * 1024 * 1024
        compression_quality = config.get('buffer', 'compression_quality')
        self.frame_buffer = FrameBuffer(max_bytes, compression_quality)
        
        self.capture_thread = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """カメラの動作状態を取得"""
        with self._lock:
            return self._running

    @contextmanager
    def camera_session(self, device_id: int = 0):
        """カメラセッションのコンテキストマネージャー"""
        try:
            self.start_capture(device_id)
            yield self
        finally:
            self.stop_capture()

    def start_capture(self, device_id: int = 0) -> bool:
        """ビデオキャプチャを開始"""
        try:
            self.camera = cv2.VideoCapture(device_id)
            if not self.camera.isOpened():
                raise CameraError(f"カメラ {device_id} を開けませんでした")

            # カメラの設定
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)

            # 実際の設定値を取得
            self.frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = int(self.camera.get(cv2.CAP_PROP_FPS))

            with self._lock:
                self._running = True
            
            self.capture_thread = threading.Thread(
                target=self._capture_frames,
                daemon=True
            )
            self.capture_thread.start()
            logger.info(f"カメラ {device_id} の録画を開始: {self.frame_width}x{self.frame_height} @{self.fps}fps")
            return True

        except Exception as e:
            logger.error(f"カメラの起動に失敗: {str(e)}")
            if self.camera:
                self.camera.release()
                self.camera = None
            return False

    def stop_capture(self):
        """ビデオキャプチャを停止"""
        with self._lock:
            self._running = False

        if self.capture_thread:
            try:
                self.capture_thread.join(timeout=3.0)
            except Exception as e:
                logger.warning(f"キャプチャスレッドの停止中にエラー: {e}")

        if self.camera:
            try:
                self.camera.release()
                self.camera = None
            except Exception as e:
                logger.error(f"カメラのリソース解放中にエラー: {e}")

        self.frame_buffer.clear()
        logger.info("カメラを停止しました")

    def _capture_frames(self):
        """フレームをキャプチャしてバッファに保存"""
        frame_interval = 1.0 / self.fps
        last_capture = time.time()

        while self.running:
            try:
                # フレームレート制御
                current_time = time.time()
                if current_time - last_capture < frame_interval:
                    time.sleep(0.001)  # CPUの負荷を軽減
                    continue

                ret, frame = self.camera.read()
                if ret:
                    self.frame_buffer.add_frame(frame)
                    last_capture = current_time
                else:
                    raise CameraError("フレームの取得に失敗")

            except Exception as e:
                logger.error(f"フレームキャプチャ中にエラー: {e}")
                break

        logger.info("フレームキャプチャを終了")

    def save_video(self, output_path: str, before_seconds: int, after_seconds: int) -> bool:
        """
        トリガー前後の動画を保存
        Args:
            output_path: 保存先のパス
            before_seconds: トリガー前の秒数
            after_seconds: トリガー後の秒数
        """
        try:
            # 必要なフレーム数を計算
            before_frames = before_seconds * self.fps
            after_frames = after_seconds * self.fps
            
            # バッファからフレームを取得
            frames = self.frame_buffer.get_frames(before_frames)
            initial_frames_count = len(frames)
            
            if initial_frames_count < before_frames:
                logger.warning(f"要求されたフレーム数に満たないため、{initial_frames_count}フレームのみ使用します")

            # トリガー後のフレームを取得
            frames_needed = after_frames
            start_time = time.time()
            while frames_needed > 0 and self.running:
                if len(self.frame_buffer.get_frames()) > initial_frames_count:
                    new_frames = self.frame_buffer.get_frames()[-1:]
                    frames.extend(new_frames)
                    frames_needed -= 1
                
                # タイムアウトチェック（5秒）
                if time.time() - start_time > 5.0:
                    logger.warning("トリガー後のフレーム取得がタイムアウト")
                    break
                
                time.sleep(1.0 / self.fps)

            # 動画ファイルの作成
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                self.fps,
                (self.frame_width, self.frame_height)
            )

            # フレームを書き込み
            for frame in frames:
                out.write(frame)

            out.release()
            logger.info(f"動画を保存しました: {output_path}")
            return True

        except Exception as e:
            logger.error(f"動画保存中にエラー: {str(e)}")
            return False

    def get_current_frame(self) -> Optional[np.ndarray]:
        """現在のフレームを取得（プレビュー用）"""
        if self.frame_buffer.frame_count > 0:
            return self.frame_buffer.get_frames(1)[0]
        return None

    def get_camera_info(self) -> Tuple[int, int, int]:
        """カメラの情報を取得"""
        return self.frame_width, self.frame_height, self.fps
