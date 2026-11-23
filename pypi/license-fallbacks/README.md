# Vendored license-text fallbacks

`collect_licenses.py` copies each bundled component's license text out of the
distribution's own `/usr/share/licenses/<pkg>/` directory. A few components ship
no text there — either the AlmaLinux 8 runtime sub-package (`*-libs`) carries no
`%license` file, or the library is rebuilt from source in this repo and so is
owned by no RPM. For those, and for header-only / statically-incorporated code
that never appears as a vendored shared library, the collector falls back to the
canonical upstream license text vendored here.

Each file is the verbatim upstream license text, fetched from the authoritative
upstream source:

| Directory   | Component(s)                | SPDX                                     | Source |
|-------------|-----------------------------|------------------------------------------|--------|
| `OpenEXR/`  | OpenEXR (IlmImf) + IlmBase  | `BSD-3-Clause`                           | AcademySoftwareFoundation/openexr `v2.3.0` `LICENSE` |
| `JasPer/`   | JasPer                      | `JasPer-2.0`                             | jasper-software/jasper `version-2.0.14` `LICENSE` |
| `jxrlib/`   | jxrlib (JPEG XR)            | `BSD-2-Clause`                           | 4creators/jxrlib `LICENSE` |
| `libtiff/`  | libtiff                     | `libtiff` (BSD-like)                     | libtiff `v4.0.9` `COPYRIGHT` (rebuilt from the distro source RPM, JBIG disabled) |
| `xz/`       | xz / liblzma                | `0BSD` / public domain                   | tukaani-project/xz `v5.2.4` `COPYING` |
| `libgomp/`  | GCC OpenMP runtime (libgomp)| `GPL-3.0-or-later WITH GCC-exception-3.1`| gcc-mirror/gcc `gcc-14.2.0` `COPYING3` + `COPYING.RUNTIME` |
| `rapidjson/`| RapidJSON (header-only)     | `MIT` (+ BSD/JSON for bundled bits)      | Tencent/rapidjson `24b5e7a` `license.txt` |
| `pybind11/` | pybind11 (header-only)      | `BSD-3-Clause`                           | pybind/pybind11 `v2.13.6` `LICENSE` |
| `OpenCASCADE-OCCT/` | OCCT (bundled shared libs) | `LGPL-2.1-only WITH OCCT-exception-1.0` | Open-Cascade-SAS/OCCT `V8_0_1` `LICENSE_LGPL_21.txt` + `OCCT_LGPL_EXCEPTION.txt` |

The text of a license is meant to be reproduced verbatim; these are the licenses'
own terms, not third-party content. Update them if a bundled component's upstream
license version changes.

Unlike the rows above (fallbacks used only when the distro ships no text), the
`OpenCASCADE-OCCT/` texts are used **local-first**: the collector always prefers
these vendored copies and only downloads from the pinned OCCT tag if a vendored
file is missing, so a transient network outage can't break the build. They are
identical to the copies shipped in the stubs wheel (`pypi-stubs/licenses/`).
