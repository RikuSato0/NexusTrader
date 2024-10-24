from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension("tradebot.ctypes", ["./tradebot/ctypes.pyx"]),
]

setup(
    name="tradebot",
    ext_modules=cythonize(extensions, language_level="3"),
    package_data={
        "tradebot": ["ctypes.pxd"],
    },
    include_package_data=True,
)
