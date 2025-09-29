"""Pytest configuration and shared fixtures."""

import json
import pytest
import responses
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.ibcp.ibcp import REST


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "base_url": "https://localhost:5000",
        "ssl_verify": False,
        "timeout": 30
    }


@pytest.fixture
def rest_client(mock_config):
    """Create a REST client instance for testing."""
    with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
        client = REST(url=mock_config["base_url"], ssl=mock_config["ssl_verify"])
        return client


@pytest.fixture
def mock_responses():
    """Mock HTTP responses for API calls."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def sample_account_data():
    """Sample account data for testing."""
    return [
        {
            "accountId": "DU123456",
            "accountVan": "DU123456",
            "accountTitle": "Test Account",
            "displayName": "DU123456",
            "accountAlias": None,
            "accountStatus": 1,
            "currency": "USD",
            "type": "DEMO",
            "tradingType": "STKNOPT",
            "faclient": False,
            "clearingStatus": "O",
            "parent": {},
            "desc": "DU123456"
        }
    ]


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing."""
    return [
        {
            "acctId": "DU123456",
            "conid": 265598,
            "contractDesc": "AAPL",
            "position": 100,
            "mktPrice": 150.25,
            "mktValue": 15025.0,
            "currency": "USD",
            "avgCost": 145.50,
            "avgPrice": 145.50,
            "realizedPnl": 0.0,
            "unrealizedPnl": 475.0,
            "exchs": None,
            "expiry": None,
            "putOrCall": None,
            "multiplier": 1,
            "strike": 0,
            "exerciseStyle": None,
            "undConid": 0,
            "conExchMap": [],
            "assetClass": "STK",
            "model": ""
        }
    ]


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return [
        {
            "conid": 265598,
            "31": "150.25",  # Last price
            "70": "150.20",  # Bid price  
            "71": "150.30",  # Ask price
            "7295": "1640995200000",  # Last update time
            "7296": "1"  # Market data availability
        }
    ]


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "conid": 265598,
        "orderType": "MKT",
        "side": "BUY", 
        "quantity": 100,
        "tif": "DAY"
    }


@pytest.fixture
def sample_order_response():
    """Sample order response for testing."""
    return [
        {
            "order_id": "123456789",
            "order_status": "Submitted",
            "encrypt_message": "1"
        }
    ]


@pytest.fixture
def mock_ib_gateway():
    """Mock IB Gateway responses for comprehensive testing."""
    def _setup_mock_responses(rsps: responses.RequestsMock):
        # Account endpoints
        rsps.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/accounts",
            json=[{"accountId": "DU123456"}],
            status=200
        )
        
        # Portfolio endpoints
        rsps.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/DU123456/positions/0",
            json=[{
                "contractDesc": "AAPL",
                "position": 100
            }],
            status=200
        )
        
        # Market data endpoints
        rsps.add(
            responses.GET,
            "https://localhost:5000/v1/api/iserver/marketdata/snapshot",
            json=[{
                "conid": 265598,
                "31": "150.25"
            }],
            status=200
        )
        
        # Contract search endpoints
        rsps.add(
            responses.GET,
            "https://localhost:5000/v1/api/trsrv/stocks",
            json={
                "AAPL": [{
                    "name": "APPLE INC",
                    "contracts": [{
                        "conid": 265598,
                        "exchange": "NASDAQ",
                        "isUS": True
                    }]
                }]
            },
            status=200
        )
        
        # Order endpoints
        rsps.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/account/DU123456/orders",
            json=[{"order_id": "123456789"}],
            status=200
        )
        
        return rsps
    
    return _setup_mock_responses


class MockWebSocket:
    """Mock WebSocket for testing streaming functionality."""
    
    def __init__(self):
        self.messages = []
        self.closed = False
    
    async def send(self, message):
        self.messages.append(message)
    
    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        return '{"type": "heartbeat"}'
    
    async def close(self):
        self.closed = True


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for streaming tests."""
    return MockWebSocket()


# Performance testing fixtures
@pytest.fixture
def benchmark_data():
    """Data for performance benchmarking."""
    return {
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"] * 20,
        "large_portfolio": [
            {"symbol": f"STOCK{i}", "quantity": i * 10}
            for i in range(1000)
        ]
    }


# Utility functions for tests
def assert_valid_response(response: Dict[str, Any], required_fields: list):
    """Assert that a response contains all required fields."""
    assert isinstance(response, dict)
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def create_mock_order(symbol="AAPL", quantity=100, side="BUY", order_type="MKT"):
    """Create a mock order for testing."""
    return {
        "conid": 265598,
        "orderType": order_type,
        "side": side,
        "quantity": quantity,
        "tif": "DAY"
    }


# Markers for different test types
pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
]
