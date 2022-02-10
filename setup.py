from setuptools import setup, find_packages

setup(
    name="ocp",
    version="7.5.3",
    packages=find_packages(include=["OCP", "OCP.*"]),
    package_data={'OCP': ['OCP.cpython-39-x86_64-linux-gnu.so']},
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
