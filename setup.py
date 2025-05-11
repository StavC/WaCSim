import setuptools

setuptools.setup(
    name="wacsim",
    version="1.1.1",
    url="https://github.com/StavC/Wacsim"
    ,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        # "Operating System :: OS Independent",
    ],
    license='MIT',
    packages=['wacsim'],
    install_requires=[
        'pyyaml==6.0.1',
        'pyyaml-include',
        'antlr4-python3-runtime==4.13.1',
        'progressbar2',
        'numpy==1.24.3',
        'wntr',
        'pandas',
        'matplotlib',
        'schema',
        'scapy',
        'pathlib',
        'testresources',
        'pytest-mock',
        'netaddr',
        'flaky',
        'pytest',
        'tensorflow',
        'scikit-learn',
        'keras',
        'pytest',
        'pytest-mock',
        'mock'
    ],
    extras_require={
        'test': ['wget', 'coverage', 'pytest-cov'],
        'doc': ['sphinx', 'sphinx-rtd-theme', 'sphinx-prompt'],
    },
    python_requires=">=3.8.10",
    entry_points={
        'console_scripts': [
            'wacsim = wacsim.command_line:main',
        ],
    },
)
