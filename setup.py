"""MQTT-Framework Setup."""
import io
import re
import os
import sys
from setuptools import setup


def read(*names, **kwargs):
    """Open a file and read its content."""
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    """Find current package version number."""
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


long_description = read("README.md")


if sys.argv[-1] == "test":
    os.system("coverage run -m unittest discover -s tests")
    os.system("coverage html --include mqtt_framework/*")
    os.system("coverage report -m --include mqtt_framework/*")
else:
    setup(
        name="MQTT-Framework",
        version=find_version("mqtt_framework", "framework.py"),
        url="https://github.com/paulianttila/MQTT-Framework",
        license="MIT",
        author="Pauli Anttila",
        author_email="pauli.anttila@gmail.com",
        description="Simple application framework for docker container based MQTT apps",
        long_description=long_description,
        long_description_content_type="text/markdown",
        packages=["mqtt_framework"],
        platforms="any",
        python_requires=">=3.6",
        install_requires=[
            "Flask",
            "APScheduler",
            "Flask-MQTT",
            "prometheus-flask-exporter",
            "Flask-Limiter",
        ],
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    )
