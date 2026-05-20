"""内部 HTTP 工具。

封装 requests.Session,把 requests 抛出的异常统一翻译成 BjtuError 子类。
这样上层代码不用到处 try except,看到任何错误都是 SDK 自己的异常体系。
"""
from __future__ import annotations

from typing import Any

import requests
from requests import Session

from ..exceptions import NetworkError, ParseError


def make_session(user_agent: str, timeout: float) -> Session:
    """创建一个配置好的 Session。

    timeout 通过 hook 注入到每次请求,不需要每次调用都传。
    """
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    # 给所有请求自动注入 timeout
    original_request = session.request

    def request_with_timeout(method: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", timeout)
        return original_request(method, url, **kwargs)

    session.request = request_with_timeout  # type: ignore[method-assign]
    return session


def get(session: Session, url: str, **kwargs: Any) -> requests.Response:
    """GET 请求,把 requests 异常翻译成 NetworkError。"""
    try:
        return session.get(url, **kwargs)
    except requests.RequestException as e:
        raise NetworkError(f"GET {url} 失败: {e}") from e


def post(session: Session, url: str, **kwargs: Any) -> requests.Response:
    try:
        return session.post(url, **kwargs)
    except requests.RequestException as e:
        raise NetworkError(f"POST {url} 失败: {e}") from e


def get_json(session: Session, url: str, **kwargs: Any) -> dict[str, Any]:
    """GET + 解析 JSON。非 JSON 响应抛 ParseError。"""
    resp = get(session, url, **kwargs)
    try:
        return resp.json()
    except ValueError as e:
        raise ParseError(
            f"{url} 返回非 JSON 内容: {resp.text[:200]}"
        ) from e


def post_json(session: Session, url: str, **kwargs: Any) -> dict[str, Any]:
    resp = post(session, url, **kwargs)
    try:
        return resp.json()
    except ValueError as e:
        raise ParseError(
            f"{url} 返回非 JSON 内容: {resp.text[:200]}"
        ) from e
