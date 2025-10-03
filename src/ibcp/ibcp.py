from functools import lru_cache
import json
import logging
import time
from typing import Any, Optional, Union

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3.util.retry import Retry

from .config import IBConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    MarketDataError,
    OrderError,
    RateLimitError,
    ValidationError,
)


urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)  # disable ssl warning


class REST:
    """Allows to send REST API requests to Interactive Brokers Client Portal Web API.

    Args:
        url: Gateway session link, defaults to "https://localhost:5000"
        ssl: Usage of SSL certificate, defaults to False
        config: Configuration object, if provided overrides url/ssl parameters
        log_level: Logging level, defaults to "INFO"
    """

    def __init__(
        self,
        url: str = "https://localhost:5000",
        ssl: bool = False,
        config: Optional[IBConfig] = None,
        log_level: str = "INFO",
    ) -> None:
        """Create a new instance to interact with REST API.

        Args:
            url: Gateway session link, defaults to "https://localhost:5000"
            ssl: Usage of SSL certificate, defaults to False
            config: Configuration object, if provided overrides url/ssl parameters
            log_level: Logging level, defaults to "INFO"
        """
        # Use config if provided, otherwise create from parameters
        if config is not None:
            self.config = config
        else:
            self.config = IBConfig(
                base_url=url,
                ssl_verify=ssl,
                log_level=log_level,
            )

        self.url = f"{self.config.base_url}/v1/api/"
        self.ssl = self.config.ssl_verify
        self.logger = logging.getLogger(__name__)

        # Set up session with connection pooling and retries
        self.session = self._setup_session()

        # Initialize account ID
        try:
            accounts = self.get_accounts()
            if not accounts:
                raise AuthenticationError(
                    "No accounts found. Please check authentication."
                )
            self.id = accounts[0]["accountId"]
            self.logger.info(f"Initialized with account ID: {self.id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize account: {e}")
            raise AuthenticationError(f"Failed to get account information: {e}") from e

    def _setup_session(self) -> requests.Session:
        """Set up requests session with connection pooling and retry strategy.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "POST",
            ],
        )

        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=10, pool_maxsize=20
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _handle_response(self, response: requests.Response, endpoint: str = "") -> Any:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object
            endpoint: API endpoint for error context

        Returns:
            JSON response data

        Raises:
            APIError: For HTTP errors
            RateLimitError: For rate limit errors
            AuthenticationError: For authentication errors
        """
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise APIError(
                    f"Invalid JSON response: {e}",
                    response.status_code,
                    {"text": response.text},
                    endpoint,
                ) from e

        # Handle specific error cases
        if response.status_code == 401:
            raise AuthenticationError("Authentication required or expired")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                endpoint=endpoint,
            )

        # General API error
        try:
            error_data = response.json()
        except ValueError:
            error_data = {"text": response.text}

        raise APIError(
            f"HTTP {response.status_code} error",
            response.status_code,
            error_data,
            endpoint,
        )

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make HTTP request with error handling and logging.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            JSON response data
        """
        url = f"{self.url}{endpoint}"
        kwargs.setdefault("verify", self.ssl)
        kwargs.setdefault("timeout", self.config.timeout)

        self.logger.debug(f"{method} {endpoint} with args: {kwargs}")

        try:
            response = self.session.request(method, url, **kwargs)
            return self._handle_response(response, endpoint)
        except requests.exceptions.Timeout:
            raise APIError(
                f"Request timeout after {self.config.timeout}s", 408, {}, endpoint
            ) from None
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"Connection error: {e}", 0, {}, endpoint) from e

    def get_accounts(self) -> list[dict[str, Any]]:
        """Returns account information.

        Returns:
            List of account information dictionaries

        Raises:
            APIError: If the API request fails
            AuthenticationError: If authentication is required
        """
        return self._make_request("GET", "portfolio/accounts")

    def switch_account(self, account_id: str) -> dict[str, Any]:
        """Switch selected account to the specified account.

        Args:
            account_id: Account ID of the desired account

        Returns:
            Response from the server

        Raises:
            ValidationError: If account_id is invalid
            APIError: If the API request fails
        """
        if not account_id or not isinstance(account_id, str):
            raise ValidationError("account_id must be a non-empty string", "account_id")

        self.logger.info(f"Switching to account: {account_id}")

        response = self._make_request(
            "POST", "iserver/account", json={"acctId": account_id}
        )

        self.id = account_id
        self.logger.info(f"Successfully switched to account: {account_id}")
        return response

    def get_cash_balance(self, currency: Optional[str] = None) -> dict[str, Any]:
        """Returns cash balance of the selected account.

        Args:
            currency: Specific currency to return, if None returns all currencies

        Returns:
            Dictionary of cash balances by currency

        Raises:
            ValidationError: If currency format is invalid
            APIError: If the API request fails
        """
        if currency is not None and (
            not isinstance(currency, str) or len(currency) != 3
        ):
            raise ValidationError(
                "currency must be a 3-character string (e.g., 'USD')", "currency"
            )

        response = self._make_request("GET", f"portfolio/{self.id}/ledger")

        if currency:
            if currency not in response:
                raise ValidationError(
                    f"Currency '{currency}' not found in account", "currency"
                )
            return {currency: response[currency]["cashbalance"]}

        balance = {}
        for key, item in response.items():
            if key != "BASE" and isinstance(item, dict) and "cashbalance" in item:
                balance[key] = item["cashbalance"]

        return balance

    def get_stock_last_price(
        self,
        ticker: str,
        conid: Union[str, int] = "default",
        contract_filters: Optional[dict[str, Any]] = None,
        max_retries: int = 10,
    ) -> float:
        """Get the last price of a stock.

        Args:
            ticker: The stock symbol (e.g., 'AAPL')
            conid: Contract ID, if 'default' will be resolved from ticker
            contract_filters: Filters for contract resolution
            max_retries: Maximum number of retry attempts

        Returns:
            Last traded price as float

        Raises:
            ValidationError: If ticker is invalid
            MarketDataError: If price data cannot be retrieved
        """
        if not ticker or not isinstance(ticker, str):
            raise ValidationError("ticker must be a non-empty string", "ticker")

        if contract_filters is None:
            contract_filters = {"isUS": True}

        fields = {"last_price": "31"}

        for attempt in range(max_retries):
            try:
                response = self.get_marketdata_snapshot(
                    ticker, conid, contract_filters=contract_filters
                )
                if (
                    response
                    and len(response) > 0
                    and fields["last_price"] in response[0]
                ):
                    price_str = response[0][fields["last_price"]]
                    # Remove currency indicator if present
                    price_str = price_str.replace("C", "").replace("$", "")
                    return float(price_str)
            except Exception as e:
                self.logger.debug(f"Attempt {attempt + 1} failed for {ticker}: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(
                        f"Waiting for {ticker} price data (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(0.5)
                else:
                    raise MarketDataError(
                        f"Failed to get price for {ticker} after {max_retries} attempts",
                        symbol=ticker,
                    ) from None

        raise MarketDataError(f"Unable to retrieve price for {ticker}", symbol=ticker)

    def get_netvalue(self, currency: Optional[str] = None) -> dict:
        """Returns net value of the selected account

        :param currency: Currency to return
        :type currency: str
        :return: Net value of the selected account
        :rtype: dict
        """
        response = self._make_request("GET", f"portfolio/{self.id}/ledger")

        body = response.json()
        if currency:
            return {currency: body[currency]["netliquidationvalue"]}

        net_value = {}
        for key, item in body.items():
            if key != "BASE":
                net_value[key] = item["netliquidationvalue"]
        return net_value

    @lru_cache(maxsize=1000)
    def get_conid(
        self,
        symbol: str,
        instrument_filters: Optional[str] = None,  # JSON string for caching
        contract_filters: Optional[str] = None,  # JSON string for caching
    ) -> int:
        """Returns contract ID of the given stock instrument (cached).

        Args:
            symbol: Symbol of the stock instrument
            instrument_filters: JSON string of instrument filters for caching
            contract_filters: JSON string of contract filters for caching

        Returns:
            Contract ID as integer

        Raises:
            ValidationError: If symbol is invalid
            MarketDataError: If contract cannot be found
        """
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("symbol must be a non-empty string", "symbol")

        # Convert JSON strings back to dicts for internal use

        instrument_filters_dict = None
        contract_filters_dict = {"isUS": True}  # default

        if instrument_filters:
            try:
                instrument_filters_dict = json.loads(instrument_filters)
            except json.JSONDecodeError:
                raise ValidationError(
                    "instrument_filters must be valid JSON", "instrument_filters"
                ) from None

        if contract_filters:
            try:
                contract_filters_dict = json.loads(contract_filters)
            except json.JSONDecodeError:
                raise ValidationError(
                    "contract_filters must be valid JSON", "contract_filters"
                ) from None

        return self._get_conid_uncached(
            symbol, instrument_filters_dict, contract_filters_dict
        )

    def _get_conid_uncached(
        self,
        symbol: str,
        instrument_filters: Optional[dict[str, Any]] = None,
        contract_filters: Optional[dict[str, Any]] = None,
    ) -> int:
        """Internal method to get contract ID without caching."""
        if contract_filters is None:
            contract_filters = {"isUS": True}

        query = {"symbols": symbol}
        response = self._make_request("GET", "trsrv/stocks", params=query)

        if symbol not in response or not response[symbol]:
            raise MarketDataError(
                f"No instruments found for symbol: {symbol}", symbol=symbol
            )

        instruments = response[symbol]

        if instrument_filters or contract_filters:

            def filter_instrument(instrument: dict[str, Any]) -> bool:
                def apply_filters(x: dict[str, Any], filters: dict[str, Any]) -> bool:
                    return all(x.get(key) == val for key, val in filters.items())

                if instrument_filters and not apply_filters(
                    instrument, instrument_filters
                ):
                    return False

                if contract_filters:
                    instrument["contracts"] = [
                        contract
                        for contract in instrument.get("contracts", [])
                        if apply_filters(contract, contract_filters)
                    ]

                return len(instrument.get("contracts", [])) > 0

            instruments = [inst for inst in instruments if filter_instrument(inst)]

        if not instruments or not instruments[0].get("contracts"):
            raise MarketDataError(
                f"No contracts found for symbol: {symbol} with given filters",
                symbol=symbol,
            )

        return instruments[0]["contracts"][0]["conid"]

    def get_conid_simple(
        self,
        symbol: str,
        instrument_filters: Optional[dict[str, Any]] = None,
        contract_filters: Optional[dict[str, Any]] = None,
    ) -> int:
        """Get contract ID with dict parameters (non-cached version for external use).

        Args:
            symbol: Symbol of the stock instrument
            instrument_filters: Dictionary of instrument filters
            contract_filters: Dictionary of contract filters

        Returns:
            Contract ID as integer
        """
        # Convert dicts to JSON strings for caching
        instrument_filters_str = (
            json.dumps(instrument_filters, sort_keys=True)
            if instrument_filters
            else None
        )
        contract_filters_str = (
            json.dumps(contract_filters, sort_keys=True) if contract_filters else None
        )

        return self.get_conid(symbol, instrument_filters_str, contract_filters_str)

    def get_portfolio(self) -> dict:
        """Returns portfolio of the selected account

        :return: Portfolio
        :rtype: dict
        """
        response = self._make_request("GET", f"portfolio/{self.id}/positions/0")

        dic = {item["contractDesc"]: item["position"] for item in response.json()}
        dic["balance"] = self.get_cash_balance()
        return dic

    def reply_yes(self, message_id: str) -> dict[str, Any]:
        """Reply yes to a single message generated during order operations.

        Args:
            message_id: Message ID to reply to

        Returns:
            Response from the reply

        Raises:
            ValidationError: If message_id is invalid
            APIError: If the reply fails
        """
        if not message_id or not isinstance(message_id, str):
            raise ValidationError("message_id must be a non-empty string", "message_id")

        self.logger.debug(f"Replying yes to message: {message_id}")

        answer = {"confirmed": True}
        response = self._make_request(
            "POST", f"iserver/reply/{message_id}", json=answer
        )

        # Handle response format
        if isinstance(response, list) and response:
            return response[0]
        return response

    def _reply_all_yes(self, response, reply_yes_to_all: bool) -> dict:
        """
        Replies yes to consecutive messages generated while submitting or modifying orders.
        """
        dic = response.json()[0]
        if reply_yes_to_all:
            while "order_id" not in dic:
                print("Answering yes to ...")
                print(dic["message"])
                dic = self.reply_yes(dic["id"])
        return dic

    def submit_orders(
        self, list_of_orders: list[dict[str, Any]], reply_yes: bool = True
    ) -> dict[str, Any]:
        """Submit a list of orders.

        Args:
            list_of_orders: List of order dictionaries
            reply_yes: Whether to automatically reply yes to confirmation messages

        Returns:
            Response from the order submission

        Raises:
            ValidationError: If orders are invalid
            OrderError: If order submission fails
        """
        if not list_of_orders or not isinstance(list_of_orders, list):
            raise ValidationError(
                "list_of_orders must be a non-empty list", "list_of_orders"
            )

        # Validate each order
        for i, order in enumerate(list_of_orders):
            self._validate_order(order, f"order[{i}]")

        self.logger.info(f"Submitting {len(list_of_orders)} orders")

        try:
            response = self._make_request(
                "POST",
                f"iserver/account/{self.id}/orders",
                json={"orders": list_of_orders},
            )

            # Handle the response using existing logic
            return self._reply_all_yes_dict(response, reply_yes)

        except APIError as e:
            raise OrderError(
                f"Failed to submit orders: {e.message}", order_data=list_of_orders
            ) from e

    def _validate_order(self, order: dict[str, Any], field_name: str = "order") -> None:
        """Validate order dictionary.

        Args:
            order: Order dictionary to validate
            field_name: Field name for error reporting

        Raises:
            ValidationError: If order is invalid
        """
        if not isinstance(order, dict):
            raise ValidationError(f"{field_name} must be a dictionary", field_name)

        required_fields = ["conid", "orderType", "side", "quantity"]
        for field in required_fields:
            if field not in order:
                raise ValidationError(
                    f"Missing required field '{field}' in {field_name}", field_name
                )

        # Validate quantity
        if not isinstance(order["quantity"], (int, float)) or order["quantity"] <= 0:
            raise ValidationError(
                f"quantity must be a positive number in {field_name}", field_name
            )

        # Validate side
        if order["side"] not in ["BUY", "SELL"]:
            raise ValidationError(
                f"side must be 'BUY' or 'SELL' in {field_name}", field_name
            )

        # Validate order type
        valid_order_types = ["MKT", "LMT", "STP", "STP_LIMIT"]
        if order["orderType"] not in valid_order_types:
            raise ValidationError(
                f"orderType must be one of {valid_order_types} in {field_name}",
                field_name,
            )

    def _reply_all_yes_dict(
        self, response: dict[str, Any], reply_yes_to_all: bool
    ) -> dict[str, Any]:
        """Handle reply-yes logic for dictionary response.

        Args:
            response: API response dictionary
            reply_yes_to_all: Whether to auto-reply yes

        Returns:
            Final response after handling confirmations
        """
        # If response is a list, take the first item
        if isinstance(response, list) and response:
            current_response = response[0]
        else:
            current_response = response

        if reply_yes_to_all and isinstance(current_response, dict):
            while "order_id" not in current_response and "id" in current_response:
                self.logger.info(
                    f"Auto-replying yes to: {current_response.get('message', 'confirmation')}"
                )
                current_response = self.reply_yes(current_response["id"])

        return current_response

    def get_order(self, orderId: str) -> dict:
        """Returns details of the order

        :param orderId: Order ID of the submitted order
        :type orderId: str
        :return: Details of the order
        :rtype: dict
        """
        response = self._make_request("GET", f"iserver/account/order/status/{orderId}")

        return response.json()

    def get_live_orders(self, filters: Optional[list] = None) -> dict:
        """Returns list of live orders

        :param filters: List of filters for the returning response. Available items -- "inactive" "pending_submit" "pre_submitted" "submitted" "filled" "pending_cancel" "cancelled" "warn_state" "sort_by_time", defaults to []
        :type filters: list, optional
        :return: list of live orders
        :rtype: dict
        """
        if filters is None:
            filters = []
        response = self._make_request(
            "GET", "iserver/account/orders", params={"filters": filters}
        )

        return response.json()

    def cancel_order(self, orderId: str) -> dict:
        """Cancel the submitted order

        :param orderId: Order ID for the input order
        :type orderId: str
        :return: Response from the server
        :rtype: dict
        """
        response = self._make_request(
            "DELETE", f"iserver/account/{self.id}/order/{orderId}"
        )

        return response.json()

    def modify_order(
        self,
        orderId: Optional[str] = None,
        order: Optional[dict] = None,
        reply_yes=True,
    ) -> dict:
        """Modify submitted order

        :param orderId: Order ID of the submitted order, defaults to None
        :type orderId: str
        :param order: Order dictionary, defaults to None
        :type order: dict
        :param reply_yes: Replies yes to the returning messages, defaults to True
        :type reply_yes: bool, optional
        :return: Response from the server
        :rtype: dict
        """
        if orderId is None or order is None:
            raise ValidationError("Input parameters (orderId or order) are missing")

        response = self._make_request(
            "POST", f"iserver/account/{self.id}/order/{orderId}", json=order
        )

        return self._reply_all_yes(response, reply_yes)

    def ping_server(self) -> dict:
        """Tickle server for maintaining connection

        :return: Response from the server
        :rtype: dict
        """
        response = self._make_request("POST", "tickle")
        return response.json()

    def get_auth_status(self) -> dict:
        """Returns authentication status

        :return: Status dictionary
        :rtype: dict
        """
        response = self._make_request("POST", "iserver/auth/status")
        return response.json()

    def re_authenticate(self) -> None:
        """Attempts to re-authenticate when authentication is lost"""
        self._make_request("POST", "iserver/reauthenticate")
        print("Reauthenticating ...")

    def log_out(self) -> None:
        """Log out from the gateway session"""
        self._make_request("POST", "logout")

    def get_bars(
        self,
        symbol: str,
        period="1w",
        bar="1d",
        outsideRth=False,
        conid: str or int = "default",
    ) -> dict:
        """Returns market history for the given instrument. conid should be provided for futures and options.

        :param symbol: Symbol of the stock instrument
        :type symbol: str
        :param period: Period for the history, available time period-- {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y, defaults to "1w"
        :type period: str, optional
        :param bar: Granularity of the history, possible value-- 1min, 2min, 3min, 5min, 10min, 15min, 30min, 1h, 2h, 3h, 4h, 8h, 1d, 1w, 1m, defaults to "1d"
        :type bar: str, optional
        :param outsideRth: For contracts that support it, will determine if historical data includes outside of regular trading hours., defaults to False
        :type outsideRth: bool, optional
        :param conid: conid should be provided separately for futures or options. If not provided, it is assumed to be a stock.
        :type conid: str or int, optional
        :return: Response from the server
        :rtype: dict
        """
        if conid == "default":
            conid = self.get_conid(symbol)

        query = {
            "conid": int(conid),
            "period": period,
            "bar": bar,
            "outsideRth": outsideRth,
        }
        response = self._make_request("GET", "iserver/marketdata/history", params=query)

        return response.json()

    def get_fut_conids(self, symbol: str) -> list:
        """Returns list of contract id objects of a future instrument.

        :param symbol: symbol of a future instrument
        :type symbol: str
        :return: list of contract id objects
        :rtype: list
        """
        query = {"symbols": symbol}
        response = self._make_request("GET", "trsrv/futures", params=query)

        return response.json()[symbol]

    def get_marketdata_snapshot(
        self,
        symbol: str,
        conid: Union[str, int] = "default",
        contract_filters: Optional[dict[str, Any]] = None,
        fields: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Returns market data snapshot for the given instrument.

        Args:
            symbol: Symbol of the stock instrument
            conid: Contract ID, if 'default' will be resolved from symbol
            contract_filters: Filters for contract resolution
            fields: List of field IDs to retrieve (default: ['31'] for last price)

        Returns:
            List of market data snapshots

        Raises:
            ValidationError: If parameters are invalid
            MarketDataError: If market data cannot be retrieved
        """
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("symbol must be a non-empty string", "symbol")

        if contract_filters is None:
            contract_filters = {"isUS": True}

        if fields is None:
            fields = ["31"]  # Default to last price

        if conid == "default":
            conid = self.get_conid_simple(symbol, contract_filters=contract_filters)

        query = {"conids": str(conid), "fields": ",".join(fields)}

        try:
            response = self._make_request(
                "GET", "iserver/marketdata/snapshot", params=query
            )

            if not response:
                raise MarketDataError(
                    f"No market data returned for {symbol}", symbol=symbol
                )

            return response

        except APIError as e:
            raise MarketDataError(
                f"Failed to get market data for {symbol}: {e.message}",
                symbol=symbol,
                contract_id=conid if isinstance(conid, int) else None,
            ) from e


if __name__ == "__main__":
    api = REST()

    orders = [
        {
            "conid": api.get_conid("AAPL"),
            "orderType": "MKT",
            "side": "BUY",
            "quantity": 7,
            "tif": "GTC",
        }
    ]
