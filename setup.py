# #!/usr/bin/env python
import os
import sys

__version__ = "0.0.1"
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def get_version(*file_paths):
    """Retrieves the version from rmq_broker/__init__.py"""
    version_match = __version__
    if version_match:
        return version_match
    raise RuntimeError("Unable to find version string.")


version = get_version("rmq_broker", "__init__.py")


if sys.argv[-1] == "publish":
    try:
        import wheel

        print("Wheel version: ", wheel.__version__)
    except ImportError:
        print("Wheel library missing. Please run 'pip install wheel'")
        sys.exit()
    os.system("python setup.py sdist upload")
    os.system("python setup.py bdist_wheel upload")
    sys.exit()

if sys.argv[-1] == "tag":
    print("Tagging the version on git:")
    os.system(f"git tag -a {version} -m 'version {version}'")
    os.system("git push --tags")
    sys.exit()

readme = open("README.rst").read()
history = open("HISTORY.rst").read().replace(".. :changelog:", "")
requirements = open("requirements.txt").readlines()

setup(
    name="rabbitmq-broker",
    version=version,
    description="""Message Queue Broker""",
    long_description=readme + "\n\n" + history,
    author="Nikita Sysoev",
    author_email="njt55cs@gmail.com",
    url="https://github.com",
    packages=[
        "rmq_broker",
    ],
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords="rabbitmq-broker",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 2.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
