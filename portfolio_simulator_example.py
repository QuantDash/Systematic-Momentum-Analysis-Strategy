# portfolio_simulator_interface.py
class PortfolioSimulatorBase:
    """
    Interface for custom portfolio execution.
    Users must implement their own cash management and order routing.
    """
    def __init__(self, starting_capital: float, friction_rate: float):
        pass

    def execute_rebalance(self, target_weights: dict):
        raise NotImplementedError("Implement your broker/order-execution logic here.")