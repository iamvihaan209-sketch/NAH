#!/usr/bin/env python3
from __future__ import annotations

import argparse, bz2, gzip, json, lzma, os, shutil, struct, subprocess, sys, tarfile, time, zipfile, zlib
from pathlib import Path

APP_VERSION = "1.0"
MAGIC = b"NAH1"
FORMAT_VERSION = 1
HEADER = struct.Struct("<4sBBIQH")
CHUNK_HEADER = struct.Struct("<BIII")
CODECS = {0:("STORE", lambda b:b), 1:("DEFLATE", zlib.decompress), 2:("BZ2", bz2.decompress), 3:("LZMA", lzma.decompress)}
MODE_LABELS = {"turbo":"Turbo", "fast":"Fast", "balanced":"Smart", "max":"Tryhard", "unhinged":"Unhinged"}
EVENT_CALLBACK = None

class Cancelled(Exception): pass

def set_event_callback(cb):
    global EVENT_CALLBACK
    EVENT_CALLBACK = cb

def human(n:int)->str:
    x=float(n)
    for u in ("B","KiB","MiB","GiB","TiB"):
        if x < 1024 or u == "TiB": return f"{int(x)} B" if u=="B" else f"{x:.2f} {u}"
        x/=1024

def emit(kind, message="", progress=None, **extra):
    obj={"kind":kind,"message":message,**extra}
    if progress is not None: obj["progress"]=float(progress)
    if EVENT_CALLBACK: EVENT_CALLBACK(obj)
    elif message: print(message, flush=True)

def check_cancel(ev):
    if ev is not None and ev.is_set(): raise Cancelled()

def probe_ratio(data:bytes)->float:
    if not data: return 1.0
    n=min(65536,len(data))
    if len(data)<=n*3: sample=data
    else:
        m=len(data)//2
        sample=data[:n]+data[m:m+n]+data[-n:]
    return len(zlib.compress(sample,1))/len(sample)

def compress_chunk(data:bytes, mode:str, entropy_bail=True, cancel_event=None):
    check_cancel(cancel_event)
    raw=len(data); crc=zlib.crc32(data)&0xffffffff; pr=probe_ratio(data)
    attempts=[("STORE",raw)]
    bail={"turbo":.995,"fast":.996,"balanced":.997,"max":.9985,"unhinged":.9992}[mode]
    if entropy_bail and pr>=bail:
        return 0,data,attempts,"entropy",crc
    zl={"turbo":1,"fast":4,"balanced":6,"max":9,"unhinged":9}[mode]
    z=zlib.compress(data,zl); attempts.append((f"DEFLATE-{zl}",len(z)))
    cid,payload=(1,z) if len(z)<raw else (0,data)
    if mode in ("max","unhinged") and zl!=4:
        z4=zlib.compress(data,4); attempts.append(("DEFLATE-4",len(z4)))
        if len(z4)<len(payload): cid,payload=1,z4
    if mode=="balanced" and pr<.97:
        x=lzma.compress(data,preset=3); attempts.append(("LZMA-3",len(x)))
        if len(x)<len(payload): cid,payload=3,x
        if pr<.91:
            b=bz2.compress(data,compresslevel=6); attempts.append(("BZ2-6",len(b)))
            if len(b)<len(payload): cid,payload=2,b
    elif mode=="max" and pr<.997:
        b=bz2.compress(data,compresslevel=9); attempts.append(("BZ2-9",len(b)))
        if len(b)<len(payload): cid,payload=2,b
        x=lzma.compress(data,preset=6); attempts.append(("LZMA-6",len(x)))
        if len(x)<len(payload): cid,payload=3,x
    elif mode=="unhinged" and pr<.999:
        b=bz2.compress(data,compresslevel=9); attempts.append(("BZ2-9",len(b)))
        if len(b)<len(payload): cid,payload=2,b
        x=lzma.compress(data,preset=9|lzma.PRESET_EXTREME); attempts.append(("LZMA-X",len(x)))
        if len(x)<len(payload): cid,payload=3,x
    return cid,payload,attempts,mode,crc

