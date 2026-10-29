import os.path
import base64
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json not found. Please provide Gmail API credentials.")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

@function_tool()
async def gmail_search_tool() -> str:
    """
    Checks for recent unread emails or emails received in the last 24 hours.
    Use this tool when the user says "mail", "check any mail", or "check incoming mail".
    """
    try:
        service = get_gmail_service()
        
        # Calculate timestamp for 24 hours ago
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        query = f'after:{int(yesterday.timestamp())} OR is:unread'
        
        results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            return "No recent unread or 24h emails found, Boss."

        summaries = []
        urgent_summaries = []
        
        urgent_keywords = ["urgent", "deadline", "boss", "client", "asap", "priority", "important"]

        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = m.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = "No Subject"
            sender = "Unknown Sender"
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']
            
            # Get a snippet (one-sentence overview)
            snippet = m.get('snippet', '')
            
            summary = f"📧 **From:** {sender}\n   **Subject:** {subject}\n   **Content:** {snippet}\n"
            
            # Check for urgency
            is_urgent = any(kw in subject.lower() or kw in snippet.lower() or kw in sender.lower() for kw in urgent_keywords)
            
            if is_urgent:
                urgent_summaries.append(f"🚨 **URGENT:**\n{summary}")
            else:
                summaries.append(summary)

        final_report = "Here is your mail summary, Boss:\n\n"
        if urgent_summaries:
            final_report += "⚠️ **Priority Alerts:**\n" + "\n".join(urgent_summaries) + "\n" + "-"*20 + "\n"
        
        if summaries:
            final_report += "\n".join(summaries)
        else:
            if not urgent_summaries:
                return "No recent emails found."

        return final_report

    except FileNotFoundError:
        return "❌ Error: `credentials.json` not found. Please set up the Gmail API credentials first."
    except Exception as e:
        return f"❌ Gmail Error: {str(e)}"

if __name__ == "__main__":
    import asyncio
    # For local testing
    async def test():
        print(await gmail_search_tool())
    asyncio.run(test())
