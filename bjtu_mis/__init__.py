"""bjtu-mis-py: BJTU 教务/MIS/智慧课程平台统一 Python SDK。

公开 API:
    from bjtu_mis import BjtuClient, Homework, Grade, Exam, Course
    from bjtu_mis import LoginError, CaptchaError  # 等异常

用法见 BjtuClient 文档。
"""
from __future__ import annotations

from .captcha import CaptchaSolver, DdddocrSolver
from .client import BjtuClient
from .enums import ExamType, HomeworkType
from .exceptions import (
    BjtuError,
    CaptchaError,
    CredentialsError,
    LoginError,
    NetworkError,
    NotLoggedInError,
    ParseError,
    RateLimitError,
    SessionExpiredError,
)
from .models import (
    Course,
    CourseSchedule,
    Exam,
    Grade,
    Homework,
    StudentInfo,
)

__version__ = "0.1.0"

# __all__ 是显式声明的"公开符号"列表。
# 用户写 `from bjtu_mis import *` 时只会拿到这里的东西。
# 更重要的:这是文档,告诉用户"这些是稳定 API,我承诺向后兼容"。
__all__ = [
    # 主入口
    "BjtuClient",
    # 数据模型
    "StudentInfo",
    "Homework",
    "Exam",
    "Course",
    "CourseSchedule",
    "Grade",
    # 枚举
    "HomeworkType",
    "ExamType",
    # 验证码接口
    "CaptchaSolver",
    "DdddocrSolver",
    # 异常体系
    "BjtuError",
    "LoginError",
    "CredentialsError",
    "CaptchaError",
    "SessionExpiredError",
    "NotLoggedInError",
    "NetworkError",
    "ParseError",
    "RateLimitError",
    # 版本号
    "__version__",
]
