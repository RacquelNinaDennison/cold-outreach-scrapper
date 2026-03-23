# agent/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Send
from agent.state import GraphState
from agent.nodes import planner, scraper, aggregate, enrichment, store_notify

def should_retry(state: GraphState) -> str:
    if state["errors"] and state.get("retry_count", 0) < 2:
        return "planner"   # retry failed locations
    return "enrich"

def build_graph(checkpointer):
    g = StateGraph(GraphState)
    
    g.add_node("planner",       planner.planner)
    g.add_node("scrape_location", scraper.scrape_location)
    g.add_node("aggregate",     aggregate.aggregate)
    g.add_node("enrich",        enrichment.enrich)
    g.add_node("store_notify",  store_notify.store_and_notify)

    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", lambda s: [
        Send("scrape_location", {"location": loc, "run_id": s["run_id"]})
        for loc in s["locations"]
    ])
    g.add_edge("scrape_location", "aggregate")
    g.add_conditional_edges("aggregate", should_retry, {"planner": "planner", "enrich": "enrich"})
    g.add_edge("enrich", "store_notify")
    g.add_edge("store_notify", END)

    return g.compile(checkpointer=checkpointer)