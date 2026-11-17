import threading
import time

from PyQt5.QtCore import QThread, pyqtSignal

from hub.lang import T

from camilab.bloques import SPECS
from camilab.documento import compute_parents, is_desc


class Abort(Exception):
    pass


class VIError(Exception):
    def __init__(self, msg, nid=None):
        Exception.__init__(self, msg)
        self.nid = nid


class Ctx(object):
    def __init__(self):
        self.stop_flag = threading.Event()
        self.sessions = []
        self.t0 = time.perf_counter()
        self.project_port = ""

    def check(self):
        if self.stop_flag.is_set():
            raise Abort()

    def sleep(self, s):
        end = time.perf_counter() + s
        while True:
            self.check()
            left = end - time.perf_counter()
            if left <= 0:
                return
            time.sleep(min(0.02, left))

    def log(self, title, result):
        pass

    def note(self, title, text):
        pass

    def ctl(self, nid):
        return 0.0

    def show(self, nid, value):
        pass

    def close_all(self):
        for w in list(self.sessions):
            try:
                w.close()
            except Exception:
                pass
        self.sessions = []


class Engine(object):
    def __init__(self, doc, ctx):
        self.doc = doc
        self.ctx = ctx
        self.nodes = doc["nodes"]
        self.wires = doc["wires"]
        self.parent = compute_parents(doc)
        self.kind = {nid: SPECS[n["type"]].kind for nid, n in self.nodes.items()}
        self.values = {}
        self.tunnel = {}
        self.order_cache = {}
        self.inw = {}
        for i, w in enumerate(self.wires):
            self.inw.setdefault(tuple(w["dst"]), []).append(i)
        self.children = {}
        for nid in self.nodes:
            p = self.parent[nid]
            f = self.nodes[nid].get("frame", 0) if p and self.nodes[p]["type"] == "case" else 0
            self.children.setdefault((p, f), []).append(nid)

    def member(self, nid, sid, f):
        cur = nid
        while cur is not None:
            p = self.parent[cur]
            if p == sid:
                if sid is not None and self.nodes[sid]["type"] == "case" and \
                        self.nodes[cur].get("frame", 0) != f:
                    return None
                return cur
            cur = p
        return None

    def order(self, sid, f):
        key = (sid, f)
        if key in self.order_cache:
            return self.order_cache[key]
        mem = list(self.children.get(key, []))
        deps = {m: set() for m in mem}
        for w in self.wires:
            a = self.member(w["src"][0], sid, f)
            b = self.member(w["dst"][0], sid, f)
            if a is not None and b is not None and a != b:
                deps[b].add(a)
        out = []
        ready = sorted([m for m in mem if not deps[m]],
                       key=lambda m: (self.nodes[m]["x"], self.nodes[m]["y"]))
        done = set()
        while ready:
            m = ready.pop(0)
            out.append(m)
            done.add(m)
            new = [k for k in mem if k not in done and k not in out and k not in ready
                   and deps[k] <= done]
            ready = sorted(ready + new, key=lambda k: (self.nodes[k]["x"], self.nodes[k]["y"]))
        if len(out) != len(mem):
            bad = [m for m in mem if m not in done][0]
            raise VIError(T("Hay un ciclo de cables (un valor depende de sí mismo). "
                            "Dentro de un lazo usa un shift register."), bad)
        self.order_cache[key] = out
        return out

    def read_wire(self, i):
        if i in self.tunnel:
            return self.tunnel[i]
        w = self.wires[i]
        return self.values.get(tuple(w["src"]))

    def read(self, nid, port, default, frame=None):
        ids = self.inw.get((nid, port), [])
        if frame is not None:
            ids = [i for i in ids if self.wires[i].get("frame", 0) == frame]
        if not ids:
            return self.nodes[nid]["params"].get("def_" + port, default)
        v = self.read_wire(ids[0])
        return default if v is None else v

    def wired(self, nid, port):
        return bool(self.inw.get((nid, port)))

    def run(self):
        try:
            self.scope(None, 0)
        finally:
            self.ctx.close_all()

    def scope(self, sid, f):
        for nid in self.order(sid, f):
            self.ctx.check()
            k = self.kind[nid]
            if k == "struct":
                t = self.nodes[nid]["type"]
                if t == "case":
                    self.case(nid)
                else:
                    self.loop(nid, t)
            else:
                self.exec_node(nid)

    def exec_node(self, nid):
        n = self.nodes[nid]
        s = SPECS[n["type"]]
        inp = {}
        for name, _t, default, _l in s.ins:
            inp[name] = self.read(nid, name, default)
        try:
            out = s.fn(self.ctx, n, inp) or {}
        except Abort:
            raise
        except VIError:
            raise
        except Exception as e:
            raise VIError("%s: %s" % (T(s.label), e), nid)
        for k, v in out.items():
            self.values[(nid, k)] = v

    def leaving(self, sid):
        out = []
        for i, w in enumerate(self.wires):
            a, b = w["src"][0], w["dst"][0]
            if is_desc(self.parent, a, sid) and not is_desc(self.parent, b, sid) and b != sid:
                out.append(i)
        return out

    def loop(self, sid, t):
        n = self.nodes[sid]
        nsr = int(n["params"].get("sr", 0))
        leave = self.leaving(sid)
        sr = [self.read(sid, "sr%d_in" % k, 0.0) for k in range(nsr)]
        count = None
        if t == "for":
            try:
                count = int(float(self.read(sid, "N", 0)))
            except (TypeError, ValueError):
                raise VIError(T("N del For Loop debe ser un número."), sid)
            acc = {i: [] for i in leave}
        it = 0
        while True:
            if count is not None and it >= count:
                break
            self.ctx.check()
            self.values[(sid, "i")] = float(it)
            for k in range(nsr):
                self.values[(sid, "sr%d_l" % k)] = sr[k]
            self.scope(sid, 0)
            for k in range(nsr):
                if self.wired(sid, "sr%d_r" % k):
                    sr[k] = self.read(sid, "sr%d_r" % k, sr[k])
            if count is not None:
                for i in leave:
                    acc[i].append(self.read_wire(i))
            it += 1
            if t == "while":
                if not self.wired(sid, "stop"):
                    raise VIError(T("El While Loop no tiene cableada su terminal Stop."), sid)
                if bool(self.read(sid, "stop", True)):
                    break
                if it % 50 == 0:
                    time.sleep(0)
        for k in range(nsr):
            self.values[(sid, "sr%d_out" % k)] = sr[k]
        for i in leave:
            self.tunnel[i] = acc[i] if count is not None else self.read_wire(i)

    def case(self, sid):
        n = self.nodes[sid]
        sel = self.read(sid, "sel", False)
        if isinstance(sel, (list, tuple)):
            raise VIError(T("El selector del Case no puede ser un arreglo."), sid)
        f = 1 if sel else 0
        self.scope(sid, f)
        for k in range(int(n["params"].get("outs", 0))):
            self.values[(sid, "o%d" % k)] = self.read(sid, "o%d_i" % k, 0.0, frame=f)


