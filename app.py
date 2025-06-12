import streamlit as st
from homeharvest import scrape_property
import pandas as pd
import requests
import math

# Haversine formula to compute distance in miles
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

st.set_page_config(page_title="HomeHarvest Rentals — POC", layout="wide")
st.title("🏠 HomeHarvest Rental Listings")

# Sidebar filters
st.sidebar.header("Search Rentals (Active Only)")
location   = st.sidebar.text_input("Location (address / city / ZIP)", "60614")
min_beds   = st.sidebar.number_input("Min Beds", min_value=0, max_value=10, value=0)
min_baths  = st.sidebar.number_input("Min Baths", min_value=0, max_value=10, value=0)
property_types = st.sidebar.multiselect(
    "Property Type (optional)",
    options=["single_family","multi_family","condos","condo_townhome",
             "townhomes","duplex_triplex","farm","land","mobile"],
    help="Select one or more types"
)
radius     = st.sidebar.number_input("Radius (miles)", 0.0, 100.0, 10.0, step=1.0)
past_days  = st.sidebar.number_input("Listed in last (days)", 1, 365, 30)
limit      = st.sidebar.number_input("Max Results", 1, 1000, 100, step=50)
extra_data = st.sidebar.checkbox("Include Extra Data (e.g. schools)", value=False)

if st.sidebar.button("Search Rentals"):
    # 1) Geocode via Census API
    with st.spinner("Geocoding location…"):
        try:
            resp = requests.get(
                "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                params={"address": location,
                        "benchmark": "Public_AR_Census2020",
                        "format": "json"},
                timeout=5
            ).json()
            matches = resp.get("result", {}).get("addressMatches", [])
            if matches:
                coord = matches[0]["coordinates"]
                center_lat, center_lon = coord["y"], coord["x"]
            else:
                center_lat = center_lon = None
        except Exception:
            center_lat = center_lon = None

    # 2) Fetch rental listings
    with st.spinner("Fetching rental listings…"):
        try:
            props = scrape_property(
                location=location,
                listing_type="for_rent",               # rentals only
                property_type=property_types or None,
                past_days=past_days,
                limit=limit,
                proxy=None,
                extra_property_data=extra_data
            )
            df = pd.DataFrame(props)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning("No rentals found. Try adjusting filters or expanding radius.")
    else:
        # 3) Clean & cast numeric columns
        df['beds'] = pd.to_numeric(df['beds'], errors='coerce').fillna(0).astype(int)
        df['full_baths'] = pd.to_numeric(df['full_baths'], errors='coerce').fillna(0)
        df['half_baths'] = pd.to_numeric(df['half_baths'], errors='coerce').fillna(0)
        df['baths'] = df['full_baths'] + df['half_baths']

        # 4) Filter by min beds/baths
        df = df[df['beds']  >= min_beds]
        df = df[df['baths'] >= min_baths]

        # 5) Filter by radius (if geocoded and lat/lon exist)
        if center_lat is not None and 'latitude' in df and 'longitude' in df:
            df['distance'] = df.apply(
                lambda r: haversine(center_lat, center_lon,
                                    r['latitude'], r['longitude']),
                axis=1
            )
            df = df[df['distance'] <= radius]

        # 6) Display as a nice list of cards
        st.markdown(f"### {len(df)} Rentals Found")
        for i, row in df.iterrows():
            # Build display values
            addr = row.get('street', '')
            unit = row.get('unit')
            city = row.get('city', '')
            zipc = row.get('zip_code', '')
            link = row.get('property_url')
            title = f"{addr}{(' ' + unit) if unit else ''}, {city} {zipc}"

            st.markdown(f"#### [{title}]({link})")
            cols = st.columns(4)
            cols[0].write(f"**Price:** {row.get('list_price','N/A')}")
            cols[1].write(f"**Beds:** {row['beds']}")
            cols[2].write(f"**Baths:** {int(row['baths'])}")
            cols[3].write(f"**Sqft:** {row.get('sqft','N/A')}")

            ag_col, of_col = st.columns(2)
            ag_col.write(f"**Agent:** {row.get('agent_name','N/A')}")
            ag_col.write(f"**Email:** {row.get('agent_email','N/A')}")
            of_col.write(f"**Office:** {row.get('office_name','N/A')}")
            of_col.write(f"**Office Email:** {row.get('office_email','N/A')}")

            # Email template button
            if st.button(f"Generate Email to {row.get('agent_name','Agent')}", key=f"email_{i}"):
                template = (
                    f"Subject: Inquiry: {row['beds']}-bed rental at {addr}, {city}\n\n"
                    f"Hi {row.get('agent_name','')},\n\n"
                    f"I’m reaching out from [Your Company]. I saw your listing at {addr}, {city} "
                    f"for ${row.get('list_price','')} per month. Would you consider a short-term "
                    f"(1–3 month) lease?\n\n"
                    f"Please let me know if that’s possible.\n\n"
                    f"Thank you,\n[Your Name]"
                )
                st.text_area("Email Template", template, height=180)

            st.markdown("---")
