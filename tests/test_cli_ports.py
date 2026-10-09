import sys

import pytest

from nano import cli


def test_litert_cli_skips_start_when_endpoint_is_already_healthy(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["nano-ai", "litert-lm"])
    monkeypatch.setattr(cli, "litert_binary", lambda: "/fake/litert-lm")
    monkeypatch.setattr(cli, "endpoint_responds", lambda url: url.endswith("/v1/models"))
    monkeypatch.setattr(cli, "port_is_open", lambda host, port: True)

    cli.main()

    assert "already responding" in capsys.readouterr().out


def test_litert_cli_explains_port_conflict_when_endpoint_is_not_litert(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nano-ai", "litert-lm"])
    monkeypatch.setattr(cli, "litert_binary", lambda: "/fake/litert-lm")
    monkeypatch.setattr(cli, "endpoint_responds", lambda url: False)
    monkeypatch.setattr(cli, "port_is_open", lambda host, port: True)

    with pytest.raises(SystemExit, match="already in use"):
        cli.main()


def test_web_cli_skips_start_when_nano_is_already_running(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["nano-ai", "web"])
    monkeypatch.setattr(cli, "endpoint_responds", lambda url: url.endswith("/api/system"))
    monkeypatch.setattr(cli, "port_is_open", lambda host, port: True)

    cli.main()

    assert "Nano AI web server is already responding" in capsys.readouterr().out


def test_web_cli_explains_port_conflict_when_other_service_owns_port(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nano-ai", "web"])
    monkeypatch.setattr(cli, "endpoint_responds", lambda url: False)
    monkeypatch.setattr(cli, "port_is_open", lambda host, port: True)

    with pytest.raises(SystemExit, match="already in use"):
        cli.main()
