import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://outreach:outreach_dev@localhost:5432/outreach"

st.set_page_config(page_title="PT Outreach Dashboard", layout="wide")
st.title("PT Outreach Dashboard")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


# --- Sidebar filters ---
st.sidebar.header("Filters")

locations = run_query(
    "SELECT DISTINCT location FROM personal_trainers ORDER BY location"
)
location_list = ["All"] + locations["location"].tolist()
selected_location = st.sidebar.selectbox("Location", location_list)

gyms = run_query("SELECT DISTINCT gym_name FROM personal_trainers ORDER BY gym_name")
gym_list = ["All"] + gyms["gym_name"].tolist()
selected_gym = st.sidebar.selectbox("Gym", gym_list)


# --- Build where clause ---
where_parts: list[str] = []
params: dict = {}
if selected_location != "All":
    where_parts.append("pt.location = :location")
    params["location"] = selected_location
if selected_gym != "All":
    where_parts.append("pt.gym_name = :gym")
    params["gym"] = selected_gym
where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""


# --- KPI row ---
stats = run_query(f"""
    SELECT
        COUNT(DISTINCT pt.id) AS total_pts,
        COUNT(DISTINCT pt.gym_slug) AS total_gyms,
        COUNT(DISTINCT pt.location) AS total_locations,
        COUNT(DISTINCT oe.id) AS total_emails,
        COUNT(DISTINCT CASE WHEN pt.phone IS NOT NULL THEN pt.id END) AS with_phone,
        COUNT(DISTINCT CASE WHEN pt.email IS NOT NULL THEN pt.id END) AS with_email,
        COUNT(DISTINCT CASE WHEN pt.instagram_handle IS NOT NULL THEN pt.id END) AS with_instagram
    FROM personal_trainers pt
    LEFT JOIN outreach_emails oe ON oe.pt_profile_id = pt.id
    {where_clause}
""", params)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Personal Trainers", int(stats["total_pts"].iloc[0]))
c2.metric("Gyms", int(stats["total_gyms"].iloc[0]))
c3.metric("Locations", int(stats["total_locations"].iloc[0]))
c4.metric("Outreach Emails", int(stats["total_emails"].iloc[0]))

c5, c6, c7, _ = st.columns(4)
c5.metric("With Phone", int(stats["with_phone"].iloc[0]))
c6.metric("With Email", int(stats["with_email"].iloc[0]))
c7.metric("With Instagram", int(stats["with_instagram"].iloc[0]))


# --- Charts ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("PTs by Location")
    by_location = run_query(f"""
        SELECT pt.location, COUNT(*) AS count
        FROM personal_trainers pt
        {where_clause}
        GROUP BY pt.location ORDER BY count DESC
    """, params)
    if not by_location.empty:
        st.bar_chart(by_location.set_index("location"))

with col_right:
    st.subheader("PTs by Gym")
    by_gym = run_query(f"""
        SELECT pt.gym_name, COUNT(*) AS count
        FROM personal_trainers pt
        {where_clause}
        GROUP BY pt.gym_name ORDER BY count DESC LIMIT 20
    """, params)
    if not by_gym.empty:
        st.bar_chart(by_gym.set_index("gym_name"))


# --- Contact coverage ---
st.subheader("Contact Coverage")
coverage = run_query(f"""
    SELECT
        pt.location,
        COUNT(*) AS total,
        COUNT(pt.phone) AS has_phone,
        COUNT(pt.email) AS has_email,
        COUNT(pt.instagram_handle) AS has_instagram,
        COUNT(pt.whatsapp_number) AS has_whatsapp
    FROM personal_trainers pt
    {where_clause}
    GROUP BY pt.location ORDER BY total DESC
""", params)
if not coverage.empty:
    st.dataframe(coverage, use_container_width=True)


# --- Profiles table ---
st.subheader("Personal Trainers")
profiles = run_query(f"""
    SELECT
        pt.name, pt.gym_name, pt.location, pt.suburb,
        pt.phone, pt.email, pt.instagram_handle, pt.whatsapp_number,
        CASE WHEN oe.id IS NOT NULL THEN 'Yes' ELSE 'No' END AS has_outreach,
        pt.scraped_at
    FROM personal_trainers pt
    LEFT JOIN outreach_emails oe ON oe.pt_profile_id = pt.id
    {where_clause}
    ORDER BY pt.location, pt.gym_name, pt.name
""", params)
st.dataframe(profiles, use_container_width=True, height=400)


# --- Outreach emails ---
st.subheader("Generated Outreach Emails")
emails = run_query(f"""
    SELECT
        pt.name, pt.gym_name, pt.location,
        oe.subject, oe.body, oe.generated_at, oe.sent_at
    FROM outreach_emails oe
    JOIN personal_trainers pt ON pt.id = oe.pt_profile_id
    {where_clause}
    ORDER BY oe.generated_at DESC
    LIMIT 50
""", params)
if emails.empty:
    st.info("No outreach emails generated yet.")
else:
    for _, row in emails.iterrows():
        with st.expander(f"{row['name']} @ {row['gym_name']} — {row['subject']}"):
            st.text(row["body"])
