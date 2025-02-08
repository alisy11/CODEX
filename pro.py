import os
import openai
import requests
import time
import random
import smtplib
import sqlite3
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# Secure API keys and credentials
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Initialize Database
def initialize_db():
    with sqlite3.connect("applications.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT,
                            company TEXT,
                            link TEXT UNIQUE,
                            status TEXT DEFAULT 'pending'
                        )''')
        conn.commit()

# Store Job Listings
def store_jobs(jobs):
    with sqlite3.connect("applications.db") as conn:
        cursor = conn.cursor()
        for job in jobs:
            try:
                cursor.execute("INSERT INTO jobs (title, company, link) VALUES (?, ?, ?)",
                               (job["title"], job["company"], job["link"]))
            except sqlite3.IntegrityError:
                pass  # Avoid duplicate job entries
        conn.commit()

# Fetch Pending Jobs
def fetch_pending_jobs():
    with sqlite3.connect("applications.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, company, link FROM jobs WHERE status='pending'")
        return cursor.fetchall()

# Update Job Status
def update_job_status(job_id, status):
    with sqlite3.connect("applications.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        conn.commit()

# Web Scraping with Selenium
def scrape_jobs():
    try:
        driver = webdriver.Chrome()
        driver.get("https://www.indeed.com/jobs?q=software+developer&l=remote")
        time.sleep(random.uniform(30, 60))
        jobs = driver.find_elements(By.CLASS_NAME, "job_seen_beacon")
        job_list = []
        for job in jobs:
            try:
                title = job.find_element(By.TAG_NAME, "h2").text.strip()
                company = job.find_element(By.CLASS_NAME, "companyName").text.strip()
                link = job.find_element(By.TAG_NAME, "a").get_attribute("href")
                job_list.append({"title": title, "company": company, "link": link})
            except NoSuchElementException:
                continue
    except WebDriverException as e:
        print(f"Web scraping failed: {e}")
        job_list = []
    finally:
        driver.quit()
    return job_list

# Generate Cover Letter using OpenAI API
def generate_cover_letter(job_title, company_name, job_description):
    if not OPENAI_API_KEY:
        print("Missing OpenAI API key")
        return ""
    openai.api_key = OPENAI_API_KEY
    prompt = f"Write a personalized cover letter for a {job_title} role at {company_name}. Job description: {job_description}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Failed to generate cover letter: {e}")
        return ""

# Auto-Fill Job Applications with Selenium
def apply_for_job(job_id, job_url, name, email, resume_path):
    try:
        driver = webdriver.Chrome()
        driver.get(job_url)
        time.sleep(random.uniform(30, 60))
        try:
            driver.find_element(By.NAME, "name").send_keys(name)
            driver.find_element(By.NAME, "email").send_keys(email)
            driver.find_element(By.XPATH, "//input[@type='file']").send_keys(resume_path)
            driver.find_element(By.XPATH, "//button[text()='Submit']").click()
            print(f"Application submitted for {job_url}")
            update_job_status(job_id, "applied")
        except NoSuchElementException:
            print(f"Elements not found for job application: {job_url}")
    except WebDriverException as e:
        print(f"Job application failed: {e}")
    finally:
        driver.quit()

# Send Follow-Up Emails
def send_follow_up_email(hr_email, job_title, company_name):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Email credentials not set.")
        return
    email = EmailMessage()
    email["Subject"] = f"Follow-up on {job_title} Application"
    email["From"] = EMAIL_USER
    email["To"] = hr_email
    email.set_content(f"Dear Hiring Manager,\n\nI wanted to follow up on my application for {job_title} at {company_name}. Looking forward to your response.\n\nBest regards,\nJohn Doe")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(email)
            print("Follow-up email sent.")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Run the Bot
def run_bot():
    initialize_db()
    jobs = scrape_jobs()
    store_jobs(jobs)
    pending_jobs = fetch_pending_jobs()
    for job in pending_jobs:
        job_id, title, company, link = job
        cover_letter = generate_cover_letter(title, company, "Job description here")
        if cover_letter:
            apply_for_job(job_id, link, "John Doe", "john.doe@example.com", "/path/to/resume.pdf")
            send_follow_up_email("hr@company.com", title, company)
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    run_bot()
