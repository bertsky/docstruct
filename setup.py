# -*- coding: utf-8 -*-
"""
Installs:

    - ocrd-docstruct
"""
import codecs

import json
from setuptools import setup, find_packages

with open('./ocrd-tool.json', 'r') as f:
    version = json.load(f)['version']
    
setup(
    name='docstruct',
    version=version,
    description='Document structure detection from PAGE to METS',
    long_description=codecs.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Robert Sachunsky',
    author_email='sachunsky@informatik.uni-leipzig.de',
    url='https://github.com/bertsky/docstruct',
    license='Apache License 2.0',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=open('requirements.txt').read().split('\n'),
    package_data={
        '': ['*.json', '*.yml', '*.yaml'],
    },
    entry_points={
        'console_scripts': [
            'ocrd-docstruct=docstruct.proc:cli',
        ]
    },
)
