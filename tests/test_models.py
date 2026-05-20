"""数据模型测试,重点测派生属性和 frozen 行为。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from bjtu_mis import Course, CourseSchedule, Exam, ExamType, Grade, Homework, HomeworkType


class TestHomework:
    def test_creation(self):
        hw = _make_hw(deadline_offset_days=5)
        assert hw.title == "测试作业"
        assert hw.course_name == "数据结构"

    def test_frozen(self):
        hw = _make_hw()
        with pytest.raises(AttributeError):  # FrozenInstanceError 是 AttributeError 子类
            hw.title = "改名"  # type: ignore[misc]

    def test_hashable(self):
        """frozen=True 让对象可以放进 set。"""
        fixed_deadline = datetime(2026, 5, 20, 23, 59)
        hw1 = Homework(
            id="hw-1", title="同名", course_name="C", course_id="cid",
            homework_type=HomeworkType.HOMEWORK, deadline=fixed_deadline,
        )
        hw2 = Homework(
            id="hw-1", title="同名", course_name="C", course_id="cid",
            homework_type=HomeworkType.HOMEWORK, deadline=fixed_deadline,
        )
        s = {hw1, hw2}
        assert len(s) == 1

    def test_days_left_positive(self):
        hw = _make_hw(deadline_offset_days=5)
        assert hw.days_left == 4 or hw.days_left == 5  # 取决于秒级精度

    def test_days_left_negative(self):
        hw = _make_hw(deadline_offset_days=-3)
        assert hw.days_left < 0

    def test_is_overdue(self):
        assert _make_hw(deadline_offset_days=-1).is_overdue
        assert not _make_hw(deadline_offset_days=1).is_overdue

    def test_class_submit_rate_normal(self):
        hw = _make_hw()
        hw.__dict__.copy()
        # 不能直接改 frozen,要新建
        hw = Homework(**{**hw.__dict__, "class_submitted": 25, "class_total": 50})
        assert hw.class_submit_rate == 0.5

    def test_class_submit_rate_no_data(self):
        hw = _make_hw()
        assert hw.class_submit_rate is None

    def test_class_submit_rate_zero_total_safe(self):
        """防御除零。"""
        hw = Homework(**{
            **_make_hw().__dict__,
            "class_submitted": 0,
            "class_total": 0,
        })
        assert hw.class_submit_rate is None


class TestExam:
    def test_end_time_with_duration(self):
        exam = Exam(
            id="e1", course_name="数据结构",
            exam_type=ExamType.FINAL,
            start_time=datetime(2026, 6, 15, 9, 0),
            duration_minutes=120,
            location="A101",
        )
        assert exam.end_time == datetime(2026, 6, 15, 11, 0)

    def test_end_time_without_duration(self):
        exam = Exam(
            id="e1", course_name="x", exam_type=ExamType.FINAL,
            start_time=datetime(2026, 6, 15, 9, 0),
            location="A101",
        )
        assert exam.end_time is None

    def test_is_past(self):
        future = Exam(
            id="e", course_name="x", exam_type=ExamType.FINAL,
            start_time=datetime.now() + timedelta(days=1),
            location="",
        )
        past = Exam(
            id="e", course_name="x", exam_type=ExamType.FINAL,
            start_time=datetime.now() - timedelta(days=1),
            location="",
        )
        assert not future.is_past
        assert past.is_past


class TestGrade:
    def test_passed_default(self):
        g = Grade(
            id="g1", course_name="x", teacher="t",
            semester="2025-2026 1", credit=3.0, score=85.0,
        )
        assert g.is_passed

    def test_can_construct_failed(self):
        g = Grade(
            id="g1", course_name="x", teacher="t",
            semester="2025-2026 1", credit=3.0, score=45.0,
            is_passed=False,
        )
        assert not g.is_passed


class TestCourse:
    def test_schedules_default_empty(self):
        c = Course(
            id="c1", name="数据结构", teacher="z",
            semester_code="2025202602", is_current=True,
        )
        assert c.schedules == ()

    def test_schedule_value_object(self):
        s = CourseSchedule(
            weekday=1, section_start=1, section_end=2,
            weeks=(1, 2, 3, 4),
            location="逸夫楼 A101",
        )
        assert s.weekday == 1


# ── 工厂方法 ──
def _make_hw(*, deadline_offset_days: int = 5) -> Homework:
    return Homework(
        id="hw-1",
        title="测试作业",
        course_name="数据结构",
        course_id="c1",
        homework_type=HomeworkType.HOMEWORK,
        deadline=datetime.now() + timedelta(days=deadline_offset_days),
    )
