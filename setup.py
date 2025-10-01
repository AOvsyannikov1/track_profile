from setuptools import setup, find_packages, Extension


def readme():
  with open('README.md', 'r') as f:
    return f.read()

setup(
    name="track_profile",
    version="1.1.0",
    packages=find_packages(),
    long_description=readme(),
    package_data={
        "track_profile": [
            "data/*.txt"
        ]
    },
    include_package_data=True,
    # entry_points={
    #     'pyinstaller40': [
    #         'hook-dirs = cornplot:_get_hook_dirs',
    #     ],
    # },
    
    author="Ovsyannikov Andrey",
    author_email="andsup108@gmail.com",
    keywords="railway"
)
