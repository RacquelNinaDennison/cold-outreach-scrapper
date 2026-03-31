import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from tools.playwright_tools import navigate, extract_pt_cards, paginate, screenshot, click, fill, get_page_content, evaluate_js, close_browser
from settings import Settings

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "virgin-active-pt-scraper" / "SKILLS.md"


def _build_agent():
    skill = SKILL_PATH.read_text()
    settings = Settings()
    llm = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0, api_key=settings.anthropic_api_key)
    return create_react_agent(
        llm,
        tools=[navigate, click, fill, evaluate_js, get_page_content, extract_pt_cards, paginate, screenshot],
        prompt=skill,
    )


async def run(state: dict) -> dict:
    agent = _build_agent()
    location = state["location"]

    inputs = {
        "messages": [{
            "role": "user",
            "content": f"Scrape all PTs at Virgin Active gyms in {location}, South Africa."
        }]
    }

    # Collect profiles directly from extract_pt_cards tool results
    all_profiles = []

    try:
        async for chunk in agent.astream(inputs, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                messages = node_output.get("messages", [])
                for msg in messages:
                    if msg.type == "ai":
                        # Print agent reasoning
                        if isinstance(msg.content, str) and msg.content:
                            print(f"\n[Agent]: {msg.content}")
                        elif isinstance(msg.content, list):
                            for block in msg.content:
                                if hasattr(block, "get"):
                                    if block.get("type") == "text" and block.get("text"):
                                        print(f"\n[Agent]: {block['text']}")
                        # Print tool calls
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"\n--- Tool call: {tc['name']}({json.dumps(tc.get('args', {}))})")

                    elif msg.type == "tool":
                        output_str = str(msg.content)
                        if len(output_str) > 300:
                            output_str = output_str[:300] + "..."
                        print(f"--- Tool result ({msg.name}): {output_str}\n")

                        # Capture profiles from tool results that return PT data
                        if msg.name in ("extract_pt_cards", "evaluate_js"):
                            try:
                                data = json.loads(msg.content)
                                # Accept a list of dicts that look like PT profiles
                                if isinstance(data, list) and data and isinstance(data[0], dict):
                                    # Heuristic: PT profiles have keys like trainer_id, phone, email, etc.
                                    pt_keys = {"trainer_id", "phone", "email", "qualifications", "whatsapp", "name"}
                                    if pt_keys & set(data[0].keys()):
                                        for p in data:
                                            p["location"] = location
                                        all_profiles.extend(data)
                                        print(f"  >> Captured {len(data)} profiles (total: {len(all_profiles)})")
                                        # Save progress to disk so data survives crashes
                                        with open(f"profiles_{location.replace(' ', '_')}.json", "w", encoding="utf-8") as f:
                                            json.dump(all_profiles, f, ensure_ascii=False, indent=2)
                            except (json.JSONDecodeError, TypeError):
                                pass
    finally:
        await close_browser()

    print(f"\n=== Done. {len(all_profiles)} profiles scraped for {location} ===")
    return {"raw_profiles": all_profiles}
