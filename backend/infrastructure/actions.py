from typing import Dict

class Action():
    def __init__(
            self, 
            service_name: str,
            actions: Dict[str, Dict[str, str]]
            
            ):
        self.service_name = service_name
        self.actions = actions
        self.categories = self.actions.keys()
        self.curr_action = ""
        self.curr_cmd = ""
        self.curr_params = []
        