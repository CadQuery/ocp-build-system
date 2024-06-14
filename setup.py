"""
Build OCP+VTK wheel with shared library dependencies bundled

From the directory containing this file, and with an appropriate conda
environment activated:

    $ python -m build --no-isolation --wheel

will build a manylinux wheel into `dist/`.

A conda environment with `OCP` (and all its dependencies, including
`vtk`), `auditwheel`, and `build` (the PEP 517 compatible Python
package builder) python packages is required, as well as the
`patchelf` binary.  Note that the vtk package needs to be bundled to
avoid multiple copies of the VTK shared libraries, which appears to
cause errors.

On Linux, a VTK manylinux wheel can be used instead of the VTK conda
package.  This may allow for a more compatible manylinux wheel to be
built.  Install the VTK manylinux wheel somewhere, e.g.:

    pip install -t /foo --no-deps vtk~=9.1.0

and then set VTK_MANYLINUX=/foo before building.  (We use the
VTK_MANYLINUX envvar instead of wrangling with custom setuptools build
option.)

This setuptools build script works by first adding the installed `OCP`
and `vtk` python package files into a wheel.  This wheel is not
portable as library dependencies are missing, so we use auditwheel to
bundle them into the wheel.

Note that auditwheel is a tool used by many packages to produce
`manylinux` python wheels.  It may be straightforward to use
`delocate` and `delvewheel`, which are similar to auditwheel, to
produce macOS and Windows wheels.

"""

import OCP
import glob
import json
import os.path
import pathlib
import platform
import re
from setuptools import Extension, setup
import setuptools.command.build_ext
import shutil
import subprocess
import sys
import tempfile
import vtkmodules
import wheel.bdist_wheel
import zipfile


# VTK_MANYLINUX = None
# if platform.system() == "Linux" and os.getenv("VTK_MANYLINUX"):
#     VTK_MANYLINUX = pathlib.Path(os.getenv("VTK_MANYLINUX")).resolve()
#     if not (VTK_MANYLINUX / "vtkmodules" / "__init__.py").exists():
#         raise Exception(f"invalid VTK_MANYLINUX: {VTK_MANYLINUX}")


# def populate_lib_dir(conda_prefix, vtk_manylinux, out_dir):
#     """Merge non-vtk conda libs and vtk manylinux libs into a single directory"""

#     conda_prefix = pathlib.Path(conda_prefix)
#     vtk_manylinux = pathlib.Path(vtk_manylinux)
#     out_dir = pathlib.Path(out_dir)

#     fns = list((conda_prefix / "conda-meta").glob("vtk-9*-qt_*.json"))
#     if len(fns) != 1:
#         raise Exception(f"could not find unique vtk meta: {fns}")
#     vtk_meta = json.loads(fns[0].read_text())
#     vtk_files = {conda_prefix / f for f in vtk_meta["files"]}

#     # Do not copy regular VTK files because we will use manylinux
#     # files instead.  Do copy VTK symlinks because they're expected by
#     # other conda packages which we may bundle into the wheel.
#     vtk_skipped_files = []
#     for f in (conda_prefix / "lib").iterdir():
#         if f.is_dir():
#             continue
#         if f in vtk_files and not f.is_symlink():
#             vtk_skipped_files.append(f)
#         else:
#             shutil.copy2(f, out_dir, follow_symlinks=False)

#     # Copy VTK files.  Symlinks in the target will be followed so we
#     # are fixing broken symlinks.
#     for f in (vtk_manylinux / "vtkmodules").glob("lib*.so*"):
#         shutil.copy2(f, out_dir, follow_symlinks=False)

#     # The VTK manylinux wheel may not provide all the libraries of the
#     # VTK conda pkg, so there may be missing files or broken symlinks.
#     # If this is problematic then auditwheel will fail.  For now,
#     # print some helpful information.
#     for f in vtk_skipped_files:
#         if not (out_dir / f.name).exists():
#             print("manylinux whl did not provide:", f)

