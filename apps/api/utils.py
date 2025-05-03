import os

from urllib.parse import urlparse, urlunparse

def get_database_url():
    return os.getenv("DATABASE_URL")
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise ValueError("DATABASE_URL is not set in environment variables.")

    try:
        with open("/proc/1/cgroup", "rt") as f:
            in_docker = "docker" in f.read()
    except Exception:
        in_docker = False

    parsed = urlparse(raw_url)
    hostname = "db" if in_docker else "localhost"
    fixed = parsed._replace(netloc=f"{parsed.username}:{parsed.password}@{hostname}:{parsed.port}")
    return urlunparse(fixed)

