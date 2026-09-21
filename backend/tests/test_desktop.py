from liquidacao_custom.desktop import _enable_webview_downloads, self_check


def test_desktop_habilita_downloads_na_janela() -> None:
    class WebViewFalso:
        settings = {"ALLOW_DOWNLOADS": False}

    _enable_webview_downloads(WebViewFalso)

    assert WebViewFalso.settings["ALLOW_DOWNLOADS"] is True


def test_autoteste_inclui_integracao_mcp(capsys) -> None:
    assert self_check() == 0
    assert '"mcp": true' in capsys.readouterr().out
