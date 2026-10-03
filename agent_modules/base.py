from dataclasses import dataclass, field


@dataclass
class Finding:
    agent: str
    summary: str
    severity: str = "info"  # info | warn | critical
    confidence: float = 0.5
    data: dict = field(default_factory=dict)


class Agent:
    name = "agent"

    def run(self, case: dict, ctx: dict) -> Finding:
        raise NotImplementedError
