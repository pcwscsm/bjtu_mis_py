# Changelog

## [0.1.0] - 2026-05-09

首版发布。

### 新增

- `BjtuClient` 主入口
- CAS 统一认证(含验证码识别 + 重试)
- 教务系统接口:`grades()` `exams()`
- 智慧课程平台接口:`courses()` `homeworks()` `current_semester_code()`
- `CaptchaSolver` Protocol + `DdddocrSolver` 默认实现
- 完整的异常体系(`BjtuError` → `LoginError` → `CredentialsError` 等)
- 数据模型全部使用 `frozen` dataclass,可哈希、线程安全
- 派生属性如 `Homework.days_left`、`Homework.is_overdue`
- 类型注解完整,带 `py.typed`
