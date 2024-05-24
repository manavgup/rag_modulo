from setuptools import setup, find_packages

setup(
    name='vectordbs',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
        'weaviate-client',
        'pymilvus',
        # Add other dependencies from your requirements.txt
    ],
    extras_require={
        'dev': [
            # Add development dependencies here
            'pytest',
            'flake8',
            'black',
            'isort',
        ],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            # Define command-line scripts if any
        ],
    },
    package_data={
        '': ['*.json'],  # Include all JSON files
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
