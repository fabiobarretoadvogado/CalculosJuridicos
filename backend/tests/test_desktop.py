from liquidacao_custom.desktop import _enable_webview_downloads


def test_desktop_habilita_downloads_na_janela() -> None:
    class WebViewFalso:
        settings = {"ALLOW_DOWNLOADS": False}

    _enable_webview_downloads(WebViewFalso)

    assert WebViewFalso.settings["ALLOW_DOWNLOADS"] is True
