import threading
import queue
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable
import json

from pynput import keyboard
try:
    from gpiozero import Button, Device
    from gpiozero.pins.mock import MockFactory # For testing on non-Pi systems if needed
    # Attempt to set the default pin factory. This will fail if not on a Pi or if gpiozero isn't properly configured.
    try:
        Device.pin_factory
    except Exception:
        # Fallback or specific handling if needed, e.g., MockFactory for testing
        # Device.pin_factory = MockFactory()
        # For production, we assume if this fails, GPIO is not truly available
        raise ImportError("gpiozero pin factory setup failed. Not on RPi or library issue?")
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

from exceptions import TriggerError
from utils import logger, Config

class TriggerEvent:
    def __init__(self, trigger_type: str, source: str, timestamp: float):
        self.type = trigger_type
        self.source = source
        self.timestamp = timestamp

class HttpTriggerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GETリクエストの処理"""
        if self.path == '/status':
            self._handle_status()
        elif self.path == '/trigger':
            self._handle_trigger('GET')
        else:
            self._send_error(404, "エンドポイントが見つかりません")

    def do_POST(self):
        """POSTリクエストの処理"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

        if self.path == '/trigger':
            self._handle_trigger('POST', data)
        elif self.path == '/config':
            self._handle_config(data)
        else:
            self._send_error(404, "エンドポイントが見つかりません")

    def _handle_status(self):
        """ステータス情報を返す"""
        response = {
            'status': 'running',
            'trigger_type': self.server.trigger_manager.trigger_type,
            'uptime': time.time() - self.server.start_time
        }
        self._send_json_response(response)

    def _handle_trigger(self, method, data=None):
        """トリガーイベントを処理"""
        source = f"http_{method.lower()}"
        if data and 'source' in data:
            source = data['source']

        self.server.trigger_queue.put(
            TriggerEvent('http', source, time.time())
        )
        self._send_json_response({'status': 'ok', 'message': 'トリガーを実行しました'})

    def _handle_config(self, data):
        """設定の更新を処理"""
        try:
            # 設定の更新（実装例）
            if 'trigger_type' in data:
                self.server.trigger_manager.set_trigger_type(data['trigger_type'])
            self._send_json_response({'status': 'ok', 'message': '設定を更新しました'})
        except Exception as e:
            self._send_error(400, str(e))

    def _send_json_response(self, data, status=200):
        """JSONレスポンスを送信"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error(self, code, message):
        """エラーレスポンスを送信"""
        self._send_json_response(
            {'status': 'error', 'message': message},
            status=code
        )

    def log_message(self, format, *args):
        """HTTPサーバーのログを抑制（必要に応じてloggerを使用）"""
        logger.debug(f"HTTP: {format%args}")

class WebSocketTrigger:
    def __init__(self, port: int, callback: Callable):
        self.port = port
        self.callback = callback
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.server.bind(('localhost', self.port))
        self.server.listen(1)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.server:
            self.server.close()
        if self.thread:
            self.thread.join(timeout=3.0)

    def _run(self):
        while self.running:
            try:
                client, _ = self.server.accept()
                data = client.recv(1024).decode('utf-8')
                if data.strip() == 'trigger':
                    self.callback(TriggerEvent('websocket', 'client', time.time()))
                client.close()
            except Exception as e:
                if self.running:
                    logger.error(f"WebSocketエラー: {e}")

class TriggerManager:
    def __init__(self, config: Config):
        """
        トリガーマネージャーの初期化
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self.trigger_queue = queue.Queue()
        self._running = False
        self.trigger_type = config.get('trigger', 'default_type')
        
        # 各トリガーのハンドラ
        self.keyboard_listener = None
        self.gpio_button = None # Changed from gpio_pin
        self.http_server = None
        self.websocket_server = None
        
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """トリガーの動作状態を取得"""
        with self._lock:
            return self._running

    def start_listening(self):
        """トリガー入力のリスニングを開始"""
        try:
            with self._lock:
                self._running = True

            if self.trigger_type == 'keyboard':
                self._start_keyboard_listener()
            elif self.trigger_type == 'gpio' and GPIO_AVAILABLE:
                self._start_gpio_listener()
            elif self.trigger_type == 'http':
                self._start_http_listener()
            elif self.trigger_type == 'websocket':
                self._start_websocket_listener()
            else:
                raise TriggerError(f"未対応のトリガータイプ: {self.trigger_type}")

            logger.info(f"トリガー監視を開始: {self.trigger_type}")

        except Exception as e:
            logger.error(f"トリガー監視の開始に失敗: {e}")
            self.stop_listening()
            raise

    def stop_listening(self):
        """トリガー入力のリスニングを停止"""
        with self._lock:
            self._running = False

        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        if self.gpio_button is not None and GPIO_AVAILABLE:
            self.gpio_button.close() # Close the gpiozero device
            self.gpio_button = None

        if self.http_server:
            self.http_server.shutdown()
            self.http_server = None

        if self.websocket_server:
            self.websocket_server.stop()
            self.websocket_server = None

        logger.info("トリガー監視を停止")

    def set_trigger_type(self, trigger_type: str):
        """トリガータイプを設定"""
        if trigger_type not in self.config.get('trigger', 'available_types'):
            raise TriggerError(f"未対応のトリガータイプ: {trigger_type}")
        
        was_running = self.running
        if was_running:
            self.stop_listening()
        
        self.trigger_type = trigger_type
        
        if was_running:
            self.start_listening()

    def manual_trigger(self):
        """手動トリガーの実行"""
        if self.running:
            self.trigger_queue.put(
                TriggerEvent('manual', 'button', time.time())
            )
            logger.info("手動トリガーを実行")

    def get_trigger(self) -> Optional[TriggerEvent]:
        """トリガーイベントを取得"""
        try:
            return self.trigger_queue.get_nowait()
        except queue.Empty:
            return None

    def _start_keyboard_listener(self):
        """キーボードリスナーの開始"""
        def on_press(key):
            if key == keyboard.Key.space and self.running:
                self.trigger_queue.put(
                    TriggerEvent('keyboard', 'space', time.time())
                )
                logger.debug("キーボードトリガーを検知")

        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

    def _start_gpio_listener(self):
        """GPIOリスナーの開始 (gpiozero版)"""
        if not GPIO_AVAILABLE:
            raise TriggerError("GPIO機能は利用できません (gpiozeroが見つからないか、RPi以外で実行されています)")

        gpio_pin_number = self.config.get('trigger', 'gpio_pin')
        
        try:
            # pull_up=True is the default for Button, equivalent to PUD_UP
            # bounce_time is in seconds for gpiozero
            self.gpio_button = Button(gpio_pin_number, pull_up=True, bounce_time=0.2)

            def gpio_pressed():
                if self.running:
                    self.trigger_queue.put(
                        TriggerEvent('gpio', f'pin{gpio_pin_number}', time.time())
                    )
                    logger.debug(f"GPIOトリガーを検知 (gpiozero): pin{gpio_pin_number}")

            # Trigger when the button is pressed (falling edge due to pull-up)
            self.gpio_button.when_pressed = gpio_pressed
            logger.info(f"GPIOリスナーを開始 (gpiozero): pin={gpio_pin_number}")

        except Exception as e:
            raise TriggerError(f"GPIOピン {gpio_pin_number} の初期化に失敗: {e}")

    def _start_http_listener(self):
        """HTTPリスナーの開始"""
        port = self.config.get('trigger', 'http_port')
        server = HTTPServer(('0.0.0.0', port), HttpTriggerHandler)
        server.trigger_queue = self.trigger_queue
        server.trigger_manager = self
        server.start_time = time.time()
        self.http_server = server
        
        threading.Thread(
            target=server.serve_forever,
            daemon=True
        ).start()
        
        logger.info(f"HTTPサーバーを起動: port={port}")

    def _start_websocket_listener(self):
        """WebSocketリスナーの開始"""
        def on_trigger(event):
            if self.running:
                self.trigger_queue.put(event)
                logger.debug("WebSocketトリガーを検知")

        port = self.config.get('trigger', 'websocket_port')
        self.websocket_server = WebSocketTrigger(port, on_trigger)
        self.websocket_server.start()
