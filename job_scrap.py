import streamlit as st
import sys
import os
import stat
import logging
from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import Events, EventData, EventMetrics
from linkedin_jobs_scraper.query import Query, QueryOptions, QueryFilters
from linkedin_jobs_scraper.filters import RelevanceFilters, TimeFilters, TypeFilters, ExperienceLevelFilters, \
    OnSiteOrRemoteFilters, SalaryBaseFilters

from threading import Event
import pandas as pd
from selenium.webdriver.chrome.options import Options  # Import Options

# Streamlit App Title
st.title("🔍 LinkedIn Job Scraper")

# Inputs
job_role = st.text_input("Enter Job Title")
job_location = st.text_input("Enter Location")
job_count = st.text_input("Enter Job Count", "10")  # Default to 10
start_scraping = st.button("Start Scraping")

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Setup chrome driver path for Linux and Windows
if sys.platform.startswith("win"):
    chrome_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    chrome_options = None
else:
    chrome_driver_path = os.path.join(os.getcwd(), "chromedriver")
    # Ensure the Linux driver is executable
    if not os.access(chrome_driver_path, os.X_OK):
        os.chmod(chrome_driver_path, os.stat(chrome_driver_path).st_mode | stat.S_IEXEC)
    
    # Create Chrome options instance
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--remote-debugging-port=9222")

# For collecting data
job_results = []
scraping_done = Event()

def on_data(data: EventData):
    job_results.append({
        "Job Title": data.title,
        "Company": data.company,
        "Location": data.place,
        "Posted": data.date_text,
        "Apply Link": data.link,
        "Insights": data.insights,
    })

def on_metrics(metrics: EventMetrics):
    pass

def on_error(error):
    st.error(f"[ERROR] {error}")

def on_end():
    scraping_done.set()

if start_scraping:
    # Clear previous results
    job_results.clear()
    scraping_done.clear()

    if not job_role or not job_location:
        st.warning("Please enter both job title and location.")
    else:
        try:
            # Ensure job_count is a valid integer
            job_count = int(job_count)
            if job_count <= 0:
                raise ValueError("Job count must be a positive integer.")
        except ValueError as e:
            st.error(f"[ERROR] {e}")
            job_count = 10  # Default to 10 if invalid value is entered

        scraper = LinkedinScraper(
            chrome_executable_path=chrome_driver_path,
            chrome_binary_location=None,
            chrome_options=chrome_options,  # Pass Options object here
            headless=True,
            max_workers=1,
            slow_mo=0.5,
            page_load_timeout=40
        )

        scraper.on(Events.DATA, on_data)
        scraper.on(Events.ERROR, on_error)
        scraper.on(Events.END, on_end)

        query = Query(
            query=job_role,
            options=QueryOptions(
                locations=[job_location],
                apply_link=True,
                skip_promoted_jobs=True,
                limit=job_count,
                filters=QueryFilters(
                    relevance=RelevanceFilters.RECENT,
                    time=TimeFilters.MONTH,
                    type=[TypeFilters.FULL_TIME, TypeFilters.INTERNSHIP],
                    on_site_or_remote=[OnSiteOrRemoteFilters.REMOTE],
                    experience=[ExperienceLevelFilters.MID_SENIOR],
                    base_salary=SalaryBaseFilters.SALARY_100K
                )
            )
        )

        with st.spinner(f"Scraping LinkedIn jobs for '{job_role}' in '{job_location}'..."):
            scraper.run([query])
            scraping_done.wait()

        if job_results:
            df = pd.DataFrame(job_results)
            st.success(f"✅ Found {len(df)} jobs for '{job_role}' in '{job_location}'!")
            st.dataframe(df)
        else:
            st.warning("No jobs found. Try changing the title or location.")
