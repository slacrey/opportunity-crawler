from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.risk import detect_risk


def test_detect_risk_classifies_login_and_captcha_text() -> None:
    assert detect_risk("请登录后继续访问")["kind"] == "login_required"
    assert detect_risk("请输入验证码完成安全验证")["kind"] == "operator_intervention_required"
    assert detect_risk("暂无数据")["kind"] == "empty_result"

