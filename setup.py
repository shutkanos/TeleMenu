from setuptools import setup

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
    long_description_content_type='text/markdown',
    url='https://github.com/shutkanos/TeleMenu',

    author='Shutkanos',
    author_email='Shutkanos836926@mail.ru',

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],

    keywords=" ".join(["telegram menu telemenu tele_menu telegram_menu tg_menu tg scene scenes tools telebot telegram_bot pytelegrambotapi"]),
    packages=['tele_menu'],

    install_requires=required,

    extras_require={
        'dev': [],
        'test': [],
    },
)