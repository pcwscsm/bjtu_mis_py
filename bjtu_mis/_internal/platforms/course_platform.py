"""智慧课程平台 (123.121.147.7:88) 接口。

需要先走 SSO 跳转拿 sessionId,后续接口请求都要在 header 带上。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from requests import Session

from ...enums import HomeworkType
from ...exceptions import ParseError
from ...models import Course, Homework
from .. import http
from ..auth import AuthState

log = logging.getLogger(__name__)

PLATFORM_BASE = "http://123.121.147.7:88"
SSO_ENTRY = "https://mis.bjtu.edu.cn/module/module/28/"


def _parse_dt(text: str) -> datetime | None:
    """支持几种常见格式:'2026-05-03 23:59'、'2026-05-03 23:59:59'、'2026-05-03'。"""
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def ensure_platform_session(session: Session, state: AuthState) -> str:
    """确保智慧课程平台 session 就绪,返回 sessionId。

    sessionId 通过实例属性 _platform_session_id 缓存,避免每次重新获取。
    """
    if hasattr(state, "platform_session_id") and state.platform_session_id:
        return state.platform_session_id

    # SSO 跳转
    http.get(session, SSO_ENTRY, allow_redirects=True)

    # 拉 sessionId
    url = f"{PLATFORM_BASE}/ve/back/coursePlatform/message.shtml?method=getArticleList"
    data = http.get_json(session, url, headers=_headers(""))
    sid = data.get("sessionId", "")
    if not sid:
        raise ParseError(
            f"无法获取智慧课程平台 sessionId, JSON keys={list(data.keys())}"
        )

    state.platform_session_id = sid  # type: ignore[attr-defined]
    return sid


def _headers(session_id: str) -> dict[str, str]:
    h = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"{PLATFORM_BASE}",
        "X-Requested-With": "XMLHttpRequest",
    }
    if session_id:
        h["sessionid"] = session_id
    return h


def get_current_semester_code(session: Session, state: AuthState) -> str:
    sid = ensure_platform_session(session, state)
    url = f"{PLATFORM_BASE}/ve/back/rp/common/teachCalendar.shtml?method=queryCurrentXq"
    data = http.get_json(session, url, headers=_headers(sid))
    try:
        return data["result"][0]["xqCode"]
    except (KeyError, IndexError, TypeError) as e:
        raise ParseError(f"无法从响应提取 xqCode: {data}") from e


# ── 课程列表 ─────────────────────────────────────────────────

def get_courses(
    session: Session,
    state: AuthState,
    *,
    current_only: bool = True,
) -> list[Course]:
    sid = ensure_platform_session(session, state)
    xq_code = get_current_semester_code(session, state)

    url = (
        f"{PLATFORM_BASE}/ve/back/coursePlatform/course.shtml"
        f"?method=getCourseList&pagesize=100&page=1&xqCode={xq_code}"
    )
    data = http.get_json(session, url, headers=_headers(sid))
    raw_list = data.get("courseList") or []

    items: list[Course] = []
    for raw in raw_list:
        items.append(Course(
            id=str(raw.get("id", "")),
            name=raw.get("name", ""),
            teacher=raw.get("teacher_name", ""),
            semester_code=raw.get("xq_code", xq_code),
            is_current=raw.get("xq_code", xq_code) == xq_code,
            schedules=(),  # 课表时间需要另一个接口(略,以后扩展)
        ))

    if current_only:
        items = [c for c in items if c.is_current]
    return items


# ── 作业列表 ─────────────────────────────────────────────────

def get_homeworks(
    session: Session,
    state: AuthState,
    *,
    course_id: str | None = None,
    types: list[HomeworkType] | None = None,
    only_pending: bool = False,
) -> list[Homework]:
    sid = ensure_platform_session(session, state)

    # 决定要遍历哪些课程
    if course_id is not None:
        # 用户指定了课程:构造一个最小课程对象,不预拉课程列表
        target_courses: list[tuple[str, str]] = [(course_id, "")]
    else:
        courses = get_courses(session, state, current_only=True)
        target_courses = [(c.id, c.name) for c in courses]

    sub_types = types or [HomeworkType.HOMEWORK, HomeworkType.DESIGN, HomeworkType.LAB]

    all_items: list[Homework] = []
    for cid, cname in target_courses:
        for stype in sub_types:
            all_items.extend(
                _fetch_homework_one(session, sid, cid, cname, stype)
            )

    if only_pending:
        all_items = [
            hw for hw in all_items
            if not hw.is_overdue and not (hw.is_submitted or False)
        ]
    return all_items


def _fetch_homework_one(
    session: Session,
    sid: str,
    course_id: str,
    course_name: str,
    sub_type: HomeworkType,
) -> list[Homework]:
    url = (
        f"{PLATFORM_BASE}/ve/back/coursePlatform/homeWork.shtml"
        f"?method=getHomeWorkList&cId={course_id}&subType={int(sub_type)}"
        "&page=1&pagesize=100"
    )
    data = http.get_json(session, url, headers=_headers(sid))

    # 空响应识别
    if data.get("STATUS") == "2" or data.get("total") == 0:
        return []

    hw_list = data.get("courseNoteList") or []
    items: list[Homework] = []
    for hw in hw_list:
        if not isinstance(hw, dict):
            continue
        up_id = hw.get("id")
        if up_id is None:
            continue

        deadline = _parse_dt(hw.get("end_time", "") or "")
        if deadline is None:
            log.warning("跳过无效 deadline 的作业: %s", hw.get("title"))
            continue

        # 课程名优先用接口里的(course_id 模式下我们没传 course_name)
        cname = course_name or hw.get("course_name", "")

        # 全班统计
        submitted = hw.get("submitCount")
        total = hw.get("allCount")

        # 注意:接口的 score 字段是作业满分,不是个人得分。stu_score 才是个人得分。
        max_score = _safe_float(hw.get("score"))
        my_score = _safe_float(hw.get("stu_score"))

        # 是否已交:接口可能不返回 subStatus,只能尽力判断
        sub_status = (hw.get("subStatus") or "").strip()
        is_submitted: bool | None
        if not sub_status:
            is_submitted = None  # 未知
        elif "未" in sub_status:
            is_submitted = False
        elif any(kw in sub_status for kw in ("已提交", "已批阅", "通过")):
            is_submitted = True
        else:
            is_submitted = None

        items.append(Homework(
            id=f"hw-{int(sub_type)}-{up_id}",
            title=hw.get("title", "(无标题)"),
            course_name=cname,
            course_id=str(hw.get("course_id", course_id)),
            homework_type=sub_type,
            deadline=deadline,
            publish_time=_parse_dt(hw.get("open_date", "") or ""),
            content=hw.get("content") or "",
            is_submitted=is_submitted,
            score=my_score,
            max_score=max_score,
            class_submitted=submitted if isinstance(submitted, int) else None,
            class_total=total if isinstance(total, int) else None,
        ))
    return items


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
