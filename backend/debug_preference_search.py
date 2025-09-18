#!/usr/bin/env python3
"""
调试偏好设置和搜索查询的关系
"""
import sys
import os

# 添加项目目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, create_tables
from models.user import User
from models.preference import Preference
from services.github_client import GitHubClient

def debug_preference_search():
    """调试偏好设置如何被转换为搜索查询"""
    print("🔍 调试偏好设置和搜索查询的关系")
    print("=" * 60)

    create_tables()
    db = SessionLocal()

    try:
        # 查找目标用户
        user = db.query(User).filter(User.email == "Ludandaye@gmail.com").first()
        if not user:
            print("❌ 未找到目标用户")
            return

        print(f"👤 用户: {user.email}")

        # 获取用户的所有偏好
        preferences = db.query(Preference).filter(
            Preference.user_id == user.id,
            Preference.enabled == True
        ).all()

        print(f"📊 找到 {len(preferences)} 个启用的偏好设置\n")

        # 分析每个偏好设置
        for i, pref in enumerate(preferences, 1):
            print(f"{i}. 偏好名称: {pref.name}")
            print(f"   描述: {pref.description}")
            print(f"   关键词: {pref.keywords}")
            print(f"   语言: {pref.languages}")
            print(f"   最小星数: {pref.min_stars}")
            print(f"   最大推荐数: {pref.max_recommendations}")
            print(f"   通知渠道: {pref.notification_channels}")
            print(f"   创建后时间: {pref.created_after}")
            print(f"   更新后时间: {pref.updated_after}")

            # 模拟构建搜索查询
            print(f"\n   📋 模拟搜索查询构建:")

            # 模拟 GitHubClient.search_repositories 的查询构建逻辑
            query_parts = []

            # 关键词处理
            if pref.keywords:
                keyword_query = " OR ".join(pref.keywords)
                query_parts.append(keyword_query)
                print(f"     关键词查询: '{keyword_query}'")

            # 语言处理
            if pref.languages:
                for lang in pref.languages:
                    lang_query_parts = query_parts.copy()
                    lang_query_parts.append(f"language:{lang}")

                    # 星数过滤
                    if pref.min_stars > 0:
                        lang_query_parts.append(f"stars:>={pref.min_stars}")

                    # 日期过滤
                    if pref.created_after:
                        date_str = pref.created_after.strftime("%Y-%m-%d")
                        lang_query_parts.append(f"created:>{date_str}")

                    if pref.updated_after:
                        date_str = pref.updated_after.strftime("%Y-%m-%d")
                        lang_query_parts.append(f"pushed:>{date_str}")

                    # 排除forks
                    lang_query_parts.append("fork:false")

                    final_query = " ".join(lang_query_parts)
                    print(f"     {lang}语言完整查询: '{final_query}'")
            else:
                # 没有语言限制的查询
                if pref.min_stars > 0:
                    query_parts.append(f"stars:>={pref.min_stars}")

                if pref.created_after:
                    date_str = pref.created_after.strftime("%Y-%m-%d")
                    query_parts.append(f"created:>{date_str}")

                if pref.updated_after:
                    date_str = pref.updated_after.strftime("%Y-%m-%d")
                    query_parts.append(f"pushed:>{date_str}")

                query_parts.append("fork:false")

                final_query = " ".join(query_parts)
                print(f"     无语言限制完整查询: '{final_query}'")

            print("-" * 50)

        # 测试实际API调用
        print(f"\n🧪 测试实际搜索功能:")

        if preferences:
            test_pref = preferences[0]
            print(f"使用偏好: {test_pref.name}")
            print(f"关键词: {test_pref.keywords}")
            print(f"语言: {test_pref.languages}")

            # 创建GitHub客户端并测试搜索
            print(f"\n正在进行实际GitHub搜索测试...")

            # 注意：这里只是显示会执行的搜索，不实际执行以避免消耗API配额
            if test_pref.languages:
                for language in test_pref.languages:
                    print(f"  将搜索: 关键词={test_pref.keywords}, 语言={language}, 最小星数={test_pref.min_stars}")
            else:
                print(f"  将搜索: 关键词={test_pref.keywords}, 最小星数={test_pref.min_stars}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_preference_search()