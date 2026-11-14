#!/usr/bin/env python3
"""Extractor NUP propio, escrito a partir de SPEC.md v1.0-draft (a55uka/nup).

Uso:
  nupx.py info    juego.nup
  nupx.py extract juego.nup carpeta_salida

Salida con el mismo esquema que los dumps de Eden-NS2:
  base/{exefs,romfs}  updates/<version>/{exefs,romfs}  dlc/<titleid>/<n>/...
"""
import hashlib, os, struct, sys, time
import zstd_compat as zstd   # Python 3.14 o paquete zstandard

KINDS = {0: "base", 1: "update", 2: "addon", 3: "addon_update", 4: "system"}
CHUNK = 8 << 20


class Nup:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        sb = self.f.read(0x80)
        if sb[:4] != b"NUP\x01":
            sys.exit("No es un NUP v1")
        (self.header_size, _hv, self.toc_off, self.toc_size) = struct.unpack_from("<HHQQ", sb, 4)
        self.toc_sha = sb[0x18:0x38]
        self.blob_off, self.file_size, self.pkg_count, flags = struct.unpack_from("<QQII", sb, 0x38)
        real = os.path.getsize(path)
        if flags:
            sys.exit(f"flags de superblock desconocidos: {flags:#x}")
        if self.file_size != real:
            sys.exit(f"Tamaño incorrecto: cabecera {self.file_size}, real {real} (¿dump incompleto?)")
        self.f.seek(self.toc_off)
        self.toc = self.f.read(self.toc_size)
        if hashlib.sha256(self.toc).digest() != self.toc_sha:
            sys.exit("SHA-256 del TOC no coincide: fichero corrupto")
        t = self.toc
        if t[:4] != b"TOC\x01":
            sys.exit("Magic del TOC incorrecto")
        pc, self.ndirs, self.nfiles, sp_off, sp_size = struct.unpack_from("<IQQQQ", t, 4)
        if pc != self.pkg_count:
            sys.exit("package_count no cuadra")
        self.pool = t[sp_off:sp_off + sp_size]
        o = 0x30
        self.pkgs = []
        for _ in range(pc):
            tid, root, exe, rom, ver, kind, pflags = struct.unpack_from("<QIIIIBB", t, o)
            meta_off, meta_size = struct.unpack_from("<QI", t, o + 0x20)
            self.pkgs.append(dict(tid=tid, root=root, exefs=exe, romfs=rom, ver=ver,
                                  kind=kind, flags=pflags, meta_off=meta_off, meta_size=meta_size))
            o += 0x40
        self.dirs = []
        for _ in range(self.ndirs):
            no, nl, fc, cc = struct.unpack_from("<IIII", t, o)
            self.dirs.append((no, nl, fc, cc))
            o += 0x18
        self.files = []
        for _ in range(self.nfiles):
            no, nl, size, eoff, esize = struct.unpack_from("<IIQQQ", t, o)
            sha = t[o + 0x20:o + 0x40]
            codec = t[o + 0x40]
            if codec not in (0, 1):
                sys.exit(f"codec desconocido {codec}")
            if size and (eoff < self.blob_off or eoff + esize > self.file_size):
                sys.exit("extent fuera de rango")
            self.files.append((no, nl, size, eoff, esize, sha, codec))
            o += 0x50
        self.children_off = o

    def name(self, off, ln):
        n = self.pool[off:off + ln].decode("utf-8")
        if not n or n in (".", "..") or "/" in n or "\\" in n or "\0" in n:
            sys.exit(f"nombre inseguro en el TOC: {n!r}")
        return n

    def children(self, d):
        _, _, fc, cc = self.dirs[d]
        return struct.unpack_from(f"<{cc}I", self.toc, self.children_off + 4 * fc)

    def walk(self, d, rel=""):
        """Devuelve (ruta_relativa, idx_fichero) de todo el subárbol del dir d."""
        for node in self.children(d):
            if node < self.ndirs:
                no, nl, _, _ = self.dirs[node]
                yield from self.walk(node, f"{rel}{self.name(no, nl)}/")
            else:
                fi = node - self.ndirs
                no, nl = self.files[fi][:2]
                yield f"{rel}{self.name(no, nl)}", fi

    def meta(self, p):
        out = {}
        if not p["meta_off"]:
            return out
        self.f.seek(p["meta_off"])
        b = self.f.read(p["meta_size"])
        o = 0
        while o + 8 <= len(b):
            typ, _, sz = struct.unpack_from("<HHI", b, o)
            if o + 8 + sz > len(b):
                break
            if typ in (4, 5, 6, 8):
                out[{4: "version", 5: "titulo", 6: "editor", 8: "origen"}[typ]] = b[o + 8:o + 8 + sz].decode("utf-8", "replace")
            o += 8 + sz
        return out

    def dest(self, p, counters):
        k = p["kind"]
        if k == 0:
            return "base"
        if k == 1:
            return f"updates/{p['ver']}"
        if k == 2:
            n = counters.setdefault(p["tid"], 0)
            counters[p["tid"]] += 1
            return f"dlc/{p['tid']:016X}/{n}"
        return f"otros/{KINDS.get(k, k)}_{p['tid']:016X}_{p['ver']}"

    def extract_file(self, fi, out_path):
        _, _, size, eoff, esize, sha, codec = self.files[fi]
        h = hashlib.sha256()
        tmp = out_path + ".part"
        with open(tmp, "wb") as w:
            if size:
                self.f.seek(eoff)
                left = esize
                dec = zstd.ZstdDecompressor() if codec == 1 else None
                while left:
                    buf = self.f.read(min(CHUNK, left))
                    if not buf:
                        sys.exit("lectura corta")
                    left -= len(buf)
                    data = dec.decompress(buf) if dec else buf
                    h.update(data)
                    w.write(data)
                # vaciar lo que quede en el descompresor
                if dec:
                    while not dec.eof and dec.needs_input is False:
                        data = dec.decompress(b"")
                        if not data:
                            break
                        h.update(data)
                        w.write(data)
        if os.path.getsize(tmp) != size:
            sys.exit(f"tamaño incorrecto en {out_path}")
        if h.digest() != sha:
            sys.exit(f"SHA-256 incorrecto en {out_path}")
        os.replace(tmp, out_path)


