import cognee
import asyncio
import logging
from cognee.modules.search.types import SearchType

logger = logging.getLogger("aegis.memory_service")

class CogneeMemoryService:
    """Manages the hybrid graph-vector memory layer for Aegis Sentinel."""

    @staticmethod
    async def remember_investigation(report_id: str, community_id: str, summary: str, risk_score: float):
        """1. Add new report summary and metadata to memory."""
        try:
            document_text = f"""
            REPORT_ID: {report_id}
            COMMUNITY: {community_id}
            RISK_SCORE: {risk_score}
            SUMMARY: {summary}
            DATE: {asyncio.get_event_loop().time()}
            """
            await cognee.add(document_text, dataset_id="fraud_investigations")
            await cognee.cognify(datasets=["fraud_investigations"])
            logger.info(f"Cognee remembered investigation: {report_id}")
        except Exception as e:
            logger.error(f"Error saving to Cognee: {str(e)}")

    @staticmethod
    async def recall_past_cases(community_id: str, search_query: str) -> str:
        """2. Recall related historical context using Cognee search."""
        try:
            results = await cognee.search(
                query_text=f"Community: {community_id} or Query: {search_query}",
                query_type=SearchType.GRAPH_COMPLETION,
                datasets=["fraud_investigations"]
            )
            if not results:
                return "No matching historical fraud memory found."
            context = "\n--- Past Memory ---\n".join([str(res) for res in results[:3]])
            return context
        except Exception as e:
            logger.error(f"Error querying Cognee: {str(e)}")
            return "Unable to retrieve past memory."

    @staticmethod
    async def improve_memory():
        """3. Strengthen context networks in the graph."""
        try:
            await cognee.cognify(datasets=["fraud_investigations"])
            logger.info("Cognee memory structure optimized.")
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")

    @staticmethod
    async def forget_case(community_id: str):
        """4. Delete datasets for false positives."""
        try:
            await cognee.forget(dataset_id=f"fraud_investigations_community_{community_id}")
            logger.info(f"Cognee forgot data for community: {community_id}")
        except Exception as e:
            logger.error(f"Error deleting from Cognee: {str(e)}")

    @staticmethod
    async def get_memory_graph_data(community_id: str):
        """Returns JSON representation of memory graph data."""
        return {"nodes": [], "links": []}
