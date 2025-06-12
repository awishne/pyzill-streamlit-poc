import streamlit as st
import pyzill
import pandas as pd
import requests
from json.decoder import JSONDecodeError

st.set_page_config(page_title="Pyzill POC", layout="wide")
st.title("🔍 Zillow Rental POC with Auto-Bounds")

loc   = st.text_input("Location (ZIP / city / address)", "60614")
beds  = st.number_input("Min beds",   min_value=0, max_value=10, value=1)
baths = st.number_input("Min baths",  min_value=0, max_value=10, value=1)

if st.button("Search"):
    with st.spinner("1) Geocoding your location…"):
        # 1. Call OpenStreetMap Nominatim
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": loc, "format": "json", "limit": 1},
            headers={"User-Agent": "Streamlit POC"}
        ).json()
    if not geo:
        st.error("🚫 Could not geocode that location. Try something more specific.")
    else:
        lat = float(geo[0]["lat"])
        lon = float(geo[0]["lon"])
        delta = 0.02  # ~2 km box; tweak as needed

        ne_lat, ne_long = lat + delta, lon + delta
        sw_lat, sw_long = lat - delta, lon - delta

        with st.spinner("2) Fetching Zillow rentals…"):
            try:
                results = pyzill.for_rent(
                    1,
                    search_value=loc or None,
                    is_entire_place=True,
                    is_room=False,
                    min_beds=beds or None,
                    max_beds=None,
                    min_bathrooms=baths or None,
                    max_bathrooms=None,
                    min_price=None,
                    max_price=None,
                    ne_lat=ne_lat,
                    ne_long=ne_long,
                    sw_lat=sw_lat,
                    sw_long=sw_long,
                    zoom_value=12,
                    proxy_url=None   # skip proxy for light POC
                )
                if not results:
                    st.warning("No listings found—try broadening your search or increasing `delta`.")
                else:
                    df = pd.DataFrame(results)
                    st.dataframe(df)
            except JSONDecodeError:
                st.error("❌ Zillow returned invalid JSON (probably blocked).")
                st.write("You may need to add a proxy or slow down requests.")
            except Exception as e:
                st.error(f"Unexpected error from PyZill: {e}")
