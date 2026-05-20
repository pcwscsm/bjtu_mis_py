"""SDK 用到的枚举。"""
from __future__ import annotations

import sys
from enum import IntEnum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Polyfill of stdlib ``enum.StrEnum`` for Python 3.10."""

        def __str__(self) -> str:
            return self.value


class HomeworkType(IntEnum):
    """作业类型。值对应智慧课程平台 API 的 subType 参数。"""

    HOMEWORK = 0   # 普通作业
    DESIGN = 1     # 课程设计
    LAB = 2        # 实验报告

    @property
    def label(self) -> str:
        """中文标签,用于显示。"""
        return _HOMEWORK_TYPE_LABELS[self]


_HOMEWORK_TYPE_LABELS: dict[HomeworkType, str] = {
    HomeworkType.HOMEWORK: "作业",
    HomeworkType.DESIGN: "课程设计",
    HomeworkType.LAB: "实验报告",
}


class ExamType(StrEnum):
    """考试类型。BJTU 教务系统返回的字符串直接对应。"""

    FINAL = "期末"
    MIDTERM = "期中"
    MAKEUP = "补考"
    OTHER = "其他"

    @classmethod
    def from_str(cls, raw: str) -> ExamType:
        """容错的字符串到枚举转换。未知字符串归为 OTHER。"""
        for member in cls:
            if member.value in raw:
                return member
        return cls.OTHER
