import os
import setuptools

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()


with open(os.path.join("src/peakrdl_socgen", "__about__.py"), encoding='utf-8') as f:
    v_dict = {}
    exec(f.read(), v_dict)
    version = v_dict['__version__']

setuptools.setup(
    name="peakrdl-socgen",
    version=version,
    author="Risto Pejasinovic",
    author_email="risto.pejasinovic@gmail.com",
    description="Generate CPP Hardware Abstraction Layer libraries",
    long_description=long_description,
    url="https://github.com/Risto97/PeakRDL-socgen",
    package_dir={'': 'src'},
    packages=[
        'peakrdl_socgen',
    ],
    package_data={'peakrdl_socgen' : ['templates/*']},
    include_package_data=True,
    install_requires=[
        "systemrdl-compiler>=1.25.0",
        "Jinja2>=3.0.0",
    ],
    entry_points = {
        "peakrdl.exporters": [
            'socgen = peakrdl_socgen.__peakrdl__:Exporter'
        ]
    },
    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: Software Development :: Documentation",
    ),
    project_urls={
        "Source": "https://github.com/Risto97/PeakRDL-socgen",
        "Tracker": "https://github.com/Risto97/PeakRDL-socgen/issues",
    },
)
