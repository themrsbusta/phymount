import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
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
        
        self.canvas.bind("<Button-1>", self.clique_iniciar)
        self.canvas.bind("<B1-Motion>", self.arrastar_pan)
        self.canvas.bind("<Button-3>", self.iniciar_troca)
        self.canvas.bind("<ButtonRelease-3>", self.finalizar_troca)
        self.canvas.bind("<Double-Button-1>", self.carregar_manual)
        self.canvas.bind("<MouseWheel>", self.zoom)
        
        self.mostrar_vazio()
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

    def iniciar_troca(self, event):
        if not self.img_original: return
        self.canvas.config(cursor="hand2")

    def finalizar_troca(self, event):
        self.canvas.config(cursor="")
        target = self.app.root.winfo_containing(event.x_root, event.y_root)
        for outro in self.app.slots:
            if target == outro.canvas:
                self.img_original, outro.img_original = outro.img_original, self.img_original
                self.scale, outro.scale = outro.scale, self.scale
                self.x, self.y, outro.x, outro.y = outro.x, outro.y, self.x, self.y
                self.atualizar_view(); outro.atualizar_view()
                if not self.img_original: self.limpar()
                break

    def mostrar_vazio(self):
        self.canvas.delete("all")
        self.canvas.create_text(self.width/2, self.height/2, text=f"Slot {self.index+1}", fill="gray")

    def limpar(self):
        self.img_original = None
        self.mostrar_vazio()

    def carregar_manual(self, e=None):
        p = filedialog.askopenfilename()
        if p: self.processar_imagem(p)

    def get_render(self, fw, fh):
        if not self.img_original: return Image.new("RGBA", (fw, fh), (46, 46, 46, 255))
        r = fw / self.width
        sw, sh = int(self.img_display.width * r), int(self.img_display.height * r)
        img_f = self.img_original.resize((sw, sh), Image.Resampling.LANCZOS)
        saida = Image.new("RGBA", (fw, fh), (0,0,0,0))
        saida.paste(img_f, (int(self.x * r), int(self.y * r)))
        return saida

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Phymount 1.01")
        
        self.cols_var = tk.IntVar(value=1)
        self.rows_var = tk.IntVar(value=1)
        self.slots = []
        
        # Flags de controle de redimensionamento
        self.is_auto_resizing = False 
        
        # Toolbar
        toolbar = tk.Frame(root, bg="#333")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(toolbar, text=" Cols:", bg="#333", fg="white").pack(side=tk.LEFT)
        tk.Spinbox(toolbar, from_=1, to=10, width=3, textvariable=self.cols_var, command=lambda: self.update_grid(force_window_resize=True)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text=" Rows:", bg="#333", fg="white").pack(side=tk.LEFT)
        tk.Spinbox(toolbar, from_=1, to=10, width=3, textvariable=self.rows_var, command=lambda: self.update_grid(force_window_resize=True)).pack(side=tk.LEFT, padx=5)

        self.res_var = tk.StringVar(value="Full HD (1080p)")
        tk.OptionMenu(toolbar, self.res_var, "HD (720p)", "Full HD (1080p)", "4K (Ultra)").pack(side=tk.LEFT, padx=10)
        
        tk.Button(toolbar, text="SAVE", command=self.salvar, bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=5)

        self.grid_frame = tk.Frame(root)
        self.grid_frame.pack(padx=10, pady=10)
        
        self.root.bind("<Configure>", self.on_window_manual_resize)
        
        # Inicia e força o tamanho inicial
        self.update_grid(force_window_resize=True)

    def on_window_manual_resize(self, event):
        # Se o redimensionamento veio do código, ignora
        if self.is_auto_resizing: return
        
        if event.widget == self.root:
            # Largura disponível / (largura do slot + padding)
            new_cols = max(1, (event.width - 20) // 254)
            # Altura disponível / (altura do slot + padding) - toolbar
            new_rows = max(1, (event.height - 60) // 204)
            
            if new_cols != self.cols_var.get() or new_rows != self.rows_var.get():
                self.cols_var.set(new_cols)
                self.rows_var.set(new_rows)
                # Chama update sem forçar resize da janela (já estamos redimensionando com mouse)
                self.update_grid(force_window_resize=False)

    def update_grid(self, force_window_resize=False):
        if force_window_resize:
            self.is_auto_resizing = True
        
        cols, rows = self.cols_var.get(), self.rows_var.get()
        
        # Salva imagens
        old_images = [s.img_original for s in self.slots]
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        
        self.slots = []
        for i in range(cols * rows):
            slot = SlotImagem(self.grid_frame, 250, 200, self, i)
            slot.container.grid(row=i//cols, column=i%cols, padx=2, pady=2)
            if i < len(old_images) and old_images[i]:
                slot.img_original = old_images[i]
                slot.atualizar_view()
            self.slots.append(slot)
            
        if force_window_resize:
            self.root.update_idletasks() # Garante que o Tkinter processou
            # Cálculo Exato: (Colunas * LarguraSlot) + PaddingLateral + (Linhas * AlturaSlot) + Toolbar
            req_w = (cols * 254) + 24 
            req_h = (rows * 204) + 60
            self.root.geometry(f"{req_w}x{req_h}")
            # Destrava depois de um tempinho pra evitar conflito
            self.root.after(100, lambda: setattr(self, 'is_auto_resizing', False))

    def on_drop_global(self, event):
        paths = re.findall(r'\{(.*?)\}|(\S+)', event.data)
        cleaned = [p[0] if p[0] else p[1] for p in paths]
        
        current_slots = self.cols_var.get() * self.rows_var.get()
        need_resize = False
        
        # Calcula novo grid se necessário
        if len(cleaned) > current_slots:
            while len(cleaned) > (self.cols_var.get() * self.rows_var.get()):
                if self.cols_var.get() <= self.rows_var.get():
                    self.cols_var.set(self.cols_var.get() + 1)
                else:
                    self.rows_var.set(self.rows_var.get() + 1)
            need_resize = True

        # Se aumentou o grid, força o redimensionamento da janela
        if need_resize:
            self.update_grid(force_window_resize=True)

        for p in cleaned:
            for s in self.slots:
                if s.img_original is None:
                    s.processar_imagem(p)
                    break

    def salvar(self):
        res_map = {"HD (720p)": 1280, "Full HD (1080p)": 1920, "4K (Ultra)": 3840}
        cols, rows = self.cols_var.get(), self.rows_var.get()
        tw = res_map[self.res_var.get()]
        sw = tw // cols
        sh = int(sw * 0.8)
        
        final = Image.new("RGBA", (sw * cols, sh * rows), (46, 46, 46, 255))
        for i, s in enumerate(self.slots):
            final.paste(s.get_render(sw, sh), ((i%cols)*sw, (i//cols)*sh))
        
        path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if path:
            if path.lower().endswith((".jpg", ".jpeg")):
                final.convert("RGB").save(path, "JPEG", quality=95)
            else:
                final.save(path, "PNG")
            messagebox.showinfo("Phymount", "Saved!")

if __name__ == "__main__":
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = App(root)
    root.mainloop()
