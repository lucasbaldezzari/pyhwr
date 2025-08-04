from setuptools import setup, find_packages
import toml

def getRequirements():
    with open('requirements.txt', 'r') as f:
        requirements = f.read().splitlines()
    return requirements

def readme():
    with open('README.md') as f:
        return f.read()
    
def version():
    with open('pyproject.toml') as f:
        return toml.load(f)['project']['version']
    
setup(
    name='hwr',
    version=version(),
    packages=find_packages(),
    install_requires=getRequirements(),
    author='Lucas Baldezzari',
    author_email='lmbaldezzari@gmail.com',
    description='Librería para llevar a cabo experimentos de reconocimiento de escritura a mano alzada usando EEG',
    long_description=readme(),
    url='https://github.com/lucasbaldezzari/hwr',
    license='MIT',
    python_requires='>=3.10',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: Microsoft :: Windows :: Windows 11',
        'Operating System :: Unix',
    ],
)