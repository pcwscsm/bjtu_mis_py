"""验证码识别抽象。

允许用户替换识别器:默认用 ddddocr,但用户可以接腾讯云、自训练模型等。

设计模式:依赖注入 (Dependency Injection)。
关键技术:Protocol (PEP 544) — 鸭子类型的类型化版本。
"""
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from .exceptions import CaptchaError


@runtime_checkable
class CaptchaSolver(Protocol):
    """验证码识别器接口。

    任何实现了 ``solve`` 方法的对象都可以传给 ``BjtuClient``。
    无需继承——这是 Protocol 的核心优势。

    用法::

        class MyCustomSolver:
            def solve(self, image_bytes: bytes) -> str:
                return my_ai_service.recognize(image_bytes)

        client = BjtuClient(stu_id, pwd, captcha_solver=MyCustomSolver())
    """

    def solve(self, image_bytes: bytes) -> str:
        """识别验证码图片,返回最终答案字符串。

        BJTU 验证码是算式题(如 "3+5=?"),识别器需要返回计算后的答案
        (字符串 "8"),而不是识别到的算式("3+5")。

        子类应在内部处理:
        - 字符替换(× → *, ÷ → /)
        - 算式计算(eval)
        - 系统性误识别的修正(如减号被吞回退减法)

        Args:
            image_bytes: 验证码图片的字节内容。

        Returns:
            算式答案字符串,如 "8"。

        Raises:
            CaptchaError: 识别失败或无法计算。
        """
        ...


class DdddocrSolver:
    """默认验证码识别器,基于 ddddocr。

    经验性回退:
    - 纯两位数字按 "前减后" 处理 (如 "31" → "3-1" → "2")
    - 首尾悬挂的运算符剥掉 (如 "6+6-" → "6+6",因 ddddocr 常把 ?/= 看成 -)
    - 三位及以上的纯数字拒绝处理,让上层重试
    """

    def __init__(self) -> None:
        self._ocr = None  # 延迟初始化:不在 import 时加载 ddddocr 模型

    def solve(self, image_bytes: bytes) -> str:
        if self._ocr is None:
            try:
                import ddddocr
            except ImportError as e:
                raise CaptchaError(
                    "默认验证码识别需要 ddddocr,请 pip install ddddocr,"
                    "或自行实现 CaptchaSolver 并传入。"
                ) from e
            self._ocr = ddddocr.DdddOcr(show_ad=False)

        raw = self._ocr.classification(image_bytes)
        normalized = self._normalize(raw)
        try:
            return str(self._eval(normalized))
        except Exception as e:
            raise CaptchaError(
                f"无法计算验证码 raw={raw!r} normalized={normalized!r}: {e}"
            ) from e

    @staticmethod
    def _normalize(raw: str) -> str:
        text = (
            raw.replace("=", "")
            .replace("?", "")
            .replace("x", "*")
            .replace("X", "*")
            .replace("×", "*")
            .replace("÷", "/")
            .replace(" ", "")
            .strip()
        )
        text = re.sub(r"[^\d\+\-\*/]", "", text)
        # 剥首尾悬挂运算符 (?和=常被错认成-)
        text = text.lstrip("+-*/").rstrip("+-*/")
        return text

    @staticmethod
    def _eval(text: str) -> int:
        if not text:
            raise ValueError("空字符串")
        if any(op in text for op in "+-*/"):
            if text[0] in "+-*/":
                raise ValueError(f"表达式以运算符开头: {text}")
            return int(eval(text, {"__builtins__": {}}, {}))
        if text.isdigit():
            if len(text) == 1:
                return int(text)
            if len(text) == 2:
                # 经验回退:两位数字 = 前减后
                return int(text[0]) - int(text[1])
            raise ValueError(f"无法处理的纯数字串: {text}")
        raise ValueError(f"未知格式: {text}")
