#!/usr/bin/env python3
"""Collect third-party license/notice material for a built cadquery_ocp wheel.

Runs against the *repaired* wheel (after auditwheel / delocate / delvewheel have
vendored the native libraries), so it documents exactly what ships. It:

  * identifies every vendored shared library in the unpacked wheel tree,
  * copies each component's upstream license text into
    ``<pkg>/licenses/`` (and the standard ``*.dist-info/licenses/``),
  * writes ``THIRD-PARTY-NOTICES.txt`` (per-component license + source pointer),
    ``CORRESPONDING-SOURCE.txt`` (how to obtain the sources, for LGPL/FIPL §3),
    and ``BUILD-MANIFEST.txt`` (OCCT/OCP revisions, patches, build flags).

Backends, in priority order:

  * ``sbom``  - manylinux. auditwheel writes a CycloneDX SBOM to
    ``*.dist-info/sboms/*.json`` that already resolved every vendored library to
    its owning AlmaLinux 8 RPM (``pkg:rpm/almalinux/<name>@<nevra>``) *during*
    repair, while the original ``/usr/lib64`` paths were still known. We take
    that as the authoritative inventory and enrich each component by querying
    ``rpm`` *by package name* (never by the hash-renamed vendored file, which no
    RPM owns) for its SPDX license tag, source RPM and ``/usr/share/licenses``
    text.
  * ``conda`` - the micromamba-based mac/windows builds (no auditwheel SBOM);
    vendored libs come from the conda environment, read from ``conda-meta``.
  * ``degraded`` - neither available: SPDX tag + upstream URL from the built-in
    table only.

The OCCT LGPL + exception texts are always fetched from the pinned tag; OCCT is
built from source in-repo, so it is never an RPM and is handled separately.

This is best-effort for per-library detail, but it is *strict* about the things
that make the wheel non-redistributable if wrong: it fails if the OCCT LGPL
texts cannot be obtained, if no vendored libraries are found at all, or if a GPL
JBIG library is present.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Friendly display name + upstream URL keyed by the AlmaLinux *RPM* name that
# auditwheel's SBOM reports. The authoritative SPDX license comes from the RPM's
# own %{LICENSE} tag; this table only supplies a human-readable name, an upstream
# pointer, and (NOTES) any build-specific caveat.
RPM_KNOWN = {
    "OpenEXR-libs":  ("OpenEXR (IlmImf)", "https://openexr.com/"),
    "ilmbase":       ("IlmBase (OpenEXR)", "https://openexr.com/"),
    "freeimage":     ("FreeImage", "https://freeimage.sourceforge.io/"),
    "fmt":           ("fmt", "https://fmt.dev/"),
    "jxrlib":        ("jxrlib (JPEG XR)", "https://github.com/4creators/jxrlib"),
    "libgomp":       ("GCC OpenMP runtime (libgomp)", "https://gcc.gnu.org/"),
    "libgcc":        ("GCC runtime (libgcc_s)", "https://gcc.gnu.org/"),
    "libstdc++":     ("GCC runtime (libstdc++)", "https://gcc.gnu.org/"),
    "fontconfig":    ("Fontconfig", "https://www.freedesktop.org/wiki/Software/fontconfig/"),
    "freetype":      ("FreeType", "https://freetype.org/"),
    "LibRaw":        ("LibRaw", "https://www.libraw.org/"),
    "libraw":        ("LibRaw", "https://www.libraw.org/"),
    "libjpeg-turbo": ("libjpeg-turbo", "https://libjpeg-turbo.org/"),
    "libpng":        ("libpng", "http://www.libpng.org/pub/png/libpng.html"),
    "libtiff":       ("libtiff", "http://www.libtiff.org/"),
    "libwebp":       ("libwebp", "https://developers.google.com/speed/webp"),
    "lcms2":         ("Little CMS", "https://littlecms.com/"),
    "openjpeg2":     ("OpenJPEG", "https://www.openjpeg.org/"),
    "jasper-libs":   ("JasPer", "https://github.com/jasper-software/jasper"),
    "bzip2-libs":    ("bzip2", "https://sourceware.org/bzip2/"),
    "xz-libs":       ("xz / liblzma", "https://tukaani.org/xz/"),
    "zlib":          ("zlib", "https://zlib.net/"),
    "libuuid":       ("libuuid (util-linux)", "https://github.com/util-linux/util-linux"),
    "libwebp7":      ("libwebp", "https://developers.google.com/speed/webp"),
}
NOTES = {
    "libtiff": "rebuilt from the AlmaLinux 8 libtiff source RPM with the GPL JBIG "
               "codec disabled: ./configure --disable-jbig --disable-static "
               "--enable-ld-version-script CFLAGS=-O2 (no source modifications). "
               "See CORRESPONDING-SOURCE.txt / BUILD-MANIFEST.txt for the exact "
               "source RPM and steps.",
}

# Upstream identity keyed by normalised soname, for the conda (mac/windows) and
# degraded backends where there is no RPM to ask.
KNOWN = {
    "freeimage": ("FreeImage", "FreeImage Public License v1.0 (FIPL) / GPLv2 / GPLv3", "https://freeimage.sourceforge.io/"),
    "freetype": ("FreeType", "FreeType License (FTL) / GPLv2", "https://freetype.org/"),
    "fontconfig": ("Fontconfig", "MIT-style (fontconfig)", "https://www.freedesktop.org/wiki/Software/fontconfig/"),
    "raw": ("LibRaw", "LGPL-2.1-only / CDDL-1.0", "https://www.libraw.org/"),
    "jpeg": ("libjpeg-turbo", "IJG / BSD-3-Clause / zlib", "https://libjpeg-turbo.org/"),
    "turbojpeg": ("libjpeg-turbo", "IJG / BSD-3-Clause / zlib", "https://libjpeg-turbo.org/"),
    "png": ("libpng", "PNG Reference Library License v2 (libpng)", "http://www.libpng.org/pub/png/libpng.html"),
    "png16": ("libpng", "PNG Reference Library License v2 (libpng)", "http://www.libpng.org/pub/png/libpng.html"),
    "tiff": ("libtiff", "libtiff license (BSD-like)  [rebuilt without the GPL JBIG codec]", "http://www.libtiff.org/"),
    "webp": ("libwebp", "BSD-3-Clause", "https://developers.google.com/speed/webp"),
    "webpmux": ("libwebp", "BSD-3-Clause", "https://developers.google.com/speed/webp"),
    "webpdemux": ("libwebp", "BSD-3-Clause", "https://developers.google.com/speed/webp"),
    "sharpyuv": ("libwebp", "BSD-3-Clause", "https://developers.google.com/speed/webp"),
    "openjp2": ("OpenJPEG", "BSD-2-Clause", "https://www.openjpeg.org/"),
    "jasper": ("JasPer", "JasPer-2.0", "https://github.com/jasper-software/jasper"),
    "lcms2": ("Little CMS", "MIT", "https://littlecms.com/"),
    "half": ("IlmBase (OpenEXR)", "BSD-3-Clause", "https://openexr.com/"),
    "iex": ("IlmBase (OpenEXR)", "BSD-3-Clause", "https://openexr.com/"),
    "iexmath": ("IlmBase (OpenEXR)", "BSD-3-Clause", "https://openexr.com/"),
    "imath": ("IlmBase (OpenEXR)", "BSD-3-Clause", "https://openexr.com/"),
    "ilmthread": ("IlmBase (OpenEXR)", "BSD-3-Clause", "https://openexr.com/"),
    "ilmimf": ("OpenEXR (IlmImf)", "BSD-3-Clause", "https://openexr.com/"),
    "fmt": ("fmt", "MIT", "https://fmt.dev/"),
    "jpegxr": ("jxrlib (JPEG XR)", "BSD-2-Clause", "https://github.com/4creators/jxrlib"),
    "jxrglue": ("jxrlib (JPEG XR)", "BSD-2-Clause", "https://github.com/4creators/jxrlib"),
    "gomp": ("GCC OpenMP runtime (libgomp)", "GPL-3.0-or-later WITH GCC-exception-3.1", "https://gcc.gnu.org/"),
    "z": ("zlib", "Zlib", "https://zlib.net/"),
    "zstd": ("Zstandard", "BSD-3-Clause / GPLv2 (BSD used here)", "https://github.com/facebook/zstd"),
    "lzma": ("xz / liblzma", "0BSD / public domain", "https://tukaani.org/xz/"),
    "bz2": ("bzip2", "bzip2-1.0.6 (BSD-like)", "https://sourceware.org/bzip2/"),
    "deflate": ("libdeflate", "MIT", "https://github.com/ebiggers/libdeflate"),
    "expat": ("Expat", "MIT", "https://libexpat.github.io/"),
    "uuid": ("libuuid (util-linux)", "BSD-3-Clause", "https://github.com/util-linux/util-linux"),
    "jbig": ("libjbig", "GPL-2.0-or-later -- MUST NOT SHIP", "https://www.cl.cam.ac.uk/~mgk25/jbigkit/"),
    "stdc++": ("GCC runtime (libstdc++)", "GPL-3.0-or-later WITH GCC-exception-3.1", "https://gcc.gnu.org/"),
    "gcc_s": ("GCC runtime (libgcc_s)", "GPL-3.0-or-later WITH GCC-exception-3.1", "https://gcc.gnu.org/"),
}

# Canonical upstream license texts vendored in-repo, used when the distribution
# ships no %license text for a component (a *-libs runtime sub-package that
# carries none, or a library rebuilt from source and so owned by no RPM) and for
# header-only code that never appears as a vendored shared library. See
# license-fallbacks/README.md for the provenance of each text.
FALLBACKS_DIR = Path(__file__).resolve().parent / "license-fallbacks"

# AlmaLinux RPM name -> license-fallbacks/ subdir (sbom backend).
FALLBACK_BY_RPM = {
    "OpenEXR-libs": "OpenEXR",
    "ilmbase":      "OpenEXR",
    "jasper-libs":  "JasPer",
    "jxrlib":       "jxrlib",
    "xz-libs":      "xz",
    "libgomp":      "libgomp",
    "libtiff":      "libtiff",
}
# Normalised soname -> license-fallbacks/ subdir, for libraries folded in without
# an owning RPM (e.g. the source-rebuilt libtiff) and for the conda/degraded
# backends on mac/windows.
FALLBACK_BY_NORM = {
    "tiff": "libtiff",
    "half": "OpenEXR", "iex": "OpenEXR", "iexmath": "OpenEXR", "imath": "OpenEXR",
    "ilmthread": "OpenEXR", "ilmimf": "OpenEXR",
    "jasper": "JasPer",
    "jpegxr": "jxrlib", "jxrglue": "jxrlib",
    "lzma": "xz",
    "gomp": "libgomp",
}
# Header-only / statically-incorporated third-party code: compiled into the OCP
# extension or the OCCT libraries, so it ships inside the binaries but never as a
# separate shared library. Not discoverable from the vendored-lib scan, so it is
# listed explicitly. ``sub`` is its license-fallbacks/ subdir; ``ver_key`` picks
# the version string passed on the command line.
HEADER_ONLY = [
    {"name": "RapidJSON", "license": "MIT (bundled msinttypes BSD-3-Clause; bundled JSON license)",
     "url": "https://github.com/Tencent/rapidjson", "sub": "rapidjson", "ver_key": "rapidjson",
     "note": "header-only; compiled into the OCCT glTF read/write libraries (OCCT built with USE_RAPIDJSON=ON)"},
    {"name": "pybind11", "license": "BSD-3-Clause",
     "url": "https://github.com/pybind/pybind11", "sub": "pybind11", "ver_key": "pybind11",
     "note": "header-only; compiled into the OCP Python extension module (OCP*.so / OCP*.pyd)"},
]


# glibc / loader libraries are provided by the platform (manylinux policy) and
# are never vendored; ignore them if they ever appear in a closure.
PLATFORM_LIBS = re.compile(r"^(ld-linux.*|libc|libm|libdl|libpthread|librt|libutil|libnsl|libresolv)\b")

VAULT_BASE = "https://vault.almalinux.org/8/"


def log(msg: str) -> None:
    print(f"[collect-licenses] {msg}", flush=True)


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.strip()
    except Exception as exc:  # pragma: no cover - defensive
        log(f"command failed {cmd!r}: {exc}")
        return ""


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (pinned raw.githubusercontent URLs)
        return resp.read()


def norm_name(filename: str) -> str:
    """libFreeImage-abc12345.so.3 -> 'freeimage'; libTKernel-...so -> 'tkernel'."""
    base = re.sub(r"\.(so|dylib|dll|pyd)(\.[0-9].*)?$", "", filename, flags=re.I)
    base = re.sub(r"-[0-9a-f]{8,}$", "", base)          # auditwheel hash
    base = re.sub(r"[-.][0-9][0-9.]*$", "", base)       # trailing version
    base = re.sub(r"^(lib|cyg)", "", base, flags=re.I)
    return base.lower()


def is_occt(norm: str) -> bool:
    return norm.startswith("tk")


def soname_stem(basename: str) -> str | None:
    """Reduce a shared-library basename to its name stem.

    ``libIlmImf-2_2-f73e7954.so.22.0.0`` -> ``libIlmImf-2_2``
    ``libHalf.so.12.0.0``                -> ``libHalf``

    The 8-hex auditwheel suffix (``-<hash>`` inserted before the ``.so``/version,
    e.g. ``libHalf-5862efe9.so.12`` or ``libfreeimage-3-69ba4c2d.17.0.so``) is
    removed first so the stem matches the original RPM-owned filename.
    """
    b = re.sub(r"-[0-9a-f]{8}(?=\.)", "", basename)
    m = re.match(r"(.+?)\.(?:so|dylib)(?:\.|$)", b)
    return m.group(1) if m else None


def find_vendored_libs(root: Path) -> list[Path]:
    exts = (".so", ".dylib", ".dll")
    out = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name
        if name.startswith("OCP.") or name.startswith("OCP-"):  # the extension itself
            continue
        if ".so" in name or name.endswith(".dylib") or name.endswith(".dll"):
            if any(e in name for e in exts):
                out.append(p)
    return sorted(set(out))


def copy_license_dir(src: Path, dest: Path) -> list[str]:
    copied = []
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.rglob("*")):
            if f.is_file():
                target = dest / f.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                copied.append(f.name)
    return copied


def fallback_license_dir(rpm_name: str, norm: str) -> Path | None:
    """Vendored upstream license text for a component the distro ships none for."""
    sub = FALLBACK_BY_RPM.get(rpm_name) or FALLBACK_BY_NORM.get(norm)
    if sub:
        d = FALLBACKS_DIR / sub
        if d.is_dir():
            return d
        log(f"WARNING: expected fallback license dir {d} is missing")
    return None


def apply_fallback(entry: dict, dest: Path, rpm_name: str, norm: str) -> None:
    """If *entry* has no bundled distro license text, fill it from the vendored
    upstream text (if one is mapped). Marks the text source for the notice."""
    if entry.get("license_files"):
        entry.setdefault("text_source", "distro")
        return
    fb = fallback_license_dir(rpm_name, norm)
    if fb:
        entry["license_files"] = copy_license_dir(fb, dest)
        entry["text_source"] = "vendored"
        log(f"using vendored upstream license text for {entry['name']} (from {fb.name}/)")
    else:
        entry.setdefault("text_source", "distro")


def build_header_only(lic_dir: Path, versions: dict[str, str]) -> list[dict]:
    """License entries for header-only / statically-incorporated code."""
    out = []
    for h in HEADER_ONLY:
        dest = lic_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", h["name"])
        files = copy_license_dir(FALLBACKS_DIR / h["sub"], dest)
        if not files:
            log(f"WARNING: no vendored license text for header-only component {h['name']}")
        out.append({**h, "version": versions.get(h["ver_key"], ""), "license_files": files})
    return out


def ensure_ocp_license(pkg_dir: Path, local: str, url: str) -> None:
    """Guarantee the Apache-2.0 OCP LICENSE is present at <pkg>/LICENSE.

    setuptools packages it for the ``cadquery_ocp`` build but not for the
    renamed ``cadquery_ocp_novtk`` package (the package-data key is not
    renamed), so the THIRD-PARTY-NOTICES reference to ``<pkg>/LICENSE`` would
    otherwise dangle. Prefer the copy curled into the build tree; fall back to
    fetching it from the OCP repository."""
    target = pkg_dir / "LICENSE"
    if target.is_file() and target.stat().st_size > 0:
        log("OCP Apache LICENSE already present in package")
        return
    if local:
        p = Path(local)
        if p.is_file() and p.stat().st_size > 0:
            shutil.copy2(p, target)
            log(f"copied OCP Apache LICENSE into package from {local}")
            return
        log(f"note: --ocp-license {local} not found; will try the network")
    if url:
        try:
            target.write_bytes(fetch(url))
            log(f"fetched OCP Apache LICENSE into package from {url}")
            return
        except Exception as exc:
            log(f"WARNING: could not fetch OCP Apache LICENSE from {url}: {exc}")
    log("WARNING: OCP Apache LICENSE could not be ensured at <pkg>/LICENSE")


def prune_backup_files(root: Path) -> None:
    """Drop stray *.bak files (e.g. a WHEEL.bak left by an upstream ``sed -i.bak``)
    so they do not ride along into the final wheel/RECORD."""
    for bak in root.rglob("*.bak"):
        if bak.is_file():
            try:
                bak.unlink()
                log(f"pruned stray backup file {bak.relative_to(root)}")
            except OSError:
                pass


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #

def load_sbom(root: Path) -> dict | None:
    """Parse auditwheel's CycloneDX SBOM into {rpm_name: {version, purl, count}}.

    Returns None when no SBOM with RPM-provided components is present (i.e. this
    is not a manylinux/auditwheel build)."""
    for p in sorted(root.glob("*.dist-info/sboms/*.json")):
        try:
            data = json.loads(p.read_text())
        except Exception as exc:
            log(f"note: could not parse SBOM {p.name}: {exc}")
            continue
        self_name = ((data.get("metadata") or {}).get("component") or {}).get("name")
        comps: dict[str, dict] = {}
        for c in data.get("components") or []:
            name = c.get("name")
            purl = c.get("purl") or ""
            if not name or name == self_name or not purl.startswith("pkg:rpm/"):
                continue
            e = comps.setdefault(name, {"count": 0, "version": c.get("version") or "", "purl": purl})
            e["count"] += 1
        if comps:
            log(f"using auditwheel SBOM {p.name} ({len(comps)} RPM component(s))")
            return comps
    return None


def rpm_fields(name: str) -> dict | None:
    """Query an installed RPM *by name* for license / source RPM / url / version."""
    out = run(["rpm", "-q", "--qf", "%{LICENSE}\t%{SOURCERPM}\t%{URL}\t%{VERSION}-%{RELEASE}\n", name])
    if not out:
        return None
    line = out.splitlines()[0]
    if "is not installed" in line or line.startswith("package "):
        return None
    parts = line.split("\t")
    if len(parts) < 4:
        return None
    url = parts[2].strip()
    if url.lower() in ("(none)", "none", ""):
        url = ""
    return {"license": parts[0].strip(), "source": parts[1].strip(), "url": url, "version": parts[3].strip()}


def rpm_owned_stems(name: str) -> set[str]:
    """Soname stems of the shared libraries an installed RPM owns."""
    stems = set()
    for f in run(["rpm", "-ql", name]).splitlines():
        stem = soname_stem(os.path.basename(f.strip()))
        if stem:
            stems.add(stem)
    return stems


def conda_index(conda_prefix: Path) -> list[dict]:
    recs = []
    meta = conda_prefix / "conda-meta"
    if not meta.is_dir():
        return recs
    for j in meta.glob("*.json"):
        try:
            data = json.loads(j.read_text())
        except Exception:
            continue
        recs.append(data)
    return recs


def conda_info(norm: str, index: list[dict], conda_prefix: Path) -> dict | None:
    for rec in index:
        pkgname = rec.get("name", "")
        if norm and (norm in pkgname.replace("-", "").replace("_", "") or pkgname.replace("-", "") in norm):
            return {
                "pkg": pkgname,
                "version": str(rec.get("version", "")),
                "license": rec.get("license") or "",
                "source": rec.get("url") or rec.get("channel") or "conda-forge",
                "licenses_path": rec.get("extracted_package_dir"),
            }
    return None


# --------------------------------------------------------------------------- #
# Inventory builders (per backend) -> dict[key] = component entry
# --------------------------------------------------------------------------- #

def build_sbom_components(sbom: dict, third_party_files: list[Path], lic_dir: Path,
                          libtiff_srpm: str = "") -> dict:
    """Authoritative inventory from the SBOM, enriched via rpm, with vendored
    files attributed by soname stem."""
    # map each RPM to the soname stems it owns, for file attribution
    owned: dict[str, set[str]] = {name: rpm_owned_stems(name) for name in sbom}

    components: dict[str, dict] = {}
    for name, meta in sorted(sbom.items()):
        rec = rpm_fields(name)
        display, url = RPM_KNOWN.get(name, (name, ""))
        version = (rec["version"] if rec else "") or meta.get("version", "")
        license_txt = rec["license"] if rec and rec.get("license") else "unknown"
        source_rpm = rec["source"] if rec and rec.get("source") else ""
        if rec and rec.get("url") and not url:
            url = rec["url"]

        entry = {
            "name": display,
            "rpm": name,
            "version": version,
            "license": license_txt,
            "source_rpm": source_rpm,
            "url": url,
            "note": NOTES.get(name, ""),
            "files": [],
            "license_files": [],
        }

        dest = lic_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        entry["license_files"] = copy_license_dir(Path("/usr/share/licenses") / name, dest)
        apply_fallback(entry, dest, rpm_name=name, norm="")
        if not entry["license_files"]:
            log(f"note: no license text (distro or vendored) for {name} - recording SPDX tag + source RPM only")
        components[name] = entry

    # attribute vendored files to their owning RPM by soname stem; anything the
    # SBOM does not cover (e.g. libtiff, which this repo rebuilds from source so
    # it is owned by no RPM) is folded in from the soname KNOWN table so it is
    # still listed.
    for lib in third_party_files:
        stem = soname_stem(lib.name)
        hit = None
        if stem:
            for name, stems in owned.items():
                if stem in stems:
                    hit = name
                    break
        if hit:
            components[hit]["files"].append(lib.name)
            continue
        norm = norm_name(lib.name)
        known = KNOWN.get(norm)
        display = known[0] if known else norm
        log(f"note: {lib.name} not in auditwheel SBOM (not RPM-owned); "
            f"recording from built-in table as '{display}'")
        entry = components.get(display)
        if entry is None:
            entry = {
                "name": display,
                "rpm": "",
                "version": "",
                "license": known[1] if known else "unknown",
                "source_rpm": libtiff_srpm if norm == "tiff" else "",
                "url": known[2] if known else "",
                "note": NOTES.get("libtiff") if norm == "tiff" else "",
                "files": [],
                "license_files": [],
            }
            dest = lic_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", display)
            apply_fallback(entry, dest, rpm_name="", norm=norm)
            components[display] = entry
        entry["files"].append(lib.name)
    return components


def build_nonlinux_components(third_party_files: list[Path], backend: str, lic_dir: Path) -> dict:
    """conda / degraded inventory keyed by normalised soname."""
    cindex = conda_index(Path(os.environ["CONDA_PREFIX"])) if backend == "conda" else []
    components: dict[str, dict] = {}
    for lib in third_party_files:
        norm = norm_name(lib.name)
        known = KNOWN.get(norm)
        rec = conda_info(norm, cindex, Path(os.environ["CONDA_PREFIX"])) if backend == "conda" else None
        display = known[0] if known else (rec["pkg"] if rec else norm)
        if display in components:
            components[display]["files"].append(lib.name)
            continue
        entry = {
            "name": display,
            "rpm": "",
            "version": rec["version"] if rec else "",
            "license": (rec["license"] if rec and rec.get("license") else (known[1] if known else "unknown")),
            "source_rpm": "",
            "url": known[2] if known else "",
            "note": "",
            "files": [lib.name],
            "license_files": [],
        }
        dest = lic_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", display)
        if backend == "conda" and rec and rec.get("licenses_path"):
            lp = Path(rec["licenses_path"]) / "info" / "licenses"
            entry["license_files"] = copy_license_dir(lp, dest)
        apply_fallback(entry, dest, rpm_name="", norm=norm)
        if not entry["license_files"]:
            log(f"note: no license text (conda or vendored) for {display} - recording SPDX tag + source pointer only")
        components[display] = entry
    return components


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel-root", required=True, help="unpacked wheel directory (contains <pkg>/ and *.dist-info)")
    ap.add_argument("--pkg", required=True, help="import package dir, e.g. cadquery_ocp_novtk")
    ap.add_argument("--occt-version", required=True)
    ap.add_argument("--occt-tag", required=True, help="e.g. V8_0_1")
    ap.add_argument("--occt-repo", default="https://github.com/Open-Cascade-SAS/OCCT")
    ap.add_argument("--ocp-version", required=True)
    ap.add_argument("--ocp-source-url", required=True)
    ap.add_argument("--occt-patches", default="")
    ap.add_argument("--build-info", default="")
    ap.add_argument("--ocp-license", default="",
                    help="path to the Apache-2.0 OCP LICENSE to guarantee at <pkg>/LICENSE")
    ap.add_argument("--ocp-license-url",
                    default="https://raw.githubusercontent.com/CadQuery/OCP/refs/heads/master/LICENSE",
                    help="fallback URL for the OCP LICENSE if --ocp-license is absent")
    ap.add_argument("--libtiff-srpm", default="",
                    help="exact AlmaLinux source RPM libtiff was rebuilt from (Linux only)")
    ap.add_argument("--rapidjson-rev", default="", help="RapidJSON revision compiled into OCCT")
    ap.add_argument("--pybind11-version", default="", help="pybind11 version compiled into the OCP extension")
    args = ap.parse_args()

    root = Path(args.wheel_root)
    pkg_dir = root / args.pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    lic_dir = pkg_dir / "licenses"
    lic_dir.mkdir(parents=True, exist_ok=True)

    # guarantee the Apache-2.0 OCP LICENSE the notices reference is in the package
    ensure_ocp_license(pkg_dir, args.ocp_license, args.ocp_license_url)

    sbom = load_sbom(root)
    if sbom is not None and shutil.which("rpm"):
        backend = "sbom"
    elif os.environ.get("CONDA_PREFIX"):
        backend = "conda"
    else:
        backend = "degraded"
    log(f"backend={backend}")

    # --- OCCT LGPL + exception (always, from the pinned tag) ----------------
    occt_dir = lic_dir / "OpenCASCADE-OCCT"
    occt_dir.mkdir(parents=True, exist_ok=True)
    base = f"{args.occt_repo}/raw/{args.occt_tag}"
    try:
        (occt_dir / "LICENSE_LGPL_21.txt").write_bytes(fetch(f"{base}/LICENSE_LGPL_21.txt"))
        (occt_dir / "OCCT_LGPL_EXCEPTION.txt").write_bytes(fetch(f"{base}/OCCT_LGPL_EXCEPTION.txt"))
        log("fetched OCCT LGPL + exception")
    except Exception as exc:
        log(f"FATAL: could not fetch OCCT license texts: {exc}")
        return 2

    # --- enumerate vendored libraries ---------------------------------------
    libs = find_vendored_libs(root)
    log(f"found {len(libs)} vendored library file(s)")
    if not libs:
        log("FATAL: no vendored libraries found - collection logic is wrong for this layout")
        return 3

    occt_count = 0
    third_party_files: list[Path] = []
    for lib in libs:
        norm = norm_name(lib.name)
        if PLATFORM_LIBS.match(f"lib{norm}"):
            continue
        if "jbig" in norm:
            log("FATAL: GPL JBIG library present in wheel")
            return 4
        if is_occt(norm):
            occt_count += 1
            continue
        third_party_files.append(lib)

    if backend == "sbom":
        components = build_sbom_components(sbom, third_party_files, lic_dir,
                                           libtiff_srpm=args.libtiff_srpm)
    else:
        components = build_nonlinux_components(third_party_files, backend, lic_dir)

    # header-only / statically incorporated code (compiled into the binaries,
    # never shipped as a separate shared library)
    header_only = build_header_only(lic_dir, {
        "rapidjson": args.rapidjson_rev,
        "pybind11": args.pybind11_version,
    })

    log(f"OCCT libraries: {occt_count}; other components: {len(components)}; "
        f"header-only: {len(header_only)}")

    # --- write the notices ---------------------------------------------------
    occt_block = (
        f"Open CASCADE Technology (OCCT) {args.occt_version}\n"
        f"  Shared libraries: {occt_count} (libTK*)\n"
        f"  License: LGPL-2.1-only WITH the Open CASCADE Exception (see licenses/OpenCASCADE-OCCT/)\n"
        f"  Source:  {args.occt_repo} @ tag {args.occt_tag}\n"
        f"  Applied patches (this repo): {args.occt_patches or 'none'}\n"
    )

    lines = [
        "THIRD-PARTY NOTICES",
        "===================",
        "",
        "This wheel bundles the following native libraries in addition to the",
        f"Apache-2.0 licensed OCP binding code (see {args.pkg}/LICENSE).",
        "Full license texts are under this package's licenses/ directory.",
        "",
        occt_block,
    ]
    for entry in sorted(components.values(), key=lambda e: e["name"].lower()):
        if entry["license_files"]:
            lf = ", ".join(sorted(set(entry["license_files"])))
            if entry.get("text_source") == "vendored":
                lf += " (upstream canonical text, vendored by ocp-build-system)"
        else:
            lf = "(text not bundled by distro; see Source/URL)"
        block = [
            f"{entry['name']} {entry['version']}".rstrip(),
            f"  License: {entry['license']}",
            f"  Upstream: {entry['url'] or 'n/a'}",
        ]
        if entry.get("source_rpm"):
            block.append(f"  Source RPM: {entry['source_rpm']}  (AlmaLinux 8 vault; see CORRESPONDING-SOURCE.txt)")
        else:
            block.append(f"  Source package: {entry.get('source_rpm') or 'see CORRESPONDING-SOURCE.txt'}")
        if entry.get("note"):
            block.append(f"  Note: {entry['note']}")
        block += [
            f"  Bundled license text: {lf}",
            f"  Vendored files: {', '.join(sorted(entry['files'])) if entry['files'] else '(see SBOM)'}",
            "",
        ]
        lines += block

    if header_only:
        lines += [
            "STATICALLY INCORPORATED / HEADER-ONLY COMPONENTS",
            "------------------------------------------------",
            "The following third-party code is compiled into the binaries above and",
            "ships inside them; it is not distributed as a separate shared library.",
            "",
        ]
        for h in header_only:
            lf = (", ".join(sorted(set(h["license_files"]))) if h["license_files"]
                  else "(see Upstream)")
            lines += [
                f"{h['name']} {h['version']}".rstrip(),
                f"  License: {h['license']}",
                f"  Upstream: {h['url']}",
                f"  Note: {h['note']}",
                f"  Bundled license text: {lf}",
                "",
            ]
    (pkg_dir / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(lines))

    # corresponding-source offer (satisfies LGPL-2.1 and FIPL source clauses)
    srpms = sorted({e["source_rpm"] for e in components.values() if e.get("source_rpm")})
    cs = [
        "CORRESPONDING SOURCE",
        "====================",
        "",
        "The complete corresponding source for every component bundled in this wheel",
        "is publicly available at the locations below. For any component, the exact",
        "source can also be requested by opening an issue at",
        "https://github.com/CadQuery/ocp-build-system/issues .",
        "",
        "* OCP binding generator and this build system: https://github.com/CadQuery/ocp-build-system",
        f"* OCP sources/stubs for this release: {args.ocp_source_url}",
        f"* OCCT {args.occt_version}: {args.occt_repo} @ tag {args.occt_tag}",
        "",
    ]
    if srpms:
        cs += [
            "Bundled third-party libraries are the distribution's own binary packages",
            "(see the exact RPM versions in THIRD-PARTY-NOTICES.txt). Their complete",
            "corresponding source is the following AlmaLinux 8 source RPMs, each",
            f"locatable by name under the 'Source' trees of {VAULT_BASE}",
            "(BaseOS / AppStream / PowerTools) and the EPEL 8 source tree:",
            "",
        ]
        cs += [f"  - {s}" for s in srpms]
        cs += [
            "",
            "libtiff is rebuilt from its distribution source RPM with the GPL JBIG",
            "codec disabled; the only modification is the configure flag --disable-jbig.",
            "",
        ]
    else:
        cs += [
            "Bundled third-party libraries are built from their distribution's source",
            "packages (identical upstream source, distro patches); the exact package",
            "names and versions are recorded in THIRD-PARTY-NOTICES.txt.",
            "",
        ]
    (pkg_dir / "CORRESPONDING-SOURCE.txt").write_text("\n".join(cs))

    # build manifest (answers "exact revisions / patches / flags")
    manifest = [
        "BUILD MANIFEST",
        "==============",
        "",
        f"cadquery-ocp wheel version : {args.ocp_version}",
        f"OCCT                       : {args.occt_version}  ({args.occt_repo} @ {args.occt_tag})",
        f"OCCT patches               : {args.occt_patches or 'none'}",
        f"OCP sources                : {args.ocp_source_url}",
        "",
        args.build_info or "",
    ]
    (pkg_dir / "BUILD-MANIFEST.txt").write_text("\n".join(manifest))

    # drop any stray backup files before the notices are mirrored / packed
    prune_backup_files(root)

    # also drop the notices into the standard .dist-info/licenses location
    for dist_info in root.glob("*.dist-info"):
        dl = dist_info / "licenses"
        dl.mkdir(parents=True, exist_ok=True)
        for f in ("THIRD-PARTY-NOTICES.txt", "CORRESPONDING-SOURCE.txt", "BUILD-MANIFEST.txt"):
            shutil.copy2(pkg_dir / f, dl / f)
        if (pkg_dir / "LICENSE").is_file():
            shutil.copy2(pkg_dir / "LICENSE", dl / "LICENSE")
        if lic_dir.is_dir():
            shutil.copytree(lic_dir, dl, dirs_exist_ok=True)

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
