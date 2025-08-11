from services.mysql_db_service.stock_transfer_service import DBController
from infrastructure.api.sync_controller import SyncAPIController
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseRequestProcessor:
    def __init__(self, 
                 api_controller: SyncAPIController,
                 db: DBController):
        self.api_controller = api_controller
        self.db = db
        
    def process_request_no_pagination(self, url, method, headers, schema, params, body, store_uuid, stream, stream_path):
        logger.info(f"Start processing request: method={method}, url={url}, store_uuid={store_uuid}")

        try:
            cached_result = self.db.get_recent_cached_data(url=url,
                                                            method=method,
                                                            schema=schema,
                                                            params=params,
                                                            body=body,
                                                            store_uuid=store_uuid)
            
            if cached_result:
                logger.info("Returning cached result from DB.")
                return cached_result
        except Exception as e:
            logger.error(f"Error fetching cached data: {e}", exc_info=True)
        
        try:
            new_data_json = self.api_controller.request(method=method, 
                                                        endpoint=url,
                                                        params=params,
                                                        json=body,
                                                        headers=headers,
                                                        stream=stream,
                                                        stream_path=stream_path)
            
            logger.info("Received response from API.")
        except Exception as e:
            logger.error(f"API request failed: {e}", exc_info=True)
            return None

        if new_data_json:
            try:
                self.db.insert_request_with_data(schema=schema,
                                                url=url,
                                                method=method,
                                                params=params,
                                                body=body,
                                                store_uuid=store_uuid,
                                                response_data=new_data_json)
                
                logger.info("API response successfully stored in DB.")
            except Exception as e:
                logger.error(f"Failed to store API response in DB: {e}", exc_info=True)

        return new_data_json
