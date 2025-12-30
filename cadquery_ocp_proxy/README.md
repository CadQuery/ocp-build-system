# TEST SETUP

There is a proxy package `cadquery_ocp_proxy` with version `7.9.3.0` that does nothing, but have optional dependencies:

    ```toml
    [project.optional-dependencies]
    vtk = ["cadquery_ocp>=7.9,< 8.0"]
    novtk = ["cadquery_ocp_novtk>=7.9,< 8.0"]
    ```

I built the following packages using the proxy package for testing on my local pypi server.

**NOTE: These are artificial new versions to force pip and uv to load them from my pypi server, so don't get confused about the version numbers. They don't exist on pypi.org**

- build123d-0.11.0-py3-none-any.whl
- cadquery-2.7-py3-none-any.whl
- ocp_gordon-0.19.0-py3-none-any.whl
- ocpsvg-0.6.0-py3-none-any.whl
- cadquery_ocp_proxy-7.8.1-py3-none-any.whl

Setup for packages in the **build123d**, **CadQuery**, or **OCP** ecosystem:

1. Packages with `cadquery_ocp` dependencies the can (like `ocpsvg` `ocp_gordon`, and `build123d`) would need to use extra dependencies

   ```toml
   dependencies = ["svgelements >= 1.9.1, <2"]

   [project.optional-dependencies]
   dev = ["pytest"]
   vtk = ["cadquery-ocp-proxy[vtk] >=7.9, < 8.0"]
   novtk = ["cadquery-ocp-proxy[novtk] >=7.9, < 8.0"]
   ```

2. Packages that need VTK like `cadquery` would only depend on `cadquery-ocp-proxy[vtk]` as default dependency

# WORKFLOWS

## Install **build123d** without VTK:

When we `pip install build123d[novtk]==0.11.0`, we get (pip list):

```text
build123d               0.11.0
cadquery-ocp-novtk      7.9.3.0
cadquery-ocp-proxy      7.9.3.0
...
ocp-gordon              0.19.0
ocpsvg                  0.6.0
```

**Tests:**

- build123d: `pytest --ignore=tests/test_direct_api/test_vtk_poly_data.py --ignore tests/test_direct_api/test_jupyter.py tests` passes all test.
- ocpsvg: `pytest tests` passes all tests
- ocp_gordon: `pytest tests` passes all tests

## Install **build123d** with VTK:

When we `pip install build123d[vtk]==0.11.0`, we get (pip list):

```text
build123d               0.11.0
cadquery-ocp            7.9.3.0
cadquery-ocp-proxy      7.9.3.0
...
ocp-gordon              0.19.0
ocpsvg                  0.6.0
```

**Tests:**

- build123d: `pytest tests` passes all test.
- ocpsvg: `pytest tests` passes all tests
- ocp_gordon: `pytest tests` passes all tests

## Install **cadquery**:

When we `pip install cadquery==2.7`, we get (pip list):

```text
cadquery           2.7
cadquery-ocp       7.9.3.0
cadquery-ocp-proxy 7.9.3.0
```

**Tests:**

- cadquery: `pytest tests` passes all test.

Since the dependency of `ocpsvg` is `cadquery-ocp-proxy `, we can `pip install ocpsvg==0.6.0`

```text
cadquery           2.7
cadquery-ocp       7.9.3.0
cadquery-ocp-proxy 7.9.3.0
...
ocpsvg             0.6.0
```

All good, because `cadquery-ocp` was already there from the `cadquery` installation

**Tests:**

- ocpsvg: `pytest tests` passes all test.

## Install **CadQuery** and **build123d** at the same time

When we

```
pip install build123d[vtk]==0.11.0
pip install cadquery==2.7

# or

pip install cadquery==2.7
pip install build123d[vtk]==0.11.0

# or

pip install cadquery==2.7 build123d==0.11.0

# or

pip install build123d==0.11.0 cadquery==2.7
```

we get (pip list)

```text
build123d               0.11.0
cadquery                2.7
cadquery-ocp            7.9.3.0
cadquery-ocp-proxy      7.9.3.0
...
ocp-gordon              0.19.0
ocpsvg                  0.6.0
```

**Tests:**

- cadquery: `pytest tests` passes all test.
- build123d: `pytest tests` passes all test.
- ocpsvg: `pytest tests` passes all tests
- ocp_gordon: `pytest tests` passes all tests

# Caveats

## Forgetting `[vtk]` or `novtk`

What happens when we only install `pip install build123d==0.11.0`?

We get (pip list):

    ```text
    build123d               0.11.0
    ...
    ocp-gordon              0.19.0
    ocpsvg                  0.6.0
    ```

No `cadquery_ocp` is installed, because it is an optional dependency . This is, unfortunately, a case where the pypi ecosystem at install time can't help any more.
This needs to be covered at runtime, e.g. in `__init__.py`

```python
try:
    import OCP
except ImportError:
    print("If you only want to use build123d, install 'build123d[novtk]'")
    print("When cadquery should also be installed, install 'build123d[vtk]'")
```

**Notes:**

- The same would hold for\*\* `ocpsvg`.
- `ocp_svg would not suffer from it, since it has `build123d` as a dependency

# Summary

The proxy package solves two major issue:

1. Install **build123d** and **CadQuery** in the same environment
2. Have a clear guidance on packages that should run with either `cadquery_ocp` and `cadquery_ocp_novtk` (optional dependencies)

The downside is that users need to specifiy `[vtk]` or `[novtk]` during install. This can be clearly mentioned in the Readme, but also caught at runtime to pürovide guidance for the user.
