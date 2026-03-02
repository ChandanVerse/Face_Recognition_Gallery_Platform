from setuptools import setup, find_packages

setup(
    name="face-recognition-module",
    version="1.0.0",
    author="Face Recognition Platform",
    description="Standalone module for scanning and indexing known people in the Face Recognition Gallery Platform",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "insightface>=0.7.3",
        "numpy>=1.24.3",
        "pymongo>=4.6.1",
        "pillow>=10.1.0",
        "opencv-python>=4.8.1.78",
        "python-dotenv>=1.0.0",
    ],
)
