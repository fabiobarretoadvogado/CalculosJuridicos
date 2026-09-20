import os
from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import (
    CalculoJudicial,
    DadosGerais,
    IndiceCorrecao,
    TipoJuros,
    Parcela,
    Honorarios,
    BaseCalculo,
    FaixaHonorariosFazenda,
    TipoHonorarios,
    MultaCPC523,
    MultaAdicional,
    TipoDevedor,
    ConfigSelicTaxaUnica,
    ConfigTaxaLegal,
    Abatimento,
    FormaImputacao,
)
from liquidacao_custom.core.motor import executar_calculo
from liquidacao_custom.core.exportadores import exportar_excel, exportar_csv

def test_calculo_privado_ipca_juros_1_por_cento():
    # Teste 24: Cálculo privado com IPCA e juros de 1% ao mês
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2024, 1, 10),
                correcao_monetaria=IndiceCorrecao.IPCA,
                data_inicial_correcao=date(2024, 1, 10),
                juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
                data_inicial_juros=date(2024, 1, 10),
                percentual_juros=Decimal("1.00")
            )
        ]
    )
    res = executar_calculo(calc)
    assert res.resumo.total_atualizado > Decimal("1000.00")

def test_honorarios_sobre_subtotal_atualizado():
    # Teste 12: Honorários sobre subtotal atualizado
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2024, 1, 10),
                correcao_monetaria=IndiceCorrecao.SEM_CORRECAO,
                juros_moratorios=TipoJuros.SEM_JUROS
            )
        ],
        honorarios=[
            Honorarios(descricao="Sucumbenciais", percentual=Decimal("10.00"), base_calculo=BaseCalculo.SUBTOTAL_ATUALIZADO)
        ]
    )
    res = executar_calculo(calc)
    assert res.resumo.honorarios == Decimal("100.00")

def test_honorarios_contratuais_entram_no_total_e_ficam_destacados():
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2024, 1, 10),
            )
        ],
        honorarios=[
            Honorarios(
                tipo=TipoHonorarios.CONTRATUAIS,
                descricao="Contratuais",
                percentual=Decimal("10.00"),
                base_calculo=BaseCalculo.SUBTOTAL_ATUALIZADO,
            )
        ],
    )
    res = executar_calculo(calc)
    assert res.resumo.honorarios == Decimal("100.00")
    assert res.resumo.total_atualizado == Decimal("1100.00")
    assert res.honorarios_detalhes[0]["tipo"] == "contratuais"
    assert res.premissas["honorarios_contratuais_destacados"] == Decimal("100.00")

def test_honorarios_sucumbenciais_fazenda_publica_escalonados():
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.FAZENDA_PUBLICA),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("250000.00"),
                data_vencimento=date(2024, 1, 10),
            )
        ],
        honorarios=[
            Honorarios(
                tipo=TipoHonorarios.SUCUMBENCIAIS,
                descricao="Sucumbenciais Fazenda Pública",
                base_calculo=BaseCalculo.SUBTOTAL_ATUALIZADO,
                escalonar_fazenda_publica=True,
                salario_minimo=Decimal("1000.00"),
                faixas_escalonamento=[
                    FaixaHonorariosFazenda(ordem=1, limite_salarios_minimos=Decimal("200"), percentual_minimo=Decimal("10"), percentual_maximo=Decimal("20"), percentual_aplicado=Decimal("10")),
                    FaixaHonorariosFazenda(ordem=2, limite_salarios_minimos=Decimal("2000"), percentual_minimo=Decimal("8"), percentual_maximo=Decimal("10"), percentual_aplicado=Decimal("8")),
                    FaixaHonorariosFazenda(ordem=3, limite_salarios_minimos=Decimal("20000"), percentual_minimo=Decimal("5"), percentual_maximo=Decimal("8")),
                    FaixaHonorariosFazenda(ordem=4, limite_salarios_minimos=Decimal("100000"), percentual_minimo=Decimal("3"), percentual_maximo=Decimal("5")),
                    FaixaHonorariosFazenda(ordem=5, limite_salarios_minimos=None, percentual_minimo=Decimal("1"), percentual_maximo=Decimal("3")),
                ],
            )
        ],
    )
    res = executar_calculo(calc)
    assert res.resumo.honorarios == Decimal("24000.00")
    assert res.resumo.total_atualizado == Decimal("274000.00")
    assert res.honorarios_detalhes[0]["faixas_escalonamento"][0]["valor_incidente"] == Decimal("200000.00")
    assert res.honorarios_detalhes[0]["faixas_escalonamento"][1]["valor_incidente"] == Decimal("50000.00")

def test_multa_cpc523():
    # Teste 13: Multa do art. 523 desligada
    # Teste 14: Multa do art. 523 ligada
    calc_off = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[Parcela(numero=1, valor_bruto=Decimal("1000.00"), data_vencimento=date(2024, 1, 10))],
        multa_cpc523=MultaCPC523(aplicar=False)
    )
    res_off = executar_calculo(calc_off)
    assert res_off.resumo.multas == Decimal("0")

    calc_on = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[Parcela(numero=1, valor_bruto=Decimal("1000.00"), data_vencimento=date(2024, 1, 10))],
        multa_cpc523=MultaCPC523(aplicar=True, percentual_multa=Decimal("10.00"), percentual_honorarios=Decimal("10.00"))
    )
    res_on = executar_calculo(calc_on)
    # Multa = 100, Honorários de Execução = 100 (somados no resumo.honorarios)
    assert res_on.resumo.multas == Decimal("100.00")
    assert res_on.resumo.honorarios == Decimal("100.00")