#     # Copy the rest of the libraries bundled in the VTK wheel.
#     for f in (vtk_manylinux / "vtk.libs").glob("lib*.so*"):
#         shutil.copy2(f, out_dir, follow_symlinks=False)


class copy_installed(setuptools.command.build_ext.build_ext):
    """Build by copying files installed by conda"""

    def build_extension(self, ext):
        # self.build_lib is created when packages are copied.  But
        # there are no packages, so we have to create it here.
        os.mkdir(os.path.dirname(self.build_lib))
        os.mkdir(self.build_lib)
        # OCP is a single-file extension; just copy it
        shutil.copy(OCP.__file__, self.build_lib)
        # vtkmodules is a package; copy it while excluding __pycache__
        # if VTK_MANYLINUX:
        #     # Copy python source files and python extensions, but not
        #     # shared libraries.  We will point auditwheel to them
        #     # separately to be bundled in.
        #     shutil.copytree(
        #         os.path.join(VTK_MANYLINUX, "vtkmodules"),
        #         os.path.join(self.build_lib, "vtkmodules"),
        #         ignore=shutil.ignore_patterns("__pycache__", "libvtk*.so*"),
        #     )
        # else:
        #     assert vtkmodules.__file__.endswith(os.path.join(os.sep, "vtkmodules", "__init__.py"))
        #     shutil.copytree(
        #         os.path.dirname(vtkmodules.__file__),
        #         os.path.join(self.build_lib, "vtkmodules"),
        #         ignore=shutil.ignore_patterns("__pycache__"),
        #     )


class bdist_wheel_repaired(wheel.bdist_wheel.bdist_wheel):
    """bdist_wheel followed by auditwheel-repair"""

    def run(self):
        super().run()
        dist_files = self.distribution.dist_files

        # Exactly one wheel has been created in `self.dist_dir` and
        # recorded in `dist_files`
        [(_, _, bad_whl)] = dist_files
        assert os.path.dirname(bad_whl) == self.dist_dir
        with zipfile.ZipFile(bad_whl) as f:
            bad_whl_files = set(zi.filename for zi in f.infolist() if not zi.is_dir())

        # Conda libraries depend on their location in $conda_prefix because
        # relative RPATHs are used find libraries elsewhere in $conda_prefix
        # (e.g. [$ORIGIN/../../..:$ORIGIN/../../../]).
        #
        # `auditwheel` works by expanding the wheel into a temporary
        # directory and computing the external shared libraries required.
        # But the relative RPATHs are broken, so this fails.  Thankfully,
        # RPATHs all resolve to $conda_prefix/lib, so we can set
        # LD_LIBRARY_PATH to allow `auditwheel` to find them.
        lib_path = os.path.join(conda_prefix, "lib")

        # Do the repair, placing the repaired wheel into out_dir.
        out_dir = os.path.join(self.dist_dir, "repaired")
        system = platform.system()
        if system == "Linux":
            # if VTK_MANYLINUX:
            #     # Create a lib dir with VTK manylinux files merged in,
            #     # and point auditwheel to it.
            #     merged_lib_dir = tempfile.mkdtemp()
            #     populate_lib_dir(conda_prefix, VTK_MANYLINUX, merged_lib_dir)
            #     lib_path = merged_lib_dir
            repair_wheel_linux(lib_path, bad_whl, out_dir)
        elif system == "Darwin":
            repair_wheel_macos(lib_path, bad_whl, out_dir)
        elif system == "Windows":
            repair_wheel_windows(lib_path, bad_whl, out_dir)
        else:
            raise Exception(f"unsupported system {system!r}")

        # Add licenses of bundled libraries
        [repaired_whl] = glob.glob(os.path.join(out_dir, "*.whl"))
        with zipfile.ZipFile(repaired_whl) as f:
            repaired_whl_files = set(zi.filename for zi in f.infolist() if not zi.is_dir())
        added_files = repaired_whl_files - bad_whl_files
        add_licenses_bundled(conda_prefix, repaired_whl, added_files)

        # Exactly one whl is expected in the dist dir, so delete the
        # bad wheel and move the repaired wheel in.
        os.unlink(bad_whl)
        new_whl = os.path.join(self.dist_dir, os.path.basename(repaired_whl))
        shutil.move(repaired_whl, new_whl)
        os.rmdir(out_dir)
        dist_files[0] = dist_files[0][:-1] + (new_whl,)


