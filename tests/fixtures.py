"""HTTP 响应 fixtures。

这些是从真实 BJTU 接口抓取并脱敏后的样本。
用 responses 库 mock 时直接喂这些字符串/JSON,不打真实网络。
"""
from __future__ import annotations

# ── CAS 登录页 ──
CAS_LOGIN_PAGE_HTML = """
<html><body>
<form method="post">
  <input type="hidden" name="csrfmiddlewaretoken" value="fake_csrf_token_xyz">
  <input type="hidden" name="captcha_0" id="id_captcha_0" value="abc123captchakey">
  <input type="text" name="captcha_1">
  <input type="text" name="loginname">
  <input type="password" name="password">
</form>
</body></html>
"""

# ── 登录失败:账号密码错 ──
CAS_LOGIN_FAIL_CREDENTIALS_HTML = """
<html><body>
<div class="errorlist">
  <div class="error">用户名或密码错误</div>
</div>
</body></html>
"""

# ── 登录失败:验证码错 ──
CAS_LOGIN_FAIL_CAPTCHA_HTML = """
<html><body>
<div class="errorlist">
  <div class="error">验证码错误</div>
</div>
</body></html>
"""

# ── MIS home 页 ──
MIS_HOME_HTML = """
<html><body>
<div class="name_right">
  <h3><a href="#">陈松林,夜已深,早点休息哟!</a></h3>
  <div class="nr_con">
    <span>身份:本科生</span>
    <span>部门:计算机科学与技术学院</span>
  </div>
</div>
</body></html>
"""

# ── aa SSO 跳转表单页 ──
AA_REDIRECT_HTML = """
<html><body>
<form id="redirect" action="https://aa.bjtu.edu.cn/sso/login" method="GET">
  <input type="submit" value="跳转">
</form>
</body></html>
"""

# ── 考试列表 ──
EXAM_LIST_HTML = """
<html><body>
<table><tbody>
<tr>
  <td>1</td>
  <td>期末</td>
  <td>数据结构</td>
  <td>2026-06-23 09:00-11:00</td>
  <td>正常</td>
  <td>逸夫楼 A101 座位 12</td>
</tr>
<tr>
  <td>2</td>
  <td>期末</td>
  <td>线性代数</td>
  <td>2026-06-25 14:00-16:00</td>
  <td>正常</td>
  <td>逸夫楼 B202</td>
</tr>
</tbody></table>
</body></html>
"""

# ── 成绩列表 ──
GRADE_LIST_HTML = """
<html><body>
<table>
<tr><th>序号</th><th>学年学期</th><th>课程</th><th>绩点</th><th>成绩</th><th>学分</th><th>教师</th><th>详情</th></tr>
<tr>
  <td>1</td>
  <td>2025-2026 1</td>
  <td>数据结构</td>
  <td>3.7</td>
  <td>87</td>
  <td>4</td>
  <td>张三</td>
  <td></td>
</tr>
<tr>
  <td>2</td>
  <td>2025-2026 1</td>
  <td>大学物理</td>
  <td>1.5</td>
  <td>52</td>
  <td>3</td>
  <td>李四</td>
  <td></td>
</tr>
<tr>
  <td>3</td>
  <td>2025-2026 1</td>
  <td>体育(成绩未出)</td>
  <td></td>
  <td></td>
  <td>1</td>
  <td>王五</td>
  <td></td>
</tr>
</table>
</body></html>
"""

# ── 智慧课程平台 ──
PLATFORM_SESSION_JSON = {"sessionId": "FAKE_SESSION_ID_123", "result": []}

PLATFORM_XQ_JSON = {"result": [{"xqCode": "2025202602"}]}

PLATFORM_COURSE_LIST_JSON = {
    "courseList": [
        {
            "id": 128008, "name": "写作与沟通", "course_num": "GE001",
            "teacher_name": "王老师", "xq_code": "2025202602",
        },
        {
            "id": 128778, "name": "地球科学概论", "course_num": "GE002",
            "teacher_name": "李老师", "xq_code": "2025202602",
        },
    ],
    "STATUS": "0",
}

PLATFORM_HOMEWORK_JSON_WITH_DATA = {
    "courseNoteList": [
        {
            "id": 937310,
            "create_date": "2026-04-30 14:56:05",
            "course_id": 128008,
            "course_name": "写作与沟通",
            "title": "文稿(讲-1)",
            "content": "<p>写一篇 500 字的文稿</p>",
            "end_time": "2026-05-20 23:59",
            "open_date": "2026-04-30 00:00",
            "score": "15",  # 满分
            "submitCount": 34,
            "allCount": 43,
            "status": "1",
        },
    ],
}

PLATFORM_HOMEWORK_JSON_EMPTY = {
    "page": 1, "size": 100, "currentRow": 0, "total": 0,
    "totalPage": 0, "STATUS": "2", "message": "没有数据",
}
