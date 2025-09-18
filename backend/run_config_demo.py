#!/usr/bin/env python3
"""
GitHub 推荐系统 - 按配置搜索演示

这个脚本演示了如何按每个配置分别进行搜索、评分和推送。
使用 rich 库提供美观的命令行输出。
"""

import asyncio
import sys
import argparse
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich import print as rich_print
from rich.prompt import Prompt, Confirm

# 添加项目路径
sys.path.append('.')

from core.database import get_db
from models.user import User
from models.preference import Preference
from models.job_run import JobRun
from services.job_service import JobExecutionService

console = Console()


class ConfigDemoRunner:
    def __init__(self):
        self.db = next(get_db())
        self.job_service = JobExecutionService(self.db)

    def show_welcome(self):
        """显示欢迎界面"""
        console.print(Panel.fit(
            "[bold blue]GitHub 推荐系统 - 按配置搜索演示[/bold blue]\n\n"
            "这个工具将演示如何：\n"
            "1. 🔍 按每个配置分别搜索GitHub项目\n"
            "2. ⭐ 独立评分和过滤\n"
            "3. 📨 推送到各自的通知渠道\n"
            "4. 📊 显示详细的执行结果",
            title="🚀 GitHub Bot",
            border_style="green"
        ))

    def list_users(self):
        """列出所有用户"""
        users = self.db.query(User).all()

        if not users:
            console.print("❌ 没有找到用户，请先注册用户", style="red")
            return None

        table = Table(title="📋 用户列表")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("用户名", style="blue")
        table.add_column("邮箱", style="green")
        table.add_column("配置数", style="yellow")

        for user in users:
            pref_count = self.db.query(Preference).filter(
                Preference.user_id == user.id,
                Preference.enabled == True
            ).count()

            table.add_row(
                str(user.id),
                user.username,
                user.email,
                str(pref_count)
            )

        console.print(table)
        return users

    def list_preferences(self, user_id: int):
        """列出用户的配置"""
        preferences = self.db.query(Preference).filter(
            Preference.user_id == user_id,
            Preference.enabled == True
        ).all()

        if not preferences:
            console.print(f"❌ 用户 {user_id} 没有启用的配置", style="red")
            return None

        table = Table(title=f"🎯 用户 {user_id} 的推荐配置")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("配置名称", style="blue", width=20)
        table.add_column("关键词", style="green", width=30)
        table.add_column("语言", style="yellow", width=15)
        table.add_column("通知渠道", style="purple", width=15)

        for pref in preferences:
            table.add_row(
                str(pref.id),
                pref.name,
                ", ".join(pref.keywords[:3]) + ("..." if len(pref.keywords) > 3 else ""),
                ", ".join(pref.languages[:2]) + ("..." if len(pref.languages) > 2 else ""),
                ", ".join(pref.notification_channels)
            )

        console.print(table)
        return preferences

    async def run_single_config(self, user_id: int, preference_id: int):
        """运行单个配置"""
        # 创建任务记录
        job_run = JobRun(
            user_id=user_id,
            status="queued",
            trigger_type="manual",
            preference_id=preference_id,
            job_config={"force_refresh": True, "preference_id": preference_id}
        )

        self.db.add(job_run)
        self.db.commit()
        self.db.refresh(job_run)

        console.print(f"\n🎯 开始执行配置 ID: {preference_id}")

        try:
            # 执行推荐任务
            result = await self.job_service.execute_recommendation_job(
                user_id=user_id,
                job_run_id=job_run.id,
                preference_id=preference_id,
                force_refresh=True
            )

            self.show_execution_result(result)
            return result

        except Exception as e:
            console.print(f"❌ 执行失败: {str(e)}", style="red")
            return None

    async def run_all_configs(self, user_id: int):
        """运行用户的所有配置"""
        preferences = self.db.query(Preference).filter(
            Preference.user_id == user_id,
            Preference.enabled == True
        ).all()

        if not preferences:
            console.print("❌ 没有找到启用的配置", style="red")
            return

        total_stats = {
            "preferences_processed": 0,
            "repos_fetched": 0,
            "recommendations_generated": 0,
            "notifications_sent": 0
        }

        console.print(f"\n🚀 开始执行 {len(preferences)} 个配置")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task("执行配置", total=len(preferences))

            for i, preference in enumerate(preferences, 1):
                progress.update(task, description=f"处理配置 {i}/{len(preferences)}: {preference.name}")

                # 创建任务记录
                job_run = JobRun(
                    user_id=user_id,
                    status="queued",
                    trigger_type="manual",
                    preference_id=preference.id,
                    job_config={"force_refresh": True, "preference_id": preference.id}
                )

                self.db.add(job_run)
                self.db.commit()
                self.db.refresh(job_run)

                try:
                    console.print(f"\n{'='*60}")
                    console.print(f"🔄 处理配置 {i}/{len(preferences)}: {preference.name}", style="bold cyan")
                    console.print(f"{'='*60}")

                    # 显示配置详情
                    self.show_preference_details(preference)

                    # 执行推荐任务
                    result = await self.job_service.execute_recommendation_job(
                        user_id=user_id,
                        job_run_id=job_run.id,
                        preference_id=preference.id,
                        force_refresh=True
                    )

                    if result["status"] == "completed":
                        stats = result.get("stats", {})
                        total_stats["preferences_processed"] += 1
                        total_stats["repos_fetched"] += stats.get("repos_fetched", 0)
                        total_stats["recommendations_generated"] += stats.get("recommendations_generated", 0)
                        total_stats["notifications_sent"] += stats.get("notifications_sent", 0)

                        console.print(f"✅ 配置 '{preference.name}' 执行完成", style="green")
                        self.show_config_summary(preference, stats)
                    else:
                        console.print(f"❌ 配置 '{preference.name}' 执行失败", style="red")

                except Exception as e:
                    console.print(f"❌ 配置 '{preference.name}' 执行出错: {str(e)}", style="red")

                progress.advance(task)

        # 显示最终统计
        self.show_final_stats(total_stats)

    def show_preference_details(self, preference: Preference):
        """显示配置详情"""
        details_table = Table(title=f"配置详情")
        details_table.add_column("属性", style="cyan")
        details_table.add_column("值", style="white")

        details_table.add_row("配置名称", preference.name)
        details_table.add_row("关键词", ", ".join(preference.keywords) if preference.keywords else "无")
        details_table.add_row("编程语言", ", ".join(preference.languages) if preference.languages else "无限制")
        details_table.add_row("最小Star数", str(preference.min_stars))
        details_table.add_row("最大推荐数", str(preference.max_recommendations))
        details_table.add_row("通知渠道", ", ".join(preference.notification_channels) if preference.notification_channels else "无")

        console.print(details_table)

    def show_config_summary(self, preference: Preference, stats: dict):
        """显示配置执行摘要"""
        summary_table = Table(title=f"执行摘要: {preference.name}")
        summary_table.add_column("指标", style="cyan")
        summary_table.add_column("数量", style="yellow")

        summary_table.add_row("获取项目数", str(stats.get("repos_fetched", 0)))
        summary_table.add_row("缓存项目数", str(stats.get("repos_cached", 0)))
        summary_table.add_row("过滤项目数", str(stats.get("repos_filtered", 0)))
        summary_table.add_row("生成推荐数", str(stats.get("recommendations_generated", 0)))

        # 显示通知发送情况
        for key, value in stats.items():
            if key.startswith("notifications_sent_"):
                if value:
                    summary_table.add_row("通知渠道", ", ".join(value))
                else:
                    summary_table.add_row("通知发送", "失败")

        console.print(summary_table)

    def show_execution_result(self, result: dict):
        """显示执行结果"""
        if result["status"] == "completed":
            console.print("✅ 执行成功！", style="green")
            stats = result.get("stats", {})
            self.show_config_summary(None, stats)
        else:
            console.print(f"❌ 执行失败: {result.get('message', '未知错误')}", style="red")

    def show_final_stats(self, stats: dict):
        """显示最终统计"""
        console.print(f"\n{'='*60}")
        console.print("📊 执行总结", style="bold magenta")
        console.print(f"{'='*60}")

        final_table = Table(title="总体统计")
        final_table.add_column("指标", style="cyan")
        final_table.add_column("数量", style="yellow")

        final_table.add_row("处理配置数", str(stats["preferences_processed"]))
        final_table.add_row("获取项目总数", str(stats["repos_fetched"]))
        final_table.add_row("生成推荐总数", str(stats["recommendations_generated"]))
        final_table.add_row("发送通知数", str(stats["notifications_sent"]))

        console.print(final_table)

    async def interactive_mode(self):
        """交互模式"""
        self.show_welcome()

        while True:
            console.print("\n" + "="*60)
            console.print("📋 请选择操作:", style="bold blue")
            console.print("1. 📋 查看所有用户")
            console.print("2. 🎯 查看用户配置")
            console.print("3. ▶️  运行单个配置")
            console.print("4. 🚀 运行所有配置")
            console.print("5. 🚪 退出")

            choice = Prompt.ask("请输入选项 (1-5)", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                self.list_users()

            elif choice == "2":
                user_id = Prompt.ask("请输入用户ID", default="1")
                try:
                    user_id = int(user_id)
                    self.list_preferences(user_id)
                except ValueError:
                    console.print("❌ 请输入有效的用户ID", style="red")

            elif choice == "3":
                user_id = Prompt.ask("请输入用户ID", default="1")
                preference_id = Prompt.ask("请输入配置ID")
                try:
                    user_id = int(user_id)
                    preference_id = int(preference_id)
                    await self.run_single_config(user_id, preference_id)
                except ValueError:
                    console.print("❌ 请输入有效的ID", style="red")
                except Exception as e:
                    console.print(f"❌ 执行失败: {str(e)}", style="red")

            elif choice == "4":
                user_id = Prompt.ask("请输入用户ID", default="1")
                try:
                    user_id = int(user_id)
                    if Confirm.ask(f"确定要运行用户 {user_id} 的所有配置吗？"):
                        await self.run_all_configs(user_id)
                except ValueError:
                    console.print("❌ 请输入有效的用户ID", style="red")
                except Exception as e:
                    console.print(f"❌ 执行失败: {str(e)}", style="red")

            elif choice == "5":
                console.print("👋 再见！", style="green")
                break

    async def run_from_args(self, args):
        """从命令行参数运行"""
        self.show_welcome()

        if args.list_users:
            self.list_users()
            return

        if args.list_preferences:
            self.list_preferences(args.user_id)
            return

        if args.config_id:
            await self.run_single_config(args.user_id, args.config_id)
        elif args.all_configs:
            await self.run_all_configs(args.user_id)
        else:
            console.print("❌ 请指定要执行的操作", style="red")


async def main():
    parser = argparse.ArgumentParser(description="GitHub 推荐系统 - 按配置搜索演示")
    parser.add_argument("--user-id", type=int, default=1, help="用户ID")
    parser.add_argument("--config-id", type=int, help="运行特定配置ID")
    parser.add_argument("--all-configs", action="store_true", help="运行用户的所有配置")
    parser.add_argument("--list-users", action="store_true", help="列出所有用户")
    parser.add_argument("--list-preferences", action="store_true", help="列出用户的配置")
    parser.add_argument("--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    runner = ConfigDemoRunner()

    try:
        if args.interactive or (not any([args.config_id, args.all_configs, args.list_users, args.list_preferences])):
            await runner.interactive_mode()
        else:
            await runner.run_from_args(args)
    except KeyboardInterrupt:
        console.print("\n👋 程序被用户中断", style="yellow")
    except Exception as e:
        console.print(f"\n❌ 程序执行出错: {str(e)}", style="red")


if __name__ == "__main__":
    # 确保安装了必要的依赖
    try:
        import rich
    except ImportError:
        print("❌ 请安装 rich 库: pip install rich")
        sys.exit(1)

    asyncio.run(main())