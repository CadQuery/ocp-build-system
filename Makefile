.PHONY: clean Build

clean:
	rm -fr ./OCCT ./OCP ./build123d ./cadquery
	rm -fr pypi/build pypi/wheel pypi/dist pypi/OCP pypi/cadquery_ocp* pypi/cadquery_ocp*.egg-info 
	rm -fr ~/opt/local/*
	# rm -f /usr/local/include/OpenGL  /opt/usr/local/include
	
	@echo "Removing build-ocp environment"
	-micromamba env remove -y -n build-ocp

	@echo "Removing vtk environment"
	-micromamba env remove -y -n vtk

	@echo "Removing test environment"
	-micromamba env remove -y -n test

	micromamba env list
	PATH=$(echo $PATH | tr ':' '\n' | grep -v /opt/homebrew/opt/llvm@15/bin | paste -s -d':' -)
	
Build:
	python get-config.py $(vtk);

