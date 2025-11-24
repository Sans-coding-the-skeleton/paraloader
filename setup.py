from setuptools import setup, find_packages

setup(
    name="paraloader",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
    ],
    entry_points={
        'console_scripts': [
            'paraloader=cli:main',
        ],
    },
    python_requires=">=3.6",
)