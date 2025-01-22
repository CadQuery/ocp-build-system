# Build System for OCP

## VTK 9.3.1 for Python 3.13

### Recipe

The github action can be found in [.github/workflows/build-ocp.yml](.github/workflows/build-vtk.yml)

### Wheels

The action creates a wheel for Python 3.13 for os in ["ubuntu-22.04", "macos-13", "macos-14", "windows-2019"]

### Known issues

This wheel will work with `cadquery_ocp`, but other packages that depend on `vtk` will most probably not work.


## OCP 7.8.1.1

**NOTE:** For final wheels always use the official sources from the [OCP repository](https://github.com/cadquery/OCP). This can be achieved by setting the environment variable `PYWRAP` to `false`. Only use `true` if you know what you do!

### Recipe

The github action can be found in [.github/workflows/build-ocp.yml](.github/workflows/build-ocp.yml)

### Wheels

The action creates two different types of delocated wheels for OCP 7.8.1.1:

1. `cadquery_ocp-7.8.1.1` which is build against pypi's VTK 9.3.1
2. `cadquery_ocp_novtk-7.8.1.1` which comes without VTK support

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


### Supported Operation Systems
The wheels are created for

- **Windows (Intel)**
- **MacOS (Intel)**: running from macOS 11.11 or newer
- **MacOS (arm64)**: running from macOS 11.11 or newer
- **Linux (Intel)**: running Ubuntu 20.04 or newer (GLIBC_2.29 and GLIBCXX_3.4.26)

### Supported Python Versions

- The **vtk** version can be built with pypi's `vtk==9.3.1` for Python 3.10 - 3.12. For Python 3.13 the dependency is `cadquery_vtk==9.3.1` since `vtk` is not provided on pypi for Python 3.13 
- The **novtk** version can be built for Python3.10 and newer, up to 3.13.

### Tests

- The **vtk** wheels are tested against `build123d` and `cadquery``
- The **novtk** wheels are tested against a patched version of `build123d` only (vtk support removed)

### Known issues

- For macOS (Intel), `nlopt` 2.9 is not on pypi. The test installs `nlopt` from conda.
- For Windows, `casadi` and `nlopt` create a segmentation fault on exit (even when OCP and VTK are not installed). The test installs `nlopt` and `casadi` from conda.
- `ocpsvg` has `cadquery_ocp` as a dependency and will install parallel to the novtk wheel. The test uninstalls `cadquery_ocp` after installation of `build123d`.

### Development

The action heavily caches artifacts since some steps can take 0.5 - 1.5 h.

For **vtk** wheels:

- `VTK-9.3.1-py<version>-<os>-`: The generated VTK SDK
- `OCCT-7.8.1-py-<version>-vtk-<os>-`: The compiled OCCT SDK with VTK support
- `OCP-source-7.8.1.1-vtk-<os>-`: The generated OCP source with VTK support
- `OCP-7.8.1.1-VTK-vtk-py<version>-<os>-`: The compiled OCP Python module with VTK support

For **novtk** wheels:

- `OCCT-7.8.1-py-<version>-novtk-<os>-`: The compiled OCCT SDK without VTK support
- `OCP-7.8.1.1-VTK-novtk-py<version>-<os>-`: The compiled OCP Python module without VTK support

`<os>` being "ubuntu-22.04", "macos-13", "macos-14", and "windows-2019".
`<version>` being "3.10", "3.11", "3.12", and "3.13"

To recompile, delete the respective [cached elements](https://github.com/bernhard-42/repackage-ocp/actions/caches) first.

## OCP 7.8.1.1 stubs

### Recipe

The github action can be found in [.github/workflows/build-ocp-stubs.yml](.github/workflows/build-ocp-stubs.yml)

### Wheels

The action creates one wheel for any Python and OS `cadquery_ocp_stubs-7.8.1.1-py3-none-any.whl` 