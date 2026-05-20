"""DdddocrSolver 的字符串后处理逻辑测试。

不测真正的图像识别(那需要真图片 + ddddocr),只测 normalize / eval 这两个静态方法。
这些方法是从实战日志里调出来的关键回退逻辑。
"""
from __future__ import annotations

import pytest

from bjtu_mis import CaptchaError, CaptchaSolver, DdddocrSolver


class TestNormalize:
    def test_strip_equals_and_question(self):
        assert DdddocrSolver._normalize("3+5=?") == "3+5"

    def test_replace_multiply_symbols(self):
        assert DdddocrSolver._normalize("3x5") == "3*5"
        assert DdddocrSolver._normalize("3X5") == "3*5"
        assert DdddocrSolver._normalize("3×5") == "3*5"

    def test_replace_divide_symbol(self):
        assert DdddocrSolver._normalize("6÷2") == "6/2"

    def test_strip_dangling_operators(self):
        """实战:ddddocr 把 ? 或 = 识别成 - 时,首尾会有悬挂运算符。"""
        assert DdddocrSolver._normalize("6+6-") == "6+6"
        assert DdddocrSolver._normalize("-1*5-") == "1*5"

    def test_remove_garbage_chars(self):
        assert DdddocrSolver._normalize("abc 3-1 def") == "3-1"


class TestEval:
    @pytest.mark.parametrize("text,expected", [
        ("3+5", 8),
        ("7-2", 5),
        ("3*4", 12),
        ("8/2", 4),
    ])
    def test_basic_arithmetic(self, text, expected):
        assert DdddocrSolver._eval(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("31", 2),    # 3-1
        ("52", 3),    # 5-2
        ("99", 0),    # 9-9
        ("17", -6),   # 1-7
        ("81", 7),    # 8-1, 用户日志里的真实样本
    ])
    def test_two_digit_fallback(self, text, expected):
        """实战回退:ddddocr 把减号识别丢了,纯两位数字按 a-b 处理。"""
        assert DdddocrSolver._eval(text) == expected

    def test_single_digit(self):
        assert DdddocrSolver._eval("5") == 5

    def test_three_digit_rejected(self):
        """三位数歧义太大,拒绝处理。"""
        with pytest.raises(ValueError):
            DdddocrSolver._eval("123")

    def test_operator_prefix_rejected(self):
        with pytest.raises(ValueError):
            DdddocrSolver._eval("-5")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            DdddocrSolver._eval("")


class TestProtocolDuckTyping:
    """Protocol 的核心好处:不用继承也能满足类型。"""

    def test_custom_solver_works(self):
        class FakeSolver:
            def solve(self, image_bytes: bytes) -> str:
                return "42"

        s: CaptchaSolver = FakeSolver()
        assert s.solve(b"") == "42"

    def test_isinstance_check(self):
        class FakeSolver:
            def solve(self, image_bytes: bytes) -> str:
                return ""

        # Protocol 用 @runtime_checkable 装饰,所以 isinstance 也能工作
        assert isinstance(FakeSolver(), CaptchaSolver)
