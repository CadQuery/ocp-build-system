#!/bin/bash
set -e

function info() {
  echo -e "\033[1;36m$1\033[0m"
}

trap "info Exited!; exit;" SIGINT SIGTERM

for python_version in '3.9' '3.10' '3.11' '3.12'
do
    info "Building wheel for Python $python_version..."
    info "Removing temp files..."
    rm -rf -v ./build
    rm -rf -v ./cadquery_ocp.egg-info
    info "Conda Deps Setup..."
    conda create --yes -n ocp-build-system -c cadquery -c conda-forge \
        python=$python_version \
        pip
    info "DONE"
    info "Conda Arch Setup..."
    conda run -n ocp-build-system conda config --env --set subdir local-vtk-build
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
        mkdir -p ./vtk/build; \
        curl -L -O https://vtk.org/files/release/9.2/VTK-9.2.6.tar.gz; \
        tar -zxf VTK-9.2.6.tar.gz --directory ./vtk/; \
        cd ./vtk/build; \
        cmake -GNinja -DVTK_WHEEL_BUILD=ON -DVTK_WRAP_PYTHON=ON -DCMAKE_BUILD_TYPE=Release ../VTK-9.2.6; \
        ninja; \
        python setup.py bdist_wheel; \
        cd ../../; \
        find ./ -iname *.whl; \
        wheel_file=$(ls vtk/build/dist/*.whl | xargs -n 1 basename); \
        echo $wheel_file; \
        mkdir wheel_build/; \
        unzip vtk/build/dist/${wheel_file} -d wheel_build/; \
        sed -i 's/Name:.*$/Name: cadquery_vtk/' wheel_build/*.dist-info/METADATA; \
        sed -i 's/Version:.9.2.6.dev0$/Version: 9.2.6/' wheel_build/*.dist-info/METADATA; \
        mv wheel_build/*.dist-info wheel_build/cadquery_vtk-9.2.6.dist-info; \
        cd wheel_build/; \
        zip -r cadquery_${wheel_file} *; \
        rm ../vtk/build/dist/*.whl; \
        mv cadquery_${wheel_file} ../vtk/build/dist/; \
        cd ../; \
        pip install vtk/build/dist/*.whl; \
        python -c "import vtk;print('vtk imported successfully')"
done