def info(n):
    print(f"Paquetes: {n.pkg_count}  dirs: {n.ndirs}  ficheros: {n.nfiles}")
    counters = {}
    for p in n.pkgs:
        m = n.meta(p)
        files = list(n.walk(p["root"]))
        tot = sum(n.files[fi][2] for _, fi in files)
        print(f"- {KINDS.get(p['kind'], p['kind'])}: tid={p['tid']:016X} ver={p['ver']} "
              f"-> {n.dest(p, counters)}  {len(files)} ficheros, {tot/1e9:.2f} GB  {m}")
        tops = sorted({f.split('/')[0] for f, _ in files})
        print(f"    raíz: {tops}")


def extract(n, out):
    os.makedirs(out, exist_ok=True)
    counters = {}
    jobs = []
    for p in n.pkgs:
        d = n.dest(p, counters)
        for rel, fi in n.walk(p["root"]):
            jobs.append((os.path.join(out, d, rel), fi))
    total = sum(n.files[fi][2] for _, fi in jobs)
    done, t0 = 0, time.time()
    for i, (path, fi) in enumerate(jobs, 1):
        size = n.files[fi][2]
        if os.path.exists(path) and os.path.getsize(path) == size:
            done += size  # reanudación: ya extraído y verificado antes (se renombra solo tras verificar)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        n.extract_file(fi, path)
        done += size
        if i % 200 == 0 or size > 500e6:
            el = time.time() - t0
            print(f"[{i}/{len(jobs)}] {done/1e9:.1f}/{total/1e9:.1f} GB  {done/1e6/max(el,1):.0f} MB/s", flush=True)
    print(f"HECHO: {len(jobs)} ficheros, {total/1e9:.2f} GB, todos con SHA-256 verificado", flush=True)



def extract_subset(n, out, prefijos):
    """Extrae solo los ficheros cuya ruta (base/..., updates/<ver>/...) empieza por alguno de los prefijos."""
    counters, jobs = {}, []
    for p in n.pkgs:
        d = n.dest(p, counters)
        for rel, fi in n.walk(p["root"]):
            r = f"{d}/{rel}"
            if any(r.startswith(x) for x in prefijos): jobs.append((os.path.join(out, r), fi))
    for path, fi in jobs:
        if os.path.exists(path) and os.path.getsize(path) == n.files[fi][2]: continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        n.extract_file(fi, path)
    return len(jobs)

def update_dir(n):
    """'updates/<versión>' del paquete de actualización más nuevo (o 'base' si no hay)."""
    ups = [p for p in n.pkgs if p["kind"] == 1]
    return f"updates/{max(p['ver'] for p in ups)}" if ups else "base"

def verify(n):
    """Descomprime todo en memoria y comprueba el SHA-256 de cada fichero, sin escribir nada."""
    files = sorted({fi for p in n.pkgs for _, fi in n.walk(p["root"])})
    total = sum(n.files[fi][2] for fi in files)
    done, t0 = 0, time.time()
    for i, fi in enumerate(files, 1):
        _, _, size, eoff, esize, sha, codec = n.files[fi]
        h, got = hashlib.sha256(), 0
        if size:
            n.f.seek(eoff)
            left = esize
            dec = zstd.ZstdDecompressor() if codec == 1 else None
            while left:
                buf = n.f.read(min(CHUNK, left))
                if not buf:
                    sys.exit("lectura corta")
                left -= len(buf)
                data = dec.decompress(buf) if dec else buf
                h.update(data); got += len(data)
        if got != size or h.digest() != sha:
            sys.exit(f"FALLO: fichero #{fi} corrupto (tamaño {got}/{size})")
        done += size
        if i % 500 == 0:
            print(f"[{i}/{len(files)}] {done/1e9:.1f}/{total/1e9:.1f} GB  {done/1e6/max(time.time()-t0,1):.0f} MB/s", flush=True)
    print(f"VERIFICADO: {len(files)} ficheros, {total/1e9:.2f} GB, SHA-256 correcto en todos", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("info", "extract", "verify"):
        sys.exit(__doc__)
    nup = Nup(sys.argv[2])
    if sys.argv[1] == "info":
        info(nup)
    elif sys.argv[1] == "verify":
        verify(nup)
    else:
        extract(nup, sys.argv[3])
