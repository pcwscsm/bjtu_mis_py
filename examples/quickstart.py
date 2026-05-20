"""
用 bjtu-mis-py SDK 实现 academic_bot 的核心功能。

证明 SDK API 真的能简化用户代码:
对比 academic_bot 里 _internal/auth.py + sources/homework_source.py 总共 ~400 行,
这里只需要 ~30 行。
"""
from datetime import datetime

from bjtu_mis import BjtuClient, BjtuError, HomeworkType


def main():
    # SDK 内部完成:CAS 登录、验证码、SSO 跳转、sessionId 拿取……
    with BjtuClient("学号", "密码") as client:
        try:
            info = client.login()
        except BjtuError as e:
            print(f"登录失败: {e}")
            return

        print(f"已登录: {info.name} ({info.role})")

        # 找出"7天内截止 + 未交"的紧急作业
        urgent = [
            hw for hw in client.homeworks(only_pending=True)
            if hw.days_left <= 7
        ]
        urgent.sort(key=lambda h: h.deadline)

        if not urgent:
            print("\n暂无紧急作业 ✓")
        else:
            print(f"\n=== 紧急作业 ({len(urgent)} 条) ===")
            for hw in urgent:
                emoji = "🔥" if hw.days_left <= 1 else "⚠️"
                print(f"{emoji} [{hw.homework_type.label}] {hw.title}")
                print(f"   课程: {hw.course_name}")
                print(f"   截止: {hw.deadline} (还剩 {hw.days_left} 天)")

        # 即将到来的考试
        exams = client.exams(only_upcoming=True)
        if exams:
            print(f"\n=== 即将考试 ({len(exams)} 场) ===")
            for e in sorted(exams, key=lambda x: x.start_time):
                print(f"📝 {e.course_name} - {e.start_time} @ {e.location}")

        # 挂科预警
        failed = [g for g in client.grades() if not g.is_passed]
        if failed:
            print(f"\n=== 不及格 ({len(failed)} 门) ===")
            for g in failed:
                print(f"🚨 {g.course_name}: {g.score}")


if __name__ == "__main__":
    main()
