from __future__ import annotations

from pathlib import Path

import pytest

from backend.services import billing_service


@pytest.fixture(autouse=True)
def _isolate_billing_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Каждый тест получает чистое usage-хранилище биллинга.

    Без изоляции интеграционные тесты копили бы расходы квоты в общем файле
    и падали бы по 402 в произвольном порядке.
    """
    monkeypatch.setattr(billing_service, "STORAGE_DIR", tmp_path / "billing-usage")
