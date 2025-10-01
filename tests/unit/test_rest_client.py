"""Unit tests for the REST client."""

import pytest
import responses
from unittest.mock import patch, Mock
from decimal import Decimal

from src.ibcp.ibcp import REST
from src.ibcp.config import IBConfig


class TestRESTClient:
    """Test cases for the REST client class."""

    def test_init_default_parameters(self):
        """Test REST client initialization with default parameters."""
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            assert client.url == "https://localhost:5000/v1/api/"
            assert client.ssl is False
            assert client.id == "DU123456"

    def test_init_custom_parameters(self):
        """Test REST client initialization with custom parameters."""
        config = IBConfig(base_url="https://example.com:8000", ssl_verify=True)
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST(config=config)
            assert client.url == "https://example.com:8000/v1/api/"
            assert client.ssl is True

    @responses.activate
    def test_get_accounts(self, sample_account_data):
        """Test getting account information."""
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/accounts",
            json=sample_account_data,
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            accounts = client.get_accounts()
            assert len(accounts) == 1
            assert accounts[0]["accountId"] == "DU123456"

    @responses.activate
    def test_switch_account(self):
        """Test switching accounts."""
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/account",
            json={"set": True, "acctId": "DU654321"},
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            response = client.switch_account("DU654321")
            assert response["acctId"] == "DU654321"
            assert client.id == "DU654321"

    @responses.activate 
    def test_get_cash_balance(self):
        """Test getting cash balance."""
        ledger_data = {
            "USD": {"cashbalance": 10000.50},
            "EUR": {"cashbalance": 5000.25},
            "BASE": {}
        }
        
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/DU123456/ledger",
            json=ledger_data,
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            # Test getting all currencies
            balance = client.get_cash_balance()
            assert balance["USD"] == 10000.50
            assert balance["EUR"] == 5000.25
            assert "BASE" not in balance
            
            # Test getting specific currency
            usd_balance = client.get_cash_balance("USD")
            assert usd_balance == {"USD": 10000.50}

    def test_get_conid(self):
        """Test getting contract ID for a symbol."""
        contract_data = [
            {
                "conid": 265598,
                "companyHeader": "Apple Inc",
                "companyName": "APPLE INC",
                "symbol": "AAPL",
                "description": "AAPL",
                "restricted": None,
                "fop": "0",
                "opt": None,
                "war": None,
                "sections": []
            }
        ]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, '_make_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = contract_data
                mock_request.return_value = mock_response
                
                conid = client.get_conid("AAPL")
                assert conid == 265598

    def test_get_conid_with_filters(self):
        """Test getting contract ID with filters."""
        contract_data = [
            {
                "conid": 265598,
                "companyHeader": "Apple Inc",
                "companyName": "APPLE INC",
                "symbol": "AAPL",
                "description": "AAPL",
                "isUS": True,
                "sections": []
            }
        ]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, '_make_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = contract_data
                mock_request.return_value = mock_response
                
                # Note: contract_filters should be a string for caching to work
                conid_us = client.get_conid("AAPL", contract_filters='{"isUS": true}')
                assert conid_us == 265598

    def test_get_marketdata_snapshot(self):
        """Test getting market data snapshot."""
        snapshot_data = [
            {
                "conid": 265598,
                "31": "150.25",  # Last price
                "70": "AAPL",    # Symbol
                "71": "NASDAQ"   # Exchange
            }
        ]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, 'get_conid_simple', return_value=265598):
                with patch.object(client, '_make_request') as mock_request:
                    mock_response = Mock()
                    mock_response.json.return_value = snapshot_data
                    mock_request.return_value = mock_response
                    
                    snapshot = client.get_marketdata_snapshot("AAPL")
                    assert snapshot[0]["conid"] == 265598
                    assert snapshot[0]["31"] == "150.25"

    def test_get_stock_last_price(self):
        """Test getting stock last price."""
        snapshot_data = [{"conid": 265598, "31": "150.25"}]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, 'get_marketdata_snapshot', return_value=snapshot_data):
                price = client.get_stock_last_price("AAPL")
                assert price == Decimal("150.25")

    @responses.activate
    def test_submit_orders(self, sample_order_data):
        """Test submitting orders."""
        order_response = {
            "orders": [
                {
                    "order_id": "12345",
                    "order_status": "Submitted",
                    "encrypt_message": "1"
                }
            ]
        }
        
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/account/DU123456/orders",
            json=order_response,
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            result = client.submit_orders([sample_order_data], reply_yes=False)
            assert result["orders"][0]["order_id"] == "12345"

    @responses.activate
    def test_reply_yes(self):
        """Test replying yes to a message."""
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/reply/test-id",
            json={"confirmed": True},
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            result = client.reply_yes("test-id")
            assert result["confirmed"] is True


class TestRESTClientEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_conid_no_contracts(self):
        """Test getting contract ID when no contracts are found."""
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, '_make_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = []
                mock_request.return_value = mock_response
                
                with pytest.raises(ValueError):
                    client.get_conid("INVALID")

    def test_get_stock_last_price_retry_logic(self):
        """Test retry logic for getting stock price."""
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            
            # Mock get_marketdata_snapshot to raise an exception
            with patch.object(client, 'get_marketdata_snapshot') as mock_get_marketdata_snapshot:
                mock_get_marketdata_snapshot.side_effect = Exception("Network error")
                
                with pytest.raises(ValueError):
                    client.get_stock_last_price("AAPL")

    @responses.activate
    def test_cash_balance_empty_response(self):
        """Test handling empty cash balance response."""
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/DU123456/ledger",
            json={},
            status=200
        )
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            balance = client.get_cash_balance()
            assert balance == {}


class TestRESTClientPerformance:
    """Performance tests for the REST client."""

    def test_get_conid_performance(self, benchmark):
        """Test performance of get_conid method."""
        contract_data = [{"conid": 265598, "symbol": "AAPL"}]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            with patch.object(client, '_make_request') as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = contract_data
                mock_request.return_value = mock_response
                
                result = benchmark(client.get_conid, "AAPL")
                assert result == 265598

    def test_bulk_quote_performance(self, benchmark):
        """Test performance of getting multiple quotes."""
        snapshot_data = [{"conid": 265598, "31": "150.25"}]
        
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST()
            
            def get_multiple_quotes():
                symbols = ["AAPL", "GOOGL", "MSFT"]
                with patch.object(client, 'get_marketdata_snapshot', return_value=snapshot_data):
                    return [client.get_stock_last_price(symbol) for symbol in symbols]
            
            result = benchmark(get_multiple_quotes)
            assert len(result) == 3


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
            "tradingType": "STKCASH",
            "faclient": False,
            "clearingStatus": "O",
            "covestor": False,
            "parent": {},
            "desc": "DU123456"
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