
import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='python-bcb',
    version='0.1.2',
    packages=setuptools.find_packages(),
    author='Wilson Freitas',
    author_email='wilson.freitas@gmail.com',
    description='Python interface to Brazilian Central Bank web services',
    url='https://github.com/wilsonfreitas/python-bcb',
    keywords='brazilian central bank, finance, central bank, banking',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3'
)
