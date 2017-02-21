from setuptools import setup

with open('requirements.txt') as reqs:
    install_requires = [line for line in reqs.read().split('\n') if (
        line and not line.startswith('--'))
    ]

with open('README.rst', 'r') as f:
    long_description = f.read()

classifiers = (
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
)

setup(
    name='movescount-sync',
    version='1.0',
    url='https://github.com/brutasse/movescount-sync',
    author='Bruno Renié',
    license='BSD',
    description='Fetch moves from movescount.com',
    long_description=long_description,
    py_modules=('movescount_sync',),
    zip_safe=False,
    platforms='any',
    include_package_data=True,
    classifiers=classifiers,
    install_requires=install_requires,
    entry_points={'console_scripts': ['movescount-sync=movescount_sync:main']},
)
