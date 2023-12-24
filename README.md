# ocp-build-system

This repository is used to build wheels for OCP, which is CadQuery's bindings to the OpenCASCADE CAD kernel. There are two GitHub Actions available as part of this repo.

* Build (Create Python wheel using Conda)
* Releases

The Build workflow is triggered manually by a developer, and sets up conda environments for each of the wheels to be built, builds the wheels, and then uploads them as artifacts to the GitHub Action. The Releases workflow is run when a tag is created, and takes the wheels attached to the latest build and uploads them to PyPi. Each time a new version of OCP is released these Actions, along with the setup.py file, need to be modified to build and release the new version.

# Building for Apple Silicon locally

Since there are no free Apple Silicon runners available for GitHub actions, a simple solution is to just run the build locally on an Apple Silicon Macbook. To that end, this repo contains a `local-build.sh` script which builds for whatever architecture the local machine is running on. On an M1 Macbook Pro it should take approx 25 minutes to build for all 4 Python versions.
