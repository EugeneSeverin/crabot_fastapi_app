from typing import Optional, Any, List
from enum import Enum
from uuid import UUID, uuid4
import json
import logging
from infrastructure.db.mysql.base import SyncDatabase
from collections import defaultdict

class DBSchema(str, Enum):
    ADVERT_API = "advert_api"

class DBController:
    def __init__(self, db: SyncDatabase):
        self.db = db


    def get_current_stocks(self, warehouse_from_ids) -> Optional[Any]:
        """Returns cache is available"""

        placeholders = ','.join(['%s'] * len(warehouse_from_ids))

        # query = f"""WITH latest_stock AS (
        #                 SELECT s.*
        #                 FROM mp_data.a_wb_stocks s
        #                 INNER JOIN (
        #                     SELECT nmId, MAX(time_beg) AS max_time_beg
        #                     FROM mp_data.a_wb_stocks
        #                     GROUP BY nmId) AS latest
        #                 ON s.nmId = latest.nmId AND s.time_beg = latest.max_time_beg
        #                 WHERE s.time_end >= NOW() - INTERVAL 24 HOUR)
        #             SELECT
        #                 a.article_name,
        #                 s.nmId AS wb_article_id,
        #                 sz.size,
        #                 s.quantity AS stock_from,
        #                 0 AS stock_to,
        #                 0 AS on_the_way
        #             FROM latest_stock s
        #             LEFT JOIN mp_data.a_wb_article a ON a.wb_article_id = s.nmId
        #             LEFT JOIN mp_data.a_wb_izd_size sz ON sz.size_id = s.techSize_id
        #             LEFT JOIN mp_data.a_wb_warehouseName awwn ON s.warehouseName_id = awwn.warehouse_id
        #             WHERE awwn.warehouse_wb_id in ({placeholders});"""
        
        query = f"""WITH latest_stock AS (
                        SELECT s.*
                        FROM mp_data.a_wb_catalog_stocks s
                        INNER JOIN (
                            SELECT wb_article_id, MAX(time_end) AS max_time_end
                            FROM mp_data.a_wb_catalog_stocks
                            GROUP BY wb_article_id) AS latest
                        ON s.wb_article_id = latest.wb_article_id AND s.time_end = latest.max_time_end)
                    SELECT
                        a.article_name,
                        s.wb_article_id AS wb_article_id,
                        sz.size,
                        s.qty AS stock_from,
                        0 AS stock_to,
                        0 AS on_the_way
                    FROM latest_stock s
                    LEFT JOIN mp_data.a_wb_article a ON a.wb_article_id = s.wb_article_id
                    LEFT JOIN mp_data.a_wb_izd_size sz ON sz.size_id = s.size_id
                    LEFT JOIN mp_data.a_wb_warehouseName awwn ON s.warehouse_id = awwn.warehouse_id   
                    WHERE time_end > DATE_SUB(CURRENT_DATE(), INTERVAL 1 HOUR) AND s.warehouse_id in ({placeholders});"""
        try:

            params = tuple(warehouse_from_ids)
            rows = self.db.execute_query(query, params)

            grouped = defaultdict(lambda: {"sizes": []})

            for row in rows:
                key = (row["article_name"], row["wb_article_id"])
                grouped[key]["sizes"].append({
                    "size": row["size"],
                    "stock_from": row["stock_from"],
                    "stock_to": row["stock_to"],
                    "on_the_way": row["on_the_way"]
                })

            result = []
            for (article_name, wb_article_id), data in grouped.items():
                result.append({
                    "article_name": article_name,
                    "wb_article_id": wb_article_id,
                    "sizes": data["sizes"]
                })

            return result

        except Exception as e:
            logging.error(f"Failed to fetch cache: {e}")
            return None
        

    def get_all_regions(self):

        query = "SELECT region_id, region_name name FROM mp_data.a_wb_stock_transfer_wb_regions"


        try:
            rows = self.db.execute_query(query)
            return rows

        except Exception as e:
            logging.error(f"Failed to fetch cache: {e}")
            return None
        

    def get_all_warehouses(self):

        query = """SELECT wb_office_id as warehouse_id, 
                        warehouse_name name, region_id 
                    FROM mp_data.a_wb_stock_transfer_wb_warehourses WHERE wb_office_id IS NOT NULL"""

        try:
            rows = self.db.execute_query(query)
            return rows

        except Exception as e:
            logging.error(f"Failed to fetch cache: {e}")
            return None
        


    def create_new_task(self, new_task_data):
        try:
            insert_query = """
                INSERT INTO mp_data.a_wb_stock_transfer_one_time_tasks 
                (warehouses_from_ids, warehouses_to_ids, task_status, is_archived) 
                VALUES (%s, %s, %s, %s)"""

            warehouses_from_json = json.dumps(new_task_data["warehouse_from_ids"])
            warehouses_to_json = json.dumps(new_task_data["warehouse_to_ids"])

            params = (
                warehouses_from_json,
                warehouses_to_json,
                0,  # task_status
                0   # is_archived
            )

            conn = self.db.connect()
            with conn.cursor() as cursor:
                cursor.execute(insert_query, params)
                conn.commit()

                cursor.execute("SELECT LAST_INSERT_ID()")
                result = cursor.fetchone()
                return list(result.values())[0] if result else None

        except Exception as e:
            logging.error(f"Failed to create new task: {e}")
            raise



    def get_tasks(self, start_date: str, end_date: str, only_active: bool):
        try:
            base_query = """WITH task_product_qty AS (
                                    SELECT p.task_id,
                                        COUNT(p.transfer_qty) as positions_total,
                                        SUM(p.transfer_qty) as quantity_total,
                                        SUM(p.transfer_qty_left) as quantity_left
                                        FROM mp_data.a_wb_stock_transfer_products_to_one_time_tasks p
                                        GROUP BY p.task_id)
                            SELECT 
                                tasks.task_id,
                                warehouses_from_ids,
                                warehouses_to_ids,
                                task_status,
                                is_archived,
                                task_creation_date,
                                task_archiving_date,
                                last_change_date,
                                tpq.*
                            FROM mp_data.a_wb_stock_transfer_one_time_tasks tasks
                            LEFT JOIN task_product_qty tpq 
                            ON tpq.task_id = tasks.task_id
                            WHERE task_creation_date BETWEEN %s AND %s"""

            params = [start_date, end_date]

            if only_active:
                base_query += " AND is_archived = 0"

            base_query += " ORDER BY task_creation_date DESC"

            rows = self.db.execute_query(base_query, params)
            return rows

        except Exception as e:
            logging.error(f"Failed to get tasks: {e}")
            raise


    def get_task_products_by_task_id(self, task_id: int):
        try:
            query = """
                SELECT 
                    p.product_wb_id, 
                    sz.size, 
                    p.transfer_qty AS quantity
                FROM mp_data.a_wb_stock_transfer_products_to_one_time_tasks p
                LEFT JOIN mp_data.a_wb_izd_size sz ON p.size_id = sz.size_id
                WHERE p.task_id = %s AND p.is_archived = 0
            """
            params = (task_id,)
            rows = self.db.execute_query(query, params)
            return rows
        except Exception as e:
            logging.error(f"Failed to get task products by task_id {task_id}: {e}")
            raise


    def update_task_products(self, task_id: int, products: List[dict]):
        try:
            conn = self.db.connect()
            with conn.cursor() as cursor:
                # 1. Архивируем старые записи
                archive_query = """
                    UPDATE mp_data.a_wb_stock_transfer_products_to_one_time_tasks
                    SET is_archived = 1
                    WHERE task_id = %s AND is_archived = 0
                """
                cursor.execute(archive_query, (task_id,))

                # 2. Вставляем новые записи
                insert_query = """
                    INSERT INTO mp_data.a_wb_stock_transfer_products_to_one_time_tasks
                    (task_id, product_wb_id, size_id, transfer_qty, transfer_qty_left, is_archived)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """

                for product in products:
                    cursor.execute(insert_query, (
                        task_id,
                        product["product_id"],
                        int(product["size"]),  # size здесь — это size_id
                        product["quantity"],
                        product["quantity"],  # transfer_qty_left = transfer_qty при создании
                        0  # is_archived
                    ))

                conn.commit()

        except Exception as e:
            logging.error(f"Failed to update task products for task_id {task_id}: {e}")
            raise