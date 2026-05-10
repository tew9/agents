import os
from typing import Dict
import sendgrid 
from sendgrid.helpers.mail import Mail, Email, To, Content
from agents import Agent, function_tool 

@function_tool
def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """ Send out an email with the given subject and HTML body """
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("tangotew@gmail.com")
    to_email = To("tangogatdet76@gmail.com")
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print("Email response status code:", response.status_code)
    return {"status": "success", "response_code": response.status_code}
  
INSTRUCTIONS = """You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line."""

email_agent = Agent(
    name="Email Agent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    tools=[send_email],
    handoff_description="Use the send_email tool to send out an email with the report. The subject line should be 'Research Report: {short_summary}', where {short_summary} is a concise summary of the report. The body of the email should be the markdown_report converted into clean, well formatted HTML.",
)