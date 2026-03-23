from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from tools.playwright_tools import navigate, extract_pt_cards, paginate, screenshot
from settings import Settings 
with open("skills/virgin_active.md") as f:
    SKILL = f.read()

llm = ChatAnthropic(model="claude-sonnet-4-5-20251022", temperature=0)

_agent = create_react_agent(
    llm,
    tools=[navigate, extract_pt_cards, paginate, screenshot],
    prompt=SKILL      # skill file = system prompt = domain knowledge
)

def parse_agent_output(output, location) -> list[dict]:
    # This is a stub parser — in production, you'd want robust parsing and error handling
    # The agent is prompted to return JSON, so we can eval() it safely here
    try:
        profiles = eval(output)  # expect a list of dicts with PT info
        for p in profiles:
            p["location"] = location  # add location context to each profile
        return profiles
    except Exception as e:
        print(f"Error parsing agent output: {e}")
        return []
    

async def run(state: dict) -> dict:
    # state here is the sub-state slice from Send()
    # it only contains {location, run_id} — not the full GraphState
    location = state["location"]

    result = await _agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": f"Scrape all PTs at Virgin Active gyms in {location}, South Africa."
        }]
    })

    profiles = parse_agent_output(result, location)

    # This dict gets merged into GraphState.raw_profiles
    # via the operator.add reducer — it appends, never overwrites
    return {"raw_profiles": profiles}