from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="Tickr",
    version="0.0.1",
    description="Algorithmic trading bot",
    author="Yasir Khalid",
    author_email="yasir_khalid@outlook.com",
    url="https://github.com/yasir-khalid/tickr",
    packages=find_packages(),
    install_requires=install_requires,
    python_requires=">=3.11",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
)
