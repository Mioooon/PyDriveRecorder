# PyDriveRecorder

自動車のドライブレコーダーのように、トリガー前後の映像を保存するプログラムです。

## 特徴
- トリガー前後の映像を自動保存
- マルチトリガー対応（キーボード、HTTP、WebSocket、GPIO）
- カスタマイズ可能な設定
- リアルタイムプレビュー
- プラットフォーム非依存（一部機能を除く）

## 必要要件
- Python 3.7以上
- OpenCV 4.5.0以上
- 依存パッケージ（requirements.txtを参照）
  - Raspberry PiでGPIOトリガーを使用する場合、`gpiozero`が必要です。
- Webカメラまたはビデオキャプチャデバイス

## インストール方法

1. リポジトリをクローン
```bash
git clone https://github.com/Mioooon/PyDriveRecorder.git
cd PyDriveRecorder
```

2. 仮想環境の作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate     # Windows
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

## 基本的な使い方

1. プログラムの起動
```bash
python main.py

# 設定ファイルを指定して起動
RECORDER_CONFIG=/path/to/config.yaml python main.py
```

2. GUI操作
   - トリガー方式を選択
   - トリガー前後の録画時間を設定
   - 保存先ディレクトリを指定
   - カメラのプレビューを確認

## 機能リファレンス

### トリガー機能

1. キーボードトリガー
   - 方式: keyboard
   - 入力: スペースキー
   - 用途: 手動でのトリガー入力

2. HTTP トリガー
   ```bash
   # ステータス確認
   GET http://localhost:8080/status
   Response: {
       "status": "running",
       "trigger_type": "http",
       "uptime": 3600.5
   }

   # トリガー実行（GET）
   GET http://localhost:8080/trigger

   # トリガー実行（POST）
   POST http://localhost:8080/trigger
   Content-Type: application/json
   {
       "source": "external_device"
   }

   # 設定更新
   POST http://localhost:8080/config
   Content-Type: application/json
   {
       "trigger_type": "keyboard"
   }
   ```

3. WebSocket トリガー
   ```python
   import socket

   def send_trigger():
       client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       try:
           client.connect(('localhost', 8081))
           client.send('trigger'.encode('utf-8'))
       finally:
           client.close()
   ```

4. GPIO トリガー（Raspberry Piのみ）
   - `gpiozero`ライブラリを使用
   - デフォルト: GPIO 17 (BCMピン番号)
   - 内部プルアップ抵抗を使用
   - ボタンが押されたとき（ピンがLOWになったとき）にトリガー

### 設定ファイル（config.yaml）

```yaml
camera:
  default_device: 0        # カメラデバイス番号
  frame_width: 640        # フレーム幅
  frame_height: 480       # フレーム高さ
  fps: 30                 # フレームレート

recording:
  default_before_time: 5  # トリガー前の秒数
  default_after_time: 5   # トリガー後の秒数
  max_time: 30           # 最大録画時間
  min_time: 1            # 最小録画時間

trigger:
  default_type: keyboard  # デフォルトのトリガー
  http_port: 8080        # HTTPサーバーポート
  websocket_port: 8081   # WebSocketサーバーポート
  gpio_pin: 17           # GPIOピン番号

buffer:
  max_size_mb: 1024      # 最大バッファサイズ（MB）
  compression_quality: 90 # JPEG圧縮品質（1-100）
```

### GUI機能

1. カメラ設定
   - カメラ番号選択（0-3）
   - プレビュー表示
   - 自動再接続機能

2. トリガー設定
   - トリガー方式選択
   - 手動トリガーボタン
   - トリガー状態表示

3. 録画設定
   - トリガー前録画時間（1-30秒）
   - トリガー後録画時間（1-30秒）
   - リアルタイム秒数表示

4. 保存設定
   - 保存先ディレクトリ指定
   - 自動ディレクトリ作成
   - ファイル名: record_YYYYMMDD_HHMMSS.mp4

## プログラム構成

### モジュール説明
```
PyDriveRecorder/
├── main.py           # メインプログラム
├── gui_manager.py    # GUI管理
├── video_manager.py  # ビデオ処理
├── trigger_manager.py # トリガー管理
├── utils.py         # ユーティリティ
├── exceptions.py    # 例外定義
├── config.yaml      # 設定ファイル
└── requirements.txt # 依存パッケージ
```

### エラー処理
各種例外クラスによるエラー管理：
- `VideoError`: ビデオ関連エラー
- `CameraError`: カメラ関連エラー
- `TriggerError`: トリガー関連エラー
- `ConfigError`: 設定関連エラー
- `ResourceError`: リソース関連エラー

## 注意事項

1. 性能考慮事項
   - メモリ使用量はバッファサイズで制御
   - CPU使用率はフレームレートで最適化
   - ディスク容量の自動管理なし

2. セキュリティ
   - HTTP/WebSocketは認証なし
   - ローカルホスト接続のみ推奨
   - ファイルパスの検証あり

3. 制限事項
   - GPIOトリガーは`gpiozero`がインストールされたRaspberry Piのみ対応
   - 音声録音未対応
   - 一部のUSBカメラで切り替え遅延あり
   - 長時間の連続録画は非推奨

