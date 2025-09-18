#!/usr/bin/env python3
"""
检查数据库缓存情况
"""
import sys
import os

# 添加项目目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, create_tables
from models.repo_cache import RepoCache
from models.recommendation import Recommendation
from models.preference import Preference
from models.user import User
from datetime import datetime, timedelta

def check_database_cache():
    """检查数据库中的缓存情况"""
    print("🔍 检查数据库缓存情况")
    print("=" * 50)

    create_tables()
    db = SessionLocal()

    try:
        # 1. 检查缓存的仓库数量
        total_cached_repos = db.query(RepoCache).count()
        print(f"1️⃣ 缓存的仓库总数: {total_cached_repos}")

        if total_cached_repos > 0:
            # 检查最新的缓存
            recent_repos = db.query(RepoCache).filter(
                RepoCache.fetched_at > datetime.utcnow() - timedelta(hours=24)
            ).all()

            print(f"   24小时内缓存: {len(recent_repos)}")

            if recent_repos:
                latest_repo = db.query(RepoCache).order_by(RepoCache.fetched_at.desc()).first()
                print(f"   最新缓存时间: {latest_repo.fetched_at}")
                print(f"   最新缓存仓库: {latest_repo.repo_id}")

        # 2. 检查推荐数量
        total_recommendations = db.query(Recommendation).count()
        print(f"\n2️⃣ 推荐记录总数: {total_recommendations}")

        if total_recommendations > 0:
            recent_recommendations = db.query(Recommendation).filter(
                Recommendation.created_at > datetime.utcnow() - timedelta(hours=24)
            ).all()

            print(f"   24小时内推荐: {len(recent_recommendations)}")

            if recent_recommendations:
                latest_rec = db.query(Recommendation).order_by(Recommendation.created_at.desc()).first()
                print(f"   最新推荐时间: {latest_rec.created_at}")
                print(f"   最新推荐仓库ID: {latest_rec.repo_id}")
                print(f"   最新推荐评分: {latest_rec.score}")

        # 3. 检查用户和偏好
        total_users = db.query(User).count()
        total_preferences = db.query(Preference).count()
        active_preferences = db.query(Preference).filter(Preference.enabled == True).count()

        print(f"\n3️⃣ 用户和偏好:")
        print(f"   用户总数: {total_users}")
        print(f"   偏好总数: {total_preferences}")
        print(f"   活跃偏好: {active_preferences}")

        # 4. 检查最近的推荐任务
        from models.job_run import JobRun
        recent_jobs = db.query(JobRun).order_by(JobRun.created_at.desc()).limit(5).all()

        print(f"\n4️⃣ 最近的任务:")
        for i, job in enumerate(recent_jobs, 1):
            print(f"   {i}. ID: {job.id}, 状态: {job.status}, 时间: {job.created_at}")
            if job.counters:
                print(f"      统计: {job.counters}")

        # 5. 分析缓存使用可能性
        print(f"\n5️⃣ 缓存分析:")

        if total_cached_repos > 0:
            print(f"   ✅ 数据库中有 {total_cached_repos} 个缓存仓库")

            if len(recent_repos) > 0:
                print(f"   ⚠️  有 {len(recent_repos)} 个24小时内的缓存")
                print(f"      这可能解释为什么手动触发没有消耗GitHub Token")
                print(f"      即使使用 force_refresh=True，如果有大量缓存数据，")
                print(f"      推荐引擎可能仍然从缓存中筛选推荐")
            else:
                print(f"   ℹ️  24小时内无新缓存，应该会调用GitHub API")
        else:
            print(f"   ℹ️  数据库中无缓存，所有搜索都应该调用GitHub API")

        return {
            "total_cached_repos": total_cached_repos,
            "recent_cached_repos": len(recent_repos) if total_cached_repos > 0 else 0,
            "total_recommendations": total_recommendations,
            "recent_recommendations": len(recent_recommendations) if total_recommendations > 0 else 0
        }

    finally:
        db.close()

if __name__ == "__main__":
    result = check_database_cache()

    print(f"\n📊 结论:")
    if result["recent_cached_repos"] > 50:
        print(f"   🎯 大量缓存数据可能导致手动触发不消耗Token")
        print(f"      建议：清理缓存或测试新的搜索条件")
    elif result["total_cached_repos"] == 0:
        print(f"   🎯 无缓存数据，所有搜索都应该真实调用GitHub API")
    else:
        print(f"   🎯 适量缓存数据，部分搜索可能使用缓存")