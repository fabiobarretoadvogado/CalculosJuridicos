import io
from datetime import date
from decimal import Decimal

import pytest
from pypdf import PdfReader

from liquidacao_custom.core.models import DadosGerais, Parcela
from liquidacao_custom.core.motor_ipcae_mensal import calcular_ipcae_mensal
from liquidacao_custom.core.relatorio_pdf import exportar_pdf


def base():
    return {"ipcae_taxas": {"2026-07": "1", "2026-08": "-1.980198019801980198019801980"},
            "fontes": {"ipcae": "https://example.org/indice"}}


def test_deflacao_parcelas_adicionais_sem_nova_correcao_e_pdf():
    parcelas = [Parcela(numero=1, data_vencimento=date(2026, 6, 30), valor_bruto="100")]
    parcelas.extend(Parcela(numero=n, data_vencimento=date(2026, 8, 31), valor_bruto=v, historico=h)
                    for n, v, h in [(2, "99", "Repetição em dobro"), (3, "120", "12 parcelas vincendas")])
    r = calcular_ipcae_mensal(DadosGerais(data_base=date(2026, 8, 31)), parcelas, base())
    assert r.parcelas[0].total_parcela == Decimal("99.00")
    assert [m.competencia for m in r.memoria_mensal] == ["2026-07", "2026-08"]
    assert r.parcelas[1].componentes["correcao"].data_inicial is None
    assert r.resumo.total_atualizado == Decimal("318.00")
    assert r.resumo.correcao_monetaria == Decimal("-1.00")
    assert r.resumo.juros_mora == 0
    r.premissas.update({"omitir_qualificacao": True, "titulo_total": "VALOR DA CAUSA"})
    reader = PdfReader(io.BytesIO(exportar_pdf(r)))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "318,00" in text and "VALOR DA CAUSA" in text
    assert "Repetição em dobro" in text and "12 parcelas vincendas" in text
    assert "Dados do processo" not in text and "Início dos juros" not in text
    assert "SELIC" not in text and "Poupança" not in text
    assert len(reader.pages[0].images) == 1


def test_indice_ausente_e_numero_duplicado_sao_erros():
    p = Parcela(numero=1, data_vencimento=date(2026, 6, 30), valor_bruto="100")
    dados = base()
    del dados["ipcae_taxas"]["2026-08"]
    with pytest.raises(ValueError, match="ausente"):
        calcular_ipcae_mensal(DadosGerais(data_base=date(2026, 8, 31)), [p], dados)
    with pytest.raises(ValueError, match="duplicada"):
        calcular_ipcae_mensal(DadosGerais(data_base=date(2026, 8, 31)), [p, p], base())
