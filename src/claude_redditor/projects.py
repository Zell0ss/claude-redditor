"""Project loader for auto-discovered project configurations."""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict


@dataclass
class Project:
    """
    Represents a project configuration.

    Each project is a self-contained entity with:
    - Configuration (topic, sources)
    - Prompts (classify, digest)
    """
    name: str
    description: str
    topic: str
    subreddits: List[str] = field(default_factory=list)
    hn_keywords: List[str] = field(default_factory=list)
    prompts_dir: Path = field(default_factory=Path)

    @classmethod
    def from_yaml(cls, name: str, config_path: Path) -> 'Project':
        """
        Load project from config.yaml file.

        Args:
            name: Project name (directory name)
            config_path: Path to config.yaml

        Returns:
            Project instance
        """
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # Extract sources
        sources = data.get('sources', {})
        reddit_config = sources.get('reddit', {})
        hn_config = sources.get('hackernews', {})

        return cls(
            name=name,
            description=data.get('description', ''),
            topic=data.get('topic', ''),
            subreddits=reddit_config.get('subreddits', []),
            hn_keywords=hn_config.get('keywords', []),
            prompts_dir=config_path.parent / 'prompts',
        )


class ProjectLoader:
    """
    Loads and manages project configurations.

    Projects are auto-discovered from the projects/ directory.
    Each project must have a config.yaml file.

    Usage:
        loader = ProjectLoader(Path("projects"))
        projects = loader.list_projects()  # ['claudeia', 'wineworld']
        proj = loader.load('claudeia')
        prompt = loader.get_prompt('claudeia', 'classify')
    """

    def __init__(self, projects_dir: Path):
        """
        Initialize project loader.

        Args:
            projects_dir: Path to projects directory
        """
        self.projects_dir = projects_dir
        self._cache: Dict[str, Project] = {}

    def list_projects(self) -> List[str]:
        """
        Auto-discover projects by scanning directories.

        A valid project must have:
        - A directory in projects/
        - A config.yaml file in that directory

        Returns:
            List of project names (sorted alphabetically)
        """
        if not self.projects_dir.exists():
            return []

        projects = []
        for d in self.projects_dir.iterdir():
            if d.is_dir() and (d / 'config.yaml').exists():
                projects.append(d.name)

        return sorted(projects)

    def load(self, name: str) -> Project:
        """
        Load a project configuration.

        Args:
            name: Project name

        Returns:
            Project instance

        Raises:
            FileNotFoundError: If project doesn't exist
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        project_dir = self.projects_dir / name
        config_path = project_dir / 'config.yaml'

        if not config_path.exists():
            raise FileNotFoundError(
                f"Project '{name}' not found. "
                f"Expected config at: {config_path}\n"
                f"Available projects: {', '.join(self.list_projects()) or 'none'}"
            )

        project = Project.from_yaml(name, config_path)
        self._cache[name] = project
        return project

    def get_prompt(self, project_name: str, prompt_name: str) -> str:
        """
        Load a prompt file for a project.

        Args:
            project_name: Project name (e.g., 'claudeia')
            prompt_name: Prompt name without extension (e.g., 'classify', 'digest')

        Returns:
            Prompt content as string

        Raises:
            FileNotFoundError: If prompt doesn't exist
        """
        project = self.load(project_name)
        prompt_path = project.prompts_dir / f'{prompt_name}.md'

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' not found for project '{project_name}'. "
                f"Expected at: {prompt_path}"
            )

        return prompt_path.read_text()

    def project_exists(self, name: str) -> bool:
        """Check if a project exists."""
        return name in self.list_projects()

    def clear_cache(self) -> None:
        """Clear the project cache (useful for testing)."""
        self._cache.clear()


def _find_projects_dir() -> Path:
    """
    Find the projects directory.

    Searches in order:
    1. Package directory / projects (relative to this file)
    2. Current working directory / projects (fallback)

    Returns:
        Path to projects directory
    """
    # Try relative to package first (src/claude_redditor/projects/)
    package_projects = Path(__file__).parent / 'projects'
    if package_projects.exists():
        return package_projects

    # Fallback to current working directory
    cwd_projects = Path.cwd() / 'projects'
    if cwd_projects.exists():
        return cwd_projects

    # Default to package location
    return package_projects


# Global project loader instance
project_loader = ProjectLoader(_find_projects_dir())
