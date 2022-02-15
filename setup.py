from setuptools import setup, find_packages

setup(
    name="ocp",
    version="7.5.3",
    packages=find_packages(include=["OCP", "OCP.*"]),
    install_requires=[
        'boost>=1.74.0',
        'joblib',
        'toml',
        'click',
        'logzero',
        'pandas',
        'path',
        'pyparsing',
        'schema',
        'tqdm',
        'toposort'
    ]
)
