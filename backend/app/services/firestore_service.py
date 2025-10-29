"""
This module provides a service for interacting with Google Cloud Firestore,
handling all database operations for the GeoWatch application.
"""

import logging
from typing import Any, Dict, List, Optional

from google.cloud import firestore_v1

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirestoreService:
    """
    A service class for handling all interactions with the Google Cloud Firestore
    database. It encapsulates the logic for creating, retrieving, updating, and
    deleting documents in the 'monitoring_areas' and 'analysis_results'
    collections.
    """

    def __init__(self, project_id: str, database: str = "(default)"):
        """
        Initializes the Firestore client.

        Args:
            project_id (str): The Google Cloud project ID.
            database (str): The Firestore database name.
        """
        try:
            self.db = firestore_v1.AsyncClient(
                project=project_id, database=database
            )
            self.monitoring_areas_ref = self.db.collection("monitoring_areas")
            self.analysis_results_ref = self.db.collection("analysis_results")
            logger.info(
                "Successfully connected to Firestore project %s", project_id
            )
        except Exception as e:
            logger.exception(
                "Failed to connect to Firestore project %s: %s", project_id, e
            )
            raise

    async def add_monitoring_area(
        self, area_data: Dict[str, Any]
    ) -> str:
        """
        Adds a new monitoring area to the 'monitoring_areas' collection.

        Args:
            area_data (Dict[str, Any]): A dictionary containing the data for the
                                       new monitoring area.

        Returns:
            str: The ID of the newly created document.

        Raises:
            Exception: If the database operation fails.
        """
        try:
            _, doc_ref = await self.monitoring_areas_ref.add(area_data)
            logger.info("Successfully added monitoring area %s", doc_ref.id)
            return doc_ref.id
        except Exception as e:
            logger.exception("Failed to add monitoring area: %s", e)
            raise

    async def get_monitoring_area(self, area_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single monitoring area by its document ID.

        Args:
            area_id (str): The ID of the monitoring area to retrieve.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the area data if
                                     found, otherwise None.
        """
        doc_ref = self.monitoring_areas_ref.document(area_id)
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def get_all_monitoring_areas(self) -> List[Dict[str, Any]]:
        """
        Retrieves all monitoring areas from the 'monitoring_areas' collection.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents a monitoring area.
        """
        areas = []
        async for doc in self.monitoring_areas_ref.stream():
            area_data = doc.to_dict()
            area_data["area_id"] = doc.id
            areas.append(area_data)
        return areas

    async def update_monitoring_area(
        self, area_id: str, update_data: Dict[str, Any]
    ) -> None:
        """
        Updates a monitoring area with the provided data.

        Args:
            area_id (str): The ID of the monitoring area to update.
            update_data (Dict[str, Any]): The data to update.
        """
        doc_ref = self.monitoring_areas_ref.document(area_id)
        await doc_ref.update(update_data)

    async def soft_delete_monitoring_area(self, area_id: str) -> None:
        """
        Soft deletes a monitoring area by setting its status to 'deleted'.

        Args:
            area_id (str): The ID of the monitoring area to delete.
        """
        await self.update_monitoring_area(
            area_id, {"status": "deleted"}
        )

    async def add_analysis_result(
        self, result_data: Dict[str, Any]
    ) -> str:
        """
        Adds a new analysis result to the 'analysis_results' collection.

        Args:
            result_data (Dict[str, Any]): The analysis result data.

        Returns:
            str: The ID of the newly created analysis result.
        """
        try:
            _, doc_ref = await self.analysis_results_ref.add(result_data)
            logger.info("Successfully added analysis result %s", doc_ref.id)
            return doc_ref.id
        except Exception as e:
            logger.exception("Failed to add analysis result: %s", e)
            raise

    async def get_analysis_results(
        self, area_id: str, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieves paginated analysis results for a given monitoring area.

        Args:
            area_id (str): The ID of the monitoring area.
            limit (int): The maximum number of results to return.
            offset (int): The number of results to skip.

        Returns:
            List[Dict[str, Any]]: A list of analysis results.
        """
        query = (
            self.analysis_results_ref.where("area_id", "==", area_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
            .offset(offset)
        )
        results = []
        async for doc in query.stream():
            result_data = doc.to_dict()
            result_data["result_id"] = doc.id
            results.append(result_data)
        return results