def repair_wheel_linux(lib_path, whl, out_dir):

    if os.uname()[4] == "aarch64":
        plat = "manylinux_2_35_aarch64"
    else:
        plat = "manylinux_2_35_x86_64"

    args = [
        "env",
        f"LD_LIBRARY_PATH={lib_path}",
        sys.executable,
        "-m",
        "auditwheel",
        "--verbose",
        "repair",
        f"--plat={plat}",
        f"--wheel-dir={out_dir}",
        whl,
    ]
    subprocess.check_call(args)


def repair_wheel_macos(lib_path, whl, out_dir):

    args = [
        "env",
        f"DYLD_LIBRARY_PATH={lib_path}",
        sys.executable,
        "-m",
        "delocate.cmd.delocate_listdeps",
        whl,
    ]
    subprocess.check_call(args)

    # Overwrites the wheel in-place by default
    args = [
        "env",
        f"DYLD_LIBRARY_PATH={lib_path}",
        sys.executable,
        "-m",
        "delocate.cmd.delocate_wheel",
        f"--wheel-dir={out_dir}",
        whl,
    ]
    subprocess.check_call(args)


def repair_wheel_windows(lib_path, whl, out_dir):
    args = [sys.executable, "-m", "delvewheel", "show", whl]
    subprocess.check_call(args)
    args = [
        sys.executable,
        "-m",
        "delvewheel",
        "repair",
        "-vv",
        "--no-mangle-all",
        f"--wheel-dir={out_dir}",
        whl,
    ]
    subprocess.check_call(args)


def add_licenses_bundled(conda_prefix, whl, added_files):
    """
    Add licenses of bundled libraries

    A file called "LICENSES_bundled.txt" will be added into the wheel,
    containing the license files of bundled libraries.  License
    information is taken from metadata in the conda env.

    """
    tmp = tempfile.mkdtemp()
    subprocess.check_call(["wheel", "unpack", "-d", tmp, whl])
    dist_infos = glob.glob(os.path.join(tmp, "*","*.dist-info"))
    if len(dist_infos) != 1:
        raise Exception(f"unexpected dist_infos: {dist_infos}")
    dist_info = dist_infos[0]
    with open(os.path.join(dist_info,"LICENSES_bundled"), "w") as f:
        f.write("This wheel distribution bundles a number of libraries that\n")
        f.write("are compatibly licensed.  We list them here.\n")
        write_licenses(conda_prefix, whl, ["ocp"], added_files, f)  # , "vtk"

    subprocess.check_call(["wheel", "pack", "-d", os.path.dirname(whl), os.path.dirname(dist_info)])


