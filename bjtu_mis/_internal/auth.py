"""BJTU CAS 统一认证。

流程:
  1. GET mis.bjtu.edu.cn/auth/sso/?next=/ → 302 到 cas.bjtu.edu.cn
  2. 解析 cas 登录页拿 captcha key + csrf token
  3. GET cas image/{key}/ 拿验证码图
  4. CaptchaSolver.solve 识别
  5. POST cas auth/login/ 提交表单 → 302 回 mis.bjtu.edu.cn/home/
  6. 解析 home 页拿学生信息

后续访问 aa.bjtu.edu.cn 还需 ensure_aa_login() 走一次 mis→aa SSO。
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

from bs4 import BeautifulSoup
from requests import Session

from ..captcha import CaptchaSolver
from ..exceptions import (
    CaptchaError,
    CredentialsError,
    LoginError,
    NetworkError,
    ParseError,
)
from ..models import StudentInfo
from . import http

log = logging.getLogger(__name__)

MIS_HOME_URL = "https://mis.bjtu.edu.cn/home/"
MIS_SSO_URL = "https://mis.bjtu.edu.cn/auth/sso/?next=/"
CAS_HOST = "cas.bjtu.edu.cn"
AA_MODULE_URL = "https://mis.bjtu.edu.cn/module/module/10/"


@dataclass
class AuthState:
    """登录状态机的运行时数据。"""

    session: Session
    student_info: StudentInfo | None = None
    aa_logged_in: bool = False


def login(
    session: Session,
    stu_id: str,
    password: str,
    captcha_solver: CaptchaSolver,
    max_retries: int = 3,
) -> StudentInfo:
    """完成 mis 登录,返回学生信息。

    会自动重试验证码错误。账号密码错立即抛出,不重试(避免风控)。

    重试逻辑:
    - ``CredentialsError`` 立即抛出,不重试。
    - ``CaptchaError`` / ``ParseError`` / ``NetworkError`` 可重试。
    - 裸 ``LoginError`` 也重试 —— BJTU CAS 经常在验证码错时返回不含 ``.errorlist``
      / ``.error`` 的页面,SDK 没法精确识别,但实战中这类失败重试一次新验证码大概率能成。
      ``CredentialsError`` 是 ``LoginError`` 的子类,所以必须在前面单独 ``except`` 拦掉。
    """
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return _try_login_once(session, stu_id, password, captcha_solver)
        except CredentialsError:
            # 账号密码错不重试
            raise
        except (CaptchaError, ParseError, NetworkError, LoginError) as e:
            last_err = e
            log.warning("第 %d 次登录失败: %s", attempt, e)
            if attempt < max_retries:
                _clear_cas_cookies(session)
                time.sleep(0.5)

    raise LoginError(f"重试 {max_retries} 次后仍失败: {last_err}")


def _try_login_once(
    session: Session,
    stu_id: str,
    password: str,
    captcha_solver: CaptchaSolver,
) -> StudentInfo:
    # Step 1: SSO 跳转
    r1 = http.get(session, MIS_SSO_URL, allow_redirects=True)
    if r1.url == MIS_HOME_URL:
        # 已经登录态,直接复用
        return _parse_home(r1.text, stu_id)

    cas_login_url = r1.url
    if CAS_HOST not in cas_login_url:
        raise ParseError(f"未跳转到 CAS, 实际 URL: {cas_login_url}")

    # Step 2: 解析 cas 登录页
    soup = BeautifulSoup(r1.text, "html.parser")
    captcha_input = soup.select_one("input#id_captcha_0")
    csrf_input = soup.select_one("input[name=csrfmiddlewaretoken]")
    if not captcha_input or not csrf_input:
        raise ParseError("CAS 登录页结构异常,找不到验证码或 csrf token")
    captcha_key = captcha_input.get("value")
    csrf_token = csrf_input.get("value")

    # Step 3: 拿验证码图
    img_url = f"https://{CAS_HOST}/image/{captcha_key}/"
    r_img = http.get(session, img_url)
    if not r_img.ok:
        raise CaptchaError(f"获取验证码图失败: status={r_img.status_code}")

    # Step 4: 识别(委托给 solver)
    captcha_ans = captcha_solver.solve(r_img.content)

    # Step 5: POST 登录
    next_url = cas_login_url.split("next=", 1)[1] if "next=" in cas_login_url else "/"
    form = {
        "csrfmiddlewaretoken": csrf_token,
        "captcha_0": captcha_key,
        "captcha_1": captcha_ans,
        "loginname": stu_id,
        "password": password,
    }
    r_login = http.post(
        session,
        f"https://{CAS_HOST}/auth/login/?next={next_url}",
        data=form,
        headers={
            "Referer": cas_login_url,
            "Origin": f"https://{CAS_HOST}",
        },
        allow_redirects=True,
    )

    if r_login.url != MIS_HOME_URL:
        # 区分账号密码错和验证码错
        err_soup = BeautifulSoup(r_login.text, "html.parser")
        err_text = ""
        err_el = err_soup.select_one(".errorlist") or err_soup.select_one(".error")
        if err_el:
            err_text = err_el.get_text(strip=True)

        if "用户名" in err_text or "密码" in err_text:
            raise CredentialsError(f"账号或密码错误: {err_text}")
        if "验证码" in err_text:
            raise CaptchaError(f"验证码错误: {err_text}")
        raise LoginError(f"登录失败: {err_text or r_login.url}")

    return _parse_home(r_login.text, stu_id)


def _parse_home(html: str, stu_id: str) -> StudentInfo:
    soup = BeautifulSoup(html, "html.parser")
    name_el = soup.select_one(".name_right > h3 > a")
    if not name_el:
        raise ParseError("MIS home 页结构异常,找不到姓名")

    raw_name = name_el.get_text(strip=True)
    # 名字可能带"夜已深,早点休息哟!"这种问候语,只取逗号前
    name = re.split(r"[,，]", raw_name)[0]

    role = ""
    dept = ""
    for span in soup.select(".name_right .nr_con span"):
        t = span.get_text(strip=True)
        if t.startswith("身份"):
            role = re.sub(r"^身份[::]", "", t)
        elif t.startswith("部门"):
            dept = re.sub(r"^部门[::]", "", t)

    return StudentInfo(name=name, role=role, department=dept, stu_id=stu_id)


def ensure_aa_login(session: Session, state: AuthState) -> None:
    """访问 aa.bjtu.edu.cn 前必须走的 SSO 跳转。

    幂等:已激活就直接返回。
    """
    if state.aa_logged_in:
        return

    r = http.get(session, AA_MODULE_URL)
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.select_one("form#redirect")
    if form is None:
        if "aa.bjtu.edu.cn" in r.url:
            state.aa_logged_in = True
            return
        raise ParseError("aa SSO 跳转失败,找不到 redirect 表单")

    action = form.get("action")
    r2 = http.get(
        session,
        action + "?",
        headers={"Referer": AA_MODULE_URL},
    )
    if "aa.bjtu.edu.cn" not in r2.url:
        raise LoginError(f"aa SSO 完成异常,最终 URL: {r2.url}")
    state.aa_logged_in = True


def _clear_cas_cookies(session: Session) -> None:
    """重试登录前清掉 cas 域 cookie,避免旧 csrf 干扰。"""
    keep = [c for c in session.cookies if CAS_HOST not in (c.domain or "")]
    session.cookies.clear()
    for c in keep:
        session.cookies.set_cookie(c)
