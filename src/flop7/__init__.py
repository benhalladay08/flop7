from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("flop7")
except PackageNotFoundError:
    __version__ = "0+unknown"
