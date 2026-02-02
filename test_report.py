import os
from tools import generate_monthly_report

# Ensure .env is loaded if needed
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    result = generate_monthly_report.invoke({})
    print("Test Result:")
    print(result)