"""模块测试：分级规划器与失效评分算法（不依赖数据库）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import AnalysisService, classify_text  # noqa: E402


def test_classify_l1():
    r = classify_text("批量导出销售数据并清洗", "按模板生成 CSV 统计报表")
    assert r["level"] == "L1", r
    assert r["auto_assignable"] is True
    assert r["reasons"]


def test_classify_l2():
    r = classify_text("设计订单中心数据库", "完成 ER 建模与接口设计")
    assert r["level"] == "L2", r


def test_classify_l3():
    r = classify_text("风控策略决策与签署", "支付签名校验，合规审批")
    assert r["level"] == "L3", r
    assert r["risk_score"] >= 55


def test_failure_score_formula():
    r = AnalysisService.compute_failure_score([
        ("critical", "agent"), ("major", "tool"), ("minor", "human"),
    ])
    assert r["score"] < 96
    assert r["grade"] in "ABCD"
    assert len(r["detail"]) == 3
    assert r["penalty"] > 0


def test_failure_score_bounds():
    assert AnalysisService.compute_failure_score([])["score"] == 96.0
    many = AnalysisService.compute_failure_score([("critical", "agent")] * 20)
    assert many["score"] >= 0.0


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn(); print("PASS", fn.__name__)
