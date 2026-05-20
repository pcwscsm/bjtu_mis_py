"""教务系统 aa.bjtu.edu.cn 平台接口。"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from requests import Session

from ...enums import ExamType
from ...models import Exam, Grade
from .. import http
from ..auth import AuthState, ensure_aa_login

log = logging.getLogger(__name__)

EXAM_URL = "https://aa.bjtu.edu.cn/examine/examplanstudent/stulist/"
GRADE_URL_TPL = (
    "https://aa.bjtu.edu.cn/score/scores/stu/view/"
    "?page=1&perpage=500&ctype={ctype}"
)


def _hash_id(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _parse_dt(text: str) -> datetime | None:
    """从 '2025-06-23 09:00-11:00' 之类字符串提取开始时间。"""
    if not text:
        return None
    # 匹配 yyyy-mm-dd HH:MM(可能后面跟 -HH:MM 表示结束时间)
    m = re.search(
        r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s+(\d{1,2}):(\d{2})",
        text,
    )
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)),
            )
        except ValueError:
            return None
    # 退化到只有日期
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _parse_duration(text: str) -> int | None:
    """从 '09:00-11:00' 提取分钟数。"""
    m = re.search(r"(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})", text)
    if not m:
        return None
    start_min = int(m.group(1)) * 60 + int(m.group(2))
    end_min = int(m.group(3)) * 60 + int(m.group(4))
    return end_min - start_min if end_min > start_min else None


# ── 考试 ─────────────────────────────────────────────────────

def get_exams(session: Session, state: AuthState) -> list[Exam]:
    ensure_aa_login(session, state)
    r = http.get(session, EXAM_URL)
    return _parse_exams(r.text)


def _parse_exams(html: str) -> list[Exam]:
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.select_one("tbody")
    if tbody is None:
        log.warning("考试页面找不到 tbody,可能未登录或页面改版")
        return []

    items: list[Exam] = []
    for tr in tbody.select("tr"):
        tds = tr.select("td")
        if len(tds) < 6:
            continue
        try:
            exam_type_raw = tds[1].get_text(strip=True)
            course = tds[2].get_text(strip=True)
            exam_time_raw = tds[3].get_text(strip=True)
            status = tds[4].get_text(strip=True)
            detail = tds[5].get_text(strip=True)
        except IndexError:
            continue

        start_time = _parse_dt(exam_time_raw)
        if start_time is None:
            # 没法解析时间的跳过,不抛错
            log.warning("跳过无法解析时间的考试: %s", exam_time_raw)
            continue

        items.append(Exam(
            id=_hash_id(course, exam_time_raw),
            course_name=course,
            exam_type=ExamType.from_str(exam_type_raw),
            start_time=start_time,
            duration_minutes=_parse_duration(exam_time_raw),
            location=detail,
            status=status,
        ))
    return items


# ── 成绩 ─────────────────────────────────────────────────────

def get_grades(
    session: Session,
    state: AuthState,
    *,
    semester: str | None = None,
) -> list[Grade]:
    ensure_aa_login(session, state)

    # ctype: "" = 全部学期; 实际 BJTU 接口 semester 过滤是另一个参数
    # 简化:先全取,内存里过滤
    url = GRADE_URL_TPL.format(ctype="")
    r = http.get(session, url)
    items = _parse_grades(r.text)

    if semester is not None:
        items = [g for g in items if g.semester == semester]
    return items


def _parse_grades(html: str) -> list[Grade]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table")
    if table is None:
        log.warning("成绩页面找不到 table")
        return []

    rows = table.select("tr")
    if len(rows) < 2:
        return []

    items: list[Grade] = []
    for row in rows[1:]:  # 跳过表头
        tds = row.select("td")
        if len(tds) < 7:
            continue
        try:
            semester = tds[1].get_text(strip=True)  # 保留中间空白(如 "2025-2026 1")
            course_name = _clean(tds[2].get_text())
            gpa_text = _clean(tds[3].get_text())
            score_raw = _clean(tds[4].get_text())
            credit_text = _clean(tds[5].get_text())
            teacher = _clean(tds[6].get_text())
        except IndexError:
            continue

        # 没成绩的跳过
        if not score_raw or score_raw in ("-", "未发布", "暂无"):
            continue

        # 数字成绩 vs 文字成绩
        score_num: float | None = None
        score_text = ""
        is_passed = True
        try:
            score_num = float(score_raw)
            is_passed = score_num >= 60
        except ValueError:
            score_text = score_raw
            is_passed = score_raw.strip() not in ("不及格", "F", "fail")

        try:
            gpa = float(gpa_text) if gpa_text else None
        except ValueError:
            gpa = None

        try:
            credit = float(credit_text) if credit_text else 0.0
        except ValueError:
            credit = 0.0

        items.append(Grade(
            id=_hash_id(semester, course_name, teacher),
            course_name=course_name,
            teacher=teacher,
            semester=semester,
            credit=credit,
            score=score_num,
            score_text=score_text,
            gpa=gpa,
            is_passed=is_passed,
            is_makeup=False,  # 当前接口未返回该字段
        ))
    return items
