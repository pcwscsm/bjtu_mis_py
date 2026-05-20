"""枚举和异常的基础测试。"""
from __future__ import annotations

import pytest

from bjtu_mis import (
    BjtuError,
    CaptchaError,
    CredentialsError,
    ExamType,
    HomeworkType,
    LoginError,
)


class TestHomeworkType:
    def test_int_values_match_api(self):
        """这些 int 值是 BJTU API 的 subType 参数,改了会破坏接口。"""
        assert int(HomeworkType.HOMEWORK) == 0
        assert int(HomeworkType.DESIGN) == 1
        assert int(HomeworkType.LAB) == 2

    def test_label_property(self):
        assert HomeworkType.HOMEWORK.label == "作业"
        assert HomeworkType.DESIGN.label == "课程设计"
        assert HomeworkType.LAB.label == "实验报告"


class TestExamType:
    def test_from_str_exact_match(self):
        assert ExamType.from_str("期末") == ExamType.FINAL
        assert ExamType.from_str("期中") == ExamType.MIDTERM
        assert ExamType.from_str("补考") == ExamType.MAKEUP

    def test_from_str_substring(self):
        """容错:实际接口可能返回"期末考试"这种。"""
        assert ExamType.from_str("期末考试") == ExamType.FINAL
        assert ExamType.from_str("学期末考核") == ExamType.FINAL

    def test_from_str_unknown_falls_back(self):
        assert ExamType.from_str("摸鱼考试") == ExamType.OTHER
        assert ExamType.from_str("") == ExamType.OTHER


class TestExceptionHierarchy:
    """异常体系的核心契约:必须可以一把 catch BjtuError。"""

    def test_all_inherit_from_bjtu_error(self):
        assert issubclass(LoginError, BjtuError)
        assert issubclass(CredentialsError, LoginError)
        assert issubclass(CaptchaError, LoginError)

    def test_credentials_error_caught_as_login(self):
        with pytest.raises(LoginError):
            raise CredentialsError("test")

    def test_captcha_error_caught_as_login(self):
        with pytest.raises(LoginError):
            raise CaptchaError("test")

    def test_login_error_caught_as_bjtu(self):
        with pytest.raises(BjtuError):
            raise LoginError("test")
