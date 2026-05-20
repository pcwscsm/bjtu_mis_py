# bjtu-mis-py API 设计

BJTU 教务系统 + MIS 门户 + 智慧课程平台的统一 Python SDK。

## 一句话用法

```python
from bjtu_mis import BjtuClient

client = BjtuClient("学号", "密码")
client.login()

for hw in client.homeworks(only_pending=True):
    print(hw.title, hw.deadline)

for grade in client.grades():
    print(grade.course_name, grade.score)
```

## 顶层 API

### `BjtuClient`

```python
class BjtuClient:
    def __init__(
        self,
        stu_id: str,
        password: str,
        *,
        captcha_solver: CaptchaSolver | None = None,
        timeout: float = 30.0,
        max_login_retries: int = 5,
        user_agent: str | None = None,
    ) -> None: ...

    # ── 会话管理 ──
    def login(self) -> StudentInfo:
        """登录,返回学生信息。失败抛 LoginError 子类。"""

    def logout(self) -> None:
        """登出并清理 cookie。"""

    @property
    def is_logged_in(self) -> bool: ...

    @property
    def student_info(self) -> StudentInfo | None: ...

    # ── 上下文管理器 ──
    def __enter__(self) -> "BjtuClient": ...
    def __exit__(self, *exc) -> None: ...

    # ── 教务系统 (aa.bjtu.edu.cn) ──
    def grades(
        self,
        *,
        semester: str | None = None,
    ) -> list[Grade]: ...

    def exams(
        self,
        *,
        only_upcoming: bool = False,
    ) -> list[Exam]: ...

    # ── 智慧课程平台 (123.121.147.7:88) ──
    def courses(
        self,
        *,
        current_only: bool = True,
    ) -> list[Course]: ...

    def homeworks(
        self,
        *,
        course_id: str | None = None,
        types: list[HomeworkType] | None = None,
        only_pending: bool = False,
    ) -> list[Homework]: ...

    def current_semester_code(self) -> str:
        """当前学期 code(如 '2025202602')。"""
```

## 数据模型

### `StudentInfo`

```python
@dataclass(frozen=True)
class StudentInfo:
    name: str
    role: str          # "本科生" / "研究生" 等
    department: str    # "计算机科学与技术学院"
    stu_id: str
```

### `Homework`

```python
@dataclass(frozen=True)
class Homework:
    id: str                                    # 稳定 ID
    title: str
    course_name: str
    course_id: str
    homework_type: HomeworkType                # 枚举
    deadline: datetime                         # 截止时间
    publish_time: datetime | None              # 发布时间
    content: str = ""                          # HTML 正文
    is_submitted: bool | None = None           # None=接口未返回此字段
    score: float | None = None                 # 个人得分
    max_score: float | None = None             # 满分
    class_submitted: int | None = None         # 全班已交人数
    class_total: int | None = None             # 全班总人数

    @property
    def days_left(self) -> int:
        """距 deadline 还剩几天(可能为负)。"""

    @property
    def is_overdue(self) -> bool: ...
```

### `Exam`

```python
@dataclass(frozen=True)
class Exam:
    id: str
    course_name: str
    course_id: str | None
    exam_type: ExamType                        # 枚举
    start_time: datetime
    duration_minutes: int | None
    location: str
    seat: str = ""
    status: str = ""                           # "正常"/"已请假"等

    @property
    def end_time(self) -> datetime | None: ...

    @property
    def days_left(self) -> int: ...
```

### `Course`

```python
@dataclass(frozen=True)
class Course:
    id: str
    name: str
    teacher: str
    semester_code: str                         # "2025202602"
    is_current: bool
    schedules: tuple[CourseSchedule, ...] = ()  # 用 tuple 因为 frozen

@dataclass(frozen=True)
class CourseSchedule:
    weekday: int                               # 1=周一, 7=周日
    section_start: int
    section_end: int
    weeks: tuple[int, ...]                     # (1, 2, 3, ..., 16)
    location: str
```

### `Grade`

```python
@dataclass(frozen=True)
class Grade:
    id: str
    course_name: str
    teacher: str
    semester: str                              # "2025-2026 1"
    credit: float
    score: float | None = None                 # 百分制成绩
    score_text: str = ""                       # 五级制或文字
    gpa: float | None = None
    is_passed: bool = True
    is_makeup: bool = False
```

## 枚举

```python
class HomeworkType(IntEnum):
    HOMEWORK = 0       # 普通作业
    DESIGN = 1         # 课程设计
    LAB = 2            # 实验报告

    @property
    def label(self) -> str: ...        # 中文标签

class ExamType(StrEnum):
    FINAL = "期末"
    MIDTERM = "期中"
    MAKEUP = "补考"
    OTHER = "其他"
```

## 异常体系

```python
class BjtuError(Exception):
    """所有 SDK 异常的基类。"""

class LoginError(BjtuError): pass
class CredentialsError(LoginError): pass         # 账号密码错,不可重试
class CaptchaError(LoginError): pass             # 验证码识别失败,可重试
class SessionExpiredError(BjtuError): pass       # 会话超时
class NotLoggedInError(BjtuError): pass          # 未登录就调接口
class NetworkError(BjtuError): pass              # HTTP 层问题
class ParseError(BjtuError): pass                # BJTU 改接口了
class RateLimitError(BjtuError): pass            # 被风控
```

## CaptchaSolver Protocol

```python
class CaptchaSolver(Protocol):
    def solve(self, image_bytes: bytes) -> str: ...

# 默认实现
class DdddocrSolver:
    def solve(self, image_bytes: bytes) -> str: ...
```
