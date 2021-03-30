import setuptools
import os

setupdir = os.path.dirname(__file__)
requirements = []
for line in open(os.path.join(setupdir, "requirements.txt"), encoding="UTF-8"):
    if line.strip() and not line.startswith("#"):
        requirements.append(line)

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="thonny-codelive",
    version="0.0.3",
    author="Codelive Project",
    author_email="sgz4@students.calvin.edu",
    description="Thonny plugin for live collaboration using MQTT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/codelive-project/thonny-codelive",
    install_requires=requirements,
    packages = ["thonnycontrib.codelive"],
    package_data={
        "thonnycontrib.codelive": ["res/*", 
                                   "views/*.py",
                                   "views/session_status/*.py",
                                   "views/session_status/res/*"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    license="License :: OSI Approved :: MIT License",
)
