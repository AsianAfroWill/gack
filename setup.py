import setuptools

setuptools.setup(
    name="gack",
    version="0.0.1",
    author="Will Chen",
    author_email="will@asianafrowill.com",
    description="Gack - Git Stack manager",
    long_description="README.md",
    long_description_content_type="text/markdown",
    url="https://github.com/AsianAfroWill/gack",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'gitpython',
    ],
    entry_points={
        "console_scripts": [
            'gack=gack.__main__:main',
        ],
    },
)

