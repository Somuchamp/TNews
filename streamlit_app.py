import streamlit as st
import sys
import io
import contextlib
from app.main import run_live, run_upcoming_matches, run_sample

# Configure the Streamlit page
st.set_page_config(
    page_title="TraceNews Auto",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Advanced CSS for a premium, modern "Frontend Developer" look
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"]  {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main Container (Simulating Mobile App Frame) */
    .block-container {
        max-width: 650px !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Gradient Title */
    .title-text {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: -10px;
    }
    
    .subtitle-text {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }

    /* Customizing the "Start Pipeline" Button */
    .stButton>button {
        width: 100%;
        height: 65px;
        font-size: 22px;
        font-weight: 700;
        border-radius: 16px;
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        border: none;
        box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3);
        transition: all 0.3s ease;
        margin-top: 20px;
    }
    
    /* Button Hover/Active Animations */
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 25px rgba(79, 172, 254, 0.4);
        color: white;
        border: none;
    }
    .stButton>button:active {
        transform: translateY(1px);
        box-shadow: 0 5px 15px rgba(79, 172, 254, 0.3);
    }
    .stButton>button:focus {
        box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3);
        color: white;
    }

    /* Styling the Radio Buttons and Select Boxes */
    .stRadio > label {
        font-weight: 600 !important;
        font-size: 1.2rem !important;
    }
    
    .stSelectbox > label {
        font-weight: 600 !important;
    }
    
    /* Adding a Glassmorphism Panel effect around inputs */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Text Area (Logs) Customization */
    .stTextArea textarea {
        background-color: #1e1e1e !important;
        color: #00ff00 !important;
        font-family: 'Courier New', Courier, monospace !important;
        border-radius: 12px !important;
        border: 1px solid #333 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-text">⚡ TraceNews</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Automated Publishing AI</p>', unsafe_allow_html=True)

st.divider()

task = st.radio(
    "Select what to publish:",
    ["Live Trends", "Upcoming Cricket Matches", "Test/Sample Payload"]
)

# Only show these filters if Live Trends is selected
if task == "Live Trends":
    st.markdown("#### Trend Filters")
    col1, col2 = st.columns(2)
    with col1:
        countries = {
            "India": "IN", "United States": "US", "United Kingdom": "GB", 
            "Australia": "AU", "Canada": "CA", "Global": ""
        }
        selected_country_name = st.selectbox("Country", list(countries.keys()))
        selected_geo = countries[selected_country_name]
        
    with col2:
        categories = {
            "All Categories": "all",
            "Business": "b",
            "Entertainment": "e",
            "Health": "m",
            "Science/Tech": "t",
            "Sports": "s",
            "Top Stories": "h"
        }
        selected_cat_name = st.selectbox("Category", list(categories.keys()))
        selected_category = categories[selected_cat_name]
        
    st.markdown("#### Settings")
    target_posts = st.slider("Target Number of Articles to Post", min_value=1, max_value=20, value=5, 
                             help="The pipeline will keep fetching and evaluating trends, skipping irrelevant ones, until it successfully posts this many articles.")
else:
    selected_geo = "IN"
    selected_category = "all"
    target_posts = 5

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
        if task == "Live Trends":
            run_live(target_posts=target_posts, geo=selected_geo, category=selected_category)
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
