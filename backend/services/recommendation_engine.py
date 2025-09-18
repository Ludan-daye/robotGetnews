import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import structlog
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from models.preference import Preference
from models.repo_cache import RepoCache
from models.recommendation import Recommendation

logger = structlog.get_logger()


class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_score(
        self,
        repo_data: Dict[str, Any],
        preference: Preference
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate recommendation score for a repository based on user preferences
        Returns (score, reasoning_details)
        """
        total_score = 0.0
        max_score = 0.0
        reasoning = {
            "matched_keywords": [],
            "excluded_keywords": [],
            "language_match": False,
            "star_score": 0.0,
            "freshness_score": 0.0,
            "topic_bonus": 0.0,
            "exclusion_penalty": 0.0,
            "total_score": 0.0
        }

        # 1. Keyword matching (40% of total score)
        keyword_score, matched_keywords, excluded_keywords = self._score_keywords(
            repo_data, preference.keywords, preference.excluded_keywords
        )
        reasoning["matched_keywords"] = matched_keywords
        reasoning["excluded_keywords"] = excluded_keywords

        # If excluded keywords found, heavily penalize
        if excluded_keywords:
            reasoning["exclusion_penalty"] = -0.5
            total_score -= 0.5

        total_score += keyword_score * 0.4
        max_score += 0.4

        # 2. Language matching (25% of total score)
        language_score = self._score_language(repo_data, preference.languages)
        reasoning["language_match"] = language_score > 0
        total_score += language_score * 0.25
        max_score += 0.25

        # 3. Star popularity (20% of total score)
        star_score = self._score_stars(repo_data, preference.min_stars, preference.max_stars)
        reasoning["star_score"] = star_score
        total_score += star_score * 0.20
        max_score += 0.20

        # 4. Freshness/Activity (10% of total score)
        freshness_score = self._score_freshness(repo_data)
        reasoning["freshness_score"] = freshness_score
        total_score += freshness_score * 0.10
        max_score += 0.10

        # 5. Topic bonus (5% of total score)
        topic_score = self._score_topics(repo_data, preference.keywords, preference.excluded_topics)
        reasoning["topic_bonus"] = topic_score
        total_score += topic_score * 0.05
        max_score += 0.05

        # Normalize score to 0-1 range
        final_score = max(0.0, min(1.0, total_score / max_score if max_score > 0 else 0.0))
        reasoning["total_score"] = final_score

        return final_score, reasoning

    def _score_keywords(
        self,
        repo_data: Dict[str, Any],
        keywords: List[str],
        excluded_keywords: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """Score based on keyword matching in name, description"""
        if not keywords:
            return 0.0, [], []

        # Combine searchable text (ensure no None values)
        searchable_fields = [
            repo_data.get("name") or "",
            repo_data.get("description") or "",
            repo_data.get("full_name") or ""
        ]
        searchable_text = " ".join(field for field in searchable_fields if field).lower()

        matched_keywords = []
        excluded_matches = []

        # Check for keyword matches
        for keyword in keywords:
            if self._keyword_matches(keyword.lower(), searchable_text):
                matched_keywords.append(keyword)

        # Check for excluded keywords
        for excluded in excluded_keywords:
            if self._keyword_matches(excluded.lower(), searchable_text):
                excluded_matches.append(excluded)

        # Score based on percentage of keywords matched
        if keywords:
            score = len(matched_keywords) / len(keywords)
        else:
            score = 0.0

        return score, matched_keywords, excluded_matches

    def _keyword_matches(self, keyword: str, text: str) -> bool:
        """Check if keyword matches in text (flexible matching)"""
        # Exact phrase match
        if keyword in text:
            return True

        # Word boundary match for single words
        if " " not in keyword:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))

        return False

    def _score_language(self, repo_data: Dict[str, Any], preferred_languages: List[str]) -> float:
        """Score based on programming language preference"""
        if not preferred_languages:
            return 0.5  # Neutral score if no language preference

        repo_language = repo_data.get("language")
        if not repo_language:
            return 0.1  # Low score for repos without specified language

        # Exact match
        if repo_language in preferred_languages:
            return 1.0

        # Partial match for similar languages
        language_lower = repo_language.lower()
        for pref_lang in preferred_languages:
            if pref_lang.lower() in language_lower or language_lower in pref_lang.lower():
                return 0.7

        return 0.0

    def _score_stars(self, repo_data: Dict[str, Any], min_stars: int, max_stars: int = None) -> float:
        """Score based on star count (popularity indicator)"""
        stars = repo_data.get("stargazers_count", 0)

        # Below minimum threshold
        if stars < min_stars:
            return 0.0

        # Above maximum threshold (if set)
        if max_stars and stars > max_stars:
            return 0.3  # Still some value, but not optimal

        # Logarithmic scoring for star count
        if stars >= min_stars:
            # Score between 0.5-1.0 based on star count
            if stars < 100:
                return 0.5
            elif stars < 1000:
                return 0.7
            elif stars < 10000:
                return 0.9
            else:
                return 1.0

        return 0.0

    def _score_freshness(self, repo_data: Dict[str, Any]) -> float:
        """Score based on how recently the repository was updated"""
        updated_at = repo_data.get("updated_at")
        if not updated_at:
            return 0.1

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        now = datetime.utcnow().replace(tzinfo=updated_at.tzinfo)
        days_since_update = (now - updated_at).days

        # Scoring based on recency
        if days_since_update <= 7:
            return 1.0  # Updated within a week
        elif days_since_update <= 30:
            return 0.8  # Updated within a month
        elif days_since_update <= 90:
            return 0.6  # Updated within 3 months
        elif days_since_update <= 365:
            return 0.4  # Updated within a year
        else:
            return 0.2  # Older than a year

    def _score_topics(
        self,
        repo_data: Dict[str, Any],
        keywords: List[str],
        excluded_topics: List[str]
    ) -> float:
        """Score based on repository topics/tags"""
        topics = repo_data.get("topics", [])
        if not topics:
            return 0.0

        score = 0.0

        # Penalty for excluded topics
        for excluded_topic in excluded_topics:
            if excluded_topic.lower() in [t.lower() for t in topics]:
                return -0.5  # Heavy penalty

        # Bonus for keyword matches in topics
        for keyword in keywords:
            for topic in topics:
                if keyword.lower() in topic.lower() or topic.lower() in keyword.lower():
                    score += 0.2
                    break

        return min(score, 1.0)

    def filter_repositories(
        self,
        repos: List[Dict[str, Any]],
        preference: Preference
    ) -> List[Tuple[Dict[str, Any], float, Dict[str, Any]]]:
        """
        Filter and score repositories based on user preferences
        Returns list of (repo_data, score, reasoning) tuples
        """
        results = []

        for repo_data in repos:
            # Basic filtering
            if not self._passes_basic_filters(repo_data, preference):
                continue

            # Calculate score
            score, reasoning = self.calculate_score(repo_data, preference)

            # Only include repos with meaningful scores
            if score > 0.1:  # Minimum threshold
                results.append((repo_data, score, reasoning))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit to max recommendations
        max_recommendations = preference.max_recommendations or 10
        return results[:max_recommendations]

    def _passes_basic_filters(self, repo_data: Dict[str, Any], preference: Preference) -> bool:
        """Apply basic filtering rules"""
        # Star count filter
        stars = repo_data.get("stargazers_count", 0)
        if stars < preference.min_stars:
            return False

        if preference.max_stars and stars > preference.max_stars:
            return False

        # Date filters
        if preference.created_after:
            created_at = repo_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_at and created_at < preference.created_after:
                return False

        if preference.updated_after:
            updated_at = repo_data.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if updated_at and updated_at < preference.updated_after:
                return False

        # Skip archived or disabled repos
        if repo_data.get("archived", False) or repo_data.get("disabled", False):
            return False

        return True

    def save_recommendations(
        self,
        user_id: int,
        preference_id: int,
        job_run_id: int,
        filtered_repos: List[Tuple[Dict[str, Any], float, Dict[str, Any]]]
    ) -> List[Recommendation]:
        """Save recommendations to database"""
        recommendations = []

        for repo_data, score, reasoning in filtered_repos:
            # Check if recommendation already exists
            existing = self.db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.repo_id == repo_data["repo_id"]
            ).first()

            if existing:
                # Update existing recommendation
                existing.score = score
                existing.reason = reasoning
                existing.preference_id = preference_id
                existing.job_run_id = job_run_id
                existing.created_at = func.now()  # Update timestamp to show as new recommendation
                recommendations.append(existing)
            else:
                # Create new recommendation
                recommendation = Recommendation(
                    user_id=user_id,
                    repo_id=repo_data["repo_id"],
                    score=score,
                    reason=reasoning,
                    preference_id=preference_id,
                    job_run_id=job_run_id
                )
                self.db.add(recommendation)
                recommendations.append(recommendation)

        self.db.commit()
        return recommendations