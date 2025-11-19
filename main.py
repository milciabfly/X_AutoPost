"""
X_AutoPost - Twitter自動投稿アプリケーション
メインエントリーポイント
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import random
import os
import re

from util.auth import get_client
from util.post_v2 import post
from util.config import load_config, save_config
from util.ui import EditPopup
from util.openai_helper import compose_with_openai


class AutoPosterApp:
    """自動ツイート投稿アプリケーションのメインクラス"""
    
    def __init__(self, root):
        self.root = root
        root.title("X AutoPost - 自動ツイート")
        self.cfg = load_config()
        if not self.cfg:
            # 初期構成
            self.cfg = {
                "tweets": [], 
                "delay_hours": 1, 
                "openai": {"enabled": False, "position": "after", "chars": 50, "prompt": ""}, 
                "external_link_warned": False
            }

        self.stop_event = threading.Event()
        self.poster_thread = None

        self._build_ui()
        self.refresh_slots()

    def _build_ui(self):
        """UI構築"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # 左側: ツイートスロット管理
        left = ttk.Frame(main_frame)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="ツイートスロット").pack()
        self.slot_listbox = tk.Listbox(left, height=12)
        self.slot_listbox.pack()
        slot_btns = ttk.Frame(left)
        slot_btns.pack(fill="x")
        ttk.Button(slot_btns, text="+", width=3, command=self.add_slot).pack(side="left")
        ttk.Button(slot_btns, text="-", width=3, command=self.remove_slot).pack(side="left")
        ttk.Button(slot_btns, text="編集", command=self.edit_slot).pack(side="left")

        # 中央: 設定エリア
        mid = ttk.Frame(main_frame, padding=(10, 0))
        mid.pack(side="left", fill="both", expand=True)

        # 投稿間隔設定
        ttk.Label(mid, text="delay (hours, 1-120):").grid(row=0, column=0, sticky="w")
        self.delay_var = tk.IntVar(value=self.cfg.get("delay_hours", 1))
        self.delay_spin = ttk.Spinbox(mid, from_=1, to=120, textvariable=self.delay_var, width=6)
        self.delay_spin.grid(row=0, column=1, sticky="w")

        # OpenAI設定
        self._build_openai_ui(mid)

        # ログ表示エリア
        ttk.Label(mid, text="ログ: ").grid(row=7, column=0, sticky="w")
        self.log_text = scrolledtext.ScrolledText(mid, width=60, height=12)
        self.log_text.grid(row=8, column=0, columnspan=3)

        # 右側: コントロールボタン
        ctrl = ttk.Frame(main_frame)
        ctrl.pack(side="right", fill="y")
        ttk.Button(ctrl, text="自動ツイート開始", command=self.start_auto).pack(fill="x", pady=4)
        ttk.Button(ctrl, text="停止", command=self.stop_auto).pack(fill="x", pady=4)
        ttk.Button(ctrl, text="保存", command=self.save_all).pack(fill="x", pady=4)
        ttk.Button(ctrl, text="テストツイート", command=self.test_post).pack(fill="x", pady=4)

    def _build_openai_ui(self, parent):
        """OpenAI関連のUI構築"""
        self.openai_api = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")
        ttk.Label(parent, text="OpenAI: ").grid(row=1, column=0, sticky="w")
        self.openai_enabled_var = tk.BooleanVar(
            value=self.cfg.get("openai", {}).get("enabled", False) and bool(self.openai_api)
        )
        self.openai_check = ttk.Checkbutton(
            parent, text="有効", 
            variable=self.openai_enabled_var, 
            command=self._on_openai_toggle
        )
        self.openai_check.grid(row=1, column=1, sticky="w")
        if not self.openai_api:
            self.openai_check.state(["disabled"])

        # 追加位置選択
        ttk.Label(parent, text="追加位置:").grid(row=2, column=0, sticky="w")
        self.openai_pos = tk.StringVar(value=self.cfg.get("openai", {}).get("position", "after"))
        self.openai_pos_after = ttk.Radiobutton(
            parent, text="下に追加", variable=self.openai_pos, value="after"
        )
        self.openai_pos_after.grid(row=2, column=1, sticky="w")
        self.openai_pos_before = ttk.Radiobutton(
            parent, text="上に追加", variable=self.openai_pos, value="before"
        )
        self.openai_pos_before.grid(row=2, column=2, sticky="w")

        # 追加文字数設定
        ttk.Label(parent, text="追加文字数: ").grid(row=3, column=0, sticky="w")
        self.openai_chars = tk.StringVar(value=str(self.cfg.get("openai", {}).get("chars", 50)))
        self.openai_chars_entry = ttk.Entry(parent, width=6, textvariable=self.openai_chars)
        self.openai_chars_entry.grid(row=3, column=1, sticky="w")

        # プロンプト入力
        ttk.Label(parent, text="プロンプト:").grid(row=4, column=0, sticky="w")
        self.openai_prompt = scrolledtext.ScrolledText(parent, width=40, height=4)
        self.openai_prompt.grid(row=5, column=0, columnspan=3, pady=4)
        saved_prompt = self.cfg.get("openai", {}).get("prompt", "")
        if saved_prompt:
            self.openai_prompt.insert(tk.END, saved_prompt)
        
        # OpenAI無効時は関連UIを無効化
        if not self.openai_enabled_var.get():
            self.openai_pos_after.config(state="disabled")
            self.openai_pos_before.config(state="disabled")
            self.openai_chars_entry.config(state="disabled")
            self.openai_prompt.config(state="disabled")

    def log(self, msg: str):
        """ログエリアにメッセージを表示"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)

    def refresh_slots(self):
        """ツイートスロットリストを更新（画像枚数表示付き）"""
        self.slot_listbox.delete(0, tk.END)
        for i, s in enumerate(self.cfg.get("tweets", [])):
            text_summary = s.get("text", "").split("\n")[0][:40]
            images = s.get("images", [])
            img_count = len(images) if images else 0
            
            # 表示形式: スロット番号: テキスト [写真×枚数]
            if img_count > 0:
                display = f"{i+1}: {text_summary} [写真×{img_count}]"
            else:
                display = f"{i+1}: {text_summary}"
            
            self.slot_listbox.insert(tk.END, display)

    def add_slot(self):
        """新しいツイートスロットを追加"""
        if len(self.cfg.get("tweets", [])) >= 10:
            messagebox.showwarning("上限", "最大10スロットまでです。")
            return
        self.cfg.setdefault("tweets", []).append({"text": "", "images": []})
        self.refresh_slots()

    def remove_slot(self):
        """選択されたツイートスロットを削除"""
        sel = self.slot_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.cfg["tweets"].pop(idx)
        save_config(self.cfg)
        self.refresh_slots()
        self.log(f"スロット{idx+1}を削除しました。設定を保存しました。")

    def edit_slot(self):
        """選択されたツイートスロットを編集"""
        sel = self.slot_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        data = self.cfg["tweets"][idx]
        popup = EditPopup(self.root, idx)
        popup.set_values(data)
        self.root.wait_window(popup)
        if popup.result:
            self.cfg["tweets"][idx] = popup.result
            save_config(self.cfg)
            self.refresh_slots()
            self.log(f"スロット{idx+1}を更新しました。設定を保存しました。")

    def start_auto(self):
        """自動ツイート投稿を開始"""
        if not self.cfg.get("tweets"):
            messagebox.showwarning("未設定", "まずツイートを1つ以上設定してください。")
            return
        
        # 現在の設定を保存
        self._save_current_settings()
        
        self.stop_event.clear()
        self.poster_thread = threading.Thread(target=self._poster_loop, daemon=True)
        self.poster_thread.start()
        self.log("自動ツイートを開始しました。")

    def stop_auto(self):
        """自動ツイート投稿を停止"""
        self.stop_event.set()
        self.log("停止要求を送信しました。スレッドが終了するまで待ってください。")

    def save_all(self):
        """現在の設定を保存"""
        self._save_current_settings()
        self.log("設定を保存しました。")

    def _save_current_settings(self):
        """UI上の設定を構成に保存"""
        try:
            self.cfg["delay_hours"] = int(self.delay_var.get())
        except Exception:
            self.cfg["delay_hours"] = 1
        
        self.cfg["openai"]["enabled"] = bool(self.openai_enabled_var.get())
        self.cfg["openai"]["position"] = self.openai_pos.get()
        
        try:
            self.cfg["openai"]["chars"] = int(self.openai_chars.get())
        except Exception:
            self.cfg["openai"]["chars"] = 50
        
        self.cfg["openai"]["prompt"] = self.openai_prompt.get(1.0, tk.END).strip()
        save_config(self.cfg)

    def _on_openai_toggle(self):
        """OpenAI有効チェックボックスが変更された時の処理"""
        self.cfg["openai"]["enabled"] = bool(self.openai_enabled_var.get())
        status = "有効" if self.openai_enabled_var.get() else "無効"
        self.log(f"OpenAI機能を{status}にしました")
        
        # UI要素の有効/無効を切り替え
        if self.openai_enabled_var.get():
            self.openai_pos_after.config(state="normal")
            self.openai_pos_before.config(state="normal")
            self.openai_chars_entry.config(state="normal")
            self.openai_prompt.config(state="normal")
        else:
            self.openai_pos_after.config(state="disabled")
            self.openai_pos_before.config(state="disabled")
            self.openai_chars_entry.config(state="disabled")
            self.openai_prompt.config(state="disabled")

    def _compose_with_openai(self, base_text: str) -> str:
        """
        OpenAI APIを使用してツイート本文を生成・編集
        
        Args:
            base_text: 元のツイート本文
        
        Returns:
            編集後のツイート本文（エラー時はNone）
        """
        self.log("OpenAI機能を使用してツイートを生成中...")
        
        if not self.cfg.get("openai", {}).get("enabled"):
            self.log("OpenAI機能が無効です")
            return base_text
        
        # GUIから現在のプロンプトを取得
        prompt = self.openai_prompt.get(1.0, tk.END).strip()
        if not prompt:
            self.log("エラー: プロンプトが入力されていません")
            messagebox.showerror("OpenAI エラー", "プロンプト欄にテキストを入力してください")
            return None
        
        try:
            max_chars = int(self.cfg["openai"].get("chars", 50))
            position = self.cfg["openai"].get("position", "after")
            
            self.log(f"OpenAI APIにリクエスト中... (最大文字数: {max_chars})")
            
            # util.openai_helperを使用
            result = compose_with_openai(base_text, prompt, max_chars, position)
            
            self.log(f"OpenAI生成完了: {result[:100]}...")
            return result
            
        except ValueError as e:
            self.log(f"プロンプトエラー: {e}")
            messagebox.showerror("OpenAI エラー", str(e))
            return None
        except Exception as e:
            error_msg = f"OpenAI APIエラー: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("OpenAI エラー", f"API呼び出しに失敗しました:\n{str(e)}")
            return base_text

    def _poster_loop(self):
        """自動投稿のメインループ（ランダム選択方式）"""
        client = get_client()
        
        while not self.stop_event.is_set():
            tweets = self.cfg.get("tweets", [])
            if not tweets:
                break
            
            # 有効なスロットのみをフィルタリング（テキストまたは画像がある）
            valid_slots = []
            for i, entry in enumerate(tweets):
                text = entry.get("text", "").strip()
                images = entry.get("images", [])
                # テキストがあるか、画像があれば有効
                if text or (images and len(images) > 0):
                    valid_slots.append(i)
            
            # 有効なスロットがない場合
            if not valid_slots:
                self.log("エラー: 有効なツイートスロットがありません（全てのスロットが空です）")
                messagebox.showerror(
                    "投稿エラー", 
                    "有効なツイートスロットがありません。\n\n"
                    "少なくとも1つのスロットにツイート本文または画像を設定してください。"
                )
                break
            
            # ランダムに有効なスロットを選択
            selected_idx = random.choice(valid_slots)
            entry = tweets[selected_idx]
            text = entry.get("text", "").strip()
            
            self.log(f"スロット {selected_idx + 1} を選択しました")
            
            # ハッシュタグチェック
            if text:
                hashtags = re.findall(r"#\w+", text)
                if len(hashtags) >= 4:
                    self.log("警告: ハッシュタグが4つ以上含まれています。シャドウバンの可能性があります。")
                    messagebox.showwarning(
                        "ハッシュタグ警告", 
                        "ツイートにハッシュタグが4つ以上含まれています。シャドウバンの可能性があります。"
                    )

            # 外部リンク検出
            if text and not self.cfg.get("external_link_warned", False) and re.search(r"https?://", text):
                self.log("外部リンクが検出されました。プロフィールにURLを記載して誘導することを推奨します。")
                messagebox.showwarning(
                    "外部リンク検出", 
                    "外部リンクが検出されました。プロフィールにURLを記載して誘導することを推奨します。"
                )
                self.cfg["external_link_warned"] = True
                save_config(self.cfg)

            # OpenAI機能による文章生成（テキストがある場合のみ）
            if text and self.cfg.get("openai", {}).get("enabled"):
                try:
                    composed_text = self._compose_with_openai(text)
                    if composed_text is None:
                        # プロンプトエラーなどで処理が中断された場合
                        self.log("OpenAI処理がスキップされました。次の投稿まで待機します。")
                        # 次のループへ進む（待機時間後）
                        text = None
                    else:
                        text = composed_text
                except Exception as e:
                    self.log(f"OpenAI統合中にエラー: {e}")

            # テキストがない場合は画像のみ投稿
            if not text:
                text = ""
            
            images = entry.get("images", []) if entry.get("images") else None
            
            # 投稿実行
            try:
                if text:
                    self.log(f"投稿中 (スロット{selected_idx + 1}): {text[:80]}")
                else:
                    self.log(f"投稿中 (スロット{selected_idx + 1}): 画像のみ")
                
                post(client, text, images)
                self.log("投稿しました。")
            except Exception as e:
                self.log(f"投稿失敗: {e}")

            # 次の待ち時間: delay_hours + ランダムな分数 ±30分
            delay_h = int(self.cfg.get("delay_hours", 1))
            offset_min = random.randint(-30, 30)
            wait_seconds = max(0, delay_h * 3600 + offset_min * 60)
            self.log(f"次の投稿まで待機: {delay_h}時間 + {offset_min}分 (約{wait_seconds}秒)")
            
            # スリープを分割して停止フラグをチェック
            slept = 0
            while slept < wait_seconds and not self.stop_event.is_set():
                time.sleep(1)
                slept += 1

        self.log("自動ツイートループを終了しました。")

    def test_post(self):
        """選択されたスロットのテスト投稿（画像のみ投稿にも対応）"""
        sel = self.slot_listbox.curselection()
        if not sel:
            messagebox.showwarning("未選択", "テスト投稿するスロットを選択してください。")
            return
        
        idx = sel[0]
        entry = self.cfg.get("tweets", [])[idx]
        text = entry.get("text", "").strip()
        images = entry.get("images", []) if entry.get("images") else None
        
        # テキストも画像もない場合はエラー
        if not text and not images:
            messagebox.showwarning(
                "内容なし", 
                "選択スロットにツイート本文または画像を設定してください。"
            )
            return
        
        # OpenAI機能が有効な場合は適用（テキストがある場合のみ）
        if text and self.cfg.get("openai", {}).get("enabled"):
            composed_text = self._compose_with_openai(text)
            if composed_text is None:
                # プロンプトエラーなどで処理が中断された場合
                return
            text = composed_text
        
        # テキストがない場合は空文字列
        if not text:
            text = ""
        
        # 確認メッセージ
        if text:
            confirm_msg = f"以下の内容をテスト投稿しますか?\n\n{text[:200]}"
        else:
            img_count = len(images) if images else 0
            confirm_msg = f"画像 {img_count} 枚をテスト投稿しますか?"
        
        if messagebox.askyesno("確認", confirm_msg):
            try:
                client = get_client()
                post(client, text, images)
                messagebox.showinfo("投稿完了", "テスト投稿しました。")
                if text:
                    self.log(f"テスト投稿を実行しました (スロット{idx + 1}): {text[:50]}")
                else:
                    self.log(f"テスト投稿を実行しました (スロット{idx + 1}): 画像のみ")
            except Exception as e:
                messagebox.showerror("投稿失敗", str(e))
                self.log(f"テスト投稿失敗: {e}")


def main():
    """アプリケーションのエントリーポイント"""
    root = tk.Tk()
    app = AutoPosterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
