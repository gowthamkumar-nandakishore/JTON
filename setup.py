from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "myson.myson_core",
        ["src/myson_core.pyx"],
        extra_compile_args=["-O3", "-march=native", "-ffast-math"],
    ),
    Extension(
        "myson.myson_fast",
        ["src/myson_fast.pyx"],
        extra_compile_args=["-O3", "-march=native", "-ffast-math", "-funroll-loops"],
    )
]

setup(
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
    packages=["myson"],
    package_dir={"myson": "src"},
)
