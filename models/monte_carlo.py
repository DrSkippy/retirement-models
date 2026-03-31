"""Monte Carlo simulation runner for the retirement financial model."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from tqdm import tqdm

from models.scenarios import RetirementFinancialModel

MONTHS_IN_YEAR = 12


@dataclass
class SimulationResult:
    """Result of a single Monte Carlo simulation run."""

    run_id: int
    terminal_net_worth: float
    ruin_period: Optional[int]  # Period index when net_worth first goes negative; None if solvent
    net_worth_trajectory: Optional[list[float]] = None  # Per-period net_worth if captured


@dataclass
class MonteCarloResults:
    """Aggregated results from all Monte Carlo runs."""

    n_runs: int
    results: list[SimulationResult]
    store_trajectories: bool = False

    def ruin_probability(self) -> float:
        """Return the fraction of runs that experienced ruin (net_worth < 0)."""
        ruined = sum(1 for r in self.results if r.ruin_period is not None)
        return ruined / self.n_runs if self.n_runs > 0 else 0.0

    def terminal_wealth_percentiles(
        self, percentiles: list[float]
    ) -> dict[float, float]:
        """Return terminal net worth at each requested percentile.

        Args:
            percentiles: List of percentile values in [0, 100].

        Returns:
            Mapping of percentile → terminal net worth.
        """
        values = sorted(r.terminal_net_worth for r in self.results)
        n = len(values)
        result: dict[float, float] = {}
        for p in percentiles:
            idx = int(p / 100.0 * n)
            result[p] = values[min(idx, n - 1)]
        return result

    def has_trajectories(self) -> bool:
        """Return True if trajectory data was captured for this run set."""
        return (
            self.store_trajectories
            and bool(self.results)
            and self.results[0].net_worth_trajectory is not None
        )

    def trajectory_array(self) -> list[list[float]]:
        """Return list of per-run net worth trajectories.

        Returns:
            List of lists, each inner list being net_worth over time for one run.
        """
        return [
            r.net_worth_trajectory
            for r in self.results
            if r.net_worth_trajectory is not None
        ]


class MonteCarloRunner:
    """Runs N independent retirement model simulations.

    Each run creates a fresh RetirementFinancialModel to prevent mutable
    asset state from leaking across runs. Stochasticity lives in
    Equity._asset_appreciation() via np.random.normal; no changes are
    needed to the asset code.
    """

    def __init__(
        self,
        config_file_path: str,
        asset_config_path: str,
        n_runs: int = 1000,
        random_seed: Optional[int] = None,
        store_trajectories: bool = False,
    ) -> None:
        """Initialise the Monte Carlo runner.

        Args:
            config_file_path: Path to the world config JSON.
            asset_config_path: Directory containing asset JSON files.
            n_runs: Number of simulation runs.
            random_seed: Optional seed for reproducible results.
            store_trajectories: If True, capture net_worth trajectory per run.
        """
        self.config_file_path = config_file_path
        self.asset_config_path = asset_config_path
        self.n_runs = n_runs
        self.random_seed = random_seed
        self.store_trajectories = store_trajectories

    def run(self) -> MonteCarloResults:
        """Execute all simulation runs and return aggregated results.

        Returns:
            MonteCarloResults containing per-run SimulationResult objects.
        """
        if self.random_seed is not None:
            np.random.seed(self.random_seed)

        results: list[SimulationResult] = []
        net_worth_idx: Optional[int] = None

        mc_bar = tqdm(range(self.n_runs), desc="Monte Carlo runs", unit="run")
        for run_id in mc_bar:
            # Fresh model instance per run — essential for state isolation.
            model = RetirementFinancialModel(self.config_file_path)
            model.setup(self.asset_config_path)
            mdata, mheader, _adata, _aheader = model.run_model(show_progress=False)

            if net_worth_idx is None:
                net_worth_idx = mheader.index("net_worth")

            net_worths = [row[net_worth_idx] for row in mdata]
            terminal_net_worth = net_worths[-1] if net_worths else 0.0

            ruin_period: Optional[int] = None
            for i, nw in enumerate(net_worths):
                if nw < 0:
                    ruin_period = i
                    break

            trajectory = net_worths if self.store_trajectories else None

            results.append(
                SimulationResult(
                    run_id=run_id,
                    terminal_net_worth=terminal_net_worth,
                    ruin_period=ruin_period,
                    net_worth_trajectory=trajectory,
                )
            )
            ruin_count = sum(1 for r in results if r.ruin_period is not None)
            mc_bar.set_postfix(
                ruin=f"{ruin_count}/{len(results)}",
                terminal=f"${terminal_net_worth:,.0f}",
            )
            logging.info(
                f"Monte Carlo run {run_id + 1}/{self.n_runs}: "
                f"terminal_net_worth={terminal_net_worth:,.0f}, "
                f"ruin={'yes (period ' + str(ruin_period) + ')' if ruin_period is not None else 'no'}"
            )

        return MonteCarloResults(
            n_runs=self.n_runs,
            results=results,
            store_trajectories=self.store_trajectories,
        )
