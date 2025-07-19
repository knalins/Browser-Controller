# Browser Control Agent
# A conversational AI that can control browsers using natural language

import asyncio
import base64
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
from contextlib import asynccontextmanager

import google.generativeai as genai
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserControlAgent:
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash') # Changed to a valid, recent model
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Conversation context
        self.conversation_history = []
        self.current_task = None
        self.task_state = {}
        
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
            headless=False,
            channel="chrome",  # <-- ADD THIS LINE
            args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            # self.browser = await self.playwright.chromium.launch(
            #     headless=False,  # Show browser for demo purposes
            #     args=['--no-sandbox', '--disable-dev-shm-usage']
            # )
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            self.page = await self.context.new_page()
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser resources closed successfully.")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def take_screenshot(self) -> str:
        """Take screenshot and return as base64 string"""
        if not self.page:
            return ""
        try:
            screenshot_bytes = await self.page.screenshot(full_page=False)
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""

    async def analyze_page(self, user_intent: str) -> Dict[str, Any]:
        """Analyze current page and determine next action"""
        if not self.page:
            return {
                "analysis": {"action": "error", "description": "Browser page not available.", "status": "error"},
                "screenshot": "", "url": "", "title": ""
            }
        try:
            # Take screenshot for analysis
            screenshot_b64 = await self.take_screenshot()
            
            # Get page info
            url = self.page.url
            title = await self.page.title()
            
            # Create prompt for Gemini
            prompt = f"""
            You are a browser automation assistant. Analyze the current webpage and determine the next action.
            
            Current URL: {url}
            Page Title: {title}
            User Intent: {user_intent}
            Current Task State: {json.dumps(self.task_state, indent=2)}
            
            Based on the screenshot, determine:
            1. What action should be taken next?
            2. What elements should be interacted with?
            3. What information needs to be filled/clicked?
            4. Are there any forms, buttons, or input fields visible?
            
            Respond in JSON format:
            {{
                "action": "click|type|navigate|wait|complete",
                "element_selector": "CSS selector or text to find",
                "value": "text to type if applicable",
                "description": "Human readable description of action",
                "needs_info": ["list of information needed from user"],
                "status": "continue|complete|error"
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            try:
                # Extract JSON from response
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'(\{.*?\})', response.text, re.DOTALL)

                if json_match:
                    analysis = json.loads(json_match.group(1))
                else:
                    # Fallback analysis
                    logger.warning(f"Could not parse JSON from Gemini response: {response.text}")
                    analysis = {
                        "action": "wait",
                        "description": "Analyzing page...",
                        "status": "continue"
                    }
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}\nResponse was: {response.text}")
                analysis = {
                    "action": "wait", 
                    "description": "Page analysis in progress...",
                    "status": "continue"
                }
            
            return {
                "analysis": analysis,
                "screenshot": screenshot_b64,
                "url": url,
                "title": title
            }
            
        except Exception as e:
            logger.error(f"Error analyzing page: {e}")
            return {
                "analysis": {"action": "error", "description": f"Error: {e}", "status": "error"},
                "screenshot": await self.take_screenshot(),
                "url": self.page.url if self.page else "",
                "title": await self.page.title() if self.page else ""
            }
        
    async def execute_action(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the determined action with added robustness and fallbacks."""
        if not self.page:
             return {
                "success": False, "description": "Browser page not available.", "screenshot": "", "url": "", "title": ""
            }
        
        action_info = analysis.get("analysis", {})
        action = action_info.get("action", "wait")
        
        try:
            if action == "navigate":
                url = action_info.get("value", "")
                if not url:
                    raise ValueError("Navigate action requires a URL 'value'.")
                logger.info(f"Navigating to URL: {url}")
                await self.page.goto(url)
                await self.page.wait_for_load_state('networkidle')
                
            elif action == "click":
                selector = action_info.get("element_selector", "")
                if not selector:
                    raise ValueError("Click action requires an 'element_selector'.")

                logger.info(f"Executing click action. AI-provided selector: '{selector}'")
                try:
                    # PRIMARY ATTEMPT: Use the selector from the AI directly.
                    # We give it a shorter timeout because we have a fallback.
                    await self.page.click(selector, timeout=3000)
                    logger.info(f"Successfully clicked using the primary selector: '{selector}'")
                except Exception:
                    # FALLBACK ATTEMPT: If the selector fails, try finding the element by its visible text.
                    # This is far more robust against the AI guessing selectors incorrectly.
                    # The 'selector' string itself might be the text to find (e.g., "Sign in").
                    logger.warning(f"Primary selector failed. Attempting fallback using text: '{selector}'")
                    
                    # Use Playwright's get_by_text, which is smart about finding elements.
                    await self.page.get_by_text(selector, exact=True).first.click(timeout=3000)
                    logger.info(f"Successfully clicked using text-based fallback: '{selector}'")

            elif action == "type":
                selector = action_info.get("element_selector", "")
                value = action_info.get("value", "")
                if not selector or value is None:
                    raise ValueError("Type action requires a 'element_selector' and 'value'.")
                
                logger.info(f"Attempting to type '{value}' into selector: {selector}")
                await self.page.fill(selector, value)
                    
            elif action == "wait":
                await asyncio.sleep(2)
            
            # Ensure the page is settled before taking the final screenshot
            await self.page.wait_for_load_state('domcontentloaded')
            screenshot_b64 = await self.take_screenshot()
            
            return {
                "success": True,
                "description": action_info.get("description", "Action completed successfully"),
                "screenshot": screenshot_b64,
                "url": self.page.url,
                "title": await self.page.title()
            }
            
        except Exception as e:
            logger.error(f"Error executing action '{action}': {e}", exc_info=True)
            return {
                "success": False,
                "description": f"Action Failed: {e}",
                "screenshot": await self.take_screenshot(),
                "url": self.page.url if self.page else "",
                "title": await self.page.title() if self.page else ""
            }

    async def process_user_message(self, message: str) -> Dict[str, Any]:
        """Process user message and determine response"""
        try:
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": message})
            
            intent_prompt = f"""
            Analyze the user's message and determine their intent for browser automation.
            
            Message: "{message}"
            Conversation History: {json.dumps(self.conversation_history[-5:], indent=2)}
            
            Determine:
            1. What task do they want to accomplish?
            2. What information is missing to complete the task?
            3. Should we start browser automation or ask for more details?
            
            Common tasks: send email, search web, navigate to website, fill forms, etc.
            
            Respond in JSON format:
            {{
                "intent": "email|search|navigate|form|other",
                "task_description": "Clear description of task",
                "missing_info": ["list of required information not provided"],
                "ready_to_start": true/false,
                "suggested_response": "What to say to user"
            }}
            """
            
            intent_response = self.model.generate_content(intent_prompt)
            
            try:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', intent_response.text, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'(\{.*?\})', intent_response.text, re.DOTALL)
                
                if json_match:
                    intent_analysis = json.loads(json_match.group(1))
                else:
                    logger.warning(f"Could not parse JSON from intent response: {intent_response.text}")
                    intent_analysis = {
                        "intent": "other",
                        "task_description": message,
                        "missing_info": [],
                        "ready_to_start": False,
                        "suggested_response": "I understand you want me to help with browser automation. Could you provide more specific details?"
                    }
            except Exception as e:
                logger.error(f"Could not parse intent analysis JSON: {e}\nResponse was: {intent_response.text}")
                intent_analysis = {
                    "intent": "other",
                    "task_description": message,
                    "missing_info": [],
                    "ready_to_start": False,
                    "suggested_response": "Let me help you with that. What specific website or action would you like me to perform?"
                }
            
            self.current_task = intent_analysis.get("task_description", message)
            
            if intent_analysis.get("ready_to_start") and not intent_analysis.get("missing_info"):
                if not self.browser:
                    await self.initialize_browser()
                
                # Default navigation for common tasks
                initial_url = "https://www.google.com" # Default to google
                if intent_analysis['intent'] == "email":
                    initial_url = "https://mail.google.com"
                
                await self.page.goto(initial_url)
                await self.page.wait_for_load_state('networkidle')
                
                screenshot = await self.take_screenshot()
                
                return {
                    "response": f"Starting task: {self.current_task}. I've opened the browser.",
                    "screenshot": screenshot,
                    "url": self.page.url,
                    "title": await self.page.title(),
                    "status": "in_progress"
                }
            else:
                return {
                    "response": intent_analysis["suggested_response"],
                    "screenshot": None,
                    "missing_info": intent_analysis.get("missing_info", []),
                    "status": "waiting_for_info"
                }
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": f"I encountered an error: {e}. Please try again.",
                "screenshot": None,
                "status": "error"
            }

