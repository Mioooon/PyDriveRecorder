import tkinter as tk
from tkinter import ttk, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import os

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
        triggers = [
            ("キーボード", "keyboard"),
            ("GPIO", "gpio"),
            ("HTTP", "http"),
            ("WebSocket", "websocket")
        ]
        
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
        self.before_time = ttk.Scale(
            self.time_frame,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL
        )
        self.before_time.set(5)
        self.before_time.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(self.time_frame, text="トリガー後（秒）:").pack(anchor=tk.W, padx=5, pady=2)
        self.after_time = ttk.Scale(
            self.time_frame,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL
        )
        self.after_time.set(5)
        self.after_time.pack(fill=tk.X, padx=5, pady=2)

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

        self.start_button = ttk.Button(
            self.button_frame,
            text="開始",
            command=self._start_recording
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            self.button_frame,
            text="停止",
            command=self._stop_recording,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.trigger_button = ttk.Button(
            self.button_frame,
            text="トリガー",
            command=self._manual_trigger,
            state=tk.DISABLED
        )
        self.trigger_button.pack(side=tk.LEFT, padx=5)

        # 右側のプレビューパネル
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="カメラプレビュー")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_label = ttk.Label(self.preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

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
        """録画開始"""
        if self.video_manager and self.trigger_manager:
            # ボタンの状態を更新
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.trigger_button.config(state=tk.NORMAL)
            
            # 保存先ディレクトリの作成
            os.makedirs(self.save_path.get(), exist_ok=True)
            
            # マネージャーの開始
            camera_id = int(self.camera_id.get())
            self.video_manager.start_capture(device_id=camera_id)
            self.trigger_manager.start_listening()
            
            # プレビューの開始
            self.preview_running = True
            self.preview_thread = threading.Thread(
                target=self._update_preview,
                daemon=True
            )
            self.preview_thread.start()
            
            self.status_var.set("録画中")

    def _stop_recording(self):
        """録画停止"""
        if self.video_manager and self.trigger_manager:
            # マネージャーの停止
            self.video_manager.stop_capture()
            self.trigger_manager.stop_listening()
            
            # プレビューの停止
            self.preview_running = False
            if self.preview_thread:
                self.preview_thread.join()
            
            # ボタンの状態を更新
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.trigger_button.config(state=tk.DISABLED)
            
            self.status_var.set("待機中")

    def _update_preview(self):
        """プレビュー画像の更新"""
        while self.preview_running:
            if self.video_manager:
                frame = self.video_manager.get_current_frame()
                if frame is not None:
                    # OpenCVのBGR形式からRGB形式に変換
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # PILイメージに変換
                    image = Image.fromarray(frame_rgb)
                    # プレビューウィンドウに合わせてリサイズ
                    preview_width = self.preview_frame.winfo_width() - 10
                    preview_height = self.preview_frame.winfo_height() - 10
                    image.thumbnail((preview_width, preview_height), Image.LANCZOS)
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

    def set_managers(self, video_manager, trigger_manager):
        """マネージャーの設定"""
        self.video_manager = video_manager
        self.trigger_manager = trigger_manager
        # 初期トリガータイプを設定
        self.trigger_manager.set_trigger_type(self.trigger_type.get())
