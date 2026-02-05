import gspread
from django.conf import settings
import pandas as pd
import requests
import time


class GoogleSheetService:
    """Service class to read and analyze Google Sheet data"""
    
    def __init__(self):
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate using service account JSON file"""
        try:
            self.client = gspread.service_account(
                filename=settings.GOOGLE_SERVICE_ACCOUNT_FILE
            )
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
    
    def read_sheet_data(self):
        """Read all data from the configured sheet"""
        try:
            spreadsheet = self.client.open_by_key(settings.GOOGLE_SHEET_ID)
            worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_NAME)
            return worksheet.get_all_records()
        except Exception as e:
            raise Exception(f"Failed to read sheet: {str(e)}")
    
    def get_dataframe(self):
        """Get data as pandas DataFrame"""
        data = self.read_sheet_data()
        df = pd.DataFrame(data)
        
        # Convert date columns to datetime
        date_columns = ['Deadline', 'Launch Date', 'Editing Start Time', 'Editing End Time']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Convert numeric columns
        if 'Editing Duration (minutes)' in df.columns:
            df['Editing Duration (minutes)'] = pd.to_numeric(df['Editing Duration (minutes)'], errors='coerce')
        
        if 'Ad time to ready (days)' in df.columns:
            df['Ad time to ready (days)'] = pd.to_numeric(df['Ad time to ready (days)'], errors='coerce')
        
        return df
    
    def calculate_win_rate(self, df):
        """
        Calculate win rate from dataframe
        Formula: (Winner) / (Winner + Loser + Launched) * 100
        Note: Status='Winner' counts as winner
        """
        if df.empty:
            return 0
        
        # Count different statuses (case-insensitive)
        winners = len(df[df['Status'].str.lower() == 'winner'])
        losers = len(df[df['Status'].str.lower() == 'loser'])
        launched = len(df[df['Status'].str.lower() == 'launched'])
        
        total = winners + losers + launched
        if total == 0:
            return 0
        
        return round((winners / total) * 100, 2)


class NotionService:
    """Service class to fetch data from Notion databases"""
    
    def fetch_data(self, database_id=None, filters=None, sorts=None):
        url = f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query"

        headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        payload = {}
        all_results = []

        try:
            while True:
                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 401:
                    raise Exception("❌ Notion API authentication failed. Your API key may have expired or is invalid. Please check your NOTION_API_KEY in settings.")
                elif response.status_code == 404:
                    raise Exception("❌ Notion database not found. The database ID may be incorrect or the database may have been deleted. Please verify NOTION_DATABASE_ID in settings.")
                elif response.status_code == 403:
                    raise Exception("❌ Access denied to Notion database. Please ensure the integration has access to the database.")
                elif response.status_code == 429:
                    raise Exception("❌ Notion API rate limit exceeded. Please try again later.")
                elif response.status_code == 500:
                    raise Exception("❌ Notion API server error. Please try again later.")
                elif response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get('message', response.text)
                    raise Exception(f"❌ Notion API error (Status {response.status_code}): {error_msg}")

                data = response.json()
                all_results.extend(data.get("results", []))

                if not data.get("has_more"):
                    break

                payload["start_cursor"] = data.get("next_cursor")
                time.sleep(0.2)  # avoid rate limits
        
        except requests.exceptions.Timeout:
            raise Exception("❌ Notion API request timed out. Please check your internet connection and try again.")
        except requests.exceptions.ConnectionError:
            raise Exception("❌ Failed to connect to Notion API. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"❌ Network error while connecting to Notion: {str(e)}")
        except Exception as e:
            # Re-raise if already our custom exception
            if "❌" in str(e):
                raise
            # Otherwise wrap in generic error
            raise Exception(f"❌ Error fetching data from Notion: {str(e)}")

        if not all_results:
            raise Exception("⚠️ No data found in Notion database. The database may be empty.")

        df = self.process_results(all_results)
        
        # Convert date columns to datetime
        date_columns = ['Deadline', 'Launch Date', 'Editing Start Time', 'Editing End Time']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Convert numeric columns
        if 'Editing Duration (minutes)' in df.columns:
            df['Editing Duration (minutes)'] = pd.to_numeric(df['Editing Duration (minutes)'], errors='coerce')
        
        if 'Ad time to ready (days)' in df.columns:
            df['Ad time to ready (days)'] = pd.to_numeric(df['Ad time to ready (days)'], errors='coerce')
        
        return df
    
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

    def calculate_win_rate(self, df):
        """
        Calculate win rate from dataframe
        Formula: (Winner) / (Winner + Loser + Launched) * 100
        Note: Status='Winner' counts as winner
        """
        if df.empty:
            return 0
        
        # Count different statuses (case-insensitive)
        winners = len(df[df['Status'].str.lower() == 'winner'])
        losers = len(df[df['Status'].str.lower() == 'loser'])
        launched = len(df[df['Status'].str.lower() == 'launched'])
        
        total = winners + losers + launched
        if total == 0:
            return 0
        
        return round((winners / total) * 100, 2)