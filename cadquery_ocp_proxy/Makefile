.PHONY: clean dist

clean:
	@rm -fr dist/*

dist: clean
	@VERSION=$$(awk -F'"' '/^version = / {print $$2}' pyproject.toml); \
	echo "# Don't edit, will be overwritten during build" > src/cadquery_ocp_proxy/_version.py; \
	echo "__version__ = \"$$VERSION\"" >> src/cadquery_ocp_proxy/_version.py
	@uv build
