import json
import os

from hub.lang import T

from camilab.bloques import SPECS


def struct_ports(node):
    t = node["type"]
    p = []
    nsr = int(node["params"].get("sr", 0))
    if t in ("while", "for"):
        if t == "for":
            p.append(("N", "in", "outer", "num", "N"))
        p.append(("i", "out", "inner", "num", "i"))
        if t == "while":
            p.append(("stop", "in", "inner", "bool", "stop"))
        for k in range(nsr):
            p.append(("sr%d_in" % k, "in", "outer", "any", T("valor inicial")))
            p.append(("sr%d_l" % k, "out", "inner", "any", T("valor anterior")))
            p.append(("sr%d_r" % k, "in", "inner", "any", T("valor siguiente")))
            p.append(("sr%d_out" % k, "out", "outer", "any", T("valor final")))
    elif t == "case":
        p.append(("sel", "in", "outer", "any", "?"))
        for k in range(int(node["params"].get("outs", 0))):
            p.append(("o%d_i" % k, "in", "inner", "any", T("salida %d") % k))
            p.append(("o%d" % k, "out", "outer", "any", T("salida %d") % k))
    return p


def ports(node):
    s = SPECS[node["type"]]
    if s.kind == "struct":
        return struct_ports(node)
    return ([(n, "in", "outer", t, lbl) for n, t, _d, lbl in s.ins] +
            [(n, "out", "outer", t, lbl) for n, t, lbl in s.outs])


def const_text(node):
    v = node["params"].get("value", 0)
    t = node["type"]
    if t == "const_bool":
        return "T" if v else "F"
    if t == "const_str":
        return '"%s"' % v
    return "%g" % float(v)


def node_size(node):
    s = SPECS[node["type"]]
    if s.kind == "struct":
        return node.get("w", 300), node.get("h", 200)
    nin, nout = len(s.ins), len(s.outs)
    if s.kind == "io":
        return 150, 24 + 16 * max(nin, nout, 1) + 6
    if s.kind == "const":
        return max(38, 8 * len(const_text(node)) + 14), 22
    if s.kind in ("ctl", "ind"):
        return 46, max(26, 14 * max(nin, nout) + 6)
    return max(36, 9 * len(s.sym or "") + 14), max(30, 14 * max(nin, nout) + 6)


def new_panel():
    return {"rows": 3, "cols": 4, "title": {"text": "", "image": None},
            "footer": {"on": False, "text": "", "image": None},
            "items": {}, "texts": []}


def new_doc():
    return {"camilab": 1, "nodes": {}, "wires": [], "next": 1, "panel": new_panel()}


def add_node(doc, tid, x, y, **params):
    nid = "n%d" % doc["next"]
    doc["next"] += 1
    s = SPECS[tid]
    p = {}
    for name, _k, default, _l in s.params:
        p[name] = default
    if s.kind == "ctl" or s.kind == "ind":
        p.setdefault("label", T(s.label))
        p.setdefault("units", "")
        if tid in ("ctl_num", "ctl_knob", "ctl_slider", "ind_gauge", "ind_bar"):
            p.setdefault("min", 0.0)
            p.setdefault("max", 10.0)
        if tid in ("ctl_num", "ctl_knob", "ctl_slider"):
            p.setdefault("value", 0.0)
        if tid == "ctl_ring":
            p.setdefault("options", T("Opción A") + ";" + T("Opción B") + ";" + T("Opción C"))
            p.setdefault("value", 0.0)
        if tid == "ctl_color":
            p.setdefault("value", [255, 0, 0])
        if tid in ("ctl_bool", "ctl_stop"):
            p.setdefault("value", False)
        if tid == "ctl_str":
            p.setdefault("value", "")
        if tid == "ind_chart":
            p.setdefault("hist", 200)
    if tid in ("while", "for"):
        p.setdefault("sr", 0)
    if tid == "case":
        p.setdefault("outs", 0)
        p.setdefault("view", 1)
    p.update(params)
    n = {"id": nid, "type": tid, "x": float(x), "y": float(y), "params": p, "frame": 0}
    if s.kind == "struct":
        n["w"], n["h"] = float(p.pop("w", 320)), float(p.pop("h", 200))
    doc["nodes"][nid] = n
    return nid


def add_wire(doc, a, ap, b, bp, frame=0):
    doc["wires"] = [w for w in doc["wires"] if not (w["dst"] == [b, bp] and
                                                    w.get("frame", 0) == frame)]
    w = {"src": [a, ap], "dst": [b, bp], "frame": frame}
    doc["wires"].append(w)
    return w


def remove_node(doc, nid):
    doc["nodes"].pop(nid, None)
    doc["wires"] = [w for w in doc["wires"] if w["src"][0] != nid and w["dst"][0] != nid]


def rect(node):
    w, h = node_size(node)
    return node["x"], node["y"], w, h


def is_desc(parent, nid, sid):
    cur = parent.get(nid)
    while cur is not None:
        if cur == sid:
            return True
        cur = parent.get(cur)
    return False


def compute_parents(doc):
    nodes = doc["nodes"]
    structs = [n for n in nodes.values() if SPECS[n["type"]].kind == "struct"]
    structs.sort(key=lambda n: n["w"] * n["h"])
    parent = {}
    for n in nodes.values():
        x, y, w, h = rect(n)
        cx, cy = x + w / 2.0, y + h / 2.0
        area = w * h
        parent[n["id"]] = None
        for s in structs:
            if s["id"] == n["id"] or s["w"] * s["h"] <= area:
                continue
            if s["x"] < cx < s["x"] + s["w"] and s["y"] < cy < s["y"] + s["h"]:
                parent[n["id"]] = s["id"]
                break
    return parent



def load_cami(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if "nodes" not in doc:
        raise ValueError(T("No es un archivo de CamiLab."))
    for n in doc["nodes"].values():
        if n["type"] not in SPECS:
            raise ValueError(T("Bloque desconocido: %s") % n["type"])
        n.setdefault("frame", 0)
        n.setdefault("params", {})
    for w in doc["wires"]:
        w.setdefault("frame", 0)
    p = doc.setdefault("panel", new_panel())
    for k, v in new_panel().items():
        p.setdefault(k, v)
    return doc


def save_json(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
