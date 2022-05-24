# ocp-build-system

This repository is used to build wheels for OCP, which is CadQuery's bindings to the OpenCASCADE CAD kernel. There are two GitHub Actions available as part of this repo.

* Build (Create Python wheel using Conda)
* Releases

The Build workflow is triggered manually by a developer, and sets up conda environments for each of the wheels to be built, builds the wheels, and then uploads them as artifacts to the GitHub Action. The Releases workflow is run when a tag is created, and takes the wheels attached to the latest build and uploads them to PyPi. Each time a new version of OCP is released these Actions, along with the setup.py file, need to be modified to build and release the new version.