def pack(src,dst,chunk_size=4*1024*1024,mode="balanced",workers=None,quiet=False,entropy_bail=True,cancel_event=None):
    src=Path(src); dst=Path(dst)
    if not src.is_file(): raise ValueError(f"input file not found: {src}")
    if mode not in MODE_LABELS: raise ValueError(f"unknown mode: {mode}")
    size=src.stat().st_size; chunks=(size+chunk_size-1)//chunk_size if size else 0
    name=src.name.encode(); tmp=dst.with_name(dst.name+".partial")
    emit("start",f"okay, eating {src.name}\ninput: {human(size)} | mode: {MODE_LABELS[mode]}",0,input_bytes=size,total_chunks=chunks)
    done_raw=done_payload=0; counts={0:0,1:0,2:0,3:0}
    try:
        with src.open("rb") as fi,tmp.open("wb") as fo:
            fo.write(HEADER.pack(MAGIC,FORMAT_VERSION,0,chunk_size,size,len(name))); fo.write(name); fo.write(struct.pack("<I",chunks))
            for i in range(chunks):
                check_cancel(cancel_event); data=fi.read(chunk_size)
                cid,payload,attempts,note,crc=compress_chunk(data,mode,entropy_bail,cancel_event)
                fo.write(CHUNK_HEADER.pack(cid,len(data),len(payload),crc)); fo.write(payload)
                counts[cid]+=1; done_raw+=len(data); done_payload+=len(payload)
                pct=(i+1)/chunks*100 if chunks else 100
                vibe="entropy soup detected; storing raw." if note=="entropy" else f"{CODECS[cid][0]} won."
                emit("progress",f"[{i+1}/{chunks}] {vibe} {human(len(data))} -> {human(len(payload))}",pct)
        os.replace(tmp,dst)
    except Exception:
        try: tmp.unlink()
        except FileNotFoundError: pass
        raise
    archive=dst.stat().st_size; saved=size-archive
    emit("done",f"done. {human(size)} -> {human(archive)} ({archive/size*100 if size else 0:.2f}%). saved {human(saved) if saved>=0 else '-'+human(-saved)}.",100,output=str(dst),output_bytes=archive)
    return dst

def read_meta(src):
    src=Path(src)
    with src.open("rb") as f:
        head=f.read(HEADER.size)
        if len(head)!=HEADER.size: raise ValueError("not a complete .nah file")
        magic,ver,flags,chunk_size,orig,name_len=HEADER.unpack(head)
        if magic!=MAGIC or ver!=FORMAT_VERSION: raise ValueError("unsupported NAH archive")
        name=f.read(name_len).decode("utf-8","replace"); count=struct.unpack("<I",f.read(4))[0]
    return {"name":name,"chunk_size":chunk_size,"original_size":orig,"chunk_count":count,"version":ver}

def unpack(src,dst=None,verify=True,quiet=False,cancel_event=None):
    src=Path(src); meta=read_meta(src); dst=Path(dst) if dst else src.with_name(meta["name"]); tmp=dst.with_name(dst.name+".partial")
    with src.open("rb") as fi:
        fi.seek(HEADER.size); magic,ver,flags,cs,orig,nlen=HEADER.unpack(fi.read(HEADER.size)); fi.read(nlen); count=struct.unpack("<I",fi.read(4))[0]
        try:
            with tmp.open("wb") as fo:
                for i in range(count):
                    check_cancel(cancel_event)
                    cid,raw_len,stored_len,crc=CHUNK_HEADER.unpack(fi.read(CHUNK_HEADER.size)); payload=fi.read(stored_len)
                    if len(payload)!=stored_len: raise ValueError("truncated chunk")
                    data=CODECS[cid][1](payload)
                    if len(data)!=raw_len: raise ValueError("decoded chunk has wrong size")
                    if verify and (zlib.crc32(data)&0xffffffff)!=crc: raise ValueError("CRC mismatch")
                    fo.write(data); emit("progress",f"[{i+1}/{count}] restored {human(len(data))}",(i+1)/count*100 if count else 100)
            os.replace(tmp,dst)
        except Exception:
            try: tmp.unlink()
            except FileNotFoundError: pass
            raise
    emit("done",f"done. restored {dst}",100,output=str(dst)); return dst

def inspect_archive(src):
    m=read_meta(src); size=Path(src).stat().st_size
    print(f"NAH{m['version']} archive\noriginal: {m['name']} ({human(m['original_size'])})\narchive: {human(size)}\nchunks: {m['chunk_count']} x {human(m['chunk_size'])}")

def prove(src):
    p=Path(src); tmp=p.with_name(p.name+".prove.tmp")
    try: unpack(p,tmp,True,True); print("yep. decoded and CRC-checked.")
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass

