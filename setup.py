from setuptools import setup, find_packages

setup(
    name="svunit",
    version="0.1.0",
    packages=find_packages(where="bin"),
    package_dir={"": "bin"},
    install_requires=[],
    entry_points={
        "console_scripts": [
            "runSVUnit.py=svunit.main:main",
        ],
    },
)