# --- FastAPI Application Setup ---

# Global agent instance
agent: Optional[BrowserControlAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    This is the modern and recommended way to manage resources.
    """
    global agent
    # Startup: Initialize the agent
    logger.info("Application startup: Initializing BrowserControlAgent...")
    
    # IMPORTANT: Replace with your actual Gemini API key.
    # For production, use an environment variable. e.g., os.getenv("GEMINI_API_KEY")
    GEMINI_API_KEY = "AIzaSyDYwiGZT4t8r3_BFY6XgQFYcRrmV6xeWYA" 
    
    if not GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Please replace the placeholder in the script.")
        # You might want to exit or handle this more gracefully
    
    agent = BrowserControlAgent(GEMINI_API_KEY)
    logger.info("BrowserControlAgent initialized.")
    
    yield
    
    # Shutdown: Close browser resources
    logger.info("Application shutdown: Closing browser resources...")
    if agent:
        await agent.close_browser()
    logger.info("Browser resources closed.")

# FastAPI Application
app = FastAPI(title="Browser Control Agent", lifespan=lifespan)

class UserMessage(BaseModel):
    message: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client.host}")
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            if not message or not agent:
                continue
            
            # This loop drives the automation for a given user command
            is_task_in_progress = True
            
            # 1. Process initial user message to get intent
            result = await agent.process_user_message(message)
            await websocket.send_json({"type": "response", "data": result})
            
            if result.get("status") == "in_progress":
                is_task_in_progress = True
            else:
                is_task_in_progress = False

            # 2. Continue autonomous operation until task is complete or needs input
            while is_task_in_progress and agent.page:
                # Analyze current page and decide next action
                analysis = await agent.analyze_page(agent.current_task)
                
                # Send analysis and screenshot to user
                await websocket.send_json({"type": "analysis", "data": analysis})
                
                action_info = analysis.get("analysis", {})
                if action_info.get("status") == "continue":
                    # Execute the action
                    action_result = await agent.execute_action(analysis)
                    
                    # Send result of the action to the user
                    await websocket.send_json({
                        "type": "action_result", 
                        "data": action_result
                    })

                    # If the action failed, stop the loop
                    if not action_result.get("success"):
                         is_task_in_progress = False
                else:
                    # Task is complete, requires info, or has an error
                    is_task_in_progress = False
                    logger.info(f"Task finished with status: {action_info.get('status')}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)}
        })

@app.get("/")
async def get_frontend():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Browser Control Agent</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 1rem;
            text-align: center;
            color: white;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        .main-container {
            display: flex;
            flex: 1;
            gap: 1rem;
            padding: 1rem;
            height: calc(100vh - 80px);
            overflow: hidden;
        }
        
        .chat-container {
            flex: 1;
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            min-width: 300px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .message {
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            max-width: 95%;
        }
        
        .message.user {
            flex-direction: row-reverse;
            align-self: flex-end;
        }
        
        .message.bot {
             align-self: flex-start;
        }
        
        .message-content {
            padding: 0.75rem 1rem;
            border-radius: 18px;
            position: relative;
        }
        
        .message.user .message-content {
            background: #007bff;
            color: white;
        }
        
        .message.bot .message-content {
            background: #e9ecef;
            color: #333;
        }
        
        .screenshot-container {
            margin-top: 1rem;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #ddd;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .screenshot {
            max-width: 100%;
            height: auto;
            display: block;
        }
        
        .input-container {
            padding: 1rem;
            border-top: 1px solid #e0e0e0;
            background: white;
            display: flex;
            gap: 0.5rem;
        }
        
        .message-input {
            flex: 1;
            padding: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .message-input:focus {
            border-color: #007bff;
        }
        
        .send-button {
            padding: 1rem 1.5rem;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            transition: background-color 0.3s;
        }
        
        .send-button:hover {
            background: #0056b3;
        }
        
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .browser-preview {
            flex: 1.5;
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            min-width: 400px;
        }
        
        .browser-header {
            background: #f8f9fa;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: #666;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .browser-content {
            flex: 1;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-waiting { background: #ffc107; }
        .status-active { background: #28a745; }
        .status-error { background: #dc3545; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1.5s infinite ease-in-out;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Browser Control Agent</h1>
        <p>Control your browser with natural language commands</p>
    </div>
    
    <div class="main-container">
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages">
                <div class="message bot">
                    <div class="message-content">
                        👋 Hi! I'm your Browser Control Agent. I can help you automate browser tasks.
                        <br><br>
                        Just tell me what you'd like to do! For example:
                        <br>
                        <em>"Search for the weather in New York"</em>
                    </div>
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" 
                       class="message-input" 
                       id="messageInput" 
                       placeholder="Tell me what you want to do..."
                       onkeypress="handleKeyPress(event)">
                <button class="send-button" id="sendButton" onclick="sendMessage()">
                    Send
                </button>
            </div>
        </div>
        
        <div class="browser-preview">
            <div class="browser-header">
                <span class="status-indicator status-waiting" id="statusIndicator"></span>
                <span id="browserStatus">Browser Ready</span>
                <span id="currentUrl" style="float: right; font-family: monospace;"></span>
            </div>
            <div class="browser-content" id="browserContent">
                Browser preview will appear here when automation starts
            </div>
        </div>
    </div>

    <script>
        let ws;
        let isConnected = false;
        
        function initWebSocket() {
            // Adjust protocol for secure (wss) or insecure (ws) connections
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                isConnected = true;
                updateStatus('active', 'Connected to Agent');
                console.log('WebSocket connected');
                document.getElementById('sendButton').disabled = false;
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log("Received message:", data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function() {
                isConnected = false;
                updateStatus('error', 'Disconnected. Please refresh.');
                console.log('WebSocket disconnected');
                document.getElementById('sendButton').disabled = true;
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus('error', 'Connection Error');
                document.getElementById('sendButton').disabled = true;
            };
        }
        
        function handleWebSocketMessage(data) {
            const sendButton = document.getElementById('sendButton');
            sendButton.disabled = false;
            updateStatus('active', 'Agent is Active');

            let messageText = '';
            let screenshot = null;

            switch(data.type) {
                case 'response':
                    messageText = data.data.response;
                    screenshot = data.data.screenshot;
                    if (data.data.status === 'in_progress') {
                        updateStatus('active', 'Task in progress...', true);
                        sendButton.disabled = true; // Disable sending while task is running
                    }
                    addBotMessage(messageText, screenshot);
                    if(data.data.url) {
                        updateBrowserPreview(screenshot, data.data.url, data.data.title);
                    }
                    break;
                case 'analysis':
                    messageText = data.data.analysis.description || "Analyzing page...";
                    screenshot = data.data.screenshot;
                    addBotMessage(messageText, screenshot);
                    updateBrowserPreview(screenshot, data.data.url, data.data.title);
                    updateStatus('active', 'Analyzing page...', true);
                    break;
                case 'action_result':
                    messageText = data.data.description;
                    screenshot = data.data.screenshot;
                    if (!data.data.success) {
                        messageText = `Action Failed: ${messageText}`;
                        updateStatus('error', 'Action Failed');
                    } else {
                        updateStatus('active', 'Action Complete...', true);
                    }
                    addBotMessage(messageText, screenshot);
                    updateBrowserPreview(screenshot, data.data.url, data.data.title);
                    break;
                case 'error':
                    messageText = `An error occurred: ${data.data.message}`;
                    addBotMessage(messageText);
                    updateStatus('error', 'Agent Error');
                    break;
            }
        }
        
        function addBotMessage(message, screenshot = null) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message bot';
            
            // Sanitize message to prevent HTML injection
            const textNode = document.createTextNode(message);
            const messageContentDiv = document.createElement('div');
            messageContentDiv.className = 'message-content';
            messageContentDiv.appendChild(textNode);
            
            if(screenshot) {
                const container = document.createElement('div');
                container.className = 'screenshot-container';
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${screenshot}`;
                img.alt = "Browser Screenshot";
                img.className = 'screenshot';
                container.appendChild(img);
                messageContentDiv.appendChild(container);
            }
            
            messageDiv.appendChild(messageContentDiv);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function addUserMessage(message) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = message; // Use textContent for security
            messageDiv.appendChild(contentDiv);
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function updateBrowserPreview(screenshot, url, title) {
            const browserContent = document.getElementById('browserContent');
            const currentUrl = document.getElementById('currentUrl');
            
            if(screenshot) {
                browserContent.innerHTML = ''; // Clear previous content
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${screenshot}`;
                img.style = "max-width: 100%; max-height: 100%; object-fit: contain;";
                img.alt = "Browser Preview";
                browserContent.appendChild(img);
                currentUrl.textContent = url || '';
            }
        }
        
        function updateStatus(status, text, loading = false) {
            const indicator = document.getElementById('statusIndicator');
            const statusText = document.getElementById('browserStatus');
            
            indicator.className = `status-indicator status-${status}`;
            indicator.classList.toggle('loading', loading);
            statusText.textContent = text;
        }
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const message = input.value.trim();
            
            if(!message || !isConnected) return;
            
            addUserMessage(message);
            
            ws.send(JSON.stringify({
                message: message
            }));
            
            input.value = '';
            sendButton.disabled = true;
            updateStatus('active', 'Sending to agent...', true);
        }
        
        function handleKeyPress(event) {
            if(event.key === 'Enter') {
                sendMessage();
            }
        }
        
        // Initialize WebSocket connection on page load
        window.onload = function() {
            document.getElementById('sendButton').disabled = true;
            initWebSocket();
        };
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    print("🤖 Browser Control Agent Starting...")
    print("📋 Setup Instructions:")
    print("1. Install dependencies: pip install fastapi uvicorn playwright google-generativeai pillow")
    print("2. Install Playwright browsers: playwright install")
    print("3. Get a Gemini API key from Google AI Studio.")
    print("4. Replace the placeholder API key in the script with your actual key.")
    print("5. Run: python browser_agent.py")
    print("6. Open your browser to: http://localhost:8000")
    print("\n🚀 Starting server...")
    
    # Run the FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8000)