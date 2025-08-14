# dependencies/dependencies.py
from utils.access_data_loader import AccessDataLoader
from infrastructure.db.mysql.base import SyncDatabase
from utils.logger import get_logger
from typing import Optional

class Dependencies:
    def __init__(self):
        self._logger = get_logger("stock_transfer_fastapi_app")
        self.access_data_loader = AccessDataLoader(logger=self._logger)
        self._db: Optional[SyncDatabase] = None

    @property
    def db(self) -> SyncDatabase:
        if self._db is None:
            mysql_connect_params_dict = self.access_data_loader.get_mysql_connect_params_dict()
            con_data = mysql_connect_params_dict['no_db_fixed']
            self._db = SyncDatabase(
                host=con_data['host'],
                port=con_data['port'],
                user=con_data['user'],
                password=con_data['password'],
                db='dostup')
            
        return self._db

    def close(self):
        if self._db is not None:
            try:
                self._db.close()
                self._logger.info("SyncDatabase pool closed")
            except Exception as e:
                self._logger.warning(f"Failed to close SyncDatabase pool: {e}")
            finally:
                self._db = None

deps = Dependencies()
