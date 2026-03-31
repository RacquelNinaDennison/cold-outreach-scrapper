"""LLM-powered outreach email generation for scraped PT profiles."""

from langchain_anthropic import ChatAnthropic

from db import AsyncSessionLocal
from db.crud import get_profiles_without_outreach
from db.models import OutreachEmail
from settings import settings

OUTREACH_PROMPT = """\
Write a short, personalized cold outreach email to {name}, a personal trainer \
at {gym_name} ({suburb}).

Their qualifications: {qualifications}.

The email is from a fitness-tech company offering a platform that helps personal \
trainers grow their client base through digital presence and automated scheduling. \
Keep the tone friendly and professional. Reference their specific gym and \
qualifications naturally. Include a clear but soft call to action.

Output ONLY the email with a subject line on the first line prefixed with \
"Subject: ", then a blank line, then the body. No extra commentary."""


async def generate_outreach(location: str) -> list[OutreachEmail]:
    """Generate outreach emails for all profiles in a location that don't have one yet."""
    llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0.7,
        api_key=settings.anthropic_api_key,
    )

    created: list[OutreachEmail] = []

    async with AsyncSessionLocal() as session:
        profiles = await get_profiles_without_outreach(session, location)
        print(f"Generating outreach for {len(profiles)} profiles...")

        for pt in profiles:
            quals = ", ".join(pt.qualifications) if pt.qualifications else "General fitness"
            suburb = pt.suburb or pt.gym_name

            prompt = OUTREACH_PROMPT.format(
                name=pt.name,
                gym_name=pt.gym_name,
                suburb=suburb,
                qualifications=quals,
            )

            response = await llm.ainvoke(prompt)
            text = response.content.strip()

            # Parse subject and body
            if text.startswith("Subject:"):
                lines = text.split("\n", 1)
                subject = lines[0].replace("Subject:", "").strip()
                body = lines[1].strip() if len(lines) > 1 else ""
            else:
                subject = f"Quick question for {pt.name}"
                body = text

            email = OutreachEmail(
                pt_profile_id=pt.id,
                subject=subject,
                body=body,
            )
            session.add(email)
            created.append(email)
            print(f"  Generated email for {pt.name}")

        await session.commit()

    print(f"Generated {len(created)} outreach emails")
    return created
