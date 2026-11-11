from __future__ import annotations

import hashlib
import json
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from pathlib import Path, PurePosixPath

from liquidacao_custom.calculos_salvos import _data_dir

BUNDLED = Path(__file__).resolve().parents[2] / "data"
PACKAGE_PREFIX = "indices-v2-"
FILES_BASE = tuple(sorted([
    "indices_simplificados.json", "indices_ec136.json", "selic_historica.json",
    "ipca_oficial.json", "taxa_legal_oficial.json", "salario_minimo.csv",
    "inpc_oficial.json", "igpm_oficial.json", "taxa_legal_reconstruida.json",
    *[f"fontes/{name}.json" for name in (
        "bcb_ipca15_2009_2026", "bcb_meta_selic", "bcb_selic_mensal",
        "bcb_poupanca_total", "bcb_poupanca_total_2009_2012",
        "bcb_poupanca_total_2012_2016", "bcb_poupanca_total_2017_2021",
        "bcb_poupanca_depositos_2021_2026", "ipca15_fonte", "poupanca_depositos_fonte",
        "bcb_selic_anual_civil5_2000_2009", "bcb_selic_anual_civil5_2010_2019",
        "bcb_selic_anual_civil5_2020_2024", "bcb_ipca15_civil5_2000_2024",
    )],
]))
FILES_HISTORICOS = (
    "fontes/bcb_ipca_1980_2026.json",
    "fontes/bcb_ipcae_1992_2026.json",
    "fontes/ipcae_historico_fonte.json",
)
FILES = tuple(sorted((*FILES_BASE, *FILES_HISTORICOS)))
_context: ContextVar[Dataset | None] = ContextVar("index_dataset", default=None)
_lock = threading.RLock()
_cache = {}


def file_records(directory: Path) -> dict:
    return {name: {"size": (directory / name).stat().st_size,
                   "sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()}
            for name in FILES}


def dataset_id(records: dict) -> str:
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Dataset:
    directory: Path
    identity: str
    revision: str = ""
    origin: str = "instalador"
    warning: str = ""
    def metadata(self):
        return {"versao": self.revision or "base-" + self.identity[:12],
                "sha256": self.identity, "origem": self.origin, "formato": 2}


def storage_root() -> Path:
    return _data_dir() / "indices"


def _fingerprint(directory: Path, names=FILES):
    return tuple((name, (directory / name).stat().st_mtime_ns,
                  (directory / name).stat().st_size) for name in names)


def bundled_dataset() -> Dataset:
    fingerprint = (str(BUNDLED), _fingerprint(BUNDLED))
    with _lock:
        if fingerprint not in _cache:
            _cache.clear()
            _cache[fingerprint] = Dataset(BUNDLED, dataset_id(file_records(BUNDLED)))
        return _cache[fingerprint]


def current_dataset() -> Dataset:
    pinned = _context.get()
    if pinned is not None:
        return pinned
    bundled = bundled_dataset()
    pointer = storage_root() / "active.json"
    if not pointer.exists():
        return bundled
    try:
        from .client import verify_manifest, UnsupportedIndexFormat
        from .validation import validate_directory, ensure_no_regression
        from liquidacao_custom.updates import settings

        envelope = pointer.read_bytes()
        manifest = verify_manifest(envelope, settings.PUBLIC_KEY, settings.REPOSITORY)
        if manifest["files"].keys() == set(FILES_BASE):
            # Este pacote assinado é anterior à inclusão das séries históricas.
            return bundled
        directory = storage_root() / "versions" / manifest["dataset_id"]
        fingerprint = (str(directory), hashlib.sha256(envelope).hexdigest(),
                       _fingerprint(directory, manifest["files"]), bundled.identity)
        with _lock:
            # Sempre confirmar os bytes assinados da base canônica.
            for name, record in manifest["files"].items():
                raw = (directory / name).read_bytes()
                if len(raw) != record["size"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise ValueError("Arquivo de índices alterado após a validação.")
            if fingerprint not in _cache:
                validate_directory(directory, manifest["files"])
                ensure_no_regression(directory, BUNDLED)
                _cache[fingerprint] = Dataset(directory, manifest["dataset_id"], manifest["revision"], "atualizacao")
            return _cache[fingerprint]
    except UnsupportedIndexFormat:
        return Dataset(bundled.directory, bundled.identity, warning=(
            "O pacote local utiliza um formato antigo e foi ignorado. "
            "Somente as novas bases oficiais incorporadas estão em uso. "
            "Os arquivos anteriores e os cálculos salvos foram preservados."
        ))
    except Exception:
        return Dataset(bundled.directory, bundled.identity, warning=(
            "O pacote local não pôde ser validado ou é anterior à base do programa. "
            "A base do instalador está em uso. Verifique a atualização dos índices."
        ))


@contextmanager
def index_context():
    """Uma operação inteira usa a mesma versão, inclusive durante um download."""
    if _context.get() is not None:
        yield _context.get()
        return
    token = _context.set(current_dataset())
    try:
        yield _context.get()
    finally:
        _context.reset(token)


def with_index_dataset(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with index_context() as dataset:
            result = function(*args, **kwargs)
            if hasattr(result, "premissas"):
                result.premissas["base_indices"] = dataset.metadata()
            elif hasattr(result, "base_indices"):
                result.base_indices = dataset.metadata()
            return result
    return wrapped


class DataPath(os.PathLike):
    """Referência estável cuja pasta é resolvida na versão fixada da operação."""
    def __init__(self, relative: str = ""):
        value = PurePosixPath(relative)
        if value.is_absolute() or ".." in value.parts or "\\" in relative or ":" in relative:
            raise ValueError("Caminho inválido da base de índices.")
        self.relative = value

    def resolve(self):
        return current_dataset().directory / self.relative

    def __fspath__(self):
        return str(self.resolve())

    def __str__(self):
        return self.__fspath__()

    def __truediv__(self, name):
        return DataPath(str(self.relative / name))

    @property
    def parent(self):
        return DataPath(str(self.relative.parent))

    def with_name(self, name):
        return DataPath(str(self.relative.with_name(name)))

    def read_text(self, *args, **kwargs):
        return self.resolve().read_text(*args, **kwargs)

    def read_bytes(self):
        return self.resolve().read_bytes()

    def exists(self):
        return self.resolve().exists()
