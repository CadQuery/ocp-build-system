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

Backends: ``rpm`` on manylinux, ``conda`` on the micromamba-based mac/windows
builds. The OCCT LGPL + exception texts are always fetched from the pinned tag.

This is best-effort for per-library detail (missing distro license dirs only
degrade to a recorded SPDX tag + upstream URL), but it is *strict* about the
things that make the wheel non-redistributable if wrong: it fails if the OCCT
LGPL texts cannot be obtained, if no vendored libraries are found at all, or if
a GPL JBIG library is present.
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

# Upstream identity for the libraries OCCT pulls in, keyed by normalised base
# name (lib-prefix, version suffix and auditwheel hash stripped). Used to label
# and point at sources when the distro/conda metadata does not carry the detail.
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

# glibc / loader libraries are provided by the platform (manylinux policy) and
# are never vendored; ignore them if they ever appear in a closure.
PLATFORM_LIBS = re.compile(r"^(ld-linux.*|libc|libm|libdl|libpthread|librt|libutil|libnsl|libresolv)\b")


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


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #

def rpm_info(soname: str) -> dict | None:
    """Map an ELF soname back to its owning RPM via RPM's own Provides."""
    arch_suffixes = ["()(64bit)", "()(32bit)", ""]
    name = ""
    for suffix in arch_suffixes:
        name = run(["rpm", "-q", "--whatprovides", f"{soname}{suffix}"])
        if name and "no package" not in name and not name.startswith("error"):
            break
        name = ""
    if not name:
        # last resort: resolve via ldconfig then rpm -qf
        for line in run(["ldconfig", "-p"]).splitlines():
            if soname in line and "=>" in line:
                path = line.split("=>")[-1].strip()
                name = run(["rpm", "-qf", "--qf", "%{NAME}", path])
                break
    if not name or "not owned" in name or name.startswith("error"):
        return None
    name = name.splitlines()[0]
    fields = run(["rpm", "-q", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\t%{LICENSE}\t%{SOURCERPM}", name])
    parts = fields.split("\t")
    if len(parts) < 4:
        return None
    pkg, nevr, lic, srpm = parts[:4]
    return {"pkg": pkg, "version": nevr, "license": lic, "source": srpm}


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
            licenses_dir = conda_prefix / "conda-meta" / f"{rec.get('name')}-{rec.get('version')}-{rec.get('build')}"
            return {
                "pkg": pkgname,
                "version": str(rec.get("version", "")),
                "license": rec.get("license") or "",
                "source": rec.get("url") or rec.get("channel") or "conda-forge",
                "licenses_path": rec.get("extracted_package_dir"),
            }
    return None


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
    args = ap.parse_args()

    root = Path(args.wheel_root)
    pkg_dir = root / args.pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    lic_dir = pkg_dir / "licenses"
    lic_dir.mkdir(parents=True, exist_ok=True)

    backend = "rpm" if shutil.which("rpm") else ("conda" if os.environ.get("CONDA_PREFIX") else "none")
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

    cindex = conda_index(Path(os.environ["CONDA_PREFIX"])) if backend == "conda" else []

    occt_count = 0
    components: dict[str, dict] = {}
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

        known = KNOWN.get(norm)
        rec = None
        if backend == "rpm":
            rec = rpm_info(re.sub(r"-[0-9a-f]{8,}(?=\.)", "", lib.name))
        elif backend == "conda":
            rec = conda_info(norm, cindex, Path(os.environ["CONDA_PREFIX"]))

        display = (known[0] if known else (rec["pkg"] if rec else norm))
        key = display
        if key in components:
            components[key]["files"].append(lib.name)
            continue

        entry = {
            "name": display,
            "version": rec["version"] if rec else "",
            "license": (rec["license"] if rec and rec.get("license") else (known[1] if known else "unknown")),
            "source": (rec["source"] if rec else ""),
            "url": known[2] if known else "",
            "files": [lib.name],
            "license_files": [],
        }

        # copy actual license text where the system/conda metadata exposes it
        dest = lic_dir / re.sub(r"[^A-Za-z0-9_.-]", "_", display)
        if backend == "rpm" and rec:
            entry["license_files"] = copy_license_dir(Path("/usr/share/licenses") / rec["pkg"], dest)
        elif backend == "conda" and rec and rec.get("licenses_path"):
            lp = Path(rec["licenses_path"]) / "info" / "licenses"
            entry["license_files"] = copy_license_dir(lp, dest)
        if not entry["license_files"]:
            log(f"note: no bundled license text for {display} - recording SPDX tag + source pointer only")

        components[key] = entry

    log(f"OCCT libraries: {occt_count}; other components: {len(components)}")

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
        lf = (", ".join(sorted(set(entry["license_files"]))) if entry["license_files"]
              else "(text not bundled by distro; see Source/URL)")
        lines += [
            f"{entry['name']} {entry['version']}".rstrip(),
            f"  License: {entry['license']}",
            f"  Upstream: {entry['url'] or 'n/a'}",
            f"  Source package: {entry['source'] or 'see CORRESPONDING-SOURCE.txt'}",
            f"  Bundled license text: {lf}",
            f"  Vendored files: {', '.join(sorted(entry['files']))}",
            "",
        ]
    (pkg_dir / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(lines))

    # corresponding-source offer (satisfies LGPL-2.1 and FIPL source clauses)
    srpms = sorted({e["source"] for e in components.values() if e["source"]})
    cs = [
        "CORRESPONDING SOURCE",
        "====================",
        "",
        "The complete corresponding source for every component bundled in this wheel",
        "is publicly available at the locations below. For any component, the exact",
        "source can also be requested by opening an issue at",
        "https://github.com/CadQuery/ocp-build-system/issues .",
        "",
        f"* OCP binding generator and this build system: https://github.com/CadQuery/ocp-build-system",
        f"* OCP sources/stubs for this release: {args.ocp_source_url}",
        f"* OCCT {args.occt_version}: {args.occt_repo} @ tag {args.occt_tag}",
        "",
        "Bundled third-party libraries are built from their distribution's source",
        "packages (identical upstream source, distro security patches). The exact",
        "source package names are recorded in THIRD-PARTY-NOTICES.txt; for the",
        "manylinux (AlmaLinux 8) build these source RPMs are:",
        "",
    ]
    cs += [f"  - {s}" for s in srpms] or ["  (see THIRD-PARTY-NOTICES.txt)"]
    cs += [
        "",
        "AlmaLinux 8 source RPMs are available from the AlmaLinux vault, e.g.",
        "https://vault.almalinux.org/8/ (BaseOS/AppStore/PowerTools 'Source' trees)",
        "and the EPEL 8 source tree. libtiff is rebuilt from the distribution source",
        "RPM with the GPL JBIG codec disabled; the modification is the configure flag",
        "--disable-jbig only.",
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
