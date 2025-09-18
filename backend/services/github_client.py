import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import structlog
from core.config import settings
from core.exceptions import ServiceUnavailableException, BadRequestException

logger = structlog.get_logger()


class GitHubRateLimitError(Exception):
    def __init__(self, reset_time: int):
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded. Resets at {reset_time}")


class GitHubClient:
    def __init__(self):
        self.base_url = settings.github_api_base_url
        self.token = settings.github_token
        self.session: Optional[httpx.AsyncClient] = None
        self.is_demo_mode = self.token in ("demo_token_replace_me", "demo", "test", "")

    async def __aenter__(self):
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Bot-WebUI/1.0.0"
        }
        self.session = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
            proxies={}  # Disable proxies for GitHub API
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limit handling"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self.session.request(method, endpoint, **kwargs)

            # Check rate limit
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))

            logger.info(
                "GitHub API request",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                rate_limit_remaining=remaining
            )

            if response.status_code == 403 and remaining == 0:
                raise GitHubRateLimitError(reset_time)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitHub API error",
                status_code=e.response.status_code,
                response_text=e.response.text,
                endpoint=endpoint
            )
            if e.response.status_code == 403:
                raise GitHubRateLimitError(reset_time)
            elif e.response.status_code >= 500:
                raise ServiceUnavailableException("GitHub API is temporarily unavailable")
            else:
                raise BadRequestException(f"GitHub API error: {e.response.text}")

    async def search_repositories(
        self,
        keywords: List[str],
        language: Optional[str] = None,
        min_stars: int = 0,
        created_after: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        per_page: int = 100,
        max_pages: int = 3
    ) -> List[Dict[str, Any]]:
        """Search repositories using GitHub Search API"""

        # Return demo data when in demo mode
        if self.is_demo_mode:
            return await self._get_demo_repositories(keywords, language, min_stars)

        # Build search query
        query_parts = []

        # Keywords (search in name, description, readme)
        # GitHub API limits OR operators to maximum 5, so we need to split large keyword lists
        if keywords:
            # Split keywords into chunks of 5 to respect GitHub API limits
            max_keywords_per_query = 5
            if len(keywords) <= max_keywords_per_query:
                keyword_query = " OR ".join(keywords)
                query_parts.append(keyword_query)
            else:
                # Use the first 5 most important keywords only
                # Prioritize shorter, more specific terms
                prioritized_keywords = sorted(keywords, key=len)[:max_keywords_per_query]
                keyword_query = " OR ".join(prioritized_keywords)
                query_parts.append(keyword_query)

        # Language filter
        if language:
            query_parts.append(f"language:{language}")

        # Stars filter
        if min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")

        # Date filters
        if created_after:
            date_str = created_after.strftime("%Y-%m-%d")
            query_parts.append(f"created:>{date_str}")

        if updated_after:
            date_str = updated_after.strftime("%Y-%m-%d")
            query_parts.append(f"pushed:>{date_str}")

        # Exclude forks by default
        query_parts.append("fork:false")

        query = " ".join(query_parts)

        logger.info("Searching GitHub repositories", query=query)

        all_repos = []
        page = 1

        while page <= max_pages:
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page
            }

            try:
                data = await self._make_request("GET", "/search/repositories", params=params)
                repos = data.get("items", [])

                if not repos:
                    break

                all_repos.extend(repos)

                # Check if we have more pages
                total_count = data.get("total_count", 0)
                if len(all_repos) >= total_count or len(repos) < per_page:
                    break

                page += 1

                # Small delay to be nice to GitHub API
                await asyncio.sleep(0.1)

            except GitHubRateLimitError as e:
                logger.warning("Hit rate limit, stopping search", reset_time=e.reset_time)
                break

        logger.info("GitHub search completed", total_repos=len(all_repos), pages_fetched=page-1)
        return all_repos

    async def get_repository_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get detailed information about a specific repository"""
        endpoint = f"/repos/{owner}/{repo}"
        return await self._make_request("GET", endpoint)

    async def get_trending_repositories(
        self,
        language: Optional[str] = None,
        since: str = "daily"  # daily, weekly, monthly
    ) -> List[Dict[str, Any]]:
        """
        Get trending repositories using GitHub Search API
        Note: GitHub doesn't have a dedicated trending API, so we simulate it
        """
        # Calculate date range for trending
        days_ago = 1 if since == "daily" else 7 if since == "weekly" else 30
        since_date = datetime.utcnow() - timedelta(days=days_ago)

        query_parts = [
            f"created:>{since_date.strftime('%Y-%m-%d')}",
            "fork:false"
        ]

        if language:
            query_parts.append(f"language:{language}")

        query = " ".join(query_parts)

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 50
        }

        data = await self._make_request("GET", "/search/repositories", params=params)
        return data.get("items", [])

    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status"""
        return await self._make_request("GET", "/rate_limit")

    def parse_repo_data(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize repository data from GitHub API response"""
        return {
            "repo_id": repo_data["id"],
            "full_name": repo_data["full_name"],
            "name": repo_data["name"],
            "owner_login": repo_data["owner"]["login"],
            "description": repo_data.get("description"),
            "topics": repo_data.get("topics", []),
            "language": repo_data.get("language"),
            "license_name": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
            "stargazers_count": repo_data["stargazers_count"],
            "forks_count": repo_data["forks_count"],
            "watchers_count": repo_data["watchers_count"],
            "open_issues_count": repo_data["open_issues_count"],
            "size": repo_data.get("size", 0),
            "html_url": repo_data["html_url"],
            "clone_url": repo_data["clone_url"],
            "homepage": repo_data.get("homepage"),
            "is_private": str(repo_data["private"]).lower(),
            "is_fork": str(repo_data["fork"]).lower(),
            "is_archived": str(repo_data.get("archived", False)).lower(),
            "is_disabled": str(repo_data.get("disabled", False)).lower(),
            "created_at": datetime.fromisoformat(repo_data["created_at"].replace("Z", "+00:00")),
            "updated_at": datetime.fromisoformat(repo_data["updated_at"].replace("Z", "+00:00")),
            "pushed_at": datetime.fromisoformat(repo_data["pushed_at"].replace("Z", "+00:00")) if repo_data.get("pushed_at") else None,
            "github_data": repo_data  # Store full response for future use
        }

    async def _get_demo_repositories(self, keywords: List[str], language: Optional[str] = None, min_stars: int = 0) -> List[Dict[str, Any]]:
        """Return demo repositories for testing purposes"""
        import random

        logger.info("Demo mode: returning mock repositories", keywords=keywords, language=language)

        demo_repos = [
            {
                "id": 1,
                "full_name": "microsoft/vscode",
                "name": "vscode",
                "owner": {"login": "microsoft"},
                "description": "Visual Studio Code - 代码编辑器重新定义和优化，用于构建和调试现代web和云应用程序",
                "topics": ["editor", "electron", "vscode", "typescript"],
                "language": "TypeScript",
                "license": {"name": "MIT License"},
                "stargazers_count": 160000,
                "forks_count": 28000,
                "watchers_count": 160000,
                "open_issues_count": 3400,
                "size": 135000,
                "html_url": "https://github.com/microsoft/vscode",
                "clone_url": "https://github.com/microsoft/vscode.git",
                "homepage": "https://code.visualstudio.com",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2015-09-03T21:40:43Z",
                "updated_at": "2025-09-18T07:30:43Z",
                "pushed_at": "2025-09-18T07:30:43Z"
            },
            {
                "id": 2,
                "full_name": "tensorflow/tensorflow",
                "name": "tensorflow",
                "owner": {"login": "tensorflow"},
                "description": "开源机器学习框架，适用于所有人",
                "topics": ["machine-learning", "deep-learning", "neural-network", "tensorflow", "python", "ai"],
                "language": "C++",
                "license": {"name": "Apache License 2.0"},
                "stargazers_count": 185000,
                "forks_count": 74000,
                "watchers_count": 185000,
                "open_issues_count": 2100,
                "size": 250000,
                "html_url": "https://github.com/tensorflow/tensorflow",
                "clone_url": "https://github.com/tensorflow/tensorflow.git",
                "homepage": "https://www.tensorflow.org",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2015-11-07T01:07:04Z",
                "updated_at": "2025-09-18T06:20:12Z",
                "pushed_at": "2025-09-18T06:20:12Z"
            },
            {
                "id": 3,
                "full_name": "facebook/react",
                "name": "react",
                "owner": {"login": "facebook"},
                "description": "用于构建用户界面的JavaScript库",
                "topics": ["react", "javascript", "library", "frontend"],
                "language": "JavaScript",
                "license": {"name": "MIT License"},
                "stargazers_count": 225000,
                "forks_count": 46000,
                "watchers_count": 225000,
                "open_issues_count": 850,
                "size": 15000,
                "html_url": "https://github.com/facebook/react",
                "clone_url": "https://github.com/facebook/react.git",
                "homepage": "https://reactjs.org",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2013-05-24T16:15:54Z",
                "updated_at": "2025-09-18T08:45:22Z",
                "pushed_at": "2025-09-18T08:45:22Z"
            },
            {
                "id": 4,
                "full_name": "pytorch/pytorch",
                "name": "pytorch",
                "owner": {"login": "pytorch"},
                "description": "具有强GPU加速的Python中的张量和动态神经网络",
                "topics": ["deep-learning", "machine-learning", "neural-network", "scientific-computing", "tensor", "pytorch", "python"],
                "language": "Python",
                "license": {"name": "BSD-3-Clause License"},
                "stargazers_count": 82000,
                "forks_count": 22000,
                "watchers_count": 82000,
                "open_issues_count": 4500,
                "size": 170000,
                "html_url": "https://github.com/pytorch/pytorch",
                "clone_url": "https://github.com/pytorch/pytorch.git",
                "homepage": "https://pytorch.org",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2016-08-13T17:05:01Z",
                "updated_at": "2025-09-18T05:12:33Z",
                "pushed_at": "2025-09-18T05:12:33Z"
            },
            {
                "id": 5,
                "full_name": "flutter/flutter",
                "name": "flutter",
                "owner": {"login": "flutter"},
                "description": "Flutter让您可以为移动、Web、桌面和嵌入式设备创建美观、快速的用户体验",
                "topics": ["flutter", "dart", "mobile", "android", "ios", "cross-platform"],
                "language": "Dart",
                "license": {"name": "BSD-3-Clause License"},
                "stargazers_count": 165000,
                "forks_count": 27000,
                "watchers_count": 165000,
                "open_issues_count": 12000,
                "size": 90000,
                "html_url": "https://github.com/flutter/flutter",
                "clone_url": "https://github.com/flutter/flutter.git",
                "homepage": "https://flutter.dev",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2015-03-06T22:54:58Z",
                "updated_at": "2025-09-18T09:22:11Z",
                "pushed_at": "2025-09-18T09:22:11Z"
            },
            {
                "id": 6,
                "full_name": "kubernetes/kubernetes",
                "name": "kubernetes",
                "owner": {"login": "kubernetes"},
                "description": "生产级容器编排",
                "topics": ["kubernetes", "containers", "orchestration", "microservices", "docker", "devops"],
                "language": "Go",
                "license": {"name": "Apache License 2.0"},
                "stargazers_count": 110000,
                "forks_count": 39000,
                "watchers_count": 110000,
                "open_issues_count": 2800,
                "size": 120000,
                "html_url": "https://github.com/kubernetes/kubernetes",
                "clone_url": "https://github.com/kubernetes/kubernetes.git",
                "homepage": "https://kubernetes.io",
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2014-06-06T22:56:04Z",
                "updated_at": "2025-09-18T04:18:45Z",
                "pushed_at": "2025-09-18T04:18:45Z"
            }
        ]

        # Filter by language if specified
        if language:
            demo_repos = [repo for repo in demo_repos if repo["language"] and repo["language"].lower() == language.lower()]

        # Filter by minimum stars
        demo_repos = [repo for repo in demo_repos if repo["stargazers_count"] >= min_stars]

        # Filter by keywords (simulate matching)
        if keywords:
            filtered_repos = []
            for repo in demo_repos:
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if (keyword_lower in repo["name"].lower() or
                        keyword_lower in (repo["description"] or "").lower() or
                        any(keyword_lower in topic.lower() for topic in repo.get("topics", []))):
                        filtered_repos.append(repo)
                        break
            demo_repos = filtered_repos

        # Shuffle and limit results
        random.shuffle(demo_repos)
        return demo_repos[:min(10, len(demo_repos))]