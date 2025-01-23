from setuptools import setup, find_packages

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'readme.md'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='tele_menu',
    version='3.0',
    description='Telegramm menu system',
    long_description=long_description,
    url='https://github.com/shutkanos',

    author='Shutkanos',
    author_email='Shutkanos836926@mail.ru',

    license='MIT',

    classifiers=[
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],

    keywords='telegramm menu telemenu tele_menu telegramm_menu tg_menu',
    packages=find_packages(),

    install_requires=required,

    extras_require={
        'dev': [],
        'test': [],
    },
)