## ライセンス
MIT License

## 開発・貢献

1. バグ報告
   - GitHub Issuesにて受付
   - 再現手順の記載をお願いします

2. 機能要望
   - GitHub Issuesにて受付
   - 具体的な使用例の記載をお願いします

3. プルリクエスト
   - フォークして変更を加えてください
   - テストを追加してください
   - プルリクエストを送信してください

---

# PyDriveRecorder (English)

A program that saves video before and after triggers, similar to a car's drive recorder.

## Features
- Automatic video saving before and after triggers
- Multi-trigger support (Keyboard, HTTP, WebSocket, GPIO)
- Customizable settings
- Real-time preview
- Platform independent (except for some features)

## Requirements
- Python 3.7 or higher
- OpenCV 4.5.0 or higher
- Dependencies (see requirements.txt)
  - Requires `gpiozero` for GPIO trigger on Raspberry Pi.
- Webcam or video capture device

## Installation

1. Clone the repository
```bash
git clone https://github.com/Mioooon/PyDriveRecorder.git
cd PyDriveRecorder
```

2. Create virtual environment (recommended)
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Basic Usage

1. Launch the program
```bash
python main.py

# Launch with custom config file
RECORDER_CONFIG=/path/to/config.yaml python main.py
```

2. GUI Operation
   - Select trigger method
   - Set recording time before/after trigger
   - Specify save directory
   - Check camera preview

## Function Reference

### Trigger Features

1. Keyboard Trigger
   - Method: keyboard
   - Input: Space key
   - Usage: Manual trigger input

2. HTTP Trigger
   ```bash
   # Check status
   GET http://localhost:8080/status
   Response: {
       "status": "running",
       "trigger_type": "http",
       "uptime": 3600.5
   }

   # Execute trigger (GET)
   GET http://localhost:8080/trigger

   # Execute trigger (POST)
   POST http://localhost:8080/trigger
   Content-Type: application/json
   {
       "source": "external_device"
   }

   # Update settings
   POST http://localhost:8080/config
   Content-Type: application/json
   {
       "trigger_type": "keyboard"
   }
   ```

3. WebSocket Trigger
   ```python
   import socket

   def send_trigger():
       client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       try:
           client.connect(('localhost', 8081))
           client.send('trigger'.encode('utf-8'))
       finally:
           client.close()
   ```

4. GPIO Trigger (Raspberry Pi only)
   - Uses the `gpiozero` library
   - Default: GPIO 17 (BCM pin number)
   - Uses internal pull-up resistor
   - Triggers when the button is pressed (pin goes LOW)

### Configuration File (config.yaml)

```yaml
camera:
  default_device: 0        # Camera device number
  frame_width: 640        # Frame width
  frame_height: 480       # Frame height
  fps: 30                 # Frame rate

recording:
  default_before_time: 5  # Seconds before trigger
  default_after_time: 5   # Seconds after trigger
  max_time: 30           # Maximum recording time
  min_time: 1            # Minimum recording time

trigger:
  default_type: keyboard  # Default trigger type
  http_port: 8080        # HTTP server port
  websocket_port: 8081   # WebSocket server port
  gpio_pin: 17           # GPIO pin number

buffer:
  max_size_mb: 1024      # Maximum buffer size (MB)
  compression_quality: 90 # JPEG compression quality (1-100)
```

### GUI Features

1. Camera Settings
   - Camera number selection (0-3)
   - Preview display
   - Auto-reconnection feature

2. Trigger Settings
   - Trigger method selection
   - Manual trigger button
   - Trigger status display

3. Recording Settings
   - Pre-trigger time (1-30 seconds)
   - Post-trigger time (1-30 seconds)
   - Real-time second display

4. Save Settings
   - Save directory specification
   - Automatic directory creation
   - Filename: record_YYYYMMDD_HHMMSS.mp4

## Program Structure

### Module Description
```
PyDriveRecorder/
├── main.py           # Main program
├── gui_manager.py    # GUI management
├── video_manager.py  # Video processing
├── trigger_manager.py # Trigger management
├── utils.py         # Utilities
├── exceptions.py    # Exception definitions
├── config.yaml      # Configuration file
└── requirements.txt # Dependencies
```

### Error Handling
Various exception classes for error management:
- `VideoError`: Video-related errors
- `CameraError`: Camera-related errors
- `TriggerError`: Trigger-related errors
- `ConfigError`: Configuration-related errors
- `ResourceError`: Resource-related errors

## Notes

1. Performance Considerations
   - Memory usage controlled by buffer size
   - CPU usage optimized by frame rate
   - No automatic disk space management

2. Security
   - No authentication for HTTP/WebSocket
   - Localhost connections recommended
   - File path validation included

3. Limitations
   - GPIO trigger only supported on Raspberry Pi with `gpiozero` installed.
   - No audio recording
   - Some USB cameras may have switching delays
   - Long continuous recording not recommended

## License
MIT License

## Development & Contribution

1. Bug Reports
   - Submit via GitHub Issues
   - Please include reproduction steps

2. Feature Requests
   - Submit via GitHub Issues
   - Please include specific use cases

3. Pull Requests
   - Fork and make changes
   - Add tests
   - Submit pull request
