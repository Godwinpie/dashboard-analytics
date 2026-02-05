import requests
from django.core.management.base import BaseCommand
from django.conf import settings


# Manual user ID to name mapping
# To get user names, you need to:
# 1. Go to https://www.notion.so/my-integrations
# 2. Select your integration
# 3. Under "Capabilities", enable "Read user information including email addresses"
# 4. Re-run this command OR manually add mappings below
USER_MAPPING = {
    # Add your user mappings here:
    # "user-id-here": "User Name",
}


class Command(BaseCommand):
    help = "Get user details from Notion - lists all user IDs found in database"

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=str, help='Specific user ID to look up', default=None)
        parser.add_argument('--list-all', action='store_true', help='List all unique user IDs from database')

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        list_all = options.get('list_all', True)  # Default to list all
        
        # First try the Users API (requires additional permissions)
        self.stdout.write("Attempting to fetch user details from Notion Users API...")
        
        headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        
        # Try to list all users
        users_url = "https://api.notion.com/v1/users"
        users_response = requests.get(users_url, headers=headers, timeout=30)
        
        if users_response.status_code == 200:
            users_data = users_response.json()
            self.stdout.write(self.style.SUCCESS("\n✅ Users API access granted!\n"))
            
            for user in users_data.get("results", []):
                uid = user.get("id", "")
                name = user.get("name", "Unknown")
                email = user.get("person", {}).get("email", "N/A")
                user_type = user.get("type", "unknown")
                
                if user_id and uid != user_id:
                    continue
                    
                self.stdout.write(f"  ID: {uid}")
                self.stdout.write(f"  Name: {name}")
                self.stdout.write(f"  Email: {email}")
                self.stdout.write(f"  Type: {user_type}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  Users API access denied (403 Forbidden)\n"
                "\nTo enable user name lookup:\n"
                "1. Go to https://www.notion.so/my-integrations\n"
                "2. Select your integration\n"
                "3. Under 'Capabilities', enable 'Read user information including email addresses'\n"
                "4. Re-run this command\n"
            ))
            
            # Fallback: List all unique user IDs from database
            self.stdout.write(self.style.SUCCESS("\nFetching user IDs from database instead...\n"))
            
            db_url = f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query"
            response = requests.post(db_url, headers=headers, json={}, timeout=30)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Failed to fetch database: {response.status_code}"))
                return
            
            data = response.json()
            unique_users = set()
            
            # Collect all unique user IDs
            for page in data.get("results", []):
                props = page.get("properties", {})
                for field_name in ["Strategist", "Editor/Designer"]:
                    field = props.get(field_name, {})
                    if field.get("type") == "people" and field.get("people"):
                        for user in field["people"]:
                            uid = user.get("id", "")
                            if uid:
                                unique_users.add(uid)
            
            self.stdout.write(f"Found {len(unique_users)} unique user(s) in database:\n")
            
            for uid in sorted(unique_users):
                mapped_name = USER_MAPPING.get(uid, "Unknown (add to USER_MAPPING)")
                self.stdout.write(f'  "{uid}": "{mapped_name}",')

