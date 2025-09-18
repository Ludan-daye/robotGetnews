#!/usr/bin/env python3
"""
修复用户通知设置
"""
import sys
import os

# 添加项目目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, create_tables
from models.user import User
from models.preference import Preference

def fix_user_notification_settings():
    """修复用户通知设置"""
    print("🔧 修复用户通知设置")
    print("=" * 50)

    create_tables()
    db = SessionLocal()

    try:
        # 1. 检查所有用户
        users = db.query(User).all()
        print(f"1️⃣ 检查 {len(users)} 个用户的通知设置...")

        fixed_users = 0
        for user in users:
            print(f"\n   用户: {user.email}")
            print(f"   当前通知邮箱: {user.notification_email or '未设置'}")

            # 如果用户没有设置通知邮箱，设置为登录邮箱
            if not user.notification_email:
                user.notification_email = user.email
                fixed_users += 1
                print(f"   ✅ 已设置通知邮箱为: {user.email}")
            else:
                print(f"   ✅ 通知邮箱已设置")

            # 检查用户的偏好设置
            preferences = db.query(Preference).filter(Preference.user_id == user.id).all()
            print(f"   偏好数量: {len(preferences)}")

            for pref in preferences:
                print(f"     - {pref.name}: 通知渠道 {pref.notification_channels}")

        # 2. 提交更改
        if fixed_users > 0:
            db.commit()
            print(f"\n2️⃣ 已修复 {fixed_users} 个用户的通知设置")
        else:
            print(f"\n2️⃣ 所有用户的通知设置都正常")

        # 3. 检查修复结果
        print(f"\n3️⃣ 检查修复结果...")
        users_after = db.query(User).all()

        for user in users_after:
            has_notification_email = user.notification_email is not None
            has_preferences_with_notification = db.query(Preference).filter(
                Preference.user_id == user.id,
                Preference.notification_channels.isnot(None)
            ).count() > 0

            status = "✅" if has_notification_email and has_preferences_with_notification else "⚠️"
            print(f"   {status} {user.email}: 通知邮箱={user.notification_email}, 有通知偏好={has_preferences_with_notification}")

        return fixed_users

    finally:
        db.close()

if __name__ == "__main__":
    fixed_count = fix_user_notification_settings()

    print(f"\n📊 修复完成:")
    print(f"   修复的用户数: {fixed_count}")
    print(f"\n💡 现在可以重新测试推荐功能，应该会成功发送通知了！")