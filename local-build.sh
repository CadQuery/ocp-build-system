#!/bin/bash
set -e

function info() {
  echo -e "\033[1;36m$1\033[0m"
}

trap "info Exited!; exit;" SIGINT SIGTERM

for python_version in '3.8' '3.9' '3.10' '3.11' '3.12'
do
    info "Building wheel for Python $python_version..."
    info "Removing temp files..."
    rm -rf -v ./build
    rm -rf -v ./cadquery_ocp.egg-info
    info "Conda Deps Setup..."
    CONDA_SUBDIR=osx-arm64 conda create --yes -n ocp-build-system -c cadquery -c conda-forge \
        python=$python_version \
        ocp=7.7.2.* \
        vtk=9.2.* \
        pip
    info "Conda Arch Setup..."
    conda run -n ocp-build-system conda config --env --set subdir osx-arm64
    info "Pip Deps Setup..."
    conda run -n ocp-build-system pip install \
        build \
        setuptools \
        wheel \
        requests \
        delocate \
        auditwheel \
        delvewheel
    info "Conda-only Build..."
    conda run --live-stream -n ocp-build-system \
        python -m build --no-isolation --wheel
done
