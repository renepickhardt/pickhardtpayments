import setuptools
#import os

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "readme.md").read_text()

setuptools.setup(
    name="pickhardtpayments",
    version="0.0.0",
    author="Rene Pickhardt",
    description="Collection of pythong classes and interfaces to integrate Pickhardt Payments to your applicatoin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages("pickhardtpayments"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    # py_modules=["pickhardtpayments"],
    package_dir={'': 'pickhardtpayments'},
    install_requires=["networkx", "ortools"]
)
