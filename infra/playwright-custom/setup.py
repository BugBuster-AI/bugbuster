import setuptools

setuptools.setup(
    name="playwright",
    version="1.49.0",
    packages=setuptools.find_packages(),
    package_data={
    "playwright": ["driver/**/*", "driver/*"],
    },
    include_package_data=True,
    install_requires=[
        'greenlet==3.1.1',
        'pyee==12.0.0',
    ],
    python_requires=">=3.9",
    description="Customized Playwright package with modified tracing",
    author="screenmate",
    license="Apache-2.0",
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ]
)