def write_licenses(prefix, whl, always_pkgs, added_files, out):
    """
    Write licenses of bundled libraries to out

    """

    # Mapping from package name (e.g. "ocp") to metadata
    pkgs = {}

    # Mapping from name of installed file (e.g. "libfoo.so") to
    # packages that may have installed it
    name_to_pkgs = {}

    # Populate the two maps above
    meta_pat = os.path.join(prefix, "conda-meta", "*.json")
    for fn in glob.glob(meta_pat):
        with open(fn) as f:
            meta = json.load(f)
            pkgs[meta["name"]] = meta
        for p in meta["files"]:
            name_to_pkgs.setdefault(os.path.basename(p), set()).add(meta["name"])

    # Figure out which packages the added files are from
    bundled_pkgs = set()
    added_files = sorted(added_files)
    not_found = []
    print(f"{added_files=}")
    for fn in added_files:
        n = os.path.basename(fn)
        if n in name_to_pkgs:
            bundled_pkgs.update(name_to_pkgs[n])
            continue
        # auditwheel and delvewheel rename bundled libraries to avoid
        # clashes.  We undo this renaming in order to match to file
        # lists in conda.
        u = try_unmangle(n)
        if u and u in name_to_pkgs:
            bundled_pkgs.update(name_to_pkgs[u])
            continue
        not_found.append(fn)
    print(f"{not_found=}")
    bundled_pkgs = sorted(bundled_pkgs)
    print(f"{bundled_pkgs=}")

    for n in sorted(set(always_pkgs) | set(bundled_pkgs)):
        m = pkgs[n]
        pkg_dir = os.path.normpath(m["extracted_package_dir"])
        info_pat = os.path.join(pkg_dir, "info", "[Ll][Ii][Cc][Ee][Nn][CcSs][Ee]*", "**")
        share_pat = os.path.join(pkg_dir, "share", "[Ll][Ii][Cc][Ee][Nn][CcSs][Ee]*", "**")
        licenses = glob.glob(info_pat, recursive=True) + glob.glob(share_pat, recursive=True)
        licenses = [fn for fn in licenses if not os.path.isdir(fn)]
        licenses.sort()
        print(file=out)
        print(f"Conda package: {m['name']}", file=out)
        print(f"Download url: {m['url']}", file=out)
        print(f"License: {m.get('license', 'unknown')}", file=out)
        for i, fn in enumerate(licenses, 1):
            if len(licenses) > 1:
                desc = f"{i} of {len(licenses)} license files"
            else:
                desc = "the only license file"
            print(f"Contents of {os.path.relpath(fn, pkg_dir)} ({desc}):", file=out)
            with open(fn, "rb") as f:
                raw = f.read()
            for l in raw.decode(errors="replace").splitlines():
                print(f"> {l.rstrip()}", file=out)


def try_unmangle(n):
    # auditwheel mangling example: "libvtkCommonColor-9.0.so.9.0.1" => "libvtkCommonColor-9-9810eeb7.0.so.9.0.1"
    m = re.match("^([^.]+)-[0-9A-Fa-f]{8,}([.].+)$", n)
    if m:
        return m.group(1) + m.group(2)


# Get the metadata for conda and the `ocp` package.
conda = "conda.bat" if platform.system() == "Windows" else "conda"
args = [conda, "info", "--json"]
info = json.loads(subprocess.check_output(args))
conda_prefix = info["active_prefix"] or info["conda_prefix"]
args = [conda, "list", "--json", "^ocp$"]
[ocp_meta] = json.loads(subprocess.check_output(args))

# Massage conda version string, e.g. "7.6.3.0", "7.6.3.alpha" into a
# wheel version string.  setuptools already converts "X.Y.Z.alpha" to
# "X.Y.Za0".  For now, just replace "X.Y.Z.0" with "X.Y.Z".
wheel_version = ocp_meta["version"]
while wheel_version.count(".") > 2 and wheel_version.endswith(".0"):
    wheel_version = wheel_version[:-2]

# # Release an alpha wheel as a non-alpha wheel
# if wheel_version == "7.7.0.alpha":
#     wheel_version = "7.7.0"

setup(
    name="cadquery-ocp",
    version=wheel_version,
    description="OCP wheel with shared library dependencies bundled.",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    author="adam-urbanczyk, fp473 (wheel generation), roipoussiere (wheel generation)",
    url='https://github.com/CadQuery/OCP',
    download_url="https://github.com/jmwright/ocp-build-system/releases",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering"
    ],
    install_requires=["vtk==9.2.*"],
    # Dummy extension to trigger build_ext
    ext_modules=[Extension("__dummy__", sources=[])],
    cmdclass={"bdist_wheel": bdist_wheel_repaired, "build_ext": copy_installed},
)
