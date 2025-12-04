#!/usr/bin/env python3
"""
Database migration script to add multi-tenant support to the calendar application.
This script adds a user_id column to existing calendar events.

Usage:
    python migrate_multitenant.py [--db-path PATH] [--default-user USER]

Options:
    --db-path PATH         Path to the SQLite database file (default: CalendarDB.db)
    --default-user USER    Default user ID to assign to existing events (default: 'admin')
"""

import sqlite3
import argparse
import os
import sys

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database(db_path, default_user='admin'):
    """Add user_id column to calendar table and assign default user to existing events."""

    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}")
        print("Creating new database with multi-tenant support...")
        # Create new database - the schema will be created by the application
        return True

    print(f"Migrating database: {db_path}")

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if user_id column already exists
        if check_column_exists(cursor, 'calendar', 'user_id'):
            print("✓ user_id column already exists - no migration needed")
            conn.close()
            return True

        print("Adding user_id column to calendar table...")

        # Add user_id column
        cursor.execute("ALTER TABLE calendar ADD COLUMN user_id TEXT")

        # Count existing events
        cursor.execute("SELECT COUNT(*) FROM calendar")
        event_count = cursor.fetchone()[0]

        if event_count > 0:
            print(f"Found {event_count} existing events")
            print(f"Assigning default user '{default_user}' to existing events...")

            # Assign default user to all existing events
            cursor.execute("UPDATE calendar SET user_id = ? WHERE user_id IS NULL", (default_user,))

            print(f"✓ Updated {cursor.rowcount} events with default user")
        else:
            print("No existing events found - database is empty")

        # Commit changes
        conn.commit()
        conn.close()

        print("✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Rebuild and deploy the calendar-api container image")
        print("2. Deploy with OAuth proxy enabled for multi-tenant access")
        print("3. Users will now see only their own calendar events")

        return True

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Migrate calendar database to support multi-tenancy"
    )
    parser.add_argument(
        '--db-path',
        default='CalendarDB.db',
        help='Path to the SQLite database file (default: CalendarDB.db)'
    )
    parser.add_argument(
        '--default-user',
        default='admin',
        help='Default user ID to assign to existing events (default: admin)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Calendar Database Multi-Tenant Migration")
    print("=" * 70)
    print()

    success = migrate_database(args.db_path, args.default_user)

    print()
    print("=" * 70)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
