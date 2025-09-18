import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rich_print

from models.user import User
from models.preference import Preference
from models.repo_cache import RepoCache
from models.job_run import JobRun
from models.recommendation import Recommendation
from services.github_client import GitHubClient, GitHubRateLimitError
from services.recommendation_engine import RecommendationEngine
from services.notification_service import NotificationService

logger = structlog.get_logger()
console = Console()


class EnhancedJobExecutionService:
    """增强版任务执行服务 - 提供详细的配置级别输出和控制"""

    def __init__(self, db: Session):
        self.db = db
        self.recommendation_engine = RecommendationEngine(db)
        self.notification_service = NotificationService(db)

    async def execute_recommendation_job(
        self,
        user_id: int,
        job_run_id: int,
        preference_id: Optional[int] = None,
        force_refresh: bool = False,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        执行推荐任务 - 按每个配置分别搜索和推送

        Args:
            user_id: 用户ID
            job_run_id: 任务运行ID
            preference_id: 特定偏好ID（可选）
            force_refresh: 强制刷新缓存
            verbose: 是否输出详细信息
        """
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if not job_run:
            raise ValueError(f"Job run {job_run_id} not found")

        try:
            # 更新任务状态
            job_run.status = "running"
            job_run.started_at = func.now()
            self.db.commit()

            if verbose:
                console.print(Panel.fit(
                    f"🚀 开始执行推荐任务\n"
                    f"用户ID: {user_id}\n"
                    f"任务ID: {job_run_id}\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    title="GitHub 推荐任务",
                    border_style="green"
                ))

            # 获取用户和偏好配置
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            # 获取要处理的偏好配置
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
                message = "没有找到启用的偏好配置"
                if verbose:
                    console.print(f"⚠️  {message}", style="yellow")

                job_run.status = "completed"
                job_run.finished_at = func.now()
                job_run.error_message = message
                self.db.commit()
                return {"status": "completed", "message": message}

            if verbose:
                console.print(f"📋 找到 {len(preferences)} 个启用的偏好配置", style="blue")

            total_stats = {
                "repos_fetched": 0,
                "repos_cached": 0,
                "repos_filtered": 0,
                "recommendations_generated": 0,
                "preferences_processed": 0,
                "notifications_sent": 0,
                "errors_count": 0
            }

            preference_results = []

            # 按配置逐个处理
            async with GitHubClient() as github_client:
                for i, preference in enumerate(preferences, 1):
                    if verbose:
                        console.print(f"\n{'=' * 60}")
                        console.print(f"🔄 处理配置 {i}/{len(preferences)}: {preference.name}", style="bold cyan")
                        console.print(f"{'=' * 60}")

                    try:
                        # 显示配置详情
                        if verbose:
                            self._print_preference_details(preference)

                        # 1. 获取仓库数据
                        console.print("🔍 正在从GitHub搜索项目...", style="yellow")
                        repos = await self._fetch_repositories(github_client, preference, force_refresh)
                        total_stats["repos_fetched"] += len(repos)

                        if verbose:
                            console.print(f"✅ 搜索完成，获取到 {len(repos)} 个项目", style="green")

                        # 2. 缓存仓库数据
                        console.print("💾 正在缓存项目数据...", style="yellow")
                        cached_repos = await self._cache_repositories(repos)
                        total_stats["repos_cached"] += len(cached_repos)

                        if verbose:
                            console.print(f"✅ 缓存完成，处理了 {len(cached_repos)} 个项目", style="green")

                        # 3. 过滤和评分
                        console.print("⭐ 正在评分和过滤项目...", style="yellow")
                        filtered_repos = self.recommendation_engine.filter_repositories(
                            [self._repo_cache_to_dict(repo) for repo in cached_repos],
                            preference
                        )
                        total_stats["repos_filtered"] += len(filtered_repos)

                        if verbose:
                            console.print(f"✅ 过滤完成，筛选出 {len(filtered_repos)} 个高质量项目", style="green")

                        # 4. 保存推荐结果
                        console.print("💾 正在保存推荐结果...", style="yellow")
                        recommendations = self.recommendation_engine.save_recommendations(
                            user_id=user_id,
                            preference_id=preference.id,
                            job_run_id=job_run_id,
                            filtered_repos=filtered_repos
                        )
                        total_stats["recommendations_generated"] += len(recommendations)

                        if verbose:
                            console.print(f"✅ 保存完成，生成了 {len(recommendations)} 条推荐", style="green")

                        # 5. 显示推荐结果
                        if verbose and recommendations:
                            self._print_recommendations_table(recommendations, preference.name)

                        # 6. 发送通知
                        sent_channels = []
                        if recommendations and preference.notification_channels:
                            console.print("📨 正在发送通知...", style="yellow")
                            try:
                                sent_channels = await self.notification_service.send_recommendations_notification(
                                    user_id=user_id,
                                    preference=preference,
                                    recommendations=recommendations
                                )
                                total_stats["notifications_sent"] += len(sent_channels)
                                total_stats[f"notifications_sent_{preference.id}"] = sent_channels

                                if verbose:
                                    if sent_channels:
                                        console.print(f"✅ 通知发送成功: {', '.join(sent_channels)}", style="green")
                                    else:
                                        console.print("⚠️  通知发送失败或无可用渠道", style="yellow")

                            except Exception as e:
                                logger.error("Failed to send notifications", preference_id=preference.id, error=str(e))
                                total_stats["notification_errors"] = total_stats.get("notification_errors", 0) + 1
                                if verbose:
                                    console.print(f"❌ 通知发送失败: {str(e)}", style="red")

                        total_stats["preferences_processed"] += 1

                        # 记录配置处理结果
                        preference_result = {
                            "preference_id": preference.id,
                            "preference_name": preference.name,
                            "repos_found": len(repos),
                            "recommendations_generated": len(recommendations),
                            "notifications_sent": sent_channels,
                            "status": "success"
                        }
                        preference_results.append(preference_result)

                        if verbose:
                            console.print(f"✅ 配置 '{preference.name}' 处理完成", style="bold green")

                        logger.info(
                            "Preference processed successfully",
                            preference_id=preference.id,
                            preference_name=preference.name,
                            repos_found=len(repos),
                            recommendations_count=len(recommendations),
                            sent_channels=sent_channels
                        )

                    except GitHubRateLimitError as e:
                        error_msg = f"GitHub API 速率限制，重置时间: {e.reset_time}"
                        logger.warning("Hit GitHub rate limit", reset_time=e.reset_time)
                        total_stats["errors_count"] += 1

                        preference_result = {
                            "preference_id": preference.id,
                            "preference_name": preference.name,
                            "error": error_msg,
                            "status": "rate_limited"
                        }
                        preference_results.append(preference_result)

                        if verbose:
                            console.print(f"⚠️  {error_msg}", style="yellow")
                        break  # 停止处理以避免更多限制

                    except Exception as e:
                        error_msg = f"处理偏好配置失败: {str(e)}"
                        logger.error("Error processing preference", preference_id=preference.id, error=str(e))
                        total_stats["errors_count"] += 1

                        preference_result = {
                            "preference_id": preference.id,
                            "preference_name": preference.name,
                            "error": error_msg,
                            "status": "failed"
                        }
                        preference_results.append(preference_result)

                        if verbose:
                            console.print(f"❌ {error_msg}", style="red")
                        continue

            # 显示最终总结
            if verbose:
                self._print_final_summary(total_stats, preference_results)

            # 更新任务完成状态
            job_run.status = "completed"
            job_run.finished_at = func.now()
            job_run.counters = total_stats
            self.db.commit()

            logger.info("Recommendation job completed",
                       user_id=user_id,
                       job_run_id=job_run_id,
                       stats=total_stats,
                       preference_results=preference_results)

            return {
                "status": "completed",
                "stats": total_stats,
                "preference_results": preference_results,
                "job_run_id": job_run_id
            }

        except Exception as e:
            # 标记任务失败
            job_run.status = "failed"
            job_run.finished_at = func.now()
            job_run.error_message = str(e)
            job_run.counters = total_stats if 'total_stats' in locals() else {}
            self.db.commit()

            logger.error("Recommendation job failed", user_id=user_id, job_run_id=job_run_id, error=str(e))

            if 'verbose' in locals() and verbose:
                console.print(f"❌ 任务执行失败: {str(e)}", style="bold red")

            raise

    def _print_preference_details(self, preference: Preference):
        """打印偏好配置详情"""
        details_table = Table(title=f"配置详情: {preference.name}")
        details_table.add_column("属性", style="cyan")
        details_table.add_column("值", style="white")

        details_table.add_row("配置名称", preference.name)
        details_table.add_row("关键词", ", ".join(preference.keywords) if preference.keywords else "无")
        details_table.add_row("编程语言", ", ".join(preference.languages) if preference.languages else "无限制")
        details_table.add_row("最小Star数", str(preference.min_stars))
        details_table.add_row("最大推荐数", str(preference.max_recommendations))
        details_table.add_row("通知渠道", ", ".join(preference.notification_channels) if preference.notification_channels else "无")

        console.print(details_table)

    def _print_recommendations_table(self, recommendations: List[Recommendation], preference_name: str):
        """打印推荐结果表格"""
        if not recommendations:
            return

        table = Table(title=f"推荐结果: {preference_name}")
        table.add_column("序号", style="cyan", width=4)
        table.add_column("项目名称", style="bold white", width=30)
        table.add_column("Stars", style="yellow", width=8)
        table.add_column("语言", style="green", width=12)
        table.add_column("评分", style="red", width=6)

        for i, rec in enumerate(recommendations[:10], 1):  # 只显示前10个
            repo = self.db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
            if repo:
                table.add_row(
                    str(i),
                    repo.full_name[:28] + "..." if len(repo.full_name) > 28 else repo.full_name,
                    f"{repo.stargazers_count:,}",
                    repo.language or "N/A",
                    f"{rec.score:.2f}"
                )

        console.print(table)

        if len(recommendations) > 10:
            console.print(f"... 还有 {len(recommendations) - 10} 个推荐项目", style="dim")

    def _print_final_summary(self, stats: Dict[str, Any], preference_results: List[Dict[str, Any]]):
        """打印最终总结"""
        console.print(f"\n{'=' * 60}")
        console.print("📊 任务执行总结", style="bold magenta")
        console.print(f"{'=' * 60}")

        # 统计表格
        summary_table = Table(title="执行统计")
        summary_table.add_column("指标", style="cyan")
        summary_table.add_column("数量", style="white")

        summary_table.add_row("处理的配置数", str(stats.get("preferences_processed", 0)))
        summary_table.add_row("获取的项目数", str(stats.get("repos_fetched", 0)))
        summary_table.add_row("缓存的项目数", str(stats.get("repos_cached", 0)))
        summary_table.add_row("过滤的项目数", str(stats.get("repos_filtered", 0)))
        summary_table.add_row("生成的推荐数", str(stats.get("recommendations_generated", 0)))
        summary_table.add_row("发送的通知数", str(stats.get("notifications_sent", 0)))
        summary_table.add_row("错误次数", str(stats.get("errors_count", 0)))

        console.print(summary_table)

        # 配置处理结果
        if preference_results:
            results_table = Table(title="各配置处理结果")
            results_table.add_column("配置名称", style="cyan")
            results_table.add_column("状态", style="white")
            results_table.add_column("推荐数", style="green")
            results_table.add_column("通知渠道", style="yellow")

            for result in preference_results:
                status_style = "green" if result["status"] == "success" else "red"
                status_text = {
                    "success": "✅ 成功",
                    "failed": "❌ 失败",
                    "rate_limited": "⚠️  限制"
                }.get(result["status"], result["status"])

                results_table.add_row(
                    result["preference_name"],
                    f"[{status_style}]{status_text}[/{status_style}]",
                    str(result.get("recommendations_generated", 0)),
                    ", ".join(result.get("notifications_sent", [])) or "无"
                )

            console.print(results_table)

    # 继承原有的辅助方法
    async def _fetch_repositories(self, github_client: GitHubClient, preference: Preference, force_refresh: bool = False):
        """从原 job_service.py 继承"""
        # 这里使用原有的实现
        pass

    async def _cache_repositories(self, repos: List[Dict[str, Any]]):
        """从原 job_service.py 继承"""
        # 这里使用原有的实现
        pass

    def _repo_cache_to_dict(self, repo_cache: RepoCache) -> Dict[str, Any]:
        """从原 job_service.py 继承"""
        # 这里使用原有的实现
        pass