#!/usr/bin/env python3
"""
GitHub 推荐系统 - 增强版主启动程序

功能特性：
1. 🚀 FastAPI Web服务器
2. 🎯 按配置级别搜索和推送
3. 🖥️ 交互式命令行工具
4. 📊 实时进度监控
5. 📨 多渠道通知推送

使用方法：
- python enhanced_main.py                    # 启动Web服务器
- python enhanced_main.py --demo             # 运行演示模式
- python enhanced_main.py --cli              # 启动命令行工具
- python enhanced_main.py --user 1 --all     # 运行用户所有配置
- python enhanced_main.py --user 1 --config 2 # 运行指定配置
"""

import asyncio
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import structlog
import uvicorn

# Rich console imports for beautiful CLI
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
    from rich import print as rich_print
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Rich库未安装，将使用基础输出模式")

# Project imports
from core.config import settings
from core.exceptions import APIException
from core.response import HealthResponse, error_response
from core.database import get_db

# Import API routers
from api.health import router as health_router
from api.auth import router as auth_router
from api.preferences import router as preferences_router
from api.projects import router as projects_router
from api.test_endpoints import router as test_router

# Import models
from models.user import User
from models.preference import Preference
from models.job_run import JobRun

# Import services
from services.job_service import JobExecutionService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize console
if RICH_AVAILABLE:
    console = Console()
else:
    class BasicConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = BasicConsole()

# Application startup time
startup_time = time.time()


