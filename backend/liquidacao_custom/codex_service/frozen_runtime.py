import importlib.abc
import importlib.resources.abc
import importlib.util
import marshal
from pathlib import Path
import struct
import sys
import zlib
import os


class InstalledResources(importlib.resources.abc.TraversableResources):
    def __init__(self, directory):
        self.directory = directory

    def files(self):
        return self.directory


class InstalledArchive(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, executable):
        self.internal = Path(executable).parent / "_internal"
        content = Path(executable).read_bytes()
        cookie = content.rfind(b"MEI\x0c\x0b\x0a\x0b\x0e")
        if cookie < 0:
            raise ValueError("Executable archive not found")
        magic, package_size, toc_offset, toc_size, python_version, library = struct.unpack_from("!8sIIII64s", content, cookie)
        if python_version != sys.version_info.major * 100 + sys.version_info.minor:
            raise RuntimeError(f"Python archive version mismatch: {python_version}")
        package_start = cookie + 88 - package_size
        position = package_start + toc_offset
        stop = position + toc_size
        self.pyz = None
        while position < stop:
            length, offset, compressed_size, original_size, compressed, kind = struct.unpack_from("!IIIIBc", content, position)
            name = content[position + 18:position + length].rstrip(b"\0").decode("utf-8")
            if kind == b"z":
                payload = content[package_start + offset:package_start + offset + compressed_size]
                self.pyz = zlib.decompress(payload) if compressed else payload
                break
            position += length
        if self.pyz is None or self.pyz[:4] != b"PYZ\0":
            raise ValueError("Python module archive not found")
        toc_position = struct.unpack_from("!i", self.pyz, 8)[0]
        self.modules = dict(marshal.loads(self.pyz[toc_position:]))
        self.dll_handles = [os.add_dll_directory(str(self.internal))]
        for directory in self.internal.glob("*.libs"):
            self.dll_handles.append(os.add_dll_directory(str(directory)))

    def find_spec(self, fullname, path=None, target=None):
        item = self.modules.get(fullname)
        if item is None or item[0] not in (0, 1):
            return None
        return importlib.util.spec_from_loader(fullname, self, is_package=item[0] == 1)

    def create_module(self, spec):
        return None

    def get_resource_reader(self, fullname):
        return InstalledResources(self.internal / Path(*fullname.split(".")))

    def exec_module(self, module):
        package, position, length = self.modules[module.__name__]
        relative = Path(*module.__name__.split("."))
        module.__file__ = str(self.internal / relative / "__init__.py" if package else self.internal / relative.with_suffix(".py"))
        if package:
            module.__path__ = [str(self.internal / relative)]
        code = marshal.loads(zlib.decompress(self.pyz[position:position + length]))
        exec(code, module.__dict__)


def mount_installed(executable):
    archive = InstalledArchive(executable)
    sys.path.insert(0, str(archive.internal))
    for relative in ("win32", "win32/lib", "pywin32_system32"):
        directory = archive.internal / relative
        if directory.is_dir():
            sys.path.insert(0, str(directory))
            archive.dll_handles.append(os.add_dll_directory(str(directory)))
    sys.frozen = True
    sys._MEIPASS = str(archive.internal)
    sys.meta_path.insert(0, archive)
    return archive
