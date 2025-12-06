#!/usr/bin/env python3
"""ALM Orchestrator - Jira + Claude Code + GitHub integration daemon."""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from alm_orchestrator.config import Config, ConfigError
from alm_orchestrator.daemon import Daemon


def setup_logging(verbose: bool = False, logs_dir: str = "logs") -> None:
    """Configure dual logging: console + CSV file.

    Args:
        verbose: If True, console shows DEBUG level.
        logs_dir: Directory for log files.
    """
    # Create logs directory if needed
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = Path(logs_dir) / f"run-{timestamp}.csv"

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all, handlers filter

    # Console handler - CSV format for easy review
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s,%(levelname)s,%(name)s,%(message)s",
        datefmt="%H:%M:%S"
    ))
    root_logger.addHandler(console_handler)

    # File handler - CSV format, DEBUG level
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s,%(levelname)s,%(name)s,%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root_logger.addHandler(file_handler)

    logging.info(f"Logging to: {log_file}")


def get_prompts_dir() -> str:
    """Get path to prompts directory."""
    # Look relative to this file
    this_dir = Path(__file__).parent
    prompts_dir = this_dir / "prompts"
    if prompts_dir.exists():
        return str(prompts_dir)

    # Fall back to current directory
    return str(Path.cwd() / "prompts")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ALM Orchestrator - Poll Jira for AI labels and invoke Claude Code"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        help="Override poll interval in seconds (default: from env or 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Poll once and exit without processing",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--logs-dir",
        type=str,
        default="logs",
        help="Directory for log files (default: logs)",
    )

    args = parser.parse_args()

    setup_logging(args.verbose, args.logs_dir)
    logger = logging.getLogger(__name__)

    # Load environment variables
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
        logger.info(f"Loaded environment from {args.env_file}")

    # Override poll interval if specified
    if args.poll_interval:
        os.environ["POLL_INTERVAL_SECONDS"] = str(args.poll_interval)

    try:
        config = Config.from_env()
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    prompts_dir = get_prompts_dir()
    if not os.path.exists(prompts_dir):
        logger.error(f"Prompts directory not found: {prompts_dir}")
        return 1

    logger.info(f"Using prompts from: {prompts_dir}")

    daemon = Daemon(config, prompts_dir)

    if args.dry_run:
        logger.info("Dry run mode - polling once")
        issues_found = daemon.poll_once()
        logger.info(f"Found {issues_found} issues with AI labels")
        return 0

    daemon.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
