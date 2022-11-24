import setuptools

setuptools.setup(
    name="mailipy",
    version="0.0.8",
    author="William Di Luigi",
    author_email="williamdiluigi@gmail.com",
    description="Bulk send emails easily",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": [
            "mailipy-gen=mailipy.gen:main",
            "mailipy-send=mailipy.send:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'jinja2',
        'markdown',
        'pyyaml',
    ],
    python_requires='>=3.6',
)
