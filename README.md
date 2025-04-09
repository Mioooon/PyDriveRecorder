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
   - BCMモードで動作
   - デフォルト: GPIO 17
   - プルアップ抵抗使用
   - 立ち下がりエッジでトリガー

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
   - GPIOはRaspberry Piのみ対応
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

[英語版は日本語版と同じ構成で続きます...]
