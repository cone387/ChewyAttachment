"""ChewyAttachment - 通用图片/附件管理插件"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("chewy-attachment")
    except PackageNotFoundError:
        # Package is not installed (development mode)
        __version__ = "0.5.1"
except ImportError:
    # Python < 3.8
    __version__ = "0.5.1"
