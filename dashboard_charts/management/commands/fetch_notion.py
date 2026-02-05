from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import time
import pandas as pd


class Command(BaseCommand):
    help = "Fetch data from Notion database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Notion fetch..."))

        url = f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query"

        headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        payload = {}
        all_results = []

        while True:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(response.text))
                break

            data = response.json()
            all_results.extend(data.get("results", []))

            if not data.get("has_more"):
                break

            payload["start_cursor"] = data.get("next_cursor")
            time.sleep(0.2)  # avoid rate limits

        self.stdout.write(
            self.style.SUCCESS(f"Fetched {len(all_results)} records from Notion")
        )

        self.process_results(all_results)

    def process_results(self, results):
        all_data = []
        
        for page in results:
            props = page.get("properties", {})
            
            # Extract and format each field
            formatted_data = {
                "Creative name": self.get_title(props.get("Creative name", {})),
                "Deadline": self.get_date(props.get("Deadline", {})),
                "Winner Market(s)": self.get_multi_select(props.get("Winner Market(s)", {})),
                "Strategist": self.get_people(props.get("Strategist", {})),
                "Format": self.get_select(props.get("Format", {})),
                "Winner": self.get_formula_string(props.get("Winner", {})),
                "Editing End Time": self.get_date(props.get("Editing End Time", {})),
                "Launch Date": self.get_date(props.get("Launch Date", {})),
                "Editing Start Time": self.get_date(props.get("Editing Start Time", {})),
                "Type": self.get_select(props.get("Type", {})),
                "Product": self.get_multi_select(props.get("Product", {})),
                "Status": self.get_status(props.get("Status", {})),
                "Editor/Designer": self.get_people(props.get("Editor/Designer", {})),
                "Editing Duration (minutes)": self.get_formula_string(props.get("Editing Duration (minutes)", {})),
                "Launch Month": self.get_formula_string(props.get("Launch Month", {})),
                "Ad time to ready (days)": self.get_formula_string(props.get("Ad time to ready (days) ", {})),
                "Launch YY-WW": self.get_formula_string(props.get("Launch YY-WW", {})),
            }
            
            all_data.append(formatted_data)
        
        # Create DataFrame
        df = pd.DataFrame(all_data)
        
        # Display DataFrame info
        self.stdout.write(self.style.SUCCESS(f"\nDataFrame created with {len(df)} rows"))
        self.stdout.write(f"\nColumns: {', '.join(df.columns.tolist())}")
        self.stdout.write(f"\n{df.to_string()}")
        
        return df
    
    def get_title(self, prop):
        """Extract title field"""
        if prop.get("type") == "title" and prop.get("title"):
            return prop["title"][0].get("plain_text", "")
        return ""
    
    def get_date(self, prop):
        """Extract date field"""
        if prop.get("type") == "date" and prop.get("date"):
            return prop["date"].get("start", "")
        return ""
    
    def get_multi_select(self, prop):
        """Extract multi_select field"""
        if prop.get("type") == "multi_select" and prop.get("multi_select"):
            return ",".join([item.get("name", "") for item in prop["multi_select"]])
        return ""
    
    def get_select(self, prop):
        """Extract select field"""
        if prop.get("type") == "select" and prop.get("select"):
            return prop["select"].get("name", "")
        return ""
    
    def get_people(self, prop):
        """Extract people field - returns names (Note: Notion API only returns IDs)"""

        if prop.get("type") == "people" and prop.get("people"):
            # Notion API returns user IDs, not names
            # You would need to fetch user details separately or maintain a mapping
            return prop["people"][0].get("name", "")
        return ""
    
    def get_status(self, prop):
        """Extract status field"""
        if prop.get("type") == "status" and prop.get("status"):
            return prop["status"].get("name", "")
        return ""
    
    def get_formula_string(self, prop):
        """Extract formula field (string or number)"""
        if prop.get("type") == "formula" and prop.get("formula"):
            formula = prop["formula"]
            if formula.get("type") == "string":
                return formula.get("string", "") or ""
            elif formula.get("type") == "number":
                num = formula.get("number")
                return str(num) if num is not None else ""
        return ""
