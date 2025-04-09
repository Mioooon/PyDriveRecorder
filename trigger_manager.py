import threading
import queue
from pynput import keyboard

class TriggerManager:
    def __init__(self):
        self.trigger_queue = queue.Queue()
        self.running = False
        self.keyboard_listener = None
        self.trigger_type = "keyboard"  # デフォルトのトリガータイプ

    def start_listening(self):
        """トリガー入力のリスニングを開始"""
        self.running = True
        if self.trigger_type == "keyboard":
            self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
            self.keyboard_listener.start()

    def stop_listening(self):
        """トリガー入力のリスニングを停止"""
        self.running = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def _on_key_press(self, key):
        """キーボード入力を処理"""
        try:
            if key == keyboard.Key.space and self.running:
                self.trigger_queue.put("KeyboardTrigger")
        except AttributeError:
            pass

    def set_trigger_type(self, trigger_type):
        """トリガータイプを設定"""
        self.trigger_type = trigger_type
        if self.running:
            self.stop_listening()
            self.start_listening()

    def manual_trigger(self):
        """手動トリガーの実行"""
        if self.running:
            self.trigger_queue.put("ManualTrigger")

    def get_trigger(self):
        """トリガーイベントを取得"""
        try:
            return self.trigger_queue.get_nowait()
        except queue.Empty:
            return None
