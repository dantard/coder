from setuptools import setup, find_packages

setup(
    name='spiceditor',
    version='0.0.5',
    packages=find_packages(where='src'),  # Specify src directory
    package_dir={'': 'src'},  # Tell setuptools that packages are under src
    install_requires=[
        'pyqt5',
        'pymupdf >= 1.18.17',
        'autopep8',
        'scipy',
        'qtconsole',
        'termqt',
        'easyconfig2'
    ],
    author='Danilo Tardioli',
    author_email='dantard@unizar.es',
    description='Spice is a Python IDE for students',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/dantard/coder',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'spice=spiceditor.spice:main',
            'spiceterm=spiceditor.spiceterm:main',
        ],
    }
)
