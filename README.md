# PyDriveRecorder

USBカメラを使用して、トリガー入力の前後数十秒の動画を保存するPythonプログラムです。

## 機能

- USBカメラからのリアルタイム映像キャプチャ
- 複数のトリガー入力方式をサポート
  - キーボード入力
  - GPIO（Raspberry Pi環境のみ）
  - HTTPリクエスト
  - WebSocket
- トリガー前後の動画を保存（1-30秒の範囲で設定可能）
- GUIによる簡単な操作
  - カメラのプレビュー表示
  - トリガー方式の選択
  - 録画時間の設定
  - 保存先の指定

## 必要要件

- Python 3.7以上
- USB対応カメラ
- （オプション）Raspberry Pi（GPIO機能を使用する場合）

## インストール

1. リポジトリをクローン
```bash
git clone https://github.com/Mioooon/PyDriveRecorder.git
cd PyDriveRecorder
```

2. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

## 使用方法

1. プログラムの起動
```bash
python main.py
```

2. GUI操作
- トリガー方式を選択（キーボード、GPIO、HTTP、WebSocket）
- トリガー前後の録画時間を設定（1-30秒）
- 保存先ディレクトリを指定
- 「開始」ボタンをクリックして録画を開始

3. トリガー入力
- キーボード: スペースキーで録画トリガー
- GPIO: 指定したピンの入力で録画トリガー
- HTTP: `http://localhost:8080/trigger` にPOSTリクエストで録画トリガー
- WebSocket: 指定したポートに接続して録画トリガー

4. 録画の停止
- 「停止」ボタンをクリックして録画を終了

## ファイル構成

- `main.py`: メインプログラム
- `gui_manager.py`: GUI管理
- `video_manager.py`: ビデオキャプチャと保存
- `trigger_manager.py`: トリガー入力の管理
- `requirements.txt`: 必要なPythonパッケージ

## 注意事項

- カメラのドライバーが正しくインストールされていることを確認してください
- GPIOを使用する場合は、Raspberry Pi環境が必要です
- 保存先ディレクトリに書き込み権限があることを確認してください

## ライセンス

MITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。
