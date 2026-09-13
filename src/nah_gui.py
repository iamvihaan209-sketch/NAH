#!/usr/bin/env python3
from __future__ import annotations

import os, queue, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import nah

APP_VERSION="1.0"
BG="#0b1220"; PANEL="#111b30"; TEXT="#f5f7ff"; MUTED="#a7b3cc"; ACCENT="#7fa2ff"
MODES={"Turbo":"turbo","Fast":"fast","Smart":"balanced","Tryhard":"max","Unhinged":"unhinged"}
CHUNKS={"1 MiB":1*1024*1024,"4 MiB":4*1024*1024,"8 MiB":8*1024*1024,"16 MiB":16*1024*1024}

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"NAH {APP_VERSION}"); self.geometry("900x700"); self.minsize(760,560); self.configure(bg=BG)
        self.selected=None; self.last_output=None; self.cancel=threading.Event(); self.events=queue.Queue()
        self.mode=tk.StringVar(value="Smart"); self.chunk=tk.StringVar(value="4 MiB"); self.entropy=tk.BooleanVar(value=True); self.verify=tk.BooleanVar(value=True)
        self.status=tk.StringVar(value="Ready. Pick a file and let NAH judge it."); self.filevar=tk.StringVar(value="No file selected"); self.progress=tk.DoubleVar(value=0)
        self._build(); self.after(80,self._poll)

    def _build(self):
        style=ttk.Style(self); 
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("TFrame",background=BG); style.configure("TLabel",background=BG,foreground=TEXT); style.configure("TButton",padding=8)
        style.configure("TCheckbutton",background=BG,foreground=TEXT); style.configure("TCombobox",padding=5)

        root=ttk.Frame(self,padding=20); root.pack(fill="both",expand=True)
        tk.Label(root,text="NAH",font=("Helvetica",30,"bold"),bg=BG,fg=TEXT).pack(anchor="w")
        tk.Label(root,text="Lossless compression that knows when to say nah.",font=("Helvetica",12),bg=BG,fg=MUTED).pack(anchor="w",pady=(0,16))

        card=tk.Frame(root,bg=PANEL,highlightthickness=1,highlightbackground="#263858",padx=16,pady=16); card.pack(fill="x")
        tk.Label(card,textvariable=self.filevar,bg=PANEL,fg=TEXT,font=("Helvetica",12,"bold"),anchor="w").pack(fill="x")
        row=tk.Frame(card,bg=PANEL); row.pack(fill="x",pady=(12,0))
        ttk.Button(row,text="Choose File",command=self.choose).pack(side="left")
        ttk.Button(row,text="Pack to .nah",command=self.pack_file).pack(side="left",padx=8)
        ttk.Button(row,text="Unpack / Extract",command=self.unpack_or_extract).pack(side="left")
        ttk.Button(row,text="Cancel",command=self.cancel_job).pack(side="right")

        opts=ttk.Frame(root); opts.pack(fill="x",pady=16)
        ttk.Label(opts,text="Mode").grid(row=0,column=0,sticky="w")
        ttk.Combobox(opts,textvariable=self.mode,values=list(MODES),state="readonly",width=14).grid(row=1,column=0,sticky="w",padx=(0,16))
        ttk.Label(opts,text="Chunk size").grid(row=0,column=1,sticky="w")
        ttk.Combobox(opts,textvariable=self.chunk,values=list(CHUNKS),state="readonly",width=12).grid(row=1,column=1,sticky="w",padx=(0,16))
        ttk.Checkbutton(opts,text="Skip entropy soup",variable=self.entropy).grid(row=1,column=2,sticky="w",padx=(0,16))
        ttk.Checkbutton(opts,text="Verify CRC when unpacking",variable=self.verify).grid(row=1,column=3,sticky="w")

        ttk.Progressbar(root,variable=self.progress,maximum=100).pack(fill="x",pady=(0,8))
        ttk.Label(root,textvariable=self.status).pack(fill="x",pady=(0,8))
        self.log=tk.Text(root,height=20,bg="#08101d",fg="#dfe8ff",insertbackground="white",wrap="word",relief="flat",padx=10,pady=10)
        self.log.pack(fill="both",expand=True)
        self.log.insert("end","NAH v1.0 ready.\n")

    def choose(self):
        p=filedialog.askopenfilename()
        if p: self.select(Path(p))

    def select(self,p:Path):
        self.selected=p; self.filevar.set(f"{p.name}  •  {nah.human(p.stat().st_size)}"); self._log(f"selected: {p}")

    def _event(self,obj): self.events.put(obj)

    def _start(self,fn):
        if getattr(self,"worker",None) and self.worker.is_alive(): messagebox.showinfo("NAH","NAH is already busy judging another file."); return
        self.cancel.clear(); self.progress.set(0); nah.set_event_callback(self._event)
        def run():
            try: fn()
            except nah.Cancelled: self.events.put({"kind":"error","message":"cancelled. partial output cleaned up."})
            except Exception as e: self.events.put({"kind":"error","message":f"nah: {e}"})
            finally: nah.set_event_callback(None)
        self.worker=threading.Thread(target=run,daemon=True); self.worker.start()

    def pack_file(self):
        if not self.selected: return self.choose()
        src=self.selected; out=Path(str(src)+".nah")
        if out.exists() and not messagebox.askyesno("Replace file?",f"{out.name} already exists. Replace it?"): return
        def work(): self.last_output=nah.pack(src,out,CHUNKS[self.chunk.get()],MODES[self.mode.get()],entropy_bail=self.entropy.get(),cancel_event=self.cancel)
        self._start(work)

    def unpack_or_extract(self):
        if not self.selected: return self.choose()
        src=self.selected
        if src.name.lower().endswith(".nah"):
            try: meta=nah.read_meta(src); suggested=src.with_name(meta["name"])
            except Exception as e: messagebox.showerror("NAH",str(e)); return
            out=Path(filedialog.asksaveasfilename(initialdir=str(src.parent),initialfile=suggested.name) or "")
            if not str(out): return
            def work(): self.last_output=nah.unpack(src,out,self.verify.get(),cancel_event=self.cancel)
        else:
            if not nah.archive_kind(src): messagebox.showerror("NAH","That file is not a supported archive. You can still pack it to .nah."); return
            out=filedialog.askdirectory(initialdir=str(src.parent))
            if not out: return
            def work(): self.last_output=nah.extract_archive(src,Path(out),self.cancel)
        self._start(work)

    def cancel_job(self):
        self.cancel.set(); self.status.set("Cancelling…")

    def _log(self,msg):
        self.log.insert("end",str(msg)+"\n"); self.log.see("end")

    def _poll(self):
        try:
            while True:
                ev=self.events.get_nowait(); kind=ev.get("kind"); msg=ev.get("message","")
                if "progress" in ev: self.progress.set(ev["progress"])
                if msg: self._log(msg); self.status.set(msg.splitlines()[0])
                if kind=="done": self.progress.set(100)
                if kind=="error": messagebox.showerror("NAH",msg)
        except queue.Empty: pass
        self.after(80,self._poll)

if __name__=="__main__": App().mainloop()
