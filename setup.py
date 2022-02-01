"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
import setuptools
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='ocp',
    version='7.5.3',
    description='CadQuery bindings to the OpenCASCADE CAD kernel.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/CadQuery/OCP',
    author='CadQuery',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.6',
        # 'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        # "Programming Language :: Python :: 3.10",
        'Programming Language :: Python :: 3 :: Only',
    ],
    package_data={'': ['OCP.cpython-39-x86_64-linux-gnu.so']},
    ext_modules =[
        setuptools.Extension(
            name='OCP',
            sources=[]
        )
    ],
    python_requires='>=3.8, <3.10',
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
    ],
    project_urls={
        'Bug Reports': 'https://github.com/CadQuery/OCP/issues',
        'Source': 'https://github.com/CadQuery/OCP',
    },
)
