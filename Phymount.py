import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import re

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class SlotImagem:
    def __init__(self, parent, width, height, app_ref, index):
        self.width, self.height, self.app, self.index = width, height, app_ref, index
        self.container = tk.Frame(parent)
        self.canvas = tk.Canvas(self.container, width=width, height=height, bg="#2e2e2e", highlightthickness=1, highlightbackground="#444")
        self.canvas.pack()
        
        if HAS_DND:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self.app.on_drop_global)

        self.img_original = None
        self.img_display = None
        self.tk_img = None
        self.scale = 1.0
        self.x, self.y = 0, 0
        
        # Botão Esquerdo: Enquadrar (Pan)
        self.canvas.bind("<Button-1>", self.clique_iniciar)
        self.canvas.bind("<B1-Motion>", self.arrastar_pan)
        
        # Botão Direito: Reorganizar (Trocar de Slot)
        self.canvas.bind("<Button-3>", self.iniciar_troca)
        self.canvas.bind("<B3-Motion>", self.movendo_troca)
        self.canvas.bind("<ButtonRelease-3>", self.finalizar_troca)
        
        self.canvas.bind("<Double-Button-1>", self.carregar_manual)
        self.canvas.bind("<MouseWheel>", self.zoom)
        
        self.instrucao = self.canvas.create_text(width/2, height/2, text=f"Slot {index+1}", fill="gray")
        tk.Button(self.container, text="X", command=self.limpar, bg="#ff4444", fg="white", font=("Arial", 7)).place(x=2, y=2)

    def processar_imagem(self, path):
        try:
            self.img_original = Image.open(path).convert("RGBA")
            self.scale, self.x, self.y = 1.0, 0, 0
            self.atualizar_view()
        except: pass

    def atualizar_view(self):
        if not self.img_original: return
        ratio = self.img_original.width / self.img_original.height
        bw, bh = (self.width, int(self.width/ratio)) if (self.width/self.height) > ratio else (int(self.height*ratio), self.height)
        nw, nh = int(bw * self.scale), int(bh * self.scale)
        self.img_display = self.img_original.resize((nw, nh), Image.Resampling.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(self.img_display)
        self.canvas.delete("all")
        self.x, self.y = max(min(self.x, 0), self.width - nw), max(min(self.y, 0), self.height - nh)
        self.canvas.create_image(self.x, self.y, image=self.tk_img, anchor="nw")

    def zoom(self, event):
        if not self.img_original: return
        self.scale = max(self.scale * (1.1 if event.delta > 0 else 0.9), 1.0)
        self.atualizar_view()

    def clique_iniciar(self, event):
        self.last_x, self.last_y = event.x, event.y

    def arrastar_pan(self, event):
        if not self.img_original: return
        dx, dy = event.x - self.last_x, event.y - self.last_y
        self.x, self.y = self.x + dx, self.y + dy
        self.atualizar_view()
        self.last_x, self.last_y = event.x, event.y

    # --- Lógica de Troca ---
    def iniciar_troca(self, event):
        if not self.img_original: return
        self.canvas.config(cursor="hand2")

    def movendo_troca(self, event): pass # Poderia criar um ghost da imagem aqui

    def finalizar_troca(self, event):
        self.canvas.config(cursor="")
        # Descobre em qual widget o mouse foi solto
        x_root, y_root = event.x_root, event.y_root
        target = self.app.root.winfo_containing(x_root, y_root)
        
        for outro_slot in self.app.slots:
            if target == outro_slot.canvas:
                # Troca os dados entre os slots
                self.img_original, outro_slot.img_original = outro_slot.img_original, self.img_original
                self.scale, outro_slot.scale = outro_slot.scale, self.scale
                self.x, self.y, outro_slot.x, outro_slot.y = outro_slot.x, outro_slot.y, self.x, self.y
                self.atualizar_view()
                outro_slot.atualizar_view()
                if not self.img_original: self.limpar()
                break

    def limpar(self):
        self.img_original = None
        self.canvas.delete("all")
        self.canvas.create_text(self.width/2, self.height/2, text="Vazio", fill="gray")

    def carregar_manual(self, e=None):
        p = filedialog.askopenfilename(); 
        if p: self.processar_imagem(p)

    def get_render(self, fw, fh):
        if not self.img_original: return Image.new("RGB", (fw, fh), (46, 46, 46))
        r = fw / self.width
        sw, sh = int(self.img_display.width * r), int(self.img_display.height * r)
        img_f = self.img_original.resize((sw, sh), Image.Resampling.LANCZOS)
        saida = Image.new("RGBA", (fw, fh), (0,0,0,0))
        saida.paste(img_f, (int(self.x * r), int(self.y * r)))
        return saida.convert("RGB")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Phymount 1.0")
        self.cols = simpledialog.askinteger("Grid", "Columns:", initialvalue=1)
        self.rows = simpledialog.askinteger("Grid", "Lines:", initialvalue=1)
        if not self.cols: root.destroy(); return

        toolbar = tk.Frame(root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.res_var = tk.StringVar(value="HD (720p)")
        tk.OptionMenu(toolbar, self.res_var, "HD (720p)", "Full HD (1080p)", "4K (Ultra)").pack(side=tk.LEFT)
        tk.Button(toolbar, text="SAVE", command=self.salvar, bg="#4CAF50", fg="white", width=12).pack(side=tk.RIGHT)

        self.grid_frame = tk.Frame(root); self.grid_frame.pack(padx=10, pady=10)
        self.slots = []
        for i in range(self.rows * self.cols):
            slot = SlotImagem(self.grid_frame, 250, 200, self, i)
            slot.container.grid(row=i//self.cols, column=i%self.cols, padx=2, pady=2)
            self.slots.append(slot)

    def on_drop_global(self, event):
        paths = re.findall(r'\{(.*?)\}|(\S+)', event.data)
        cleaned = [p[0] if p[0] else p[1] for p in paths]
        for p in cleaned:
            for s in self.slots:
                if s.img_original is None:
                    s.processar_imagem(p)
                    break

    def salvar(self):
        res_map = {"HD (720p)": 1280, "Full HD (1080p)": 1920, "4K (Ultra)": 3840}
        tw = res_map[self.res_var.get()]
        sw = tw // self.cols
        sh = int(sw * 0.8)
        final = Image.new("RGB", (sw * self.cols, sh * self.rows))
        for i, s in enumerate(self.slots):
            final.paste(s.get_render(sw, sh), ((i%self.cols)*sw, (i//self.cols)*sh))
        path = filedialog.asksaveasfilename(defaultextension=".jpg")
        if path: final.save(path, quality=95); messagebox.showinfo("Phymount", "Salvo!")

if __name__ == "__main__":
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = App(root)
    root.mainloop()
