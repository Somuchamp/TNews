import streamlit as st
import sys
import io
import contextlib
from app.main import run_live, run_upcoming_matches, run_sample

# Configure the Streamlit page
st.set_page_config(
    page_title="TraceNews Pipeline",
    page_icon="📰",
    layout="centered"
)

# Custom CSS to make it look like a mobile app
st.markdown("""
<style>
    .main {
        max-width: 600px;
        margin: 0 auto;
    }
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
        background-color: #009270;
        color: white;
    }
    .stButton>button:hover {
        background-color: #007a5d;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("📰 TraceNews")
st.subheader("Automated Publishing Pipeline")
st.write("Tap a button below to trigger the AI pipeline. It will automatically fetch data, generate articles, and publish them to WordPress.")

st.divider()

task = st.radio(
    "Select what to publish:",
    ["Live Trends (Top 5)", "Upcoming Cricket Matches", "Test/Sample Payload"]
)

if st.button("🚀 Start Pipeline"):
    st.info("Pipeline is running... Please wait. This may take a few minutes.")
    
    # We will capture the print statements so the user can see them on their phone!
    log_output = st.empty()
    
    class StreamlitCapture:
        def __init__(self, placeholder):
            self.placeholder = placeholder
            self.logs = ""
            
        def write(self, text):
            # Streamlit updates the UI live as it receives text
            if text.strip():
                self.logs += text.strip() + "\n"
                self.placeholder.text_area("Pipeline Logs", self.logs, height=300)
                
        def flush(self):
            pass

    # Redirect standard output to our Streamlit component
    original_stdout = sys.stdout
    sys.stdout = StreamlitCapture(log_output)
    
    try:
        if task == "Live Trends (Top 5)":
            run_live(limit=5)
        elif task == "Upcoming Cricket Matches":
            run_upcoming_matches()
        elif task == "Test/Sample Payload":
            run_sample()
            
        st.success("✅ Pipeline completed successfully!")
        st.balloons()
    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
    finally:
        sys.stdout = original_stdout
