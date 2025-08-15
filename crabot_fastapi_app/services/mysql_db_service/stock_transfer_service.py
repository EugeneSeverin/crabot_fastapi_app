from typing import Optional, Any, List, Dict, Tuple
from enum import Enum
import json
import logging
from collections import defaultdict

from infrastructure.db.mysql.base import SyncDatabase


class DBSchema(str, Enum):
    ADVERT_API = "advert_api"


class DBController:
    def __init__(self, db: SyncDatabase):
        self.db = db

    
    # ---------- МАППИНГ РЕГИОНОВ -> КОЛОНКИ ----------
    # ключи — ровно как в UI/Excel
    _REGION_COLS: Dict[str, Tuple[str, str]] = {
        "Центральный":        ("target_central",       "min_central"),
        "Северо-Западный":    ("target_north_west",    "min_north_west"),
        "Приволжский":        ("target_volga",         "min_volga"),
        "Южный":              ("target_south",         "min_south"),
        "Уральский":          ("target_urals",         "min_urals"),
        "Сибирский":          ("target_siberia",       "min_siberia"),
        "Северо-Кавказский":  ("target_north_caucasus","min_north_caucasus"),
        "Дальневосточный":    ("target_far_east",      "min_far_east"),
    }

    # -------- Текущие остатки
    def get_current_stocks(self, warehouse_from_ids: List[int]) -> Optional[Any]:
        """Возвращает актуальные остатки по списку складов."""
        try:
            if not warehouse_from_ids:
                return []

            placeholders = ",".join(["%s"] * len(warehouse_from_ids))
            query = f"""
                WITH latest_stock AS (
                    SELECT s.*
                    FROM mp_data.a_wb_catalog_stocks s
                    INNER JOIN (
                        SELECT wb_article_id, MAX(time_end) AS max_time_end
                        FROM mp_data.a_wb_catalog_stocks
                        GROUP BY wb_article_id
                    ) AS latest
                    ON s.wb_article_id = latest.wb_article_id
                    AND s.time_end = latest.max_time_end
                )
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
                WHERE s.time_end > DATE_SUB(CURRENT_DATE(), INTERVAL 1 HOUR)
                  AND s.warehouse_id IN ({placeholders});
            """

            rows = self.db.execute_query(query, tuple(warehouse_from_ids))

            grouped = defaultdict(lambda: {"sizes": []})
            for row in rows:
                key = (row["article_name"], row["wb_article_id"])
                grouped[key]["sizes"].append({
                    "size": row["size"],
                    "stock_from": row["stock_from"],
                    "stock_to": row["stock_to"],
                    "on_the_way": row["on_the_way"],
                })

            result = []
            for (article_name, wb_article_id), data in grouped.items():
                result.append({
                    "article_name": article_name,
                    "wb_article_id": wb_article_id,
                    "sizes": data["sizes"],
                })

            return result

        except Exception as e:
            logging.error(f"Failed to fetch current stocks: {e}")
            return None

    # -------- Справочники
    def get_all_regions(self):
        try:
            query = "SELECT region_id, region_name AS name FROM mp_data.a_wb_stock_transfer_wb_regions"
            return self.db.execute_query(query)
        except Exception as e:
            logging.error(f"Failed to get regions: {e}")
            return None

    def get_all_warehouses(self):
        try:
            query = """
                SELECT wb_office_id AS warehouse_id,
                       warehouse_name AS name,
                       region_id
                FROM mp_data.a_wb_stock_transfer_wb_warehourses
                WHERE wb_office_id IS NOT NULL
            """
            return self.db.execute_query(query)
        except Exception as e:
            logging.error(f"Failed to get warehouses: {e}")
            return None

    # -------- Задания
    def create_new_task(self, new_task_data):
        try:
            insert_query = """
                INSERT INTO mp_data.a_wb_stock_transfer_one_time_tasks
                (warehouses_from_ids, warehouses_to_ids, task_status, is_archived)
                VALUES (%s, %s, %s, %s)
            """
            warehouses_from_json = json.dumps(new_task_data["warehouse_from_ids"])
            warehouses_to_json = json.dumps(new_task_data["warehouse_to_ids"])
            params = (warehouses_from_json, warehouses_to_json, 0, 0)

            # вставка
            self.db.execute_non_query(insert_query, params)
            # получить id
            task_id = self.db.execute_scalar("SELECT LAST_INSERT_ID()")
            return task_id
        except Exception as e:
            logging.error(f"Failed to create new task: {e}")
            raise

    def get_tasks(self, start_date: str, end_date: str, only_active: bool):
        try:
            base_query = """
                WITH task_product_qty AS (
                    SELECT p.task_id,
                           COUNT(p.transfer_qty) AS positions_total,
                           SUM(p.transfer_qty)   AS quantity_total,
                           SUM(p.transfer_qty_left) AS quantity_left
                    FROM mp_data.a_wb_stock_transfer_products_to_one_time_tasks p
                    GROUP BY p.task_id
                )
                SELECT
                    tasks.task_id,
                    warehouses_from_ids,
                    warehouses_to_ids,
                    task_status,
                    is_archived,
                    task_creation_date,
                    task_archiving_date,
                    last_change_date,
                    tpq.positions_total,
                    tpq.quantity_total,
                    tpq.quantity_left
                FROM mp_data.a_wb_stock_transfer_one_time_tasks tasks
                LEFT JOIN task_product_qty tpq
                  ON tpq.task_id = tasks.task_id
                WHERE task_creation_date BETWEEN %s AND %s
            """
            params: List[Any] = [start_date, end_date]
            if only_active:
                base_query += " AND is_archived = 0 AND task_status != 2"
            base_query += " ORDER BY task_creation_date DESC"

            return self.db.execute_query(base_query, params)
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
            return self.db.execute_query(query, (task_id,))
        except Exception as e:
            logging.error(f"Failed to get task products by task_id {task_id}: {e}")
            raise

    def update_task_products(self, task_id: int, products: List[dict]):
        try:
            # 1) Архивируем текущие
            archive_query = """
                UPDATE mp_data.a_wb_stock_transfer_products_to_one_time_tasks
                SET is_archived = 1
                WHERE task_id = %s AND is_archived = 0
            """
            self.db.execute_non_query(archive_query, (task_id,))

            # 2) Вставляем новые записи батчем
            if products:
                insert_query = """
                    INSERT INTO mp_data.a_wb_stock_transfer_products_to_one_time_tasks
                    (task_id, product_wb_id, size_id, transfer_qty, transfer_qty_left, is_archived)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                batch = []
                for p in products:
                    batch.append((
                        task_id,
                        p["product_id"],
                        int(p["size"]),    # здесь size — это size_id
                        p["quantity"],
                        p["quantity"],     # transfer_qty_left = transfer_qty при создании
                        0
                    ))
                self.db.execute_many(insert_query, batch)
        except Exception as e:
            logging.error(f"Failed to update task products for task_id {task_id}: {e}")
            raise


    # ---------- РЕГУЛЯРНЫЕ ЗАДАНИЯ ----------
    def save_regular_task(self, supplier_id: int, target: Dict[str, float], minimum: Dict[str, float]) -> int:
        """
        Архивирует все активные и создаёт новую регулярную запись.
        target/minimum — доли 0..1 по русским названиям регионов.
        """
        try:
            # 1) Архивируем все активные
            self.db.execute_non_query(
                """
                UPDATE mp_data.a_wb_stock_transfer_regular_tasks
                   SET is_archived = 1,
                       task_archiving_date = NOW()
                 WHERE is_archived = 0
                """
            )

            # 2) Подготавливаем колонки и значения
            col_names = ["is_archived"]
            col_values = [0]
            placeholders = ["%s"]

            # опционально можем хранить supplier_id, если добавишь поле в таблицу
            # col_names.append("supplier_id"); col_values.append(supplier_id); placeholders.append("%s")

            for ru_name, (t_col, m_col) in self._REGION_COLS.items():
                t_val = float(target.get(ru_name, 0.0) or 0.0)
                m_val = float(minimum.get(ru_name, 0.0) or 0.0)
                # клипуем 0..1 для безопасности
                t_val = max(0.0, min(1.0, t_val))
                m_val = max(0.0, min(1.0, m_val))
                col_names.extend([t_col, m_col])
                col_values.extend([t_val, m_val])
                placeholders.extend(["%s", "%s"])

            insert_sql = f"""
                INSERT INTO mp_data.a_wb_stock_transfer_regular_tasks
                ({", ".join(col_names)})
                VALUES ({", ".join(placeholders)})
            """
            self.db.execute_non_query(insert_sql, tuple(col_values))

            new_id = self.db.execute_scalar("SELECT LAST_INSERT_ID()")
            return int(new_id)
        except Exception as e:
            logging.error(f"Failed to save regular task: {e}")
            raise

    def get_active_regular_task(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает активную регулярную запись в словарном виде:
        {
          "task_id": ...,
          "target": { "Центральный":0.3, ... },
          "minimum": { "Центральный":0.05, ... },
          "task_creation_date": "..."
        }
        """
        try:
            # выбираем последнюю неархивную
            cols = ["task_id", "task_creation_date"] + \
                   [c for pair in self._REGION_COLS.values() for c in pair]  # все target_* и min_*

            sql = f"""
                SELECT {", ".join(cols)}
                FROM mp_data.a_wb_stock_transfer_regular_tasks
                WHERE is_archived = 0
                ORDER BY task_creation_date DESC, task_id DESC
                LIMIT 1
            """
            rows = self.db.execute_query(sql)
            if not rows:
                return None

            row = rows[0]
            target: Dict[str, float] = {}
            minimum: Dict[str, float] = {}
            for ru_name, (t_col, m_col) in self._REGION_COLS.items():
                target[ru_name]  = float(row.get(t_col) or 0.0)
                minimum[ru_name] = float(row.get(m_col) or 0.0)

            return {
                "task_id": row["task_id"],
                "target": target,
                "minimum": minimum,
                "task_creation_date": row.get("task_creation_date").isoformat() if row.get("task_creation_date") else None
            }
        except Exception as e:
            logging.error(f"Failed to get active regular task: {e}")
            raise