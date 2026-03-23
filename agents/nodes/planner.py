from langgraph.types import Send
from agent.state import GraphState

def planner(state: GraphState) -> list[Send]:
    """
    Returns a list of Send actions based on the current state of the graph.
    
    """

    return [
        Send("scrape_locations", {"locations": loc, "run_id": state["run_id"]}) for loc in state["locations"]
    ]