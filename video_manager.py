import cv2
import numpy as np
import threading
import queue
import time
from collections import deque
from datetime import datetime

class VideoManager:
    def __init__(self, buffer_seconds=30, fps=30):
        """
        VideoManagerの初期化
        Args:
            buffer_seconds (int): バッファに保持する秒数
            fps (int): フレームレート
        """
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.frame_buffer = deque(maxlen=buffer_seconds * fps)
        self._running = False
        self.camera = None
        self.frame_width = 640  # デフォルト値
        self.frame_height = 480  # デフォルト値
        self.capture_thread = None

    @property
    def running(self):
        """カメラの動作状態を取得"""
        return self._running

    def start_capture(self, device_id=0):
        """ビデオキャプチャを開始"""
        try:
            self.camera = cv2.VideoCapture(device_id)
            if not self.camera.isOpened():
                raise Exception("カメラを開けませんでした")

            # カメラの設定を取得
            self.frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self._running = True
            self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.capture_thread.start()
            return True
        except Exception as e:
            print(f"エラー: {str(e)}")
            return False

    def stop_capture(self):
        """ビデオキャプチャを停止"""
        self._running = False
        if self.capture_thread:
            self.capture_thread.join()
        if self.camera:
            self.camera.release()

    def _capture_frames(self):
        """フレームをキャプチャしてバッファに保存"""
        while self.running:
            ret, frame = self.camera.read()
            if ret:
                self.frame_buffer.append(frame)
            else:
                print("フレームの取得に失敗しました")
                break

    def save_video(self, output_path, before_seconds, after_seconds):
        """
        トリガー前後の動画を保存
        Args:
            output_path (str): 保存先のパス
            before_seconds (int): トリガー前の秒数
            after_seconds (int): トリガー後の秒数
        """
        try:
            # 必要なフレーム数を計算
            before_frames = before_seconds * self.fps
            after_frames = after_seconds * self.fps
            total_frames = before_frames + after_frames

            # バッファから必要なフレームを取得
            frames = list(self.frame_buffer)[-before_frames:]
            initial_frames_count = len(frames)

            # トリガー後のフレームを取得
            frames_needed = after_frames
            while frames_needed > 0 and self.running:
                if len(self.frame_buffer) > initial_frames_count:
                    frames.append(self.frame_buffer[-1])
                    frames_needed -= 1
                time.sleep(1.0 / self.fps)

            # 動画ファイルの作成
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4形式
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
            return True

        except Exception as e:
            print(f"動画保存エラー: {str(e)}")
            return False

    def get_current_frame(self):
        """現在のフレームを取得（プレビュー用）"""
        if len(self.frame_buffer) > 0:
            return self.frame_buffer[-1]
        return None
