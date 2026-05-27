#!/usr/bin/env python3
"""
GitHub Monitor Web Viewer
A simple Flask-based web application to visualize SQLite database data.
"""

from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
DB_PATH = 'github_monitor.db'


def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_timestamp(ts_str):
    """Format ISO timestamp to readable format."""
    try:
        if 'T' in ts_str:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        return ts_str
    except:
        return ts_str


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """Get overall statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total repositories
    cursor.execute('SELECT COUNT(*) as count FROM repositories')
    total_repos = cursor.fetchone()['count']
    
    # Total updates
    cursor.execute('SELECT COUNT(*) as count FROM updates')
    total_updates = cursor.fetchone()['count']
    
    # Updates today
    cursor.execute('''
        SELECT COUNT(*) as count FROM updates 
        WHERE date(check_timestamp) = date('now')
    ''')
    updates_today = cursor.fetchone()['count']
    
    # Most active repository
    cursor.execute('''
        SELECT repo_name, COUNT(*) as update_count 
        FROM updates 
        GROUP BY repo_name 
        ORDER BY update_count DESC 
        LIMIT 1
    ''')
    most_active = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'total_repos': total_repos,
        'total_updates': total_updates,
        'updates_today': updates_today,
        'most_active': dict(most_active) if most_active else None
    })


@app.route('/api/repositories')
def get_repositories():
    """Get all repositories with their update counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            r.id,
            r.repo_name,
            r.first_checked_at,
            r.last_checked_at,
            COUNT(u.id) as update_count
        FROM repositories r
        LEFT JOIN updates u ON r.id = u.repo_id
        GROUP BY r.id
        ORDER BY r.repo_name
    ''')
    
    repos = []
    for row in cursor.fetchall():
        repos.append({
            'id': row['id'],
            'repo_name': row['repo_name'],
            'first_checked_at': format_timestamp(row['first_checked_at']),
            'last_checked_at': format_timestamp(row['last_checked_at']),
            'update_count': row['update_count']
        })
    
    conn.close()
    return jsonify(repos)


@app.route('/api/updates')
def get_updates():
    """Get recent updates."""
    limit = 50
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id,
            repo_name,
            update_timestamp,
            check_timestamp,
            is_first_run
        FROM updates
        ORDER BY check_timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    updates = []
    for row in cursor.fetchall():
        updates.append({
            'id': row['id'],
            'repo_name': row['repo_name'],
            'update_timestamp': format_timestamp(row['update_timestamp']),
            'check_timestamp': format_timestamp(row['check_timestamp']),
            'is_first_run': bool(row['is_first_run'])
        })
    
    conn.close()
    return jsonify(updates)


@app.route('/api/repository/<int:repo_id>')
def get_repository_details(repo_id):
    """Get detailed information about a specific repository."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get repository info
    cursor.execute('SELECT * FROM repositories WHERE id = ?', (repo_id,))
    repo = cursor.fetchone()
    
    if not repo:
        conn.close()
        return jsonify({'error': 'Repository not found'}), 404
    
    # Get updates for this repository
    cursor.execute('''
        SELECT * FROM updates 
        WHERE repo_id = ? 
        ORDER BY check_timestamp DESC
    ''', (repo_id,))
    
    updates = []
    for row in cursor.fetchall():
        updates.append({
            'id': row['id'],
            'update_timestamp': format_timestamp(row['update_timestamp']),
            'check_timestamp': format_timestamp(row['check_timestamp']),
            'is_first_run': bool(row['is_first_run'])
        })
    
    conn.close()
    
    return jsonify({
        'repository': {
            'id': repo['id'],
            'repo_name': repo['repo_name'],
            'first_checked_at': format_timestamp(repo['first_checked_at']),
            'last_checked_at': format_timestamp(repo['last_checked_at'])
        },
        'updates': updates
    })


@app.route('/api/timeline')
def get_timeline():
    """Get update timeline data for visualization."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            date(check_timestamp) as date,
            COUNT(*) as count
        FROM updates
        GROUP BY date(check_timestamp)
        ORDER BY date DESC
        LIMIT 30
    ''')
    
    timeline = []
    for row in cursor.fetchall():
        timeline.append({
            'date': row['date'],
            'count': row['count']
        })
    
    conn.close()
    return jsonify(timeline)


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found!")
        print("Please run github_monitor.py first to create the database.")
        exit(1)
    
    print("=" * 60)
    print("GitHub Monitor Web Viewer")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print("Starting server...")
    print("Open your browser at: http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Use port 5001 to avoid macOS AirDrop conflict on port 5000
    app.run(debug=True, host='127.0.0.1', port=5001)

# Made with Bob
