import tkinter as tk
from tkinter import ttk, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import os
import time

class GUIManager:
    def __init__(self, root):
        self.root = root
        self.root.geometry("800x600")
        
        # ビデオマネージャーとトリガーマネージャーの参照（後で設定）
        self.video_manager = None
        self.trigger_manager = None
        
        # GUI要素の初期化
        self._init_gui()
        
        # プレビュー更新用の変数
        self.preview_running = False
        self.preview_thread = None

    def _init_gui(self):
        """GUI要素の初期化"""
        # メインフレームの作成
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左側のコントロールパネル
        self.control_frame = ttk.LabelFrame(self.main_frame, text="設定")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # カメラ設定
        self.camera_frame = ttk.LabelFrame(self.control_frame, text="カメラ設定")
        self.camera_frame.pack(fill=tk.X, padx=5, pady=5)

        self.camera_id = tk.StringVar(value="0")
        ttk.Label(self.camera_frame, text="カメラ番号:").pack(side=tk.LEFT, padx=5, pady=2)
        self.camera_combo = ttk.Combobox(
            self.camera_frame,
            textvariable=self.camera_id,
            values=["0", "1", "2", "3"],
            width=5,
            state="readonly"
        )
        self.camera_combo.bind('<<ComboboxSelected>>', self._on_camera_change)
        self.camera_combo.pack(side=tk.LEFT, padx=5, pady=2)

        # トリガー設定
        self.trigger_frame = ttk.LabelFrame(self.control_frame, text="トリガー設定")
        self.trigger_frame.pack(fill=tk.X, padx=5, pady=5)

        self.trigger_type = tk.StringVar(value="keyboard")
        # プラットフォームに応じてトリガーオプションを設定
        triggers = [("キーボード", "keyboard")]
        
        # LinuxでのみGPIOを有効化
        if os.name == 'posix':
            triggers.append(("GPIO", "gpio"))
            
        # その他のトリガー
        triggers.extend([
            ("HTTP", "http"),
            ("WebSocket", "websocket")
        ])
        
        for text, value in triggers:
            ttk.Radiobutton(
                self.trigger_frame,
                text=text,
                value=value,
                variable=self.trigger_type,
                command=self._on_trigger_type_change
            ).pack(anchor=tk.W, padx=5, pady=2)

        # 録画時間設定
        self.time_frame = ttk.LabelFrame(self.control_frame, text="録画時間設定")
        self.time_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.time_frame, text="トリガー前（秒）:").pack(anchor=tk.W, padx=5, pady=2)
        before_frame = ttk.Frame(self.time_frame)
        before_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(before_frame, text="トリガー前:").pack(side=tk.LEFT, padx=5)
        self.before_time = ttk.Scale(
            before_frame,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL
        )
        self.before_time.set(5)
        self.before_time.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.before_time_label = ttk.Label(before_frame, text="5秒")
        self.before_time_label.pack(side=tk.LEFT, padx=5)
        self.before_time.configure(command=self._on_before_time_change)

        after_frame = ttk.Frame(self.time_frame)
        after_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(after_frame, text="トリガー後:").pack(side=tk.LEFT, padx=5)
        self.after_time = ttk.Scale(
            after_frame,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL
        )
        self.after_time.set(5)
        self.after_time.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.after_time_label = ttk.Label(after_frame, text="5秒")
        self.after_time_label.pack(side=tk.LEFT, padx=5)
        self.after_time.configure(command=self._on_after_time_change)

        # 保存先設定
        self.save_frame = ttk.LabelFrame(self.control_frame, text="保存先設定")
        self.save_frame.pack(fill=tk.X, padx=5, pady=5)

        self.save_path = tk.StringVar(value=os.path.join(os.getcwd(), "videos"))
        ttk.Entry(self.save_frame, textvariable=self.save_path).pack(
            fill=tk.X, padx=5, pady=2
        )
        ttk.Button(
            self.save_frame,
            text="参照",
            command=self._browse_save_path
        ).pack(anchor=tk.E, padx=5, pady=2)

        # 操作ボタン
        self.button_frame = ttk.Frame(self.control_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.trigger_button = ttk.Button(
            self.button_frame,
            text="トリガー実行",
            command=self._manual_trigger
        )
        self.trigger_button.pack(side=tk.LEFT, padx=5)

        # 右側のプレビューパネル
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="カメラプレビュー")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_label = ttk.Label(self.preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # ウィンドウリサイズイベントの設定
        self.root.bind('<Configure>', self._on_window_resize)

        # ステータス表示
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=5, pady=2)

    def _browse_save_path(self):
        """保存先ディレクトリの選択"""
        path = filedialog.askdirectory()
        if path:
            self.save_path.set(path)

    def _start_recording(self):
        """録画開始（内部メソッド）"""
        if self.video_manager and self.trigger_manager:
            # 保存先ディレクトリの作成
            os.makedirs(self.save_path.get(), exist_ok=True)
            
            # マネージャーの開始
            camera_id = int(self.camera_id.get())
            if self.video_manager.start_capture(device_id=camera_id):
                self.trigger_manager.start_listening()
                
                # プレビューの開始
                self.preview_running = True
                self.preview_thread = threading.Thread(
                    target=self._update_preview,
                    daemon=True
                )
                self.preview_thread.start()
                
                self.status_var.set("録画中 - トリガー待機")
            else:
                self.status_var.set(f"エラー: カメラ {camera_id} を開けませんでした")

    def _stop_recording(self):
        """録画停止（内部メソッド）"""
        if self.video_manager and self.trigger_manager:
            # マネージャーの停止
            self.video_manager.stop_capture()
            self.trigger_manager.stop_listening()
            
            # プレビューの停止
            self.preview_running = False
            if self.preview_thread:
                try:
                    # 最大3秒待機
                    self.preview_thread.join(timeout=3.0)
                except:
                    pass
            
            self.status_var.set("終了処理中...")

    def _update_preview(self):
        """プレビュー画像の更新"""
        while self.preview_running:
            if self.video_manager:
                # フレームレートを制限（約30fps）
                time.sleep(0.033)
                frame = self.video_manager.get_current_frame()
                if frame is not None:
                    # OpenCVのBGR形式からRGB形式に変換
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # PILイメージに変換
                    image = Image.fromarray(frame_rgb)
                    # プレビューウィンドウに合わせてリサイズ
                    preview_width = max(100, self.preview_frame.winfo_width() - 10)
                    preview_height = max(100, self.preview_frame.winfo_height() - 10)
                    
                    # アスペクト比を維持しながらリサイズ
                    image_ratio = image.width / image.height
                    preview_ratio = preview_width / preview_height
                    
                    if image_ratio > preview_ratio:
                        # 画像が横長の場合
                        new_width = preview_width
                        new_height = int(preview_width / image_ratio)
                    else:
                        # 画像が縦長の場合
                        new_height = preview_height
                        new_width = int(preview_height * image_ratio)
                    
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # Tkinter用のイメージに変換
                    photo = ImageTk.PhotoImage(image=image)
                    # プレビューの更新
                    self.preview_label.config(image=photo)
                    self.preview_label.image = photo  # ガベージコレクション対策

    def _on_trigger_type_change(self):
        """トリガータイプが変更された時の処理"""
        if self.trigger_manager:
            self.trigger_manager.set_trigger_type(self.trigger_type.get())

    def _on_camera_change(self, event=None):
        """カメラ番号が変更された時の処理"""
        if self.video_manager and self.video_manager.running:
            # 現在のカメラを停止
            self.video_manager.stop_capture()
            # 新しいカメラで再起動
            camera_id = int(self.camera_id.get())
            success = self.video_manager.start_capture(device_id=camera_id)
            if not success:
                self.status_var.set(f"カメラ {camera_id} の起動に失敗しました")
                # 失敗した場合は録画を停止
                self._stop_recording()
            else:
                self.status_var.set(f"カメラ {camera_id} に切り替えました")

    def _manual_trigger(self):
        """手動トリガーボタンが押された時の処理"""
        if self.trigger_manager:
            self.trigger_manager.manual_trigger()
            self.status_var.set("手動トリガーが実行されました")

    def _on_window_resize(self, event=None):
        """ウィンドウがリサイズされた時のイベントハンドラ"""
        if hasattr(self, 'preview_frame'):
            self.preview_frame.update()

    def _on_before_time_change(self, value):
        """トリガー前の時間が変更された時の処理"""
        self.before_time_label.configure(text=f"{int(float(value))}秒")

    def _on_after_time_change(self, value):
        """トリガー後の時間が変更された時の処理"""
        self.after_time_label.configure(text=f"{int(float(value))}秒")

    def set_managers(self, video_manager, trigger_manager):
        """マネージャーの設定"""
        self.video_manager = video_manager
        self.trigger_manager = trigger_manager
        # 初期トリガータイプを設定
        self.trigger_manager.set_trigger_type(self.trigger_type.get())
