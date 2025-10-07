from ...imports import *

class AlgoInverseFrequencyWeight(BaseModel):
    lambda_: float = 1.0
    a_: float = 1.0

class AlgoLogInverseFrequencyWeight(BaseModel):
    lambda_: float = 1.0
    log_a_: float = 1.0
    a_: float = 1.0

rand_showcase_algo_parser = typer.Typer()

@rand_showcase_algo_parser.command("IFW")
def ifw(
    lambda_: float = typer.Option(
        1.0, "--lambda", "-l", min=0.0, max=5.0,
        help="正则化幂变换系数，默认 1.0，高则均匀"
    ),
    a_: float = typer.Option(
        1.0, "--a", "-a", min=0.1,
        help="冷启动平滑稀疏，默认 1，高则启动时方差大"
    )
) -> AlgoInverseFrequencyWeight:
    return AlgoInverseFrequencyWeight(lambda_=lambda_, a_=a_)

@rand_showcase_algo_parser.command("LogIFW")
def log_ifw(
    lambda_: float = typer.Option(
        1.0, "--lambda", "-l", min=0.0, max=5.0,
        help="正则化幂变换系数，默认 1.0，高则均匀"
    ),
    log_a_: float = typer.Option(
        1.0, "--log_a", "-la", min=0.1,
        help="对数平滑稀疏，默认 1，高则整体拉回力度小，方差大"
    ),
    a_: float = typer.Option(
        1.0, "--a", "-a", min=0.1,
        help="冷启动平滑稀疏，默认 1，高则启动时方差大"
    )
) -> AlgoLogInverseFrequencyWeight:
    return AlgoLogInverseFrequencyWeight(lambda_=lambda_, log_a_=log_a_, a_=a_)
