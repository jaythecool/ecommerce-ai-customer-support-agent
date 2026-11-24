import sqlite3
from pathlib import Path

# Store the demo database alongside this file
DB_PATH = Path(__file__).parent / "demo_orders.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create demo database and sample orders if they don't exist."""

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                order_purchase_timestamp TEXT,
                order_delivered_customer_date TEXT,
                order_estimated_delivery_date TEXT,
                order_status TEXT
            )
        """)

        # Sample orders are inserted only if the database is empty
        count = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        if count == 0:
            sample_orders = [
                ("1001", "2026-11-20", None, "2026-11-27", "shipped"),
                ("1002", "2026-11-21", None, "2026-11-28", "processing"),
                ("1003", "2026-11-15", "2026-11-19", "2026-11-20", "delivered"),
                ("1004", "2026-11-22", None, "2026-11-30", "processing"),
                ("1005", "2026-11-18", None, "2026-11-25", "canceled"),
            ]

            connection.executemany("""
                INSERT INTO orders (
                    order_id,
                    order_purchase_timestamp,
                    order_delivered_customer_date,
                    order_estimated_delivery_date,
                    order_status
                )
                VALUES (?, ?, ?, ?, ?)
            """, sample_orders)


# Initialize database automatically
initialize_database()


# Get order status
def get_order_status(order_id):
    query = """
        SELECT order_id,
               order_purchase_timestamp,
               order_delivered_customer_date,
               order_estimated_delivery_date,
               order_status
        FROM orders
        WHERE order_id = ?
    """

    with get_connection() as connection:
        order = connection.execute(query, (order_id,)).fetchone()

        if not order:
            return "Order not found!"

        return dict(order)


# Cancel order
def cancel_order(order_id):
    with get_connection() as connection:
        order = connection.execute("""
            SELECT order_status
            FROM orders
            WHERE order_id = ?
        """, (order_id,)).fetchone()

        if not order:
            return "Order not found!"

        status = order["order_status"]

        if status == "delivered":
            return "Order cannot be cancelled because it is already delivered."

        if status == "canceled":
            return "Order already cancelled."

        connection.execute("""
            UPDATE orders
            SET order_status = 'canceled'
            WHERE order_id = ?
        """, (order_id,))

        return "Order cancelled successfully!"
