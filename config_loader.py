"""Load configuration from config.yaml and environment variables."""

import os
import sys
from pathlib import Path

import yaml


def load_config():
    """Load config from config.yaml, with env var overrides for credentials."""
    config_path = Path(__file__).resolve().parent / "config.yaml"
    if not config_path.exists():
        print("ERROR: config.yaml not found.")
        print("Copy config.example.yaml to config.yaml and fill in your values.")
        sys.exit(1)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Environment variables override config file for credentials
    jira = cfg.get("jira", {})
    jira["url"] = os.environ.get("JIRA_URL", jira.get("url", "")).rstrip("/")
    jira["username"] = os.environ.get("JIRA_USERNAME", jira.get("username", ""))
    jira["api_token"] = os.environ.get("JIRA_API_TOKEN", jira.get("api_token", ""))

    if not jira["url"] or not jira["username"] or not jira["api_token"]:
        print("ERROR: Jira credentials not configured.")
        print("Set JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN as environment variables")
        print("or fill them in config.yaml.")
        sys.exit(1)

    cfg["jira"] = jira
    return cfg
