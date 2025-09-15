from typing import List, Dict

def get_frame_parameters(fixed_parameters: Dict[str, str], cmd_parameters: List[str]):
    net_parameters = {k: v for k, v in fixed_parameters.copy().items() if k in cmd_parameters}
    net_parameters.update({p: p for p in cmd_parameters})
    return net_parameters