import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "LXMKit",
    version = "0.0.1",
    author = "Gregory Taylor",
    author_email = "gregory.taylor.au@gmail.com",
    description = "Create LXM app with ease",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/Aveygo/LXMKit",
    project_urls = {
        "Bug Tracker": "https://github.com/Aveygo/LXMKit/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    python_requires = ">=3.6",
    install_requires=[
        'RNS', 'LXMF', 'lmdb'
    ],
)
