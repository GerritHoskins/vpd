from tapo import ApiClient
from config.settings import TAPO_USERNAME, TAPO_PASSWORD

async def get_tapo_client():
    """Initialize and return a Tapo API Client instance."""
    
    return ApiClient(TAPO_USERNAME, TAPO_PASSWORD)
