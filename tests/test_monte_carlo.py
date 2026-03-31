import unittest

from models.monte_carlo import MonteCarloResults, MonteCarloRunner, SimulationResult


class TestSimulationResult(unittest.TestCase):
    def test_solvent(self):
        r = SimulationResult(run_id=0, terminal_net_worth=500_000.0, ruin_period=None)
        self.assertIsNone(r.ruin_period)

    def test_ruined(self):
        r = SimulationResult(run_id=1, terminal_net_worth=-10_000.0, ruin_period=42)
        self.assertEqual(r.ruin_period, 42)


class TestMonteCarloResults(unittest.TestCase):
    def _make_results(self, worths: list[float]) -> MonteCarloResults:
        results = [
            SimulationResult(
                run_id=i,
                terminal_net_worth=w,
                ruin_period=None if w >= 0 else 100,
            )
            for i, w in enumerate(worths)
        ]
        return MonteCarloResults(n_runs=len(results), results=results)

    def test_ruin_probability_zero(self):
        mc = self._make_results([100_000.0, 200_000.0, 300_000.0])
        self.assertAlmostEqual(mc.ruin_probability(), 0.0)

    def test_ruin_probability_one(self):
        mc = self._make_results([-1.0, -2.0])
        self.assertAlmostEqual(mc.ruin_probability(), 1.0)

    def test_ruin_probability_partial(self):
        mc = self._make_results([100_000.0, -1.0, 200_000.0, -2.0])
        self.assertAlmostEqual(mc.ruin_probability(), 0.5)

    def test_terminal_wealth_percentiles_order(self):
        mc = self._make_results([100_000.0, 200_000.0, 300_000.0])
        pcts = mc.terminal_wealth_percentiles([0, 50, 100])
        self.assertLessEqual(pcts[0], pcts[50])
        self.assertLessEqual(pcts[50], pcts[100])

    def test_empty_results(self):
        mc = MonteCarloResults(n_runs=0, results=[])
        self.assertAlmostEqual(mc.ruin_probability(), 0.0)


class TestMonteCarloRunner(unittest.TestCase):
    TEST_CONFIG = "./tests/test_config/test.json"
    TEST_ASSETS = "./tests/test_config/assets"

    def test_smoke_fixed_seed(self):
        runner = MonteCarloRunner(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=5,
            random_seed=42,
        )
        results = runner.run()
        self.assertEqual(results.n_runs, 5)
        self.assertEqual(len(results.results), 5)

    def test_ruin_probability_in_range(self):
        runner = MonteCarloRunner(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=10,
            random_seed=42,
        )
        results = runner.run()
        prob = results.ruin_probability()
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_deterministic_with_same_seed(self):
        """Two runners with the same seed must produce identical terminal values."""
        kwargs = dict(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=5,
            random_seed=99,
        )
        r1 = MonteCarloRunner(**kwargs).run()
        r2 = MonteCarloRunner(**kwargs).run()
        for s1, s2 in zip(r1.results, r2.results):
            self.assertAlmostEqual(
                s1.terminal_net_worth, s2.terminal_net_worth, places=2
            )

    def test_run_ids_sequential(self):
        runner = MonteCarloRunner(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=4,
            random_seed=7,
        )
        results = runner.run()
        for i, r in enumerate(results.results):
            self.assertEqual(r.run_id, i)

    def test_store_trajectories(self):
        """store_trajectories=True must capture per-run net_worth trajectories."""
        runner = MonteCarloRunner(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=3,
            random_seed=42,
            store_trajectories=True,
        )
        results = runner.run()
        self.assertTrue(results.store_trajectories)
        self.assertTrue(results.has_trajectories())
        trajectories = results.trajectory_array()
        self.assertEqual(len(trajectories), 3)
        for traj in trajectories:
            self.assertIsInstance(traj, list)
            self.assertGreater(len(traj), 0)
            self.assertIsInstance(traj[0], float)

    def test_no_trajectories_by_default(self):
        """store_trajectories defaults to False; trajectories must be None."""
        runner = MonteCarloRunner(
            config_file_path=self.TEST_CONFIG,
            asset_config_path=self.TEST_ASSETS,
            n_runs=3,
            random_seed=42,
        )
        results = runner.run()
        self.assertFalse(results.has_trajectories())
        for r in results.results:
            self.assertIsNone(r.net_worth_trajectory)


if __name__ == "__main__":
    unittest.main()
