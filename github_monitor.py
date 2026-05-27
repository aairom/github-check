#!/usr/bin/env python3
"""
GitHub Repository Monitor
Monitors GitHub repositories for updates and logs them to SQLite database.
"""

import sqlite3
import requests
import json
import time
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class GitHubMonitor:
    """Main class for monitoring GitHub repositories."""
    
    def __init__(self, db_path: str = "github_monitor.db", 
                 repos_file: str = "input/repositories.txt",
                 check_days: int = 1):
        """
        Initialize the GitHub Monitor.
        
        Args:
            db_path: Path to SQLite database
            repos_file: Path to file containing repository list
            check_days: Number of days to check for updates (0=today, 1=today+yesterday)
        """
        self.db_path = db_path
        self.repos_file = repos_file
        self.check_days = check_days
        self.github_token = os.getenv('GITHUB_TOKEN')  # Optional: for higher rate limits
        self.session = requests.Session()
        
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT UNIQUE NOT NULL,
                first_checked_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                repo_name TEXT NOT NULL,
                update_timestamp TEXT NOT NULL,
                pushed_at TEXT NOT NULL,
                check_timestamp TEXT NOT NULL,
                is_first_run BOOLEAN NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_repo_name ON repositories(repo_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_update_timestamp ON updates(update_timestamp)
        ''')
        
        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {self.db_path}")
    
    def _read_repositories(self) -> List[str]:
        """
        Read repository list from input file.
        
        Returns:
            List of repository names in format 'owner/repo'
        """
        if not os.path.exists(self.repos_file):
            print(f"✗ Repository file not found: {self.repos_file}")
            print(f"  Please create the file and add repositories (one per line)")
            print(f"  Format: owner/repo (e.g., torvalds/linux)")
            return []
        
        repos = []
        with open(self.repos_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    repos.append(line)
        
        return repos
    
    def _get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """
        Fetch repository information from GitHub API.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            
        Returns:
            Dictionary with repo info or None if error
        """
        url = f"https://api.github.com/repos/{repo_name}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"✗ Repository not found: {repo_name}")
                return None
            elif response.status_code == 403:
                print(f"✗ Rate limit exceeded. Consider using GITHUB_TOKEN environment variable.")
                return None
            else:
                print(f"✗ Error fetching {repo_name}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error fetching {repo_name}: {e}")
            return None
    
    def _is_repo_in_db(self, repo_name: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Check if repository exists in database.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Tuple of (exists, repo_id, last_update_time)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, last_checked_at FROM repositories WHERE repo_name = ?
        ''', (repo_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, result[0], result[1]
        return False, None, None
    
    def _add_repository(self, repo_name: str, pushed_at: str) -> int:
        """
        Add new repository to database.
        
        Args:
            repo_name: Repository name
            pushed_at: Last push timestamp from GitHub
            
        Returns:
            Repository ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO repositories (repo_name, first_checked_at, last_checked_at)
            VALUES (?, ?, ?)
        ''', (repo_name, now, pushed_at))
        
        repo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # lastrowid should always be an int after INSERT, but type checker needs assurance
        if repo_id is None:
            raise ValueError(f"Failed to insert repository: {repo_name}")
        
        return repo_id
    
    def _log_update(self, repo_id: int, repo_name: str, pushed_at: str, is_first_run: bool):
        """
        Log repository update to database.
        
        Args:
            repo_id: Repository ID
            repo_name: Repository name
            pushed_at: Last push timestamp from GitHub
            is_first_run: Whether this is the first time checking this repo
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO updates (repo_id, repo_name, update_timestamp, pushed_at, 
                               check_timestamp, is_first_run)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (repo_id, repo_name, pushed_at, pushed_at, now, is_first_run))
        
        # Update last_checked_at in repositories table
        cursor.execute('''
            UPDATE repositories SET last_checked_at = ? WHERE id = ?
        ''', (pushed_at, repo_id))
        
        conn.commit()
        conn.close()
    
    def _has_recent_update(self, pushed_at_str: str) -> bool:
        """
        Check if the push timestamp is within the check window.
        
        Args:
            pushed_at_str: ISO format timestamp string
            
        Returns:
            True if within check window
        """
        pushed_at = datetime.fromisoformat(pushed_at_str.replace('Z', '+00:00'))
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.check_days)
        
        return pushed_at >= cutoff
    
    def check_repositories(self):
        """Main method to check all repositories for updates."""
        repos = self._read_repositories()
        
        if not repos:
            print("✗ No repositories to check")
            return
        
        print(f"\n{'='*60}")
        print(f"GitHub Repository Monitor")
        print(f"{'='*60}")
        print(f"Checking {len(repos)} repositories...")
        print(f"Check window: Last {self.check_days} day(s)")
        print(f"{'='*60}\n")
        
        updates_found = 0
        new_repos = 0
        
        for repo_name in repos:
            print(f"Checking: {repo_name}")
            
            # Get repo info from GitHub
            repo_info = self._get_repo_info(repo_name)
            
            if not repo_info:
                continue
            
            pushed_at = repo_info.get('pushed_at')
            
            if not pushed_at:
                print(f"  ⚠ No push timestamp available")
                continue
            
            # Check if repo is in database
            exists, repo_id, last_checked = self._is_repo_in_db(repo_name)
            
            if not exists:
                # First time seeing this repo
                repo_id = self._add_repository(repo_name, pushed_at)
                self._log_update(repo_id, repo_name, pushed_at, is_first_run=True)
                print(f"  ✓ New repository logged (ID: {repo_id})")
                print(f"    Last push: {pushed_at}")
                new_repos += 1
            else:
                # repo_id is guaranteed to be not None here
                if repo_id is None:
                    print(f"  ✗ Database error: repo_id is None")
                    continue
                    
                # Check if there's a recent update
                if self._has_recent_update(pushed_at):
                    # Check if this is a new update since last check
                    if pushed_at != last_checked:
                        self._log_update(repo_id, repo_name, pushed_at, is_first_run=False)
                        print(f"  🔔 UPDATE DETECTED!")
                        print(f"    Previous: {last_checked}")
                        print(f"    Current:  {pushed_at}")
                        updates_found += 1
                    else:
                        print(f"  ✓ Already logged (no new changes)")
                else:
                    print(f"  ✓ No recent updates")
                    print(f"    Last push: {pushed_at}")
            
            print()
            time.sleep(0.5)  # Be nice to GitHub API
        
        print(f"{'='*60}")
        print(f"Summary:")
        print(f"  New repositories: {new_repos}")
        print(f"  Updates found: {updates_found}")
        print(f"{'='*60}\n")
    
    def generate_report(self, output_file: Optional[str] = None):
        """
        Generate a report of all monitored repositories and their updates.
        
        Args:
            output_file: Optional path to save report
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all repositories
        cursor.execute('''
            SELECT r.repo_name, r.first_checked_at, r.last_checked_at,
                   COUNT(u.id) as update_count
            FROM repositories r
            LEFT JOIN updates u ON r.id = u.repo_id
            GROUP BY r.id
            ORDER BY r.repo_name
        ''')
        
        repos = cursor.fetchall()
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GitHub Repository Monitor - Report")
        report_lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        for repo_name, first_checked, last_checked, update_count in repos:
            report_lines.append(f"Repository: {repo_name}")
            report_lines.append(f"  First checked: {first_checked}")
            report_lines.append(f"  Last update:   {last_checked}")
            report_lines.append(f"  Total updates: {update_count}")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("Recent Updates (Last 10)")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        cursor.execute('''
            SELECT repo_name, update_timestamp, check_timestamp, is_first_run
            FROM updates
            ORDER BY check_timestamp DESC
            LIMIT 10
        ''')
        
        updates = cursor.fetchall()
        
        for repo_name, update_ts, check_ts, is_first in updates:
            status = "FIRST RUN" if is_first else "UPDATE"
            report_lines.append(f"[{status}] {repo_name}")
            report_lines.append(f"  Updated: {update_ts}")
            report_lines.append(f"  Checked: {check_ts}")
            report_lines.append("")
        
        conn.close()
        
        report = "\n".join(report_lines)
        
        if output_file:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = f"output/{timestamp}_{output_file}"
            os.makedirs("output", exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"✓ Report saved to: {output_path}")
        
        print(report)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor GitHub repositories for updates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Check repositories (default: last 1 day)
  python github_monitor.py
  
  # Check for updates in the last 2 days
  python github_monitor.py --days 2
  
  # Generate a report
  python github_monitor.py --report
  
  # Use custom database and repository file
  python github_monitor.py --db custom.db --repos custom_repos.txt
  
Environment Variables:
  GITHUB_TOKEN    Optional GitHub personal access token for higher rate limits
        '''
    )
    
    parser.add_argument('--db', default='github_monitor.db',
                       help='Path to SQLite database (default: github_monitor.db)')
    parser.add_argument('--repos', default='input/repositories.txt',
                       help='Path to repositories file (default: input/repositories.txt)')
    parser.add_argument('--days', type=int, default=1,
                       help='Number of days to check for updates (default: 1)')
    parser.add_argument('--report', action='store_true',
                       help='Generate a report of all repositories')
    parser.add_argument('--output', default='report.txt',
                       help='Output filename for report (default: report.txt)')
    
    args = parser.parse_args()
    
    monitor = GitHubMonitor(
        db_path=args.db,
        repos_file=args.repos,
        check_days=args.days
    )
    
    if args.report:
        monitor.generate_report(args.output)
    else:
        monitor.check_repositories()


if __name__ == '__main__':
    main()

# Made with Bob
