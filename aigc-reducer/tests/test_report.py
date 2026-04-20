# tests/test_report.py
from aigc_reducer.report import _calc_rate


class TestReport:
    def test_calc_rate_empty(self):
        assert _calc_rate([]) == 0

    def test_calc_rate_all_high(self):
        results = [
            {"risk_level": "高风险", "composite_score": 80},
            {"risk_level": "中高", "composite_score": 50},
        ]
        rate = _calc_rate(results)
        assert rate == 100

    def test_calc_rate_mixed(self):
        results = [
            {"risk_level": "高风险", "composite_score": 70},
            {"risk_level": "低风险", "composite_score": 5},
            {"risk_level": "中风险", "composite_score": 20},
        ]
        rate = _calc_rate(results)
        assert rate == 33  # 1/3
