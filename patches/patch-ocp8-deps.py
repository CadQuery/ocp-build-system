#!/usr/bin/env python
"""Adapt ocp_gordon and ocpsvg to the OCP 8 API, in place in site-packages.

Neither project supports OCP 8 yet:
  * the NCollection typedefs moved from OCP.TColStd / OCP.TColgp into OCP.collections
  * OCP 8.0.0.0 binds Array2_*.__call__ with Array1's single-index signature, so
    arr(i, j) returns NotImplemented; arr.Value(i, j) works

Idempotent: re-running on already-patched files is a no-op.
Remove once both projects release OCP 8 support.
"""
import re, sys, sysconfig, os

MOVED = {
    "TColStd_Array1OfInteger":  "Array1_int",
    "TColStd_Array1OfReal":     "Array1_double",
    "TColStd_Array2OfReal":     "Array2_double",
    "TColStd_HArray1OfInteger": "HArray1_int",
    "TColStd_HArray1OfReal":    "HArray1_double",
    "TColgp_Array1OfPnt":       "Array1_gp_Pnt",
    "TColgp_Array2OfPnt":       "Array2_gp_Pnt",
    "TColgp_HArray1OfPnt":      "HArray1_gp_Pnt",
    "TColgp_HArray1OfPnt2d":    "HArray1_gp_Pnt2d",
}
# identifiers that hold an Array2_* and are called as arr(row, col)
ARRAY2_VARS = {"points", "matrix", "point", "equivalent", "control_points_matrix",
               "cp_surf", "intersection_points", "poles", "weights"}

IMPORT_RE = re.compile(r'^([ \t]*)from OCP\.(TColStd|TColgp) import (?:\(([^)]*)\)|([^\n]*))$', re.M)


def fix_imports(src):
    moved_here = []

    def repl(m):
        indent, mod = m.group(1), m.group(2)
        body = m.group(3) if m.group(3) is not None else m.group(4)
        names = [n.strip() for n in body.split(",") if n.strip()]
        stay = [n for n in names if n not in MOVED]
        move = [MOVED[n] for n in names if n in MOVED]
        if not move:
            return m.group(0)
        moved_here.extend(move)
        out = []
        if stay:
            out.append("%sfrom OCP.%s import %s" % (indent, mod, ", ".join(stay)))
        out.append("%sfrom OCP.collections import %s" % (indent, ", ".join(sorted(set(move)))))
        return "\n".join(out)

    src = IMPORT_RE.sub(repl, src)
    for old, new in MOVED.items():
        src = re.sub(r'\b%s\b' % old, new, src)
    return src, moved_here


def split_top(s):
    depth, parts, cur = 0, [], ""
    for ch in s:
        if ch in "([{": depth += 1
        elif ch in ")]}": depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def fix_array2_calls(src):
    """arr(row, col) -> arr.Value(row, col); leaves single-argument calls alone."""
    name_re = re.compile(r'\b(%s)\(' % "|".join(sorted(ARRAY2_VARS)))
    out, i, n = [], 0, 0
    while True:
        m = name_re.search(src, i)
        if not m:
            out.append(src[i:]); break
        j, depth = m.end(), 1
        while j < len(src) and depth:
            if src[j] in "([{": depth += 1
            elif src[j] in ")]}": depth -= 1
            j += 1
        args = src[m.end():j - 1]
        if len(split_top(args)) == 2 and (m.start() == 0 or src[m.start() - 1] != "."):
            out.append(src[i:m.start()])
            out.append("%s.Value(%s)" % (m.group(1), args))
            n += 1
        else:
            out.append(src[i:j])
        i = j
    return "".join(out), n


def locate(pkg):
    """Package directory, whether installed normally or editable from a checkout."""
    import importlib.util
    spec = importlib.util.find_spec(pkg)
    if spec is None or not spec.origin:
        sys.exit("ERROR: %s is not importable" % pkg)
    return os.path.dirname(spec.origin)


def main():
    total_imports = total_calls = 0
    for pkg, do_calls in (("ocp_gordon", True), ("ocpsvg", False)):
        root = locate(pkg)
        print("%s -> %s" % (pkg, root))
        for dp, _, fs in os.walk(root):
            for f in sorted(fs):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dp, f)
                with open(p, encoding="utf-8") as fh:
                    src = orig = fh.read()
                src, moved = fix_imports(src)
                calls = 0
                if do_calls:
                    src, calls = fix_array2_calls(src)
                if src != orig:
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(src)
                    total_imports += len(moved); total_calls += calls
                    print("  patched %s (%d imports, %d Array2 calls)"
                          % (os.path.relpath(p, root), len(moved), calls))
    print("ocp8 dep patch: %d imports moved, %d Array2 calls rewritten" % (total_imports, total_calls))


if __name__ == "__main__":
    main()
