import asyncio
import json
import unittest
from unittest.mock import patch, AsyncMock
import sys
import os

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Mocked Data based on user prompt
MOCK_PROCESSORS = {
    "processors": [
        {
            "id": "bca9ae30-019c-1000-c468-a3fac3e455d5",
            "component": {
                "id": "bca9ae30-019c-1000-c468-a3fac3e455d5",
                "name": "EvaluateJsonPath",
                "config": {"properties": {"token": "$.token"}}
            }
        },
        {
            "id": "bcb0a5ac-019c-1000-539e-eba592add906",
            "component": {
                "id": "bcb0a5ac-019c-1000-539e-eba592add906",
                "name": "EvaluateJsonPath",
                "config": {"properties": {"errorCode": "$.errorCode"}}
            }
        },
        {
            "id": "d53becc0-b72d-3b3f-a83f-3be8cff13020",
            "component": {
                "id": "d53becc0-b72d-3b3f-a83f-3be8cff13020",
                "name": "EvaluateJsonPath",
                "config": {"properties": {"username": "$.username"}}
            }
        },
        {"id": "5994466f-fb94-3f58-bb5f-bd551c40a9d7", "component": {"id": "5994466f-fb94-3f58-bb5f-bd551c40a9d7", "name": "HandleHttpRequest"}},
        {"id": "5bacc689-b2e0-3433-9ec5-bd7229cce004", "component": {"id": "5bacc689-b2e0-3433-9ec5-bd7229cce004", "name": "RouteOnAttribute"}}
    ]
}

MOCK_CONNECTIONS = {
    "connections": [
        {
            "component": {
                "source": {"id": "5994466f-fb94-3f58-bb5f-bd551c40a9d7"},
                "destination": {"id": "d53becc0-b72d-3b3f-a83f-3be8cff13020"},
                "selectedRelationships": ["success"]
            }
        },
        {
            "component": {
                "source": {"id": "5bacc689-b2e0-3433-9ec5-bd7229cce004"},
                "destination": {"id": "bca9ae30-019c-1000-c468-a3fac3e455d5"},
                "selectedRelationships": ["success"]
            }
        },
        {
            "component": {
                "source": {"id": "5bacc689-b2e0-3433-9ec5-bd7229cce004"},
                "destination": {"id": "bcb0a5ac-019c-1000-539e-eba592add906"},
                "selectedRelationships": ["error"]
            }
        }
    ]
}

class TestProcessorFinder(unittest.IsolatedAsyncioTestCase):

    @patch('app.nifi_client._request', new_callable=AsyncMock)
    @patch('app.nifi_client.get_connections', new_callable=AsyncMock)
    async def test_find_by_after_processor(self, mock_get_connections, mock_request):
        from app.nifi_client import find_processors_by_criteria
        
        mock_request.return_value = MOCK_PROCESSORS
        mock_get_connections.return_value = MOCK_CONNECTIONS
        
        # 1. Test: EvaluateJsonPath after HandleHttpRequest
        results = await find_processors_by_criteria(
            group_id="dummy",
            name="EvaluateJsonPath",
            after_processor="HandleHttpRequest"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "d53becc0-b72d-3b3f-a83f-3be8cff13020")
        print("Test 1 Passed: Found 'EvaluateJsonPath' after 'HandleHttpRequest'")

    @patch('app.nifi_client._request', new_callable=AsyncMock)
    @patch('app.nifi_client.get_connections', new_callable=AsyncMock)
    async def test_find_by_after_and_relationship(self, mock_get_connections, mock_request):
        from app.nifi_client import find_processors_by_criteria
        
        mock_request.return_value = MOCK_PROCESSORS
        mock_get_connections.return_value = MOCK_CONNECTIONS

        # 2. Test: EvaluateJsonPath after RouteOnAttribute success
        results = await find_processors_by_criteria(
            group_id="dummy",
            name="EvaluateJsonPath",
            after_processor="RouteOnAttribute",
            relationship="success"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "bca9ae30-019c-1000-c468-a3fac3e455d5")
        print("Test 2 Passed: Found 'EvaluateJsonPath' after 'RouteOnAttribute' (success)")

        # 3. Test: EvaluateJsonPath after RouteOnAttribute error
        results = await find_processors_by_criteria(
            group_id="dummy",
            name="EvaluateJsonPath",
            after_processor="RouteOnAttribute",
            relationship="error"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "bcb0a5ac-019c-1000-539e-eba592add906")
        print("Test 3 Passed: Found 'EvaluateJsonPath' after 'RouteOnAttribute' (error)")

    @patch('app.nifi_client._request', new_callable=AsyncMock)
    async def test_find_all_ambiguous(self, mock_request):
        from app.nifi_client import find_processors_by_criteria
        
        mock_request.return_value = MOCK_PROCESSORS
        
        # 4. Test: EvaluateJsonPath (ambiguous)
        results = await find_processors_by_criteria(
            group_id="dummy",
            name="EvaluateJsonPath"
        )
        self.assertEqual(len(results), 3)
        print(f"Test 4 Passed: Found {len(results)} 'EvaluateJsonPath' processors when no criteria provided")

    @patch('app.nifi_client._request', new_callable=AsyncMock)
    async def test_find_by_property(self, mock_request):
        from app.nifi_client import find_processors_by_criteria
        
        mock_request.return_value = MOCK_PROCESSORS
        
        # 5. Test: EvaluateJsonPath with specific property
        results = await find_processors_by_criteria(
            group_id="dummy",
            name="EvaluateJsonPath",
            property_filters={"username": "$.username"}
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "d53becc0-b72d-3b3f-a83f-3be8cff13020")
        print("Test 5 Passed: Found 'EvaluateJsonPath' by property filter")

if __name__ == "__main__":
    unittest.main()
