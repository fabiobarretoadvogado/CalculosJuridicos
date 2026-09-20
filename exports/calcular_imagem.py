"""Executa as 36 competências visíveis pelo serviço local, sem alterar o projeto."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent / "outputs" / "01a077a8-b0ae-7ef0-8bcc-ac04bc886031"
OUT.mkdir(parents=True, exist_ok=True)
parcelas = []
for ano in range(2021, 2025):
    for mes in range(1, 13):
        competencia = date(ano, mes, 1)
        if not date(2021, 3, 1) <= competencia <= date(2024, 2, 1):
            continue
        parcelas.append({
            "numero": len(parcelas) + 1,
            "historico": f"Parcela vencida — competência {mes:02d}/{ano}",
            "data_vencimento": competencia.isoformat(),
            "valor_bruto": "999.13" if ano == 2021 else "1231.83",
            "valor_pago_na_data": "0.00",
            "data_inicial_juros": competencia.isoformat(),
        })
assert len(parcelas) == 36
assert sum(Decimal(p["valor_bruto"]) for p in parcelas) == Decimal("42018.88")
payload = {"perfil": "selic_ipcae_poupanca_v1", "dados_gerais": {
    "data_base": "2026-08-31",
    "observacoes": "36 parcelas visíveis na imagem, de 03/2021 a 02/2024. A imagem informa somente mês e ano. Premissa adotada: vencimento, início da atualização e dos juros no dia 1 de cada competência, sujeito à conferência com o título. Sem pagamentos informados. Data-base: último mês com índices completos."
}, "parcelas": parcelas}
body = json.dumps(payload, ensure_ascii=False).encode()
req = Request("http://127.0.0.1:8000/api/v1/calculo", data=body, headers={"Content-Type": "application/json"})
with urlopen(req, timeout=120) as response:
    result = json.load(response)
assert result["premissas"]["versao_metodologia"] == "tema905_poupanca_total_v3"
assert not result["alertas"]
for campo in ("valor_bruto", "correcao_monetaria", "juros_mora", "total_parcela"):
    resumo = {"valor_bruto": "principal_original", "total_parcela": "total_atualizado"}.get(campo, campo)
    assert sum(Decimal(p[campo]) for p in result["parcelas"]) == Decimal(result["resumo"][resumo])
for p in result["parcelas"]:
    assert Decimal(p["valor_bruto"]) + Decimal(p["correcao_monetaria"]) + Decimal(p["juros_mora"]) == Decimal(p["total_parcela"])
(OUT / "entrada.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "memoria_completa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"resumo": result["resumo"], "parcelas": len(parcelas), "linhas_memoria": len(result["memoria_mensal"]), "destino": str(OUT)}, ensure_ascii=False))
