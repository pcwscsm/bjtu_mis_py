# bjtu-mis-py

BJTU 教务系统 + MIS 门户 + 智慧课程平台的 Python SDK。

把 CAS 登录、验证码识别、SSO 跳转、HTML/JSON 解析这些麻烦事全部封装,
你只需要一句 `client.homeworks()`。

## 安装

```bash
pip install bjtu-mis-py[captcha]
```

`[captcha]` 是可选依赖,会装上默认的验证码识别器 `ddddocr`。
如果你打算用自己的识别器(如腾讯云 OCR),可以不带:

```bash
pip install bjtu-mis-py
```

## 5 分钟上手

```python
from bjtu_mis import BjtuClient

with BjtuClient("你的学号", "你的密码") as client:
    info = client.login()
    print(f"你好,{info.name}!")

    # 没提交的作业
    for hw in client.homeworks(only_pending=True):
        print(f"[{hw.homework_type.label}] {hw.title} - 还剩 {hw.days_left} 天")

    # 全部成绩
    for grade in client.grades():
        status = "✓" if grade.is_passed else "✗"
        print(f"{status} {grade.course_name}: {grade.score} ({grade.gpa})")

    # 未来的考试
    for exam in client.exams(only_upcoming=True):
        print(f"{exam.course_name} @ {exam.start_time} - {exam.location}")
```

## 主要功能

| 接口 | 数据源 | 说明 |
|---|---|---|
| `client.login()` | CAS 统一认证 | 含验证码识别和重试 |
| `client.grades()` | `aa.bjtu.edu.cn` | 历史所有成绩 |
| `client.exams()` | `aa.bjtu.edu.cn` | 考试安排 |
| `client.courses()` | 智慧课程平台 | 当前学期课程 |
| `client.homeworks()` | 智慧课程平台 | 作业、课程设计、实验报告 |
| `client.current_semester_code()` | 智慧课程平台 | 当前学期 code |

## 自定义验证码识别器

默认用 ddddocr,但它偶尔会识错。你可以接入任何更强的识别服务:

```python
class MyCaptchaSolver:
    def solve(self, image_bytes: bytes) -> str:
        # 调腾讯云 / 阿里云 / 自训练模型,返回算式答案字符串
        return call_my_ocr_service(image_bytes)

client = BjtuClient(stu_id, pwd, captcha_solver=MyCaptchaSolver())
```

任何有 `solve(bytes) -> str` 方法的对象都能传入,不需要继承。

## 错误处理

```python
from bjtu_mis import BjtuClient, CredentialsError, CaptchaError, BjtuError

client = BjtuClient(stu_id, pwd)
try:
    client.login()
except CredentialsError:
    print("账号或密码错了,检查一下")
    # 不要重试,可能被风控
except CaptchaError:
    print("验证码连续识别失败,换个识别器或晚点再试")
except BjtuError as e:
    # 兜底:所有 SDK 异常都继承自 BjtuError
    print(f"未知错误: {e}")
```

## 已知限制

- **作业的个人提交状态**:`getHomeWorkList` 接口不返回 `subStatus`,所以 `Homework.is_submitted` 可能为 `None`(未知)。要拿真实状态需要逐条调详情接口,SDK 目前没做。
- **课表时间地点**:`Course.schedules` 当前是空 tuple。要拿到周几第几节这种结构化信息需要额外接口,以后版本加。

## 开发

```bash
git clone https://github.com/your_user/bjtu-mis-py
cd bjtu-mis-py
pip install -e ".[dev,captcha]"
pytest
```

测试不会打真实 BJTU 服务器——所有 HTTP 响应都用固定 fixture mock。

## License

MIT
