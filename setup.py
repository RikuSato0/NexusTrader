from setuptools import setup, Extension
from Cython.Build import cythonize
import sys

extra_compile_args = []
extra_link_args = []

if sys.platform == "darwin":
    extra_compile_args.extend(["-arch", "arm64"])
    extra_link_args.extend(["-arch", "arm64"])

extensions = [
    Extension(
        "tradebot.ctypes",
        ["./tradebot/ctypes.pyx"],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

setup(
    name="tradebot",
    ext_modules=cythonize(extensions, language_level="3"),
    package_data={
        "tradebot": ["ctypes.pxd"],
    },
    include_package_data=True,
)
