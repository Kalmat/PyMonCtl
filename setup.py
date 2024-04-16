import io
import os
import re
from setuptools import setup, find_packages

scriptFolder = os.path.dirname(os.path.realpath(__file__))
os.chdir(scriptFolder)

# Find version info from module (without importing the module):
with open("src/pymonctl/__init__.py", "r") as fileObj:
    match = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fileObj.read(), re.MULTILINE
    )
    if not match:
        raise TypeError("'__version__' not found in 'src/pymonctl/__init__.py'")
    version = match.group(1)

# Use the README.md content for the long description:
with io.open("README.md", encoding="utf-8") as fileObj:
    long_description = fileObj.read()

setup(
    name='PyMonCtl',
    version=version,
    url='https://github.com/Kalmat/PyMonCtl',
    # download_url='https://github.com/Kalmat/PyMonCtl/archive/refs/tags/%s.tar.gz' % version,
    author='Kalmat',
    author_email='palookjones@gmail.com',
    description=('Cross-Platform toolkit to get info on and control monitors connected'),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='BSD 3',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={"pymonctl": ["py.typed"]},
    test_suite='tests',
    install_requires=[
        "pywin32>=302; sys_platform == 'win32'",
        "python-xlib>=0.21; sys_platform == 'linux'",
        "ewmhlib>=0.1; sys_platform == 'linux'",
        "pyobjc>=8.1; sys_platform == 'darwin'",
        "typing_extensions>=4.4.0"
    ],
    extras_require={
        'dev': [
            "types-setuptools>=65.5",
            "mypy>=0.990",
            "types-pywin32>=305.0.0.3",
            "types-python-xlib>=0.32",
            "pywinctl>=0.3"
        ]
    },
    keywords="screen display monitor control geometry size position frequency scale orientation "
             "screen-size mouse-position",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Environment :: MacOS X',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11'
    ],
)
