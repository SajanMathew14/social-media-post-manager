"""
Database connection status tracking
"""

# Global variable to track database status
database_connected = False


def set_database_status(status: bool):
    """Set the database connection status"""
    global database_connected
    database_connected = status


def get_database_status() -> bool:
    """Get the current database connection status"""
    return database_connected
