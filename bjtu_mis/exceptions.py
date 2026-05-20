"""SDK 异常体系。

设计原则:
1. 所有 SDK 抛出的异常都继承 BjtuError,用户一把 catch 干净。
2. 区分"可重试"和"不可重试"——账号密码错重试 100 次也没用,验证码错可以重试。
3. 区分"我们的问题"和"BJTU 的问题"——ParseError 通常意味着对方改接口了。
"""
from __future__ import annotations


class BjtuError(Exception):
    """所有 bjtu-mis-py 异常的基类。

    用户可以 ``except BjtuError`` 一把抓所有 SDK 相关错误。
    """


# ── 登录相关 ──────────────────────────────────────────────────

class LoginError(BjtuError):
    """登录失败的总称。具体子类区分原因。"""


class CredentialsError(LoginError):
    """学号或密码错误。

    **不要重试**——连续错误密码可能被风控锁号。
    用户应该提示重新输入。
    """


class CaptchaError(LoginError):
    """验证码识别失败。

    **可以重试**——刷新一张新验证码再试。
    SDK 内部 ``login()`` 已经处理了重试。
    """


# ── 会话相关 ──────────────────────────────────────────────────

class NotLoggedInError(BjtuError):
    """未登录就调用了需要登录的接口。

    通常意味着调用方忘了 ``client.login()``,
    或者用 ``client.is_logged_in`` 做了错误判断。
    """


class SessionExpiredError(BjtuError):
    """会话超时,需要重新登录。

    BJTU 服务器有时会主动失效会话(如长时间未活动)。
    上层应捕获并 ``client.login()`` 后重试。
    """


# ── 网络与解析 ────────────────────────────────────────────────

class NetworkError(BjtuError):
    """HTTP 请求层失败:超时、连接错、HTTP 5xx 等。"""


class ParseError(BjtuError):
    """服务器返回了非预期格式。

    通常意味着 BJTU 修改了接口结构,需要 SDK 维护者更新解析逻辑。
    遇到此异常请提 issue 并附上原始响应。
    """


class RateLimitError(BjtuError):
    """疑似被风控:连续 4xx/5xx,或被重定向到验证码页面等。"""
