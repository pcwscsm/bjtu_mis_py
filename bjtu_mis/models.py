"""SDK 公开的数据模型。

设计原则:
1. 全部 frozen — 不可变 = 可哈希 + 线程安全 + 防误改。
2. 字段类型用真正的语义类型(datetime, bool, float),不用 str 兜底。
3. 派生信息(如 days_left, is_overdue)做成 property,而不是字段——
   因为字段是"快照",day_left 应该按当前时间算,每次访问都新算。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .enums import ExamType, HomeworkType


@dataclass(frozen=True)
class StudentInfo:
    """登录后从 MIS 主页解析出的学生信息。"""

    name: str
    role: str           # "本科生" / "研究生" 等
    department: str     # "计算机科学与技术学院"
    stu_id: str         # 学号


@dataclass(frozen=True)
class Homework:
    """智慧课程平台的一条作业(含课程设计、实验报告)。"""

    id: str
    title: str
    course_name: str
    course_id: str
    homework_type: HomeworkType
    deadline: datetime
    publish_time: datetime | None = None
    content: str = ""
    is_submitted: bool | None = None
    score: float | None = None
    max_score: float | None = None
    class_submitted: int | None = None
    class_total: int | None = None

    @property
    def days_left(self) -> int:
        """距 deadline 还剩几天(向下取整,可能为负)。

        以当前时刻计算,每次访问可能不同。
        """
        delta = self.deadline - datetime.now()
        return delta.days

    @property
    def is_overdue(self) -> bool:
        """是否已过 deadline。"""
        return datetime.now() > self.deadline

    @property
    def class_submit_rate(self) -> float | None:
        """全班提交率 (0.0 ~ 1.0)。数据不全时返回 None。"""
        if self.class_submitted is None or not self.class_total:
            return None
        return self.class_submitted / self.class_total


@dataclass(frozen=True)
class Exam:
    """一场考试。"""

    id: str
    course_name: str
    exam_type: ExamType
    start_time: datetime
    location: str
    course_id: str | None = None
    duration_minutes: int | None = None
    seat: str = ""
    status: str = ""

    @property
    def end_time(self) -> datetime | None:
        """根据 duration 推断的结束时间。未知 duration 时 None。"""
        if self.duration_minutes is None:
            return None
        return self.start_time + timedelta(minutes=self.duration_minutes)

    @property
    def days_left(self) -> int:
        return (self.start_time - datetime.now()).days

    @property
    def is_past(self) -> bool:
        return datetime.now() > self.start_time


@dataclass(frozen=True)
class CourseSchedule:
    """一门课的一个上课时段。同一门课可能有多个段(理论+实验)。"""

    weekday: int                # 1=周一, 7=周日
    section_start: int          # 第几节开始
    section_end: int            # 第几节结束
    weeks: tuple[int, ...]      # 上课周次,如 (1,2,...,16)
    location: str = ""


@dataclass(frozen=True)
class Course:
    """学期内的一门课。"""

    id: str
    name: str
    teacher: str
    semester_code: str          # "2025202602"
    is_current: bool
    schedules: tuple[CourseSchedule, ...] = ()


@dataclass(frozen=True)
class Grade:
    """单门课的成绩记录。"""

    id: str
    course_name: str
    teacher: str
    semester: str               # "2025-2026 1"
    credit: float
    score: float | None = None
    score_text: str = ""
    gpa: float | None = None
    is_passed: bool = True
    is_makeup: bool = False
