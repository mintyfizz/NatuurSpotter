from pathlib import Path
from setuptools import setup, find_packages

README = Path(__file__).resolve().parent / "README.md"
long_description = README.read_text(encoding="utf-8") if README.exists() else ""

setup(
    name="natuurspotter",
    version="1.0.1",
    description="Biodiversity and moth observation analysis for West Flanders",
    author="Thomas Gatse",
    author_email="thomasgatse@outlook.be",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={"natuurspotter": ["fonts/*.ttf", "fonts/*.txt"]},
    install_requires=[
        "wikipedia",
        "requests",
        "beautifulsoup4",
        "pandas>=2.0",
        "googletrans==4.0.0rc1",
        "fpdf2",
        "folium",
        "matplotlib>=3.8",
        "together",
        "pillow",
        "python-dotenv",
    ],
    python_requires=">=3.8,<3.13",
    license="MIT",
    keywords=["biodiversity", "moths", "ecology", "belgium", "data-analysis", "mapping"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
)
