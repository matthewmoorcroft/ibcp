"""Performance benchmarks for the IBCP library."""

import pytest
from unittest.mock import patch

from src.ibcp.ibcp import REST


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_rest_client_initialization(self, benchmark):
        """Benchmark REST client initialization."""
        with patch.object(REST, 'get_accounts', return_value=[{"accountId": "DU123456"}]):
            result = benchmark(REST)
            assert result is not None

    def test_config_creation(self, benchmark):
        """Benchmark config creation."""
        from src.ibcp.config import IBConfig
        
        result = benchmark(IBConfig)
        assert result is not None
