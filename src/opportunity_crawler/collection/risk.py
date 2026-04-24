from __future__ import annotations


def detect_risk(text: str) -> dict[str, str]:
    if _contains_any(text, ("请登录", "登录后", "用户登录", "账号登录")):
        return {"kind": "login_required", "message": "login prompt detected"}
    if _contains_any(text, ("验证码", "安全验证", "滑块验证", "人机验证")):
        return {"kind": "operator_intervention_required", "message": "operator intervention prompt detected"}
    if _contains_any(text, ("暂无数据", "无相关数据", "没有找到", "无结果")):
        return {"kind": "empty_result", "message": "empty result prompt detected"}
    return {"kind": "none", "message": "no risk detected"}


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)

