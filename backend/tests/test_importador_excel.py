import os
from decimal import Decimal
from liquidacao_custom.core.importador_excel import gerar_template, importar_parcelas

def test_importacao_excel_completa(tmp_path):
    # Teste 7: Importação de parcelas por Excel
    caminho = os.path.join(tmp_path, "modelo.xlsx")
    gerar_template(caminho)
    assert os.path.exists(caminho)
    
    parcelas, erros = importar_parcelas(caminho)
    # Deve conter a linha de exemplo adicionada no template
    assert len(parcelas) == 1
    assert len(erros) == 0
    assert parcelas[0].valor_bruto == Decimal("1500.00")
