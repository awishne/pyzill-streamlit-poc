import streamlit as st
from homeharvest import scrape_property
import pandas as pd

st.set_page_config(page_title="HomeHarvest Rental Search", layout="wide")
st.title("🏠 HomeHarvest Rental Search — Rentals Only")

# Sidebar filters (rentals only)
st.sidebar.header("Search Filters")
location = st.sidebar.text_input("Location (address / city / ZIP)", "60614")

property_types = st.sidebar.multiselect(
    "Property Type (optional)", 
    options=[
        "single_family", "multi_family", "condos", "condo_townhome", 
        "townhomes", "duplex_triplex", "farm", "land", "mobile"
    ],
    help="Select one or more property types"
)
radius = st.sidebar.number_input(
    "Radius (miles)", min_value=0.0, max_value=100.0,
    value=10.0, step=1.0,
    help="Search radius around the location"
)
past_days = st.sidebar.number_input(
    "Listed in last (days)", min_value=1, max_value=365,
    value=30,
    help="Fetch rentals listed in the past X days"
)
limit = st.sidebar.number_input(
    "Max Results", min_value=1, max_value=1000,
    value=100, step=50,
    help="Limit the number of listings returned"
)
extra_data = st.sidebar.checkbox(
    "Include Extra Property Data", value=False,
    help="Fetch additional details (e.g. tax, schools)"
)

if st.sidebar.button("Search Rentals"):
    with st.spinner("Fetching rental listings…"):
        try:
            props = scrape_property(
                location=location,
                listing_type="for_rent",               # fixed to rentals
                property_type=property_types or None,
                radius=radius,
                past_days=past_days,
                limit=limit,
                proxy=None,
                extra_property_data=extra_data
            )
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            props = pd.DataFrame()

    if props.empty:
        st.warning("No rental listings found. Adjust filters or expand radius.")
    else:
        # Map columns to user-friendly names
        display_cols = {
            "property_url": "URL",
            "list_price": "Price",
            "beds": "Beds",
            "full_baths": "Full Baths",
            "half_baths": "Half Baths",
            "sqft": "Sqft",
            "agent_name": "Agent",
            "agent_email": "Agent Email",
            "office_name": "Office",
            "office_phones": "Office Phones",
            "office_email": "Office Email"
        }
        df = pd.DataFrame(props)
        df = df[list(display_cols.keys())].rename(columns=display_cols)
        # Render clickable URLs
        df['URL'] = df['URL'].apply(lambda u: f"[Link]({u})")

        st.markdown(f"### {len(df)} active rentals found")
        st.dataframe(df, use_container_width=True)
