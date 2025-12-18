"""Track iteration history for debugging and inspection"""
import time
from typing import List, Dict, Any


class IterationHistory:
    """
    Records what happened in each iteration for debugging and inspection.

    IMPORTANT: This does NOT manage Claude's context accumulation - that's
    handled automatically by 'claude -c'. This class just records iteration
    results so you can inspect what happened later.

    Use case: Debugging failed sessions, analyzing iteration patterns,
    understanding how the atom solved the problem.
    """

    def __init__(self):
        self.iterations: List[Dict[str, Any]] = []

    def add_iteration(self, iteration: int, result: Dict[str, Any]):
        """
        Record an iteration's result.

        Args:
            iteration: Iteration number
            result: Result dict with 'stdout', 'returncode', etc.
        """
        self.iterations.append({
            "iteration": iteration,
            "stdout": result.get("stdout", ""),
            "returncode": result.get("returncode", -1),
            "timestamp": time.time()
        })

    def get_all_iterations(self) -> List[Dict[str, Any]]:
        """Get complete iteration history"""
        return self.iterations

    def get_summary(self) -> str:
        """Get human-readable summary"""
        if not self.iterations:
            return "No iterations recorded"

        total = len(self.iterations)
        successes = sum(1 for it in self.iterations if it.get("returncode") == 0)

        return f"{total} iterations: {successes} successful, {total - successes} with errors"

    def get_last_iteration(self) -> Dict[str, Any]:
        """Get the most recent iteration, or empty dict if none"""
        return self.iterations[-1] if self.iterations else {}
