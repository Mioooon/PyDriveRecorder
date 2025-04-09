import threading
import queue
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable
import json

from pynput import keyboard

# Try importing GPIO libraries
try:
    from gpiozero import Button, Device
    # Attempt to set the default pin factory. This might fail if not on a Pi.
    try:
        Device.pin_factory # Accessing this property initializes the default factory
        GPIOZERO_AVAILABLE = True
        logger.debug("gpiozero library is available.")
    except Exception as e:
        logger.debug(f"gpiozero pin factory setup failed, likely not on RPi or config issue: {e}")
        GPIOZERO_AVAILABLE = False
except ImportError:
    GPIOZERO_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    RPIGPIO_AVAILABLE = True
    logger.debug("RPi.GPIO library is available.")
except ImportError:
    RPIGPIO_AVAILABLE = False

# Overall GPIO availability check
GPIO_AVAILABLE = GPIOZERO_AVAILABLE or RPIGPIO_AVAILABLE

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
        self.gpio_library_preference = config.get('trigger', 'gpio_library', 'auto').lower() # Read library preference
        
        # 各トリガーのハンドラ
        self.keyboard_listener = None
        self.active_gpio_handler = None # Holds the active GPIO object (Button or pin number)
        self.active_gpio_library = None # Stores 'gpiozero' or 'rpigpio'
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
            elif self.trigger_type == 'gpio':
                # GPIO listener start now depends on library availability and preference
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

        # Cleanup based on the active GPIO library
        if self.active_gpio_handler is not None:
            if self.active_gpio_library == 'gpiozero' and GPIOZERO_AVAILABLE:
                try:
                    self.active_gpio_handler.close()
                    logger.debug("Closed gpiozero handler.")
                except Exception as e:
                    logger.error(f"Error closing gpiozero handler: {e}")
            elif self.active_gpio_library == 'rpigpio' and RPIGPIO_AVAILABLE:
                try:
                    # RPi.GPIO cleans up all channels used by the script unless specific channels are passed
                    GPIO.cleanup()
                    logger.debug("Cleaned up RPi.GPIO.")
                except Exception as e:
                    logger.error(f"Error cleaning up RPi.GPIO: {e}")
            self.active_gpio_handler = None
            self.active_gpio_library = None

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
        """GPIOリスナーの開始 (ライブラリ自動選択対応)"""
        if not GPIO_AVAILABLE:
            raise TriggerError("利用可能なGPIOライブラリが見つかりません。")

        gpio_pin_number = self.config.get('trigger', 'gpio_pin')
        library_to_use = None

        # Determine which library to use based on preference and availability
        if self.gpio_library_preference == 'gpiozero' and GPIOZERO_AVAILABLE:
            library_to_use = 'gpiozero'
        elif self.gpio_library_preference == 'rpigpio' and RPIGPIO_AVAILABLE:
            library_to_use = 'rpigpio'
        elif self.gpio_library_preference == 'auto':
            if GPIOZERO_AVAILABLE:
                library_to_use = 'gpiozero'
            elif RPIGPIO_AVAILABLE:
                library_to_use = 'rpigpio'

        if not library_to_use:
            raise TriggerError(f"要求されたGPIOライブラリ '{self.gpio_library_preference}' が利用できないか、'auto' で利用可能なライブラリがありません。")

        # Initialize the chosen library
        try:
            if library_to_use == 'gpiozero':
                self._initialize_gpiozero(gpio_pin_number)
            elif library_to_use == 'rpigpio':
                self._initialize_rpigpio(gpio_pin_number)
            self.active_gpio_library = library_to_use
            logger.info(f"GPIOリスナーを開始 ({library_to_use}): pin={gpio_pin_number}")
        except Exception as e:
            self.active_gpio_library = None # Ensure state is clean on failure
            raise TriggerError(f"GPIOピン {gpio_pin_number} の初期化に失敗 ({library_to_use}): {e}")

    def _initialize_gpiozero(self, pin_number):
        """gpiozeroライブラリを使用してGPIOを初期化"""
        # pull_up=True is the default for Button, equivalent to PUD_UP
        # bounce_time is in seconds for gpiozero
        button = Button(pin_number, pull_up=True, bounce_time=0.2)

        def gpio_pressed():
            if self.running:
                self.trigger_queue.put(
                    TriggerEvent('gpio', f'pin{pin_number}', time.time())
                )
                logger.debug(f"GPIOトリガーを検知 (gpiozero): pin{pin_number}")

        button.when_pressed = gpio_pressed
        self.active_gpio_handler = button # Store the Button object

    def _initialize_rpigpio(self, pin_number):
        """RPi.GPIOライブラリを使用してGPIOを初期化"""
        GPIO.setmode(GPIO.BCM)
        # Setup with pull-up resistor
        GPIO.setup(pin_number, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        def gpio_callback(channel):
            # Check if still running and if the event is for the correct pin
            if self.running and channel == pin_number:
                 # Add a small delay to debounce manually if needed, though bouncetime helps
                time.sleep(0.05)
                # Re-check the pin state to confirm it's low (pressed)
                if GPIO.input(channel) == GPIO.LOW:
                    self.trigger_queue.put(
                        TriggerEvent('gpio', f'pin{channel}', time.time())
                    )
                    logger.debug(f"GPIOトリガーを検知 (RPi.GPIO): pin{channel}")

        # Detect falling edge (high to low transition due to pull-up)
        GPIO.add_event_detect(
            pin_number,
            GPIO.FALLING,
            callback=gpio_callback,
            bouncetime=200 # milliseconds
        )
        self.active_gpio_handler = pin_number # Store the pin number for cleanup reference

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
