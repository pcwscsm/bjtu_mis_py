"""平台层的纯函数解析器测试。

这些函数只接收 HTML/JSON 字符串,输出 dataclass,适合直接单测,不需要 mock HTTP。
"""
from __future__ import annotations

from datetime import datetime

from bjtu_mis import ExamType, HomeworkType
from bjtu_mis._internal.platforms.aa import _parse_exams, _parse_grades
from bjtu_mis._internal.platforms.course_platform import _fetch_homework_one  # noqa

from . import fixtures as F


class TestExamParser:
    def test_parse_two_exams(self):
        items = _parse_exams(F.EXAM_LIST_HTML)
        assert len(items) == 2

    def test_first_exam_fields(self):
        items = _parse_exams(F.EXAM_LIST_HTML)
        e = items[0]
        assert e.course_name == "数据结构"
        assert e.exam_type == ExamType.FINAL
        assert e.start_time == datetime(2026, 6, 23, 9, 0)
        assert e.duration_minutes == 120
        assert e.location == "逸夫楼 A101 座位 12"

    def test_empty_page_returns_empty(self):
        items = _parse_exams("<html><body>no table</body></html>")
        assert items == []

    def test_id_is_stable(self):
        """同样的数据应该生成相同 ID。"""
        items1 = _parse_exams(F.EXAM_LIST_HTML)
        items2 = _parse_exams(F.EXAM_LIST_HTML)
        assert items1[0].id == items2[0].id


class TestGradeParser:
    def test_parse_grades(self):
        items = _parse_grades(F.GRADE_LIST_HTML)
        # 第三行没成绩(体育)会被过滤
        assert len(items) == 2

    def test_first_grade_fields(self):
        items = _parse_grades(F.GRADE_LIST_HTML)
        g = items[0]
        assert g.course_name == "数据结构"
        assert g.score == 87.0
        assert g.gpa == 3.7
        assert g.credit == 4.0
        assert g.teacher == "张三"
        assert g.semester == "2025-2026 1"
        assert g.is_passed

    def test_failed_grade_marked(self):
        items = _parse_grades(F.GRADE_LIST_HTML)
        physics = [g for g in items if g.course_name == "大学物理"][0]
        assert physics.score == 52.0
        assert not physics.is_passed

    def test_unreleased_grade_filtered(self):
        items = _parse_grades(F.GRADE_LIST_HTML)
        names = [g.course_name for g in items]
        assert not any("体育" in n for n in names)
