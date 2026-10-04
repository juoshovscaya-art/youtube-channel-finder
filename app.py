import streamlit as st

st.set_page_config(
    page_title="YouTube Channel Finder",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 YouTube Channel Finder")
st.write("Find promising YouTube channels using custom filters.")

st.divider()

st.subheader("🔐 YouTube API")

api_key = st.text_input(
    "Your YouTube API Key",
    type="password",
    placeholder="Paste your API key here"
)

with st.expander("How to get a free YouTube API key?"):
    st.write("""
    1. Open Google Cloud Console.
    2. Create a new project.
    3. Enable YouTube Data API v3.
    4. Create an API key.
    5. Restrict the key to YouTube Data API v3.
    """)

st.divider()

st.subheader("🔎 Search settings")

query = st.text_input(
    "Topic or search query",
    placeholder="Example: Ancient Egypt mysteries"
)

col1, col2 = st.columns(2)

with col1:
    max_subscribers = st.number_input(
        "Maximum subscribers",
        min_value=0,
        value=10000,
        step=1000
    )

    min_views = st.number_input(
        "Minimum views",
        min_value=0,
        value=20000,
        step=1000
    )

    min_videos = st.number_input(
        "Minimum videos on channel",
        min_value=0,
        value=10,
        step=1
    )

with col2:
    search_depth = st.selectbox(
        "Search depth",
        [50, 100, 250, 500],
        index=2
    )

    recent_videos = st.selectbox(
        "Recent videos to inspect",
        [10, 20, 30],
        index=1
    )

    content_type = st.selectbox(
        "Content type",
        ["Both", "Long-form", "Shorts"]
    )

upload_recency = st.selectbox(
    "Upload recency",
    ["30 days", "90 days", "365 days", "Any time"]
)

language = st.selectbox(
    "Language",
    ["Any", "English", "Ukrainian", "Russian", "Spanish", "German", "French"]
)

st.divider()

if st.button("🚀 Find channels", type="primary", use_container_width=True):
    if not api_key:
        st.warning("Please enter your YouTube API key.")
    elif not query:
        st.warning("Please enter a topic or search query.")
    else:
        st.success("Everything is ready! YouTube search will be connected next. 🚀")