def safe_join(root,member):
    root=Path(root).resolve(); target=(root/member).resolve()
    if target==root or root in target.parents: return target
    raise ValueError(f"archive entry escapes destination: {member}")

def archive_kind(path):
    n=Path(path).name.lower()
    if n.endswith(".zip"): return "zip"
    if any(n.endswith(x) for x in (".tar",".tar.gz",".tgz",".tar.bz2",".tbz",".tbz2",".tar.xz",".txz",".tar.lzma",".tlz")): return "tar"
    if n.endswith(".gz"): return "gz"
    if n.endswith(".bz2"): return "bz2"
    if n.endswith(".xz"): return "xz"
    if n.endswith(".lzma"): return "lzma"
    if n.endswith((".7z",".rar",".tar.zst",".tzst")): return "external"

def default_extract_dir(src):
    p=Path(src); return p.parent/(p.name+" extracted")

def extract_archive(src,dest=None,cancel_event=None):
    src=Path(src); kind=archive_kind(src)
    if not kind: raise ValueError("unsupported archive type")
    dest=Path(dest) if dest else default_extract_dir(src); dest.mkdir(parents=True,exist_ok=True)
    emit("start",f"extracting {src.name}",0)
    if kind=="zip":
        with zipfile.ZipFile(src) as z:
            infos=z.infolist()
            for i,x in enumerate(infos,1): safe_join(dest,x.filename); z.extract(x,dest); emit("progress",x.filename,i/max(1,len(infos))*100)
    elif kind=="tar":
        with tarfile.open(src,"r:*") as t:
            members=t.getmembers()
            for i,x in enumerate(members,1): safe_join(dest,x.name); t.extract(x,dest); emit("progress",x.name,i/max(1,len(members))*100)
    elif kind in ("gz","bz2","xz","lzma"):
        opener={"gz":gzip.open,"bz2":bz2.open,"xz":lzma.open,"lzma":lzma.open}[kind]; out=dest/src.stem
        with opener(src,"rb") as fi,out.open("wb") as fo: shutil.copyfileobj(fi,fo)
    else:
        for exe in ("7zz","7z","7za","unar","unrar","bsdtar","tar"):
            p=shutil.which(exe)
            if not p: continue
            if exe in ("7zz","7z","7za"): cmd=[p,"x","-y",f"-o{dest}",str(src)]
            elif exe=="unar": cmd=[p,"-f","-o",str(dest),str(src)]
            elif exe=="unrar": cmd=[p,"x","-o+",str(src),str(dest)+os.sep]
            else: cmd=[p,"-xf",str(src),"-C",str(dest)]
            if subprocess.run(cmd).returncode==0: break
        else: raise ValueError("no compatible external extractor found")
    emit("done",f"done. extracted into {dest}",100,output=str(dest)); return dest

def main(argv=None):
    p=argparse.ArgumentParser(prog="nah",description="NAH v1.0 — lossless compression that knows when to say nah.")
    p.add_argument("--version",action="version",version=f"NAH {APP_VERSION} (format NAH1)")
    sp=p.add_subparsers(dest="cmd",required=True)
    a=sp.add_parser("pack"); a.add_argument("input"); a.add_argument("output",nargs="?"); a.add_argument("--mode",choices=MODE_LABELS,default="balanced"); a.add_argument("-c","--chunk-size",type=int,default=4*1024*1024); a.add_argument("--no-entropy-bail",action="store_true")
    a=sp.add_parser("unpack"); a.add_argument("input"); a.add_argument("output",nargs="?"); a.add_argument("--no-verify",action="store_true")
    a=sp.add_parser("extract"); a.add_argument("input"); a.add_argument("output",nargs="?")
    a=sp.add_parser("inspect"); a.add_argument("input")
    a=sp.add_parser("prove-it"); a.add_argument("input")
    args=p.parse_args(argv)
    try:
        if args.cmd=="pack": pack(args.input,args.output or str(args.input)+".nah",args.chunk_size,args.mode,entropy_bail=not args.no_entropy_bail)
        elif args.cmd=="unpack": unpack(args.input,args.output,not args.no_verify)
        elif args.cmd=="extract": extract_archive(args.input,args.output)
        elif args.cmd=="inspect": inspect_archive(args.input)
        else: prove(args.input)
    except Cancelled: raise SystemExit(130)
    except Exception as e: print(f"nah: {e}",file=sys.stderr); raise SystemExit(1)

if __name__=="__main__": main()
