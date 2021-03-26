import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="thonny-codelive",
    version="0.0.1",
    author="Codelive Project",
    author_email="sgz4@students.calvin.edu",
    description="Thonny plugin for live collaboration using MQTT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/codelive-project/thonny-codelive",
    packages=setuptools.find_namespace_packages(),
    install_requires=["paho-mqtt>=1.5.1", "thonny>=3.2.7", "sortedcontainers>=2.3.0"],
    package_data={
        "thonnycontrib.codelive": ["res/*.*", "views/*.*"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    license="License :: OSI Approved :: MIT License",
)