class EnhancedGitHubBot:
    """增强版GitHub推荐机器人"""

    def __init__(self):
        self.app = self.create_app()
        self.db = next(get_db())
        self.job_service = JobExecutionService(self.db)

    def create_app(self) -> FastAPI:
        """创建FastAPI应用"""
        app = FastAPI(
            title=f"{settings.app_name} - Enhanced",
            version=f"{settings.app_version}-enhanced",
            description="Enhanced GitHub project recommendation system with CLI tools and per-config execution",
            docs_url="/docs" if settings.debug else None,
            redoc_url="/redoc" if settings.debug else None,
        )

        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Logging middleware
        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = time.time()
            trace_id = request.headers.get("X-Trace-ID", f"req_{int(time.time() * 1000)}")

            logger.info(
                "Request received",
                method=request.method,
                url=str(request.url),
                trace_id=trace_id,
                user_agent=request.headers.get("user-agent"),
            )

            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                "Request processed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=round(process_time, 3),
                trace_id=trace_id,
            )

            response.headers["X-Trace-ID"] = trace_id
            return response

        # Exception handlers
        @app.exception_handler(APIException)
        async def api_exception_handler(request: Request, exc: APIException):
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response(
                    code=exc.status_code,
                    error_code=exc.error_code,
                    message=exc.message,
                    details=exc.details,
                    trace_id=exc.trace_id,
                ),
            )

        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response(
                    code=exc.status_code,
                    error_code=f"HTTP_{exc.status_code}",
                    message=str(exc.detail),
                    trace_id=request.headers.get("X-Trace-ID"),
                ),
            )

        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(
                "Unhandled exception",
                error=str(exc),
                trace_id=request.headers.get("X-Trace-ID"),
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content=error_response(
                    code=500,
                    error_code="INTERNAL_SERVER_ERROR",
                    message="An unexpected error occurred",
                    trace_id=request.headers.get("X-Trace-ID"),
                ),
            )

        # Include API routers
        app.include_router(health_router, prefix="/api/v1", tags=["Health"])
        app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
        app.include_router(preferences_router, prefix="/api/v1/preferences", tags=["Preferences"])
        app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])

        if settings.debug:
            app.include_router(test_router, prefix="/api/v1/test", tags=["Testing"])

        # Mount static files and serve frontend
        self.setup_frontend(app)

        # Setup startup and shutdown events
        @app.on_event("startup")
        async def startup_event():
            logger.info(
                "Enhanced GitHub Bot starting",
                app_name=settings.app_name,
                version=settings.app_version,
                debug=settings.debug,
            )

            # Initialize database
            from core.init_db import init_database
            init_database()

        @app.on_event("shutdown")
        async def shutdown_event():
            logger.info("Enhanced GitHub Bot shutting down")

        return app

    def setup_frontend(self, app: FastAPI):
        """设置前端文件服务"""
        frontend_path = Path(__file__).parent.parent / "frontend"

        if frontend_path.exists():
            app.mount("/static", StaticFiles(directory=frontend_path), name="static")

            @app.get("/")
            async def serve_index():
                return FileResponse(frontend_path / "index.html")

            @app.get("/index.html")
            async def serve_index_explicit():
                return FileResponse(frontend_path / "index.html")

        # 提供增强UI界面
        enhanced_ui_path = Path(__file__).parent / "enhanced_recommendation_ui.html"
        if enhanced_ui_path.exists():
            @app.get("/enhanced")
            async def serve_enhanced_ui():
                return FileResponse(enhanced_ui_path)

    def show_welcome(self):
        """显示欢迎界面"""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold blue]🚀 GitHub 推荐系统 - 增强版[/bold blue]\n\n"
                "功能特性：\n"
                "• 🎯 按配置级别独立搜索和推送\n"
                "• 📊 实时进度监控和统计\n"
                "• 📨 多渠道通知推送\n"
                "• 🖥️ 美观的命令行界面\n"
                "• 🌐 Web管理界面\n\n"
                f"版本: {settings.app_version}-enhanced\n"
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                title="GitHub Bot Enhanced",
                border_style="green"
            ))
        else:
            print("\n" + "="*60)
            print("🚀 GitHub 推荐系统 - 增强版")
            print("="*60)
            print("• 按配置级别独立搜索和推送")
            print("• 实时进度监控和统计")
            print("• 多渠道通知推送")
            print("• 命令行和Web界面")
            print(f"版本: {settings.app_version}-enhanced")
            print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)

    def list_users(self) -> List[User]:
        """列出所有用户"""
        users = self.db.query(User).all()

        if not users:
            if RICH_AVAILABLE:
                console.print("❌ 没有找到用户，请先注册用户", style="red")
            else:
                print("❌ 没有找到用户，请先注册用户")
            return []

        if RICH_AVAILABLE:
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
        else:
            print("\n📋 用户列表:")
            print("-" * 60)
            for user in users:
                pref_count = self.db.query(Preference).filter(
                    Preference.user_id == user.id,
                    Preference.enabled == True
                ).count()
                print(f"ID: {user.id} | 用户名: {user.username} | 邮箱: {user.email} | 配置数: {pref_count}")

        return users

    def list_preferences(self, user_id: int) -> List[Preference]:
        """列出用户的配置"""
        preferences = self.db.query(Preference).filter(
            Preference.user_id == user_id,
            Preference.enabled == True
        ).all()

        if not preferences:
            if RICH_AVAILABLE:
                console.print(f"❌ 用户 {user_id} 没有启用的配置", style="red")
            else:
                print(f"❌ 用户 {user_id} 没有启用的配置")
            return []

        if RICH_AVAILABLE:
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
        else:
            print(f"\n🎯 用户 {user_id} 的推荐配置:")
            print("-" * 80)
            for pref in preferences:
                print(f"ID: {pref.id} | 名称: {pref.name}")
                print(f"   关键词: {', '.join(pref.keywords[:3])}")
                print(f"   语言: {', '.join(pref.languages[:2])}")
                print(f"   通知: {', '.join(pref.notification_channels)}")
                print("-" * 40)

        return preferences

    async def run_single_config(self, user_id: int, preference_id: int):
        """运行单个配置"""
        if RICH_AVAILABLE:
            console.print(f"\n🎯 开始执行配置 ID: {preference_id}", style="bold cyan")
        else:
            print(f"\n🎯 开始执行配置 ID: {preference_id}")

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
            if RICH_AVAILABLE:
                console.print(f"❌ 执行失败: {str(e)}", style="red")
            else:
                print(f"❌ 执行失败: {str(e)}")
            return None

    async def run_all_configs(self, user_id: int):
        """运行用户的所有配置"""
        preferences = self.db.query(Preference).filter(
            Preference.user_id == user_id,
            Preference.enabled == True
        ).all()

        if not preferences:
            if RICH_AVAILABLE:
                console.print("❌ 没有找到启用的配置", style="red")
            else:
                print("❌ 没有找到启用的配置")
            return

        if RICH_AVAILABLE:
            console.print(f"\n🚀 开始执行 {len(preferences)} 个配置", style="bold green")
        else:
            print(f"\n🚀 开始执行 {len(preferences)} 个配置")

        total_stats = {
            "preferences_processed": 0,
            "repos_fetched": 0,
            "recommendations_generated": 0,
            "notifications_sent": 0
        }

        if RICH_AVAILABLE:
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
                    result = await self._process_single_preference(user_id, preference, i, len(preferences))
                    if result:
                        self._update_total_stats(total_stats, result.get("stats", {}))
                    progress.advance(task)
        else:
            for i, preference in enumerate(preferences, 1):
                print(f"\n[{i}/{len(preferences)}] 处理配置: {preference.name}")
                result = await self._process_single_preference(user_id, preference, i, len(preferences))
                if result:
                    self._update_total_stats(total_stats, result.get("stats", {}))

        # 显示最终统计
        self.show_final_stats(total_stats)

    async def _process_single_preference(self, user_id: int, preference: Preference, index: int, total: int):
        """处理单个偏好配置"""
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
            if RICH_AVAILABLE:
                console.print(f"\n{'='*60}")
                console.print(f"🔄 处理配置 {index}/{total}: {preference.name}", style="bold cyan")
                console.print(f"{'='*60}")
            else:
                print(f"\n{'='*60}")
                print(f"🔄 处理配置 {index}/{total}: {preference.name}")
                print(f"{'='*60}")

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
                if RICH_AVAILABLE:
                    console.print(f"✅ 配置 '{preference.name}' 执行完成", style="green")
                else:
                    print(f"✅ 配置 '{preference.name}' 执行完成")
                self.show_config_summary(preference, result.get("stats", {}))
            else:
                if RICH_AVAILABLE:
                    console.print(f"❌ 配置 '{preference.name}' 执行失败", style="red")
                else:
                    print(f"❌ 配置 '{preference.name}' 执行失败")

            return result

        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"❌ 配置 '{preference.name}' 执行出错: {str(e)}", style="red")
            else:
                print(f"❌ 配置 '{preference.name}' 执行出错: {str(e)}")
            return None

    def _update_total_stats(self, total_stats: dict, config_stats: dict):
        """更新总统计"""
        total_stats["preferences_processed"] += 1
        total_stats["repos_fetched"] += config_stats.get("repos_fetched", 0)
        total_stats["recommendations_generated"] += config_stats.get("recommendations_generated", 0)
        total_stats["notifications_sent"] += config_stats.get("notifications_sent", 0)

    def show_preference_details(self, preference: Preference):
        """显示配置详情"""
        if RICH_AVAILABLE:
            details_table = Table(title="配置详情")
            details_table.add_column("属性", style="cyan")
            details_table.add_column("值", style="white")

            details_table.add_row("配置名称", preference.name)
            details_table.add_row("关键词", ", ".join(preference.keywords) if preference.keywords else "无")
            details_table.add_row("编程语言", ", ".join(preference.languages) if preference.languages else "无限制")
            details_table.add_row("最小Star数", str(preference.min_stars))
            details_table.add_row("最大推荐数", str(preference.max_recommendations))
            details_table.add_row("通知渠道", ", ".join(preference.notification_channels) if preference.notification_channels else "无")

            console.print(details_table)
        else:
            print(f"📋 配置名称: {preference.name}")
            print(f"🔍 关键词: {', '.join(preference.keywords) if preference.keywords else '无'}")
            print(f"💻 编程语言: {', '.join(preference.languages) if preference.languages else '无限制'}")
            print(f"⭐ 最小Star数: {preference.min_stars}")
            print(f"📨 通知渠道: {', '.join(preference.notification_channels) if preference.notification_channels else '无'}")

    def show_config_summary(self, preference: Preference, stats: dict):
        """显示配置执行摘要"""
        if RICH_AVAILABLE:
            summary_table = Table(title=f"执行摘要: {preference.name if preference else '单配置'}")
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
        else:
            print(f"📊 执行摘要:")
            print(f"   获取项目数: {stats.get('repos_fetched', 0)}")
            print(f"   缓存项目数: {stats.get('repos_cached', 0)}")
            print(f"   过滤项目数: {stats.get('repos_filtered', 0)}")
            print(f"   生成推荐数: {stats.get('recommendations_generated', 0)}")

    def show_execution_result(self, result: dict):
        """显示执行结果"""
        if result["status"] == "completed":
            if RICH_AVAILABLE:
                console.print("✅ 执行成功！", style="green")
            else:
                print("✅ 执行成功！")
            stats = result.get("stats", {})
            self.show_config_summary(None, stats)
        else:
            if RICH_AVAILABLE:
                console.print(f"❌ 执行失败: {result.get('message', '未知错误')}", style="red")
            else:
                print(f"❌ 执行失败: {result.get('message', '未知错误')}")

    def show_final_stats(self, stats: dict):
        """显示最终统计"""
        if RICH_AVAILABLE:
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
        else:
            print(f"\n{'='*60}")
            print("📊 执行总结")
            print(f"{'='*60}")
            print(f"处理配置数: {stats['preferences_processed']}")
            print(f"获取项目总数: {stats['repos_fetched']}")
            print(f"生成推荐总数: {stats['recommendations_generated']}")
            print(f"发送通知数: {stats['notifications_sent']}")

    async def interactive_mode(self):
        """交互模式"""
        self.show_welcome()

        while True:
            if RICH_AVAILABLE:
                console.print("\n" + "="*60)
                console.print("📋 请选择操作:", style="bold blue")
                console.print("1. 📋 查看所有用户")
                console.print("2. 🎯 查看用户配置")
                console.print("3. ▶️  运行单个配置")
                console.print("4. 🚀 运行所有配置")
                console.print("5. 🌐 启动Web服务器")
                console.print("6. 🚪 退出")

                if RICH_AVAILABLE:
                    choice = Prompt.ask("请输入选项 (1-6)", choices=["1", "2", "3", "4", "5", "6"])
                else:
                    choice = input("请输入选项 (1-6): ")
            else:
                print("\n" + "="*60)
                print("📋 请选择操作:")
                print("1. 📋 查看所有用户")
                print("2. 🎯 查看用户配置")
                print("3. ▶️  运行单个配置")
                print("4. 🚀 运行所有配置")
                print("5. 🌐 启动Web服务器")
                print("6. 🚪 退出")
                choice = input("请输入选项 (1-6): ")

            if choice == "1":
                self.list_users()

            elif choice == "2":
                if RICH_AVAILABLE:
                    user_id = Prompt.ask("请输入用户ID", default="1")
                else:
                    user_id = input("请输入用户ID (默认: 1): ") or "1"
                try:
                    user_id = int(user_id)
                    self.list_preferences(user_id)
                except ValueError:
                    if RICH_AVAILABLE:
                        console.print("❌ 请输入有效的用户ID", style="red")
                    else:
                        print("❌ 请输入有效的用户ID")

            elif choice == "3":
                if RICH_AVAILABLE:
                    user_id = Prompt.ask("请输入用户ID", default="1")
                    preference_id = Prompt.ask("请输入配置ID")
                else:
                    user_id = input("请输入用户ID (默认: 1): ") or "1"
                    preference_id = input("请输入配置ID: ")
                try:
                    user_id = int(user_id)
                    preference_id = int(preference_id)
                    await self.run_single_config(user_id, preference_id)
                except ValueError:
                    if RICH_AVAILABLE:
                        console.print("❌ 请输入有效的ID", style="red")
                    else:
                        print("❌ 请输入有效的ID")
                except Exception as e:
                    if RICH_AVAILABLE:
                        console.print(f"❌ 执行失败: {str(e)}", style="red")
                    else:
                        print(f"❌ 执行失败: {str(e)}")

            elif choice == "4":
                if RICH_AVAILABLE:
                    user_id = Prompt.ask("请输入用户ID", default="1")
                    if Confirm.ask(f"确定要运行用户 {user_id} 的所有配置吗？"):
                        await self.run_all_configs(int(user_id))
                else:
                    user_id = input("请输入用户ID (默认: 1): ") or "1"
                    confirm = input(f"确定要运行用户 {user_id} 的所有配置吗？(y/N): ")
                    if confirm.lower() == 'y':
                        await self.run_all_configs(int(user_id))

            elif choice == "5":
                if RICH_AVAILABLE:
                    console.print("🌐 启动Web服务器...", style="green")
                else:
                    print("🌐 启动Web服务器...")
                self.start_web_server()
                break

            elif choice == "6":
                if RICH_AVAILABLE:
                    console.print("👋 再见！", style="green")
                else:
                    print("👋 再见！")
                break

    def start_web_server(self):
        """启动Web服务器"""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold green]🌐 Web服务器启动中...[/bold green]\n\n"
                "访问地址：\n"
                "• 主界面: http://localhost:8000\n"
                "• 增强界面: http://localhost:8000/enhanced\n"
                "• API文档: http://localhost:8000/docs\n\n"
                "按 Ctrl+C 停止服务器",
                title="GitHub Bot Web Server",
                border_style="blue"
            ))
        else:
            print("\n" + "="*60)
            print("🌐 Web服务器启动中...")
            print("访问地址：")
            print("• 主界面: http://localhost:8000")
            print("• 增强界面: http://localhost:8000/enhanced")
            print("• API文档: http://localhost:8000/docs")
            print("按 Ctrl+C 停止服务器")
            print("="*60)

        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )

    async def demo_mode(self):
        """演示模式"""
        self.show_welcome()

        if RICH_AVAILABLE:
            console.print("\n🎬 演示模式启动", style="bold yellow")
            console.print("将展示按配置搜索和推送的完整流程", style="yellow")
        else:
            print("\n🎬 演示模式启动")
            print("将展示按配置搜索和推送的完整流程")

        # 显示用户和配置信息
        users = self.list_users()
        if users:
            user = users[0]
            preferences = self.list_preferences(user.id)

            if preferences:
                if RICH_AVAILABLE:
                    console.print(f"\n🎯 将演示用户 {user.username} 的配置处理", style="bold cyan")
                else:
                    print(f"\n🎯 将演示用户 {user.username} 的配置处理")

                # 运行所有配置
                await self.run_all_configs(user.id)
            else:
                if RICH_AVAILABLE:
                    console.print("❌ 演示需要至少一个启用的配置", style="red")
                else:
                    print("❌ 演示需要至少一个启用的配置")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub 推荐系统 - 增强版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python enhanced_main.py                    # 启动交互模式
  python enhanced_main.py --server           # 启动Web服务器
  python enhanced_main.py --demo             # 运行演示模式
  python enhanced_main.py --cli              # 启动命令行工具
  python enhanced_main.py --user 1 --all     # 运行用户所有配置
  python enhanced_main.py --user 1 --config 2 # 运行指定配置
        """
    )

    parser.add_argument("--server", action="store_true", help="启动Web服务器")
    parser.add_argument("--demo", action="store_true", help="运行演示模式")
    parser.add_argument("--cli", action="store_true", help="启动命令行工具（与交互模式相同）")
    parser.add_argument("--user", type=int, help="指定用户ID")
    parser.add_argument("--config", type=int, help="运行特定配置ID")
    parser.add_argument("--all", action="store_true", help="运行用户的所有配置")
    parser.add_argument("--list-users", action="store_true", help="列出所有用户")
    parser.add_argument("--list-configs", action="store_true", help="列出用户的配置")

    args = parser.parse_args()

    # 创建增强版GitHub Bot实例
    bot = EnhancedGitHubBot()

    try:
        if args.server:
            # 启动Web服务器
            bot.start_web_server()

        elif args.demo:
            # 演示模式
            await bot.demo_mode()

        elif args.list_users:
            # 列出用户
            bot.show_welcome()
            bot.list_users()

        elif args.list_configs and args.user:
            # 列出配置
            bot.show_welcome()
            bot.list_preferences(args.user)

        elif args.user and args.config:
            # 运行单个配置
            bot.show_welcome()
            await bot.run_single_config(args.user, args.config)

        elif args.user and args.all:
            # 运行所有配置
            bot.show_welcome()
            await bot.run_all_configs(args.user)

        elif args.cli:
            # 命令行工具（交互模式）
            await bot.interactive_mode()

        else:
            # 默认交互模式
            await bot.interactive_mode()

    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n👋 程序被用户中断", style="yellow")
        else:
            print("\n👋 程序被用户中断")
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"\n❌ 程序执行出错: {str(e)}", style="red")
        else:
            print(f"\n❌ 程序执行出错: {str(e)}")


if __name__ == "__main__":
    # 检查依赖
    if not RICH_AVAILABLE:
        print("💡 提示: 安装 rich 库可获得更好的界面体验")
        print("   pip install rich")

    # 运行主程序
    asyncio.run(main())