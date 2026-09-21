from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from liquidacao_custom.metadata import (  # noqa: E402
    APP_DISPLAY_VERSION,
    APP_ID,
    APP_NAME,
    APP_VERSION,
    EXECUTABLE_NAME,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: prepare_installer.py PASTA_DO_APLICATIVO")
    payload = Path(sys.argv[1]).resolve(strict=True)
    executable = payload / EXECUTABLE_NAME
    if not executable.is_file():
        raise FileNotFoundError(f"Executável ausente: {executable}")
    identity = {
        "app_id": APP_ID,
        "name": APP_NAME,
        "version": APP_VERSION,
        "display_version": APP_DISPLAY_VERSION,
        "executable": EXECUTABLE_NAME,
        "distribution": "installed",
    }
    (payload / "app-info.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (payload / "LEIA-ME.md").write_text(
        f"# {APP_NAME} {APP_DISPLAY_VERSION}\n\n"
        "Aplicativo Windows para cálculos jurídicos com processamento local.\n\n"
        "Os critérios de cada cálculo, as fontes e a memória ficam disponíveis "
        "na interface e nos arquivos exportados. O aplicativo consulta o GitHub "
        "somente para verificar atualizações assinadas.\n\n"
        "Quando a integração com o Codex é selecionada no instalador, o próprio "
        "executável fornece ferramentas locais de cálculo e geração de PDF, sem "
        "abrir a interface e sem enviar os dados do cálculo a um serviço do aplicativo.\n",
        encoding="utf-8",
    )
    print(f"Pacote preparado: {payload}")


if __name__ == "__main__":
    main()
