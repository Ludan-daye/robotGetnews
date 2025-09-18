#!/usr/bin/env python3
"""
验证偏好设置是否真正影响搜索结果的针对性
"""
import asyncio
import sys
import os

# 添加项目目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, create_tables
from models.user import User
from models.preference import Preference
from models.recommendation import Recommendation
from models.repo_cache import RepoCache
from services.job_service import JobExecutionService

async def verify_preference_targeting():
    """验证偏好设置的针对性"""
    print("🎯 验证偏好设置是否真正影响搜索结果")
    print("=" * 60)

    create_tables()
    db = SessionLocal()

    try:
        # 1. 找到目标用户和偏好
        user = db.query(User).filter(User.email == "Ludandaye@gmail.com").first()
        if not user:
            print("❌ 未找到目标用户")
            return

        preference = db.query(Preference).filter(
            Preference.user_id == user.id,
            Preference.enabled == True
        ).first()

        if not preference:
            print("❌ 未找到启用的偏好")
            return

        print(f"👤 用户: {user.email}")
        print(f"📋 偏好: {preference.name}")
        print(f"🔍 关键词: {preference.keywords}")
        print(f"💻 语言: {preference.languages}")
        print(f"⭐ 最小星数: {preference.min_stars}")

        # 2. 查看最新的推荐结果
        print(f"\n📊 检查最近的推荐结果...")
        recent_recommendations = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.preference_id == preference.id
        ).order_by(Recommendation.created_at.desc()).limit(10).all()

        print(f"找到 {len(recent_recommendations)} 个最新推荐")

        if not recent_recommendations:
            print("⚠️ 没有推荐结果，执行一次推荐任务...")
            # 执行推荐任务
            from models.job_run import JobRun
            job_run = JobRun(
                user_id=user.id,
                status="queued",
                trigger_type="manual",
                preference_id=preference.id,
                job_config={"force_refresh": True, "preference_id": preference.id}
            )
            db.add(job_run)
            db.commit()
            db.refresh(job_run)

            job_service = JobExecutionService(db)
            result = await job_service.execute_recommendation_job(
                user_id=user.id,
                job_run_id=job_run.id,
                preference_id=preference.id,
                force_refresh=True
            )

            print(f"任务结果: {result.get('status')}")
            print(f"统计: {result.get('stats', {})}")

            # 重新获取推荐
            recent_recommendations = db.query(Recommendation).filter(
                Recommendation.user_id == user.id,
                Recommendation.preference_id == preference.id
            ).order_by(Recommendation.created_at.desc()).limit(10).all()

        # 3. 分析推荐结果是否符合偏好
        print(f"\n🔍 分析推荐结果的针对性:")

        preference_keywords_lower = [kw.lower() for kw in preference.keywords]
        preference_languages = [lang.lower() for lang in preference.languages]

        matching_analysis = {
            "total_recommendations": len(recent_recommendations),
            "keyword_matches": 0,
            "language_matches": 0,
            "star_matches": 0,
            "mismatches": []
        }

        for i, rec in enumerate(recent_recommendations, 1):
            # 获取仓库信息
            repo = db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
            if not repo:
                continue

            print(f"\n{i}. {repo.full_name}")
            print(f"   ⭐ Stars: {repo.stargazers_count}")
            print(f"   💻 Language: {repo.language}")
            print(f"   📝 Description: {(repo.description or '')[:100]}...")
            print(f"   🎯 Score: {rec.score:.2f}")

            # 检查关键词匹配
            keyword_match = False
            if repo.description:
                desc_lower = repo.description.lower()
                name_lower = repo.full_name.lower()
                for kw in preference_keywords_lower:
                    if kw in desc_lower or kw in name_lower:
                        keyword_match = True
                        break

            # 检查Topics匹配
            if repo.topics:
                topics_lower = [t.lower() for t in repo.topics]
                for kw in preference_keywords_lower:
                    if kw in topics_lower:
                        keyword_match = True
                        break

            # 检查语言匹配
            language_match = repo.language and repo.language.lower() in preference_languages

            # 检查星数匹配
            star_match = repo.stargazers_count >= preference.min_stars

            print(f"   ✅ 关键词匹配: {keyword_match}")
            print(f"   ✅ 语言匹配: {language_match}")
            print(f"   ✅ 星数匹配: {star_match}")

            # 统计匹配情况
            if keyword_match:
                matching_analysis["keyword_matches"] += 1
            if language_match:
                matching_analysis["language_matches"] += 1
            if star_match:
                matching_analysis["star_matches"] += 1

            # 记录不匹配的情况
            if not (keyword_match or language_match) or not star_match:
                matching_analysis["mismatches"].append({
                    "repo": repo.full_name,
                    "keyword_match": keyword_match,
                    "language_match": language_match,
                    "star_match": star_match
                })

        # 4. 计算匹配率
        print(f"\n📈 偏好匹配分析:")
        total = matching_analysis["total_recommendations"]
        if total > 0:
            keyword_rate = (matching_analysis["keyword_matches"] / total) * 100
            language_rate = (matching_analysis["language_matches"] / total) * 100
            star_rate = (matching_analysis["star_matches"] / total) * 100

            print(f"   关键词匹配率: {keyword_rate:.1f}% ({matching_analysis['keyword_matches']}/{total})")
            print(f"   语言匹配率: {language_rate:.1f}% ({matching_analysis['language_matches']}/{total})")
            print(f"   星数匹配率: {star_rate:.1f}% ({matching_analysis['star_matches']}/{total})")

            # 总体匹配率（至少满足关键词或语言匹配，且满足星数要求）
            relevant_count = len([r for r in recent_recommendations
                                if r.repo_id not in [m['repo'] for m in matching_analysis["mismatches"]]])

            if matching_analysis["mismatches"]:
                print(f"\n⚠️ 发现 {len(matching_analysis['mismatches'])} 个可能不相关的推荐:")
                for mismatch in matching_analysis["mismatches"]:
                    print(f"     - {mismatch['repo']}: 关键词={mismatch['keyword_match']}, 语言={mismatch['language_match']}, 星数={mismatch['star_match']}")

            print(f"\n🎯 结论:")
            if keyword_rate >= 70 and language_rate >= 50 and star_rate >= 90:
                print("   ✅ 偏好设置工作正常，搜索结果高度相关")
            elif keyword_rate >= 50 and star_rate >= 80:
                print("   ⚠️ 偏好设置基本工作，但可能需要优化关键词或语言过滤")
            else:
                print("   ❌ 偏好设置可能没有正确应用，需要检查搜索逻辑")

        return matching_analysis

    finally:
        db.close()

if __name__ == "__main__":
    result = asyncio.run(verify_preference_targeting())

    print(f"\n📋 验证完成")
    if result:
        total = result["total_recommendations"]
        if total > 0:
            overall_relevance = ((result["keyword_matches"] + result["language_matches"]) / (total * 2)) * 100
            print(f"   整体相关度: {overall_relevance:.1f}%")

            if overall_relevance >= 70:
                print("   🎉 偏好设置成功影响搜索结果!")
            else:
                print("   🤔 偏好设置的影响可能需要进一步优化")