import os
import mysql.connector as mysql
from contextlib import closing
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create a MySQL connection using environment variables."""

    db_config = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }

    return mysql.connect(**db_config)


# Get order status
def get_order_status(order_id):

    query = """
        SELECT order_id,
               order_purchase_timestamp,
               order_delivered_customer_date,
               order_estimated_delivery_date,
               order_status
        FROM orders
        WHERE order_id = %s
    """

    with closing(get_connection()) as connection:
        with closing(connection.cursor()) as cursor:

            cursor.execute(query, (order_id,))
            order = cursor.fetchone()

            if not order:
                return "Order not found!"

            return {
                "order_id": order[0],
                "order_purchase_timestamp": order[1],
                "order_delivered_customer_date": order[2],
                "order_estimated_delivery_date": order[3],
                "order_status": order[4]
            }


# Cancel order
def cancel_order(order_id):

    select_query = """
        SELECT order_status
        FROM orders
        WHERE order_id = %s
    """

    update_query = """
        UPDATE orders
        SET order_status = 'canceled'
        WHERE order_id = %s
    """

    with closing(get_connection()) as connection:
        with closing(connection.cursor()) as cursor:

            cursor.execute(select_query, (order_id,))
            order = cursor.fetchone()

            if not order:
                return "Order not found!"

            status = order[0]

            if status == "delivered":
                return "Order cannot be cancelled because it is already delivered."

            if status == "canceled":
                return "Order already cancelled."

            cursor.execute(update_query, (order_id,))
            connection.commit()

            return "Order cancelled successfully!"
