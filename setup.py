# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

""" setup.py for setuptools """

import setuptools

with open("README.md") as readme:
    long_description = readme.read()


requires = ["pandas", "tabulate", "colorlog"]

setuptools.setup(
    name="stracepy",
    version="0.1.0",
    description="Python tools for parsing and analyzing strace log",
    url="https://github.com/bmwcarit/stracepy",
    author="BMW Car IT",
    author_email="henri.rosten@unikie.com, daniel.krefft@bmw.de",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=requires,
    license="MIT",
    classifiers=[  # See:https://pypi.org/classifiers/
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="strace",
    packages=setuptools.find_packages(include=["stracepy", "stracepy.*"]),
    zip_safe=False,
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "strace2csv = stracepy.strace2csv:main",
            "strace_analyzer = stracepy.strace_analyzer:main",
        ]
    },
)
