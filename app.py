from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from root_agent import root_agent

APP_NAME = "fortimanager_health_agents"
print("")
# ADK Web needs a session service
session_service = InMemorySessionService()

# ADK Web looks for this variable
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)
