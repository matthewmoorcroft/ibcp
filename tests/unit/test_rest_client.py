"""Unit tests for the REST client."""

import pytest
import responses
from unittest.mock import patch, Mock
from decimal import Decimal

from src.ibcp.ibcp import REST


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
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            client = REST(url="https://example.com:8000", ssl=True)
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
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            
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
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            client.id = "DU123456"
            
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
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            client.id = "DU123456"
            
            # Test getting all currencies
            balance = client.get_cash_balance()
            assert balance["USD"] == 10000.50
            assert balance["EUR"] == 5000.25
            assert "BASE" not in balance
            
            # Test getting specific currency
            usd_balance = client.get_cash_balance("USD")
            assert usd_balance == {"USD": 10000.50}

    @responses.activate
    def test_get_conid(self):
        """Test getting contract ID for a symbol."""
        contract_data = {
            "AAPL": [{
                "name": "APPLE INC",
                "contracts": [{
                    "conid": 265598,
                    "exchange": "NASDAQ",
                    "isUS": True
                }]
            }]
        }
        
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/trsrv/stocks",
            json=contract_data,
            status=200
        )
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            
            conid = client.get_conid("AAPL")
            assert conid == 265598

    @responses.activate
    def test_get_conid_with_filters(self):
        """Test getting contract ID with filters."""
        contract_data = {
            "AAPL": [{
                "name": "APPLE INC",
                "assetClass": "STK",
                "contracts": [{
                    "conid": 265598,
                    "exchange": "NASDAQ",
                    "isUS": True
                }, {
                    "conid": 265599,
                    "exchange": "LSE",
                    "isUS": False
                }]
            }]
        }
        
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/trsrv/stocks",
            json=contract_data,
            status=200
        )
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            
            # Test with US filter
            conid_us = client.get_conid("AAPL", contract_filters={"isUS": True})
            assert conid_us == 265598
            
            # Test with non-US filter  
            conid_non_us = client.get_conid("AAPL", contract_filters={"isUS": False})
            assert conid_non_us == 265599

    @responses.activate
    def test_get_marketdata_snapshot(self, sample_market_data):
        """Test getting market data snapshot."""
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/iserver/marketdata/snapshot",
            json=sample_market_data,
            status=200
        )
        
        # Mock get_conid
        with patch.object(REST, 'get_conid', return_value=265598):
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                snapshot = client.get_marketdata_snapshot("AAPL")
                assert len(snapshot) == 1
                assert snapshot[0]["conid"] == 265598
                assert snapshot[0]["31"] == "150.25"  # Last price

    @responses.activate
    def test_get_stock_last_price(self):
        """Test getting stock last price."""
        market_data = [{
            "conid": 265598,
            "31": "C150.25"  # Last price with currency indicator
        }]
        
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/iserver/marketdata/snapshot",
            json=market_data,
            status=200
        )
        
        with patch.object(REST, 'get_conid', return_value=265598):
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                price = client.get_stock_last_price("AAPL")
                assert price == 150.25

    @responses.activate
    def test_submit_orders(self, sample_order_data, sample_order_response):
        """Test submitting orders."""
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/account/DU123456/orders",
            json=sample_order_response,
            status=200
        )
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            client.id = "DU123456"
            
            result = client.submit_orders([sample_order_data], reply_yes=False)
            assert result["order_id"] == "123456789"

    @responses.activate
    def test_get_portfolio(self, sample_portfolio_data):
        """Test getting portfolio."""
        responses.add(
            responses.GET,
            "https://localhost:5000/v1/api/portfolio/DU123456/positions/0",
            json=sample_portfolio_data,
            status=200
        )
        
        # Mock get_cash_balance
        with patch.object(REST, 'get_cash_balance', return_value={"USD": 10000}):
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                client.id = "DU123456"
                
                portfolio = client.get_portfolio()
                assert "AAPL" in portfolio
                assert portfolio["AAPL"] == 100
                assert "balance" in portfolio

    def test_reply_yes(self):
        """Test replying yes to order confirmation."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://localhost:5000/v1/api/iserver/reply/test-id",
                json=[{"confirmed": True, "order_id": "123456"}],
                status=200
            )
            
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                result = client.reply_yes("test-id")
                assert result["confirmed"] is True

    @responses.activate
    def test_ping_server(self):
        """Test server ping."""
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/tickle",
            json={"session": "active", "ssoExpires": 123456789},
            status=200
        )
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            
            result = client.ping_server()
            assert result["session"] == "active"

    @responses.activate
    def test_get_auth_status(self):
        """Test getting authentication status."""
        responses.add(
            responses.POST,
            "https://localhost:5000/v1/api/iserver/auth/status",
            json={"authenticated": True, "competing": False, "connected": True},
            status=200
        )
        
        with patch.object(REST, '__init__', lambda x: None):
            client = REST()
            client.url = "https://localhost:5000/v1/api/"
            client.ssl = False
            
            status = client.get_auth_status()
            assert status["authenticated"] is True
            assert status["connected"] is True


@pytest.mark.unit
class TestRESTClientEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_conid_no_contracts(self):
        """Test getting contract ID when no contracts are found."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://localhost:5000/v1/api/trsrv/stocks",
                json={"INVALID": []},
                status=200
            )
            
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                with pytest.raises(IndexError):
                    client.get_conid("INVALID")

    def test_get_stock_last_price_retry_logic(self):
        """Test the retry logic in get_stock_last_price."""
        call_count = 0
        
        def mock_get_marketdata_snapshot(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return [{"31": "150.25"}]
        
        with patch.object(REST, '__init__', lambda x: None):
            with patch.object(REST, 'get_conid', return_value=265598):
                with patch.object(REST, 'get_marketdata_snapshot', side_effect=mock_get_marketdata_snapshot):
                    with patch('time.sleep'):  # Mock sleep to speed up test
                        client = REST()
                        price = client.get_stock_last_price("AAPL")
                        assert price == 150.25
                        assert call_count == 2

    def test_cash_balance_empty_response(self):
        """Test cash balance with empty response."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://localhost:5000/v1/api/portfolio/DU123456/ledger",
                json={"BASE": {}},
                status=200
            )
            
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                client.id = "DU123456"
                
                balance = client.get_cash_balance()
                assert balance == {}


@pytest.mark.benchmark
class TestRESTClientPerformance:
    """Performance tests for the REST client."""

    def test_get_conid_performance(self, benchmark, mock_ib_gateway):
        """Benchmark contract ID lookup performance."""
        with responses.RequestsMock() as rsps:
            mock_ib_gateway(rsps)
            
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                result = benchmark(client.get_conid, "AAPL")
                assert result == 265598

    def test_bulk_quote_performance(self, benchmark, mock_ib_gateway):
        """Benchmark bulk quote retrieval performance."""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        with responses.RequestsMock() as rsps:
            mock_ib_gateway(rsps)
            
            with patch.object(REST, '__init__', lambda x: None):
                client = REST()
                client.url = "https://localhost:5000/v1/api/"
                client.ssl = False
                
                def get_multiple_quotes():
                    return [client.get_stock_last_price(symbol) for symbol in symbols]
                
                # This would benefit from bulk operations in the new architecture
                result = benchmark(get_multiple_quotes)
                assert len(result) == 5
