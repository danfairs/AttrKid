from setuptools import setup, find_packages

NAME = "attrkid"
VERSION = "0.9.0"

setup(
    name=NAME,
    version=VERSION,
    description="attrkid: serialise and deserialise attrs classes to dicts ",
    author_email="dan.fairs@gmail.com",
    url="https://polihq.com",
    keywords=["attrs"],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'attrs>=18.2.0',
        'python-dateutil>=2.7.5',
        'pytz>=2018.9',
    ],
    setup_requires=['pytest-runner'],
    tests_require=[
        'hypothesis>=4.0.1',
        'pytest>=4.1.1',
        'pytest-mock>=1.10.0',
        'python-dateutil>=2.7.5',
        'pytz>=2018.9',
    ],
)
