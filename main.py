import tkinter as tk
import threading
import os
from datetime import datetime
from gui_manager import GUIManager
from video_manager import VideoManager
from trigger_manager import TriggerManager

class RecorderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("動画保存プログラム")
        
        # マネージャーの初期化
        self.video_manager = VideoManager()
        self.trigger_manager = TriggerManager()
        self.gui = GUIManager(self.root)
        
        # マネージャーの設定
        self.gui.set_managers(self.video_manager, self.trigger_manager)
        
        # トリガー監視スレッドの初期化
        self.trigger_thread = None
        self.monitoring = False

        # トリガー監視の開始
        self._start_trigger_monitoring()

    def _start_trigger_monitoring(self):
        """トリガー監視を開始"""
        self.monitoring = True
        self.trigger_thread = threading.Thread(
            target=self._monitor_triggers,
            daemon=True
        )
        self.trigger_thread.start()

    def _monitor_triggers(self):
        """トリガーイベントを監視"""
        while self.monitoring:
            trigger = self.trigger_manager.get_trigger()
            if trigger:
                self._handle_trigger()

    def _handle_trigger(self):
        """トリガーイベントの処理"""
        # 保存先ディレクトリの準備
        save_dir = self.gui.save_path.get()
        os.makedirs(save_dir, exist_ok=True)

        # ファイル名の生成（タイムスタンプ使用）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"record_{timestamp}.mp4"
        filepath = os.path.join(save_dir, filename)

        # 動画の保存
        before_time = int(self.gui.before_time.get())
        after_time = int(self.gui.after_time.get())
        
        # GUIのステータス更新
        self.gui.status_var.set(f"トリガー検知: {filename}を保存中...")
        
        # 動画保存
        success = self.video_manager.save_video(
            filepath,
            before_time,
            after_time
        )
        
        # 保存結果に応じてステータス更新
        if success:
            self.gui.status_var.set(f"保存完了: {filename}")
        else:
            self.gui.status_var.set("保存失敗")

    def run(self):
        """アプリケーションの実行"""
        self.root.mainloop()

def main():
    app = RecorderApp()
    app.run()

if __name__ == "__main__":
    main()