def hexs(b):
    return " ".join("%02X" % x for x in b)


def rx_text(b):
    if not b:
        return T("(nada: timeout)")
    if b.endswith(b"\n"):
        return "'%s\\n'" % b.decode("latin-1").rstrip("\r\n")
    return " ".join("'%s'" % chr(x) if 32 <= x < 127 else "%02X" % x for x in b)


class RunCtx(Ctx):
    def __init__(self, win):
        Ctx.__init__(self)
        self.win = win
        self.lock = threading.Lock()
        self.latest = {}
        self.feeds = {}
        self.lines = []
        self.charts = {nid for nid, n in win.doc["nodes"].items() if n["type"] == "ind_chart"}
        self.vals = win.panel.ctl_values
        self.defaults = {nid: n["params"].get("value") for nid, n in win.doc["nodes"].items()}

    def ctl(self, nid):
        v = self.vals.get(nid)
        return self.defaults.get(nid, 0.0) if v is None else v

    def show(self, nid, v):
        with self.lock:
            if nid in self.charts:
                self.feeds.setdefault(nid, []).append(v)
            else:
                self.latest[nid] = v

    def log(self, title, r):
        line = "%-18s → %-22s ← %-16s %5.1f ms" % (title, hexs(r.tx), rx_text(r.rx), r.ms)
        with self.lock:
            self.lines.append(line)

    def note(self, title, text):
        with self.lock:
            self.lines.append("- %s: %s" % (title, text))

    def take(self):
        with self.lock:
            a, b, c = self.latest, self.feeds, self.lines
            self.latest, self.feeds, self.lines = {}, {}, []
        return a, b, c


class EngineThread(QThread):
    done = pyqtSignal(str, str)

    def __init__(self, doc, ctx):
        QThread.__init__(self)
        self.doc = doc
        self.ctx = ctx

    def run(self):
        try:
            Engine(self.doc, self.ctx).run()
            self.done.emit("", "")
        except Abort:
            self.done.emit("abort", "")
        except VIError as e:
            self.done.emit(str(e), e.nid or "")
        except Exception as e:
            self.done.emit(T("Error inesperado: %s") % e, "")
