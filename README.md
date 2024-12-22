# Build System for OCP

## Recipe

The github action can be found in [.github/workflows/build-ocp.yml](.github/workflows/build-ocp.yml)

## Wheels

The action creates two different types of delocated wheels:

1. `cadquery_ocp` which is build against pypi's VTK 9.2.6
2. `cadquery_ocp_novtk` which comes without VTK support

The wheels encapsulate the native OCP module into a folder `OCP`.

```
OCP
├── Adaptor2d
│   └── __init__.py
├── Adaptor3d
│   └── __init__.py
...
├── IVtk
│   └── __init__.py
├── IVtkOCC
│   └── __init__.py
├── IVtkTools
│   └── __init__.py
├── IVtkVTK
│   └── __init__.py
...
├── OCP.cpython-311-x86_64-linux-gnu.so
...
```

with `__init__.py` e.g. for `Adaptor2d` looking like

```python
from ..OCP.Adaptor2d import *
```

OCP behaves exactly like the conda version, i.e. you can just ìmport `OCP.BRep` as usual. However, error traces can involve `OCP.OCP.BRep ...` prefixing the module with the `OCP` folder


## Supported Operation Systems
The wheels are created for

- **Windows (Intel)**
- **MacOS (Intel)**: running from macOS 11.11 or newer
- **MacOS (arm64)**: running from macOS 11.11 or newer
- **Linux (Intel)**: running Ubuntu 20.04 or newer (GLIBC_2.29 and GLIBCXX_3.4.26)

## Supported Python Versions

- The **vtk** version can only be built for Python 3.11 and older, since this is the limitation of pypi VTK 9.2.6.
- The **novtk** version can be built for Python3.10 and newer, up to 3.13. However, currently only 3.11 is built.

## Tests

- The **vtk** wheels are tested against `build123d` and `cadquery``
- The **novtk** wheels are tested against a patched version of `build123d` only (vtk support removed)

## Known issues

- For macOS (Intel), `nlopt` 2.9 is not on pypi. The test installs `nlopt` from conda.
- For Windows, `casadi` and `nlopt` create a segmentation fault on exit (even when OCP and VTK are not installed). The test installs `nlopt` and `casadi` from conda.
- `ocpsvg` has `cadquery_ocp` as a dependency and will install parallel to the novtk wheel. The test uninstalls `cadquery_ocp` after installation of `build123d`.

## Development

The action heavily caches artifacts since some steps can take 0.5 - 1.5 h.

For **vtk** wheels:

- `VTK-9.2.6-py3.11-<os>-`: The generated VTK SDK
- `OCCT-7.7.2-VTK-ON-<os>-`: The compiled OCCT SDK with VTK support
- `OCP-source-7.7.2-VTK-ON-<os>-`: The generated OCP source with VTK support
- `OCP-7.7.2-VTK-ON-py<python version>-<os>-`: The compiled OCP Python module with VTK support

For **novtk** wheels:

- `OCCT-7.7.2-VTK-OFF-<os>-`: The compiled OCCT SDK without VTK support
- `OCP-source-7.7.2-VTK-OFF-<os>-`: The generated OCP source without VTK support
- `OCP-7.7.2-VTK-OFF-py<python version>-<os>-`: The compiled OCP Python module without VTK support

`<os>` being "ubuntu-22.04", "macos-13", "macos-14", and "windows-2019".

To recompile, delete the respective [cached elements](https://github.com/bernhard-42/repackage-ocp/actions/caches) first.

**Note:**
Run this strategy first to create the caches:

```yaml
    matrix:
    os: ["ubuntu-22.04", "macos-13", "macos-14", "windows-2019"]
    python-version: ["3.11"]
    # python-version: ["3.10", "3.11", "3.12", "3.13"]
    use-vtk: ["OFF", "ON"]

    # exclude:
    #   - use-vtk: ON
    #     python-version: 3.12
    #   - use-vtk: ON
    #     python-version: 3.13
```

Otherwise a lot of duplicate long lasting jobs will run.
Then run:

```yaml
    matrix:
    os: ["ubuntu-22.04", "macos-13", "macos-14", "windows-2019"]
    # python-version: ["3.11"]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    use-vtk: ["OFF", "ON"]

    exclude:
      - use-vtk: ON
        python-version: 3.12
      - use-vtk: ON
        python-version: 3.13
```