def test_multas_independentes_e_adicionais():
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[Parcela(numero=1, valor_bruto=Decimal("1000.00"), data_vencimento=date(2024, 1, 10))],
        multa_cpc523=MultaCPC523(
            aplicar_multa=True,
            aplicar_honorarios=False,
            percentual_multa=Decimal("10.00"),
            percentual_honorarios=Decimal("10.00"),
        ),
        multas_adicionais=[
            MultaAdicional(
                descricao="Litigância de má-fé",
                percentual=Decimal("5.00"),
                base_calculo=BaseCalculo.SUBTOTAL_ATUALIZADO,
            )
        ],
    )
    res = executar_calculo(calc)
    assert res.resumo.multas == Decimal("150.00")
    assert res.resumo.honorarios == Decimal("0.00")

def test_abatimento_maior_que_debito_zera_total_atualizado():
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[Parcela(numero=1, valor_bruto=Decimal("1000.00"), data_vencimento=date(2024, 1, 1))],
        abatimentos=[
            Abatimento(
                data_pagamento=date(2024, 2, 15),
                valor=Decimal("1500.00"),
                forma_imputacao=FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE,
            )
        ],
    )

    res = executar_calculo(calc)

    assert res.resumo.total_atualizado == Decimal("0.00")
    assert res.resumo.abatimentos == Decimal("1000.00")
    assert res.memorias_abatimento[0].competencia_quitacao == "2024-02"
    assert res.memorias_abatimento[0].saldo_remanescente == Decimal("500.00")

def test_fazenda_publica_ec113():
    # Teste 23: Cálculo contra Fazenda Pública com SELIC como taxa única em período configurado
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 6, 1), tipo_devedor=TipoDevedor.FAZENDA_PUBLICA),
        config_selic_taxa_unica=ConfigSelicTaxaUnica(aplicar=True, data_inicio=date(2021, 12, 9)),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2021, 1, 10),
                correcao_monetaria=IndiceCorrecao.IPCAE,
                data_inicial_correcao=date(2021, 1, 10),
                juros_moratorios=TipoJuros.POUPANCA,
                data_inicial_juros=date(2021, 1, 10)
            )
        ]
    )
    res = executar_calculo(calc)
    assert res.resumo.total_atualizado > Decimal("1000.00")

def test_fazenda_publica_ec113_nao_antecipa_selic_antes_da_parcela():
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 6, 1), tipo_devedor=TipoDevedor.FAZENDA_PUBLICA),
        config_selic_taxa_unica=ConfigSelicTaxaUnica(aplicar=True, data_inicio=date(2021, 12, 9)),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2023, 1, 10),
                correcao_monetaria=IndiceCorrecao.IPCAE,
                data_inicial_correcao=date(2023, 1, 10),
                juros_moratorios=TipoJuros.POUPANCA,
                data_inicial_juros=date(2023, 1, 10),
            )
        ],
    )

    res = executar_calculo(calc)

    assert res.parcelas[0].valor_corrigido == Decimal("1179.96")
    assert res.parcelas[0].memoria_correcao[0].competencia == "2023-01"

def test_fazenda_publica_ec113_nao_reescreve_criterios_da_parcela():
    parcela = Parcela(
        numero=1,
        valor_bruto=Decimal("1000.00"),
        data_vencimento=date(2023, 1, 10),
        correcao_monetaria=IndiceCorrecao.IPCAE,
        data_inicial_correcao=date(2023, 1, 10),
        juros_moratorios=TipoJuros.POUPANCA,
        data_inicial_juros=date(2023, 1, 10),
    )
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 6, 1), tipo_devedor=TipoDevedor.FAZENDA_PUBLICA),
        config_selic_taxa_unica=ConfigSelicTaxaUnica(aplicar=True, data_inicio=date(2021, 12, 9)),
        parcelas=[parcela],
    )

    executar_calculo(calc)

    assert parcela.periodos_correcao == []
    assert parcela.periodos_juros == []
    assert parcela.correcao_monetaria == IndiceCorrecao.IPCAE
    assert parcela.juros_moratorios == TipoJuros.POUPANCA

def test_taxa_legal_vigencia_configuravel():
    # Teste 25: Taxa Legal com data de início configurável
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        config_taxa_legal=ConfigTaxaLegal(data_inicio_vigencia=date(2023, 1, 1)),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("1000.00"),
                data_vencimento=date(2024, 1, 10),
                correcao_monetaria=IndiceCorrecao.SEM_CORRECAO,
                juros_moratorios=TipoJuros.TAXA_LEGAL,
                data_inicial_juros=date(2024, 1, 10)
            )
        ]
    )
    res = executar_calculo(calc)
    assert res.resumo.total_atualizado > Decimal("1000.00")

def test_exportadores(tmp_path):
    # Teste 21: Exportação de Excel com todas as abas esperadas
    # Teste 22: Exportação de CSV
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(data_base=date(2024, 4, 1), tipo_devedor=TipoDevedor.PRIVADO),
        parcelas=[Parcela(numero=1, valor_bruto=Decimal("1000.00"), data_vencimento=date(2024, 1, 10))]
    )
    res = executar_calculo(calc)
    
    excel_path = os.path.join(tmp_path, "memoria.xlsx")
    exportar_excel(res, excel_path)
    assert os.path.exists(excel_path)

    csv_dir = os.path.join(tmp_path, "csv")
    exportar_csv(res, csv_dir)
    assert os.path.exists(os.path.join(csv_dir, "resumo_geral.csv"))
    assert os.path.exists(os.path.join(csv_dir, "memoria_mensal.csv"))
    assert os.path.exists(os.path.join(csv_dir, "alertas.csv"))
