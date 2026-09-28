"""Where the data lives: the repo checkout when run from one, else a user cache dir."""
import os
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parent


def root() -> Path:
    if os.getenv("SHADCN_EXPLORER_HOME"):
        return Path(os.environ["SHADCN_EXPLORER_HOME"]).expanduser()
    if (REPO / "AGENTS.md").exists() and (REPO / "data" / "artifacts.json").exists():
        return REPO                                   # running from a clone
    cache = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache / "shadcn-registry-explorer"


def data(*parts) -> Path:
    return root() / "data" / Path(*parts)


def manifest() -> Path:
    """The repo's manifest in a clone; the copy bundled into the wheel otherwise."""
    p = data("artifacts.json")
    return p if p.exists() else PKG / "artifacts.json"


def load_env():
    """OPENAI_API_KEY from the environment, else from <root>/.env."""
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(root() / ".env")
    except ImportError:
        pass
