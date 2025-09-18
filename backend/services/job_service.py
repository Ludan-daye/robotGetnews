import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models.user import User
from models.preference import Preference
from models.repo_cache import RepoCache
from models.job_run import JobRun
from models.recommendation import Recommendation
from services.github_client import GitHubClient, GitHubRateLimitError
from services.recommendation_engine import RecommendationEngine
from services.notification_service import NotificationService

logger = structlog.get_logger()


class JobExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.recommendation_engine = RecommendationEngine(db)
        self.notification_service = NotificationService(db)

    async def execute_recommendation_job(
        self,
        user_id: int,
        job_run_id: int,
        preference_id: Optional[int] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a recommendation job for a user
        """
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if not job_run:
            raise ValueError(f"Job run {job_run_id} not found")

        try:
            # Update job status
            job_run.status = "running"
            job_run.started_at = func.now()
            self.db.commit()

            logger.info("Starting recommendation job", user_id=user_id, job_run_id=job_run_id)

            # 打印开始信息
            print(f"\n🚀 开始执行推荐任务")
            print(f"   - 用户ID: {user_id}")
            print(f"   - 任务ID: {job_run_id}")
            print(f"   - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if preference_id:
                print(f"   - 指定配置ID: {preference_id}")
            print(f"   - 强制刷新: {'是' if force_refresh else '否'}")

            # Get user and preferences
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Get preferences to process
            if preference_id:
                preferences = self.db.query(Preference).filter(
                    Preference.id == preference_id,
                    Preference.user_id == user_id,
                    Preference.enabled == True
                ).all()
            else:
                preferences = self.db.query(Preference).filter(
                    Preference.user_id == user_id,
                    Preference.enabled == True
                ).all()

            if not preferences:
                print(f"\n⚠️  没有找到启用的推荐配置")
                job_run.status = "completed"
                job_run.finished_at = func.now()
                job_run.error_message = "No active preferences found"
                self.db.commit()
                return {"status": "completed", "message": "No active preferences found"}

            print(f"\n📋 找到 {len(preferences)} 个启用的推荐配置，准备按配置分别处理...")

            total_stats = {
                "repos_fetched": 0,
                "repos_cached": 0,
                "repos_filtered": 0,
                "recommendations_generated": 0,
                "preferences_processed": 0,
                "errors_count": 0
            }

            # Process each preference
            async with GitHubClient() as github_client:
                for i, preference in enumerate(preferences, 1):
                    try:
                        # 详细打印配置信息
                        print(f"\n{'='*80}")
                        print(f"🔄 处理配置 {i}/{len(preferences)}: {preference.name}")
                        print(f"{'='*80}")
                        print(f"📋 配置详情:")
                        print(f"   - 配置ID: {preference.id}")
                        print(f"   - 配置名称: {preference.name}")
                        print(f"   - 关键词: {', '.join(preference.keywords) if preference.keywords else '无'}")
                        print(f"   - 编程语言: {', '.join(preference.languages) if preference.languages else '无限制'}")
                        print(f"   - 最小Star数: {preference.min_stars}")
                        print(f"   - 最大推荐数: {preference.max_recommendations}")
                        print(f"   - 通知渠道: {', '.join(preference.notification_channels) if preference.notification_channels else '无'}")
                        print(f"")

                        logger.info("Processing preference", preference_id=preference.id, name=preference.name)

                        # Fetch repositories from GitHub
                        print(f"🔍 正在搜索GitHub项目...")
                        repos = await self._fetch_repositories(github_client, preference, force_refresh)
                        total_stats["repos_fetched"] += len(repos)
                        print(f"✅ 搜索完成，找到 {len(repos)} 个相关项目")

                        # Cache repositories
                        print(f"💾 正在缓存项目数据...")
                        cached_repos = await self._cache_repositories(repos)
                        total_stats["repos_cached"] += len(cached_repos)
                        print(f"✅ 缓存完成，处理了 {len(cached_repos)} 个项目")

                        # Filter and score repositories
                        print(f"⭐ 正在评分和过滤项目...")
                        filtered_repos = self.recommendation_engine.filter_repositories(
                            [self._repo_cache_to_dict(repo) for repo in cached_repos],
                            preference
                        )
                        total_stats["repos_filtered"] += len(filtered_repos)
                        print(f"✅ 过滤完成，筛选出 {len(filtered_repos)} 个高质量项目")

                        # Save recommendations
                        print(f"💾 正在保存推荐结果...")
                        recommendations = self.recommendation_engine.save_recommendations(
                            user_id=user_id,
                            preference_id=preference.id,
                            job_run_id=job_run_id,
                            filtered_repos=filtered_repos
                        )
                        total_stats["recommendations_generated"] += len(recommendations)
                        print(f"✅ 保存完成，生成了 {len(recommendations)} 条推荐")

                        # 打印推荐项目详情
                        if recommendations:
                            print(f"\n📊 推荐项目列表:")
                            for j, rec in enumerate(recommendations[:5], 1):  # 只显示前5个
                                repo = self.db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
                                if repo:
                                    print(f"   {j}. {repo.full_name} (⭐{repo.stargazers_count:,} stars, 💻{repo.language or 'N/A'}, 🎯{rec.score:.2f})")
                            if len(recommendations) > 5:
                                print(f"   ... 还有 {len(recommendations) - 5} 个推荐项目")
                        else:
                            print(f"   暂无符合条件的推荐项目")

                        # Send notifications if there are new recommendations
                        sent_channels = []
                        if recommendations and preference.notification_channels:
                            try:
                                print(f"\n📨 正在发送通知到: {', '.join(preference.notification_channels)}")
                                sent_channels = await self.notification_service.send_recommendations_notification(
                                    user_id=user_id,
                                    preference=preference,
                                    recommendations=recommendations
                                )
                                total_stats[f"notifications_sent_{preference.id}"] = sent_channels

                                if sent_channels:
                                    print(f"✅ 通知发送成功: {', '.join(sent_channels)}")
                                else:
                                    print(f"⚠️  通知发送失败或无可用渠道")

                                logger.info(
                                    "Notifications sent for preference",
                                    preference_id=preference.id,
                                    sent_channels=sent_channels
                                )
                            except Exception as e:
                                print(f"❌ 通知发送失败: {str(e)}")
                                logger.error(
                                    "Failed to send notifications",
                                    preference_id=preference.id,
                                    error=str(e)
                                )
                                total_stats["notification_errors"] = total_stats.get("notification_errors", 0) + 1
                        elif recommendations:
                            print(f"⚠️  该配置未设置通知渠道，跳过通知发送")
                        else:
                            print(f"ℹ️  无推荐结果，跳过通知发送")

                        total_stats["preferences_processed"] += 1

                        # 打印配置处理摘要
                        print(f"\n📊 配置 '{preference.name}' 处理摘要:")
                        print(f"   - 搜索到的项目: {len(repos)}")
                        print(f"   - 生成的推荐: {len(recommendations)}")
                        print(f"   - 通知渠道: {', '.join(sent_channels) if sent_channels else '无'}")
                        print(f"✅ 配置 '{preference.name}' 处理完成")

                        logger.info(
                            "Preference processed successfully",
                            preference_id=preference.id,
                            preference_name=preference.name,
                            repos_found=len(repos),
                            recommendations_count=len(recommendations),
                            sent_channels=sent_channels
                        )

                    except GitHubRateLimitError as e:
                        logger.warning("Hit GitHub rate limit", reset_time=e.reset_time)
                        total_stats["errors_count"] += 1
                        break  # Stop processing to avoid more rate limit hits

                    except Exception as e:
                        logger.error("Error processing preference", preference_id=preference.id, error=str(e))
                        total_stats["errors_count"] += 1
                        continue

            # Update job completion
            job_run.status = "completed"
            job_run.finished_at = func.now()
            job_run.counters = total_stats
            self.db.commit()

            # 打印最终总结
            print(f"\n{'='*80}")
            print(f"📊 推荐任务执行完成 - 总结报告")
            print(f"{'='*80}")
            print(f"✅ 处理的配置数: {total_stats['preferences_processed']}")
            print(f"🔍 搜索到的项目总数: {total_stats['repos_fetched']}")
            print(f"💾 缓存的项目数: {total_stats['repos_cached']}")
            print(f"⭐ 过滤的项目数: {total_stats['repos_filtered']}")
            print(f"🎯 生成的推荐总数: {total_stats['recommendations_generated']}")

            # 统计通知发送情况
            total_notifications = 0
            successful_configs = []
            for key, value in total_stats.items():
                if key.startswith("notifications_sent_") and value:
                    total_notifications += 1
                    config_id = key.split("_")[-1]
                    config_name = next((p.name for p in preferences if str(p.id) == config_id), f"配置{config_id}")
                    successful_configs.append(f"{config_name}({', '.join(value)})")

            print(f"📨 成功发送通知的配置: {total_notifications}")
            if successful_configs:
                for config_info in successful_configs:
                    print(f"   - {config_info}")

            if total_stats.get("errors_count", 0) > 0:
                print(f"❌ 错误次数: {total_stats['errors_count']}")

            print(f"🎉 任务完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")

            logger.info("Recommendation job completed", user_id=user_id, job_run_id=job_run_id, stats=total_stats)

            return {
                "status": "completed",
                "stats": total_stats,
                "job_run_id": job_run_id
            }

        except Exception as e:
            # Mark job as failed
            job_run.status = "failed"
            job_run.finished_at = func.now()
            job_run.error_message = str(e)
            job_run.counters = total_stats if 'total_stats' in locals() else {}
            self.db.commit()

            logger.error("Recommendation job failed", user_id=user_id, job_run_id=job_run_id, error=str(e))
            raise

    async def _fetch_repositories(
        self,
        github_client: GitHubClient,
        preference: Preference,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch repositories from GitHub based on preference"""

        # Check if we should use cached data
        if not force_refresh:
            # Look for recent cached data
            recent_repos = self.db.query(RepoCache).filter(
                RepoCache.fetched_at > datetime.utcnow() - preference.created_after if preference.created_after else datetime.utcnow() - timedelta(hours=1)
            ).limit(100).all()

            if recent_repos:
                logger.info("Using cached repository data", count=len(recent_repos))
                return [github_client.parse_repo_data(repo.github_data) for repo in recent_repos if repo.github_data]

        # Fetch from GitHub API
        repos = []

        # Handle large keyword lists by splitting them into multiple searches
        # GitHub API limits OR operators to 5, so we need to do multiple searches for better coverage
        max_keywords_per_search = 5
        keyword_chunks = []

        if preference.keywords:
            # Split keywords into chunks of 5
            for i in range(0, len(preference.keywords), max_keywords_per_search):
                chunk = preference.keywords[i:i + max_keywords_per_search]
                keyword_chunks.append(chunk)
        else:
            keyword_chunks = [[]]  # Empty search

        # Search for each language and keyword chunk combination
        if preference.languages:
            for language in preference.languages:
                for keyword_chunk in keyword_chunks:
                    try:
                        language_repos = await github_client.search_repositories(
                            keywords=keyword_chunk,
                            language=language,
                            min_stars=preference.min_stars,
                            created_after=preference.created_after,
                            updated_after=preference.updated_after,
                            per_page=30,  # Reduced to allow for more searches
                            max_pages=1   # Reduced to allow for more searches
                        )
                        repos.extend(language_repos)

                        # Log search results
                        logger.info("Search completed",
                                  language=language,
                                  keywords=keyword_chunk,
                                  results=len(language_repos))
                    except Exception as e:
                        logger.error("Search failed",
                                   language=language,
                                   keywords=keyword_chunk,
                                   error=str(e))
                        continue
        else:
            # Search without language filter using keyword chunks
            for keyword_chunk in keyword_chunks:
                try:
                    chunk_repos = await github_client.search_repositories(
                        keywords=keyword_chunk,
                        min_stars=preference.min_stars,
                        created_after=preference.created_after,
                        updated_after=preference.updated_after,
                        per_page=50,
                        max_pages=2
                    )
                    repos.extend(chunk_repos)

                    # Log search results
                    logger.info("Search completed",
                              keywords=keyword_chunk,
                              results=len(chunk_repos))
                except Exception as e:
                    logger.error("Search failed",
                               keywords=keyword_chunk,
                               error=str(e))
                    continue

        # Remove duplicates
        seen_ids = set()
        unique_repos = []
        for repo in repos:
            if repo["id"] not in seen_ids:
                seen_ids.add(repo["id"])
                unique_repos.append(repo)

        logger.info("Fetched repositories from GitHub", count=len(unique_repos))
        return unique_repos

    async def _cache_repositories(self, repos: List[Dict[str, Any]]) -> List[RepoCache]:
        """Cache repositories in the database"""
        cached_repos = []

        for repo_data in repos:
            try:
                # Parse repository data
                parsed_data = GitHubClient().parse_repo_data(repo_data)

                # Check if repo already exists in cache
                existing_repo = self.db.query(RepoCache).filter(
                    RepoCache.repo_id == parsed_data["repo_id"]
                ).first()

                if existing_repo:
                    # Update existing cache entry
                    for key, value in parsed_data.items():
                        if key != "repo_id":  # Don't update the primary key
                            setattr(existing_repo, key, value)
                    existing_repo.fetched_at = func.now()
                    cached_repos.append(existing_repo)
                else:
                    # Create new cache entry
                    repo_cache = RepoCache(**parsed_data)
                    self.db.add(repo_cache)
                    cached_repos.append(repo_cache)

            except Exception as e:
                logger.error("Failed to cache repository", repo_id=repo_data.get("id"), error=str(e))
                continue

        self.db.commit()
        return cached_repos

    def _repo_cache_to_dict(self, repo_cache: RepoCache) -> Dict[str, Any]:
        """Convert RepoCache model to dictionary for processing"""
        return {
            "repo_id": repo_cache.repo_id,
            "full_name": repo_cache.full_name,
            "name": repo_cache.name,
            "owner_login": repo_cache.owner_login,
            "description": repo_cache.description,
            "topics": repo_cache.topics,
            "language": repo_cache.language,
            "license_name": repo_cache.license_name,
            "stargazers_count": repo_cache.stargazers_count,
            "forks_count": repo_cache.forks_count,
            "watchers_count": repo_cache.watchers_count,
            "open_issues_count": repo_cache.open_issues_count,
            "size": repo_cache.size,
            "html_url": repo_cache.html_url,
            "clone_url": repo_cache.clone_url,
            "homepage": repo_cache.homepage,
            "is_private": repo_cache.is_private,
            "is_fork": repo_cache.is_fork,
            "is_archived": repo_cache.is_archived,
            "is_disabled": repo_cache.is_disabled,
            "created_at": repo_cache.created_at,
            "updated_at": repo_cache.updated_at,
            "pushed_at": repo_cache.pushed_at,
            "fetched_at": repo_cache.fetched_at
        }

    async def cleanup_old_data(self, days_old: int = 7) -> Dict[str, int]:
        """Clean up old cached data and job runs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Clean old repo cache entries
        old_repos = self.db.query(RepoCache).filter(
            RepoCache.fetched_at < cutoff_date
        ).count()

        self.db.query(RepoCache).filter(
            RepoCache.fetched_at < cutoff_date
        ).delete()

        # Clean old job runs
        old_jobs = self.db.query(JobRun).filter(
            JobRun.started_at < cutoff_date,
            JobRun.status.in_(["completed", "failed"])
        ).count()

        self.db.query(JobRun).filter(
            JobRun.started_at < cutoff_date,
            JobRun.status.in_(["completed", "failed"])
        ).delete()

        self.db.commit()

        return {
            "repos_cleaned": old_repos,
            "jobs_cleaned": old_jobs
        }