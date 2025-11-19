"""
GUI関連のウィジェットとダイアログクラス
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext


class EditPopup(tk.Toplevel):
    """ツイートスロット編集用のポップアップウィンドウ"""
    
    def __init__(self, parent, slot):
        super().__init__(parent)
        self.title(f"ツイート内容編集 - スロット{slot+1}")
        self.slot = slot
        self.result = None
        self.geometry("600x400")

        ttk.Label(self, text="ツイート本文:").pack(anchor="w", padx=8, pady=(8, 0))
        self.text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=8)
        self.text.pack(fill="both", expand=True, padx=8)

        ttk.Label(self, text="画像 (最大4枚):").pack(anchor="w", padx=8, pady=(8, 0))
        self.img_frame = ttk.Frame(self)
        self.img_frame.pack(fill="x", padx=8)
        # 画像リストは純粋なPythonリストで管理する（StringVarを使うと文字単位で分解される問題を防ぐ）
        self.images = []
        self.img_listbox = tk.Listbox(self.img_frame, height=4)
        self.img_listbox.pack(side="left", fill="x", expand=True)
        img_btn_frame = ttk.Frame(self.img_frame)
        img_btn_frame.pack(side="right")
        ttk.Button(img_btn_frame, text="追加", command=self.add_images).pack(fill="x")
        ttk.Button(img_btn_frame, text="削除", command=self.remove_selected_image).pack(fill="x", pady=4)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=8, padx=8)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="リセット", command=self.on_reset).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="保存", command=self.on_save).pack(side="right")
        

    def set_values(self, data):
        """既存のツイートデータをUIに反映"""
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, data.get("text", ""))
        imgs = data.get("images", [])
        # imagesはリストで受け取り、Listboxを更新する
        self.images = imgs[:] if isinstance(imgs, list) else list(imgs)
        self._refresh_img_listbox()

    def add_images(self):
        """画像ファイル選択ダイアログを表示して画像を追加"""
        files = filedialog.askopenfilenames(
            title="画像を選択", 
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if not files:
            return
        # 追加してListboxを更新
        for f in files:
            if len(self.images) >= 4:
                break
            if f not in self.images:
                self.images.append(f)
        self._refresh_img_listbox()

    def remove_selected_image(self):
        """選択された画像をリストから削除"""
        sel = self.img_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self.images):
            self.images.pop(idx)
        self._refresh_img_listbox()

    def on_save(self):
        """編集内容を保存してダイアログを閉じる"""
        text = self.text.get(1.0, tk.END).strip()
        images = self.images[:]
        self.result = {"text": text, "images": images}
        self.destroy()

    def on_reset(self):
        """本文と画像をクリアしてUIに反映"""
        self.text.delete(1.0, tk.END)
        self.images = []
        self._refresh_img_listbox()

    def _refresh_img_listbox(self):
        """画像リストボックスを更新"""
        self.img_listbox.delete(0, tk.END)
        for p in self.images:
            self.img_listbox.insert(tk.END, p)
