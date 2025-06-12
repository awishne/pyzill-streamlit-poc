import streamlit as st
import pyzill
import pandas as pd
from json.decoder import JSONDecodeError

st.title("🔍 Zillow Rental POC")

loc   = st.text_input("Location (ZIP / city / address)", "60614")
beds  = st.number_input("Min beds",   min_value=0, max_value=10, value=1)
baths = st.number_input("Min baths",  min_value=0, max_value=10, value=1)

# 1°: Hard-code a small bounding box around your target:
#     (for Chicago 60614, approx.)
ne_lat, ne_long = 41.995, -87.65
sw_lat, sw_long = 41.85,  -87.75
zoom = 12

if st.button("Search"):
    with st.spinner("Fetching listings…"):
        try:
            results = pyzill.for_rent(
                1,
                search_value=loc or None,
                is_entire_place=True,   # whole unit
                is_room=False,          # not just a room
                min_beds=beds or None,
                max_beds=None,
                min_bathrooms=baths or None,
                max_bathrooms=None,
                min_price=None,         # no price floor
                max_price=None,         # no price ceiling
                ne_lat=ne_lat,          # REQUIRED
                ne_long=ne_long,        # REQUIRED
                sw_lat=sw_lat,          # REQUIRED
                sw_long=sw_long,        # REQUIRED
                zoom_value=zoom,
                proxy_url=None          # skip proxy for POC
            )
            if not results:
                st.warning("No results—try a different area or loosen your filters.")
            else:
                df = pd.DataFrame(results)
                st.dataframe(df)
        except JSONDecodeError:
            st.error("❌ Failed to parse JSON—Zillow likely returned an HTML error page.")
            st.write("Try adjusting your bounding box or adding a proxy.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
