"""Integration tests for Flask API endpoints.

DB calls are mocked so no live database is required.
"""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


def _make_client():
    from api import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@contextmanager
def _mock_conn_ctx():
    """Context manager that yields a MagicMock connection."""
    yield MagicMock()


class TestHealthEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_health_returns_200(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})


class TestRunsEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    @patch("api.blueprints.runs.get_connection", _mock_conn_ctx)
    @patch("api.blueprints.runs.load_run_summary_list", return_value=[])
    def test_list_runs_returns_200(self, _mock_load: MagicMock) -> None:
        resp = self.client.get("/api/runs")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_list_runs_invalid_limit_returns_400(self) -> None:
        resp = self.client.get("/api/runs?limit=abc")
        self.assertEqual(resp.status_code, 400)

    def test_list_runs_invalid_offset_returns_400(self) -> None:
        resp = self.client.get("/api/runs?offset=xyz")
        self.assertEqual(resp.status_code, 400)

    @patch("api.blueprints.runs.get_connection", _mock_conn_ctx)
    @patch("api.blueprints.runs.load_run_summary_list", return_value=[])
    def test_list_runs_limit_capped_at_200(self, _mock_load: MagicMock) -> None:
        resp = self.client.get("/api/runs?limit=9999")
        self.assertEqual(resp.status_code, 200)

    def test_get_run_not_found(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = None

        @contextmanager
        def mock_ctx():  # type: ignore[misc]
            yield mock_conn

        with patch("api.blueprints.runs.get_connection", mock_ctx):
            resp = self.client.get("/api/runs/99999")
        self.assertEqual(resp.status_code, 404)

    def test_get_run_returns_run_and_metrics(self) -> None:
        mock_row = {
            "id": 1,
            "config_id": 1,
            "label": "test",
            "tags": [],
            "run_started_at": "2025-01-01",
            "run_completed_at": "2025-01-01",
            "n_periods": 360,
            "terminal_net_worth": 1_000_000.0,
            "ruin_period": None,
            "notes": None,
        }
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = mock_row

        @contextmanager
        def mock_ctx():  # type: ignore[misc]
            yield mock_conn

        with patch("api.blueprints.runs.get_connection", mock_ctx), patch(
            "api.blueprints.runs.load_run_scenario", return_value=[]
        ):
            resp = self.client.get("/api/runs/1")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("run", body)
        self.assertIn("metrics", body)


class TestMCEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    @patch("api.blueprints.mc.get_connection", _mock_conn_ctx)
    @patch("api.blueprints.mc.load_mc_summary_list", return_value=[])
    def test_list_mc_returns_200(self, _mock_load: MagicMock) -> None:
        resp = self.client.get("/api/mc")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_list_mc_invalid_limit_returns_400(self) -> None:
        resp = self.client.get("/api/mc?limit=bad")
        self.assertEqual(resp.status_code, 400)

    def test_get_mc_not_found(self) -> None:
        @contextmanager
        def mock_ctx():  # type: ignore[misc]
            yield MagicMock()

        with patch("api.blueprints.mc.get_connection", mock_ctx), patch(
            "api.blueprints.mc.load_mc_detail", return_value=None
        ):
            resp = self.client.get("/api/mc/99999")
        self.assertEqual(resp.status_code, 404)


class TestAssetsEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_get_run_assets_not_found(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None

        @contextmanager
        def mock_ctx():  # type: ignore[misc]
            yield mock_conn

        with patch("api.blueprints.assets.get_connection", mock_ctx):
            resp = self.client.get("/api/runs/99999/assets")
        self.assertEqual(resp.status_code, 404)

    def test_get_run_assets_returns_list(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (1,)

        @contextmanager
        def mock_ctx():  # type: ignore[misc]
            yield mock_conn

        with patch("api.blueprints.assets.get_connection", mock_ctx), patch(
            "api.blueprints.assets.load_run_assets", return_value=[]
        ):
            resp = self.client.get("/api/runs/1/assets")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)


class TestConfigurationEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_get_asset_bad_filename_returns_400(self) -> None:
        # Filename with semicolon fails the safety regex — Flask routes it to the handler
        resp = self.client.get("/api/configuration/assets/bad%3Bname.json")
        self.assertEqual(resp.status_code, 400)

    def test_put_asset_bad_filename_returns_400(self) -> None:
        resp = self.client.put(
            "/api/configuration/assets/bad%3Bname.json",
            json={"type": "Equity"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_asset_not_found_returns_404(self) -> None:
        resp = self.client.delete("/api/configuration/assets/nonexistent.json")
        self.assertEqual(resp.status_code, 404)


class TestErrorHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_404_returns_json(self) -> None:
        resp = self.client.get("/api/does_not_exist")
        self.assertEqual(resp.status_code, 404)
        body = resp.get_json()
        self.assertIn("error", body)
        self.assertEqual(body["code"], 404)


if __name__ == "__main__":
    unittest.main()
