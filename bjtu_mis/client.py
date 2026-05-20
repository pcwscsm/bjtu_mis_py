"""BjtuClient 主入口。

把 _internal/ 下的实现细节装配成一个简洁的用户面 API。
用户只看 import,看不到内部模块结构。
"""
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from ._internal import auth as _auth
from ._internal import http as _http
from ._internal.auth import AuthState
from ._internal.platforms import aa as _aa
from ._internal.platforms import course_platform as _cp
from .captcha import CaptchaSolver, DdddocrSolver
from .enums import HomeworkType
from .exceptions import NotLoggedInError
from .models import Course, Exam, Grade, Homework, StudentInfo

if TYPE_CHECKING:
    from types import TracebackType


_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)


class BjtuClient:
    """BJTU 教务 / MIS / 智慧课程平台统一客户端。

    用法::

        from bjtu_mis import BjtuClient

        with BjtuClient("学号", "密码") as client:
            client.login()
            for hw in client.homeworks(only_pending=True):
                print(hw.title, hw.deadline)
            for grade in client.grades():
                print(grade.course_name, grade.score)

    Args:
        stu_id: 学号。
        password: 密码。
        captcha_solver: 验证码识别器。默认 DdddocrSolver。
        timeout: HTTP 请求超时(秒)。
        max_login_retries: 验证码识别失败时的最大重试次数。
        user_agent: 自定义 User-Agent。
    """

    def __init__(
        self,
        stu_id: str,
        password: str,
        *,
        captcha_solver: CaptchaSolver | None = None,
        timeout: float = 30.0,
        max_login_retries: int = 5,
        user_agent: str | None = None,
    ) -> None:
        self._stu_id = stu_id
        self._password = password
        self._captcha_solver: CaptchaSolver = captcha_solver or DdddocrSolver()
        self._max_login_retries = max_login_retries

        self._session = _http.make_session(
            user_agent=user_agent or _DEFAULT_USER_AGENT,
            timeout=timeout,
        )
        self._state = AuthState(session=self._session)

    # ── 状态属性 ─────────────────────────────────────────────

    @property
    def is_logged_in(self) -> bool:
        """是否已登录(本地状态)。

        服务端 session 可能超时,真正调接口才能确认。
        """
        return self._state.student_info is not None

    @property
    def student_info(self) -> StudentInfo | None:
        """学生信息,未登录时为 None。"""
        return self._state.student_info

    def _ensure_logged_in(self) -> None:
        if not self.is_logged_in:
            raise NotLoggedInError("请先调用 client.login() 完成登录。")

    # ── 上下文管理器 ─────────────────────────────────────────

    def __enter__(self) -> BjtuClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        with contextlib.suppress(Exception):
            self.logout()

    # ── 登录登出 ─────────────────────────────────────────────

    def login(self) -> StudentInfo:
        """登录并返回学生信息。

        Raises:
            CredentialsError: 学号或密码错误。
            CaptchaError: 验证码识别连续失败。
            NetworkError: 网络故障。
            ParseError: BJTU 页面结构与预期不符。
        """
        info = _auth.login(
            self._session,
            self._stu_id,
            self._password,
            self._captcha_solver,
            max_retries=self._max_login_retries,
        )
        self._state.student_info = info
        return info

    def logout(self) -> None:
        """登出并清理本地 cookie / session。"""
        with contextlib.suppress(Exception):
            self._session.close()
        self._state.student_info = None
        self._state.aa_logged_in = False

    # ── 教务系统 ─────────────────────────────────────────────

    def grades(self, *, semester: str | None = None) -> list[Grade]:
        """获取成绩列表。

        Args:
            semester: 学期字符串过滤(如 "2025-2026 1")。None 表示全部历史。
        """
        self._ensure_logged_in()
        return _aa.get_grades(self._session, self._state, semester=semester)

    def exams(self, *, only_upcoming: bool = False) -> list[Exam]:
        """获取考试列表。

        Args:
            only_upcoming: 只返回未发生的考试。
        """
        self._ensure_logged_in()
        items = _aa.get_exams(self._session, self._state)
        if only_upcoming:
            items = [e for e in items if not e.is_past]
        return items

    # ── 智慧课程平台 ──────────────────────────────────────────

    def current_semester_code(self) -> str:
        """当前学期 code(如 '2025202602')。"""
        self._ensure_logged_in()
        return _cp.get_current_semester_code(self._session, self._state)

    def courses(self, *, current_only: bool = True) -> list[Course]:
        """获取课程列表。

        Args:
            current_only: 只返回当前学期的课程。
        """
        self._ensure_logged_in()
        return _cp.get_courses(self._session, self._state, current_only=current_only)

    def homeworks(
        self,
        *,
        course_id: str | None = None,
        types: list[HomeworkType] | None = None,
        only_pending: bool = False,
    ) -> list[Homework]:
        """获取作业列表。

        Args:
            course_id: 只取指定课程的作业。None 表示所有当前学期课程。
            types: 作业类型过滤。None 表示全部三类。
            only_pending: 只返回未提交且未过期的作业。
        """
        self._ensure_logged_in()
        return _cp.get_homeworks(
            self._session, self._state,
            course_id=course_id, types=types, only_pending=only_pending,
        )
