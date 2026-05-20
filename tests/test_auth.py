"""认证层的可单测部分。

完整 SSO 流程依赖 302 链,responses 库模拟麻烦,这里聚焦在
HTML 解析和错误分类逻辑——这些是最容易出 bug 的地方。
"""
from __future__ import annotations

from bjtu_mis._internal.auth import _parse_home

from . import fixtures as F


class TestParseHome:
    def test_basic(self):
        info = _parse_home(F.MIS_HOME_HTML, "25531064")
        # 姓名应该剥掉问候语
        assert info.name == "陈松林"
        assert info.role == "本科生"
        assert info.department == "计算机科学与技术学院"
        assert info.stu_id == "25531064"

    def test_strips_greeting(self):
        """实测姓名后面常带问候语,需要剥掉。"""
        html = """
        <html><body><div class="name_right">
        <h3><a>张三,你好啊!</a></h3>
        <div class="nr_con"><span>身份:本科生</span></div>
        </div></body></html>
        """
        info = _parse_home(html, "xxx")
        assert info.name == "张三"
