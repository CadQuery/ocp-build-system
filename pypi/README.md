# cadquery-ocp (also known as OCP)

Python wrapper for OCCT generated using pywrap. Typing [stubs](https://pypi.org/project/cadquery-ocp-stubs/) available from pypi.

## Goals of OCP
* Provide thin bindings to OCCT.
* Wrap all OCCT modules (if practical).
* React quickly to new OCCT releases.
* Cater primarily for the CadQuery project.

## Non-goals
* Provide additional functionality not present in OCCT

## Licensing

The OCP binding code in this project is licensed under the Apache-2.0 license
(see the bundled `LICENSE`). The binary wheels additionally **bundle native
libraries under other licenses**, most notably Open CASCADE Technology (OCCT),
which is **LGPL-2.1 with the Open CASCADE Exception**, along with FreeImage,
FreeType, Fontconfig, LibRaw and several image/compression codecs.

Each wheel ships the full set of third-party license texts under
`<package>/licenses/` and in the standard `*.dist-info/licenses/` location, a
`THIRD-PARTY-NOTICES.txt` listing every bundled component and its license, a
`CORRESPONDING-SOURCE.txt` written offer/pointer for obtaining the sources
(OCCT, OCP and the distribution source packages), and a `BUILD-MANIFEST.txt`
recording the exact OCCT/OCP revisions, applied patches and build options.
Downstream redistributors should carry these files with any redistribution.
