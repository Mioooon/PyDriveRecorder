import tkinter as tk
import threading
import os
import sys
from datetime import datetime

from gui_manager import GUIManager
from video_manager import VideoManager
from trigger_manager import TriggerManager, TriggerEvent
from utils import logger, Config
from exceptions import VideoError, TriggerError, ConfigError

class RecorderApp:
    def __init__(self, config_path: str = None):
        """
        アプリケーションの初期化
        Args:
            config_path: 設定ファイルのパス
        """
        try:
            # 設定の読み込み
            self.config = Config(config_path)
            
            # GUIの初期化
            self.root = tk.Tk()
            self.root.title("動画保存プログラム")
            
            # マネージャーの初期化
            self.video_manager = VideoManager(self.config)
            self.trigger_manager = TriggerManager(self.config)
            self.gui = GUIManager(self.root)
            
            # マネージャーの設定
            self.gui.set_managers(self.video_manager, self.trigger_manager)
            
            # トリガー監視スレッドの初期化
            self.trigger_thread = None
            self.monitoring = False

            # ウィンドウクローズ時のイベントハンドラを設定
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # エラーハンドラの設定
            sys.excepthook = self._handle_exception
            
            # トリガー監視の開始と録画開始
            self._start_trigger_monitoring()
            self.gui._start_recording()
            
            logger.info("アプリケーションを初期化しました")
            
        except ConfigError as e:
            logger.error(f"設定エラー: {e}")
            self._show_error("設定エラー", str(e))
            sys.exit(1)
        except Exception as e:
            logger.error(f"初期化エラー: {e}")
            self._show_error("初期化エラー", str(e))
            sys.exit(1)

    def _start_trigger_monitoring(self):
        """トリガー監視を開始"""
        self.monitoring = True
        self.trigger_thread = threading.Thread(
            target=self._monitor_triggers,
            daemon=True
        )
        self.trigger_thread.start()
        logger.info("トリガー監視を開始")

    def _monitor_triggers(self):
        """トリガーイベントを監視"""
        while self.monitoring:
            try:
                trigger = self.trigger_manager.get_trigger()
                if trigger:
                    self._handle_trigger(trigger)
            except Exception as e:
                logger.error(f"トリガー監視中にエラー: {e}")

    def _handle_trigger(self, trigger: TriggerEvent):
        """
        トリガーイベントの処理
        Args:
            trigger: トリガーイベント
        """
        try:
            # 保存先ディレクトリの準備
            save_dir = self.gui.save_path.get()
            os.makedirs(save_dir, exist_ok=True)

            # ファイル名の生成
            timestamp = datetime.fromtimestamp(trigger.timestamp).strftime("%Y%m%d_%H%M%S")
            filename = f"record_{trigger.type}_{timestamp}.mp4"
            filepath = os.path.join(save_dir, filename)

            # 動画の保存
            before_time = int(self.gui.before_time.get())
            after_time = int(self.gui.after_time.get())
            
            self.gui.status_var.set(f"トリガー検知 ({trigger.type}): {filename}を保存中...")
            logger.info(f"トリガー検知: type={trigger.type}, source={trigger.source}")
            
            success = self.video_manager.save_video(
                filepath,
                before_time,
                after_time
            )
            
            if success:
                self.gui.status_var.set(f"保存完了: {filename}")
                logger.info(f"動画を保存: {filename}")
            else:
                self.gui.status_var.set("保存失敗")
                logger.error("動画の保存に失敗")

        except Exception as e:
            logger.error(f"トリガー処理中にエラー: {e}")
            self.gui.status_var.set(f"エラー: {str(e)}")

    def _on_closing(self):
        """ウィンドウが閉じられる時の処理"""
        try:
            logger.info("アプリケーションを終了します")
            if self.gui:
                self.gui._stop_recording()
            if self.video_manager:
                self.video_manager.stop_capture()
            if self.trigger_manager:
                self.trigger_manager.stop_listening()
                
            self.monitoring = False
            if self.trigger_thread:
                try:
                    self.trigger_thread.join(timeout=3.0)
                except:
                    pass
        finally:
            self.root.quit()
            self.root.destroy()

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """未処理の例外をハンドル"""
        logger.error(
            "未処理の例外が発生:",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        self._show_error("エラー", str(exc_value))

    def _show_error(self, title: str, message: str):
        """エラーダイアログを表示"""
        if hasattr(self, 'root') and self.root:
            tk.messagebox.showerror(title, message)

    def run(self):
        """アプリケーションの実行"""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"実行時エラー: {e}")
            self._show_error("実行時エラー", str(e))

def main():
    try:
        # デフォルトの設定ファイルパス
        default_config = os.path.join(os.path.dirname(__file__), 'config.yaml')
        # 環境変数で上書き可能
        config_path = os.environ.get('RECORDER_CONFIG', default_config)
        
        if not os.path.exists(config_path):
            logger.warning(f"設定ファイルが見つかりません: {config_path}")
            config_path = None
            
        app = RecorderApp(config_path)
        app.run()
    except Exception as e:
        logger.error(f"アプリケーションエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
