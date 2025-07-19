# Browser-Controller

Setup Video: https://drive.google.com/file/d/1HhXtPQxRgBDRvmwkIZXekPXCPWf3V6jw/view?usp=sharing

Working Video: https://drive.google.com/file/d/1UDJdXSmgd0EC1bNefYkYyHwXI9jUEqFB/view?usp=sharing

<img width="2872" height="1586" alt="image" src="https://github.com/user-attachments/assets/2adf7d37-5e00-452b-b1db-cd7532e602ec" />


### Prerequisites
- Python 3.8+
- Google AI Studio API key (Gemini) {Change it at LineNo.: 355}
### TechStacks Used:
1. Browser Automation: Playwright
Chosen over alternatives like Selenium for its superior speed and integrates perfectly with FastAPI
2. AI Engine: Google Gemini
It performs two key roles: (1) Intent Recognition to understand the user's goal, and (2) Visual Analysis to analyze screenshots and decide the next logical action (e.g., "click button," "fill input").
3. Backend Framework: FastAPI
A high-performance, asynchronous Python framework.

### Challenges:
1. I controlled browser with playwright.
2. I was suffering integrating gemini and playwright.


### Installation Steps

#### Make sure you are in your project's main folder
1. rm -rf venv

#### Create the new virtual environment
2. python3 -m venv venv
#### Activate it
3. source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate   # On Windows


1. **Clone/Download the project**
   ```bash
   mkdir browser-control-agent
   cd browser-control-agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install fastapi uvicorn playwright google-generativeai pillow pydantic websockets python-multipart
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install
   ```

4. **Get Gemini API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the API key

5. **Configure the API Key**
   - Open `browser_agent.py`
   - Replace `YOUR_GEMINI_API_KEY_HERE` with your actual API key
   - Or set environment variable: `export GEMINI_API_KEY="your-key-here"`

6. **Run the application**
   ```bash
   python browser_agent.py
   ```

7. **Open your browser**
   - Navigate to `http://localhost:8000`
   - Start chatting with your browser agent!

## 🎯 Usage Examples

### Example 1: Send Email
**User**: "Send email for leave to my manager"

**Agent Response**:
1. "I'll help you send a leave email. I need some details:"
2. "What's your email address?"
3. "What's your manager's email?"
4. "What are the leave dates?"
5. "Any specific reason for leave?"

**Then the agent will**:
- Open browser → Screenshot
- Navigate to gmail.com → Screenshot  
- Fill login details → Screenshot
- Compose email → Screenshot
- Fill all fields → Screenshot
- Send email → Screenshot
- Confirm "Email sent successfully!"

### Example 2: Google Search
**User**: "Search for 'AI startups in India'"

**Agent Response**:
- Opens browser → Screenshot
- Goes to google.com → Screenshot
- Types in search box → Screenshot
- Clicks search → Screenshot
- Shows results → Screenshot
- "Search completed successfully!"

### Example 3: Complex Task
**User**: "Find and apply to software engineer jobs on LinkedIn"

**Agent Response**:
1. "I'll help you job hunt! I need some info:"
2. "What's your LinkedIn email/password?"
3. "What location are you targeting?"
4. "What experience level?"
5. "Any specific companies?"

**Then automates**:
- Login to LinkedIn → Screenshots
- Search for jobs → Screenshots
- Filter results → Screenshots
- Apply to relevant positions → Screenshots
- Report back with summary

## 🛠️ Technical Architecture

### Components
1. **FastAPI Backend** - Handles WebSocket connections
2. **Playwright** - Browser automation engine
3. **Google Gemini** - AI for understanding and planning
4. **WebSocket Interface** - Real-time communication
5. **Screenshot System** - Visual feedback
6. **Conversational AI** - Natural language processing

### Data Flow
```
User Message → Gemini Analysis → Action Planning → 
Browser Automation → Screenshot → Response → User
```

## 🔧 Configuration Options

### Environment Variables
```bash
export GEMINI_API_KEY="your-gemini-key"
export BROWSER_HEADLESS="false"  # Show/hide browser
export SCREENSHOT_QUALITY="100"  # Screenshot quality
export MAX_WAIT_TIME="30"        # Max wait time for elements
```

### Browser Settings
```python
# In browser_agent.py, modify these settings:
self.browser = await self.playwright.chromium.launch(
    headless=False,  # Set True to hide browser
    args=[
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--start-maximized'  # Start browser maximized
    ]
)
```

## 🎨 Customization

### Adding New Task Types

1. **Extend the intent analysis in `process_user_message`**:
```python
# Add new intents like 'shopping', 'booking', 'social_media'
if intent_analysis["intent"] == "shopping":
    await self.page.goto("https://amazon.com")
elif intent_analysis["intent"] == "booking":
    await self.page.goto("https://booking.com")
```

2. **Create specialized handlers**:
```python
async def handle_shopping_task(self, details):
    """Handle e-commerce automation"""
    # Implementation for shopping automation
    pass

async def handle_social_media_task(self, details):
    """Handle social media automation"""  
    # Implementation for social media automation
    pass
```

## 🐛 Troubleshooting

### Common Issues

1. **"Browser failed to launch"**
   ```bash
   # Solution: Install system dependencies
   sudo apt-get install -y chromium-browser
   playwright install-deps
   ```

2. **"Gemini API key error"**
   ```bash
   # Check your API key
   export GEMINI_API_KEY="your-actual-key"
   # Verify it's set
   echo $GEMINI_API_KEY
   ```

3. **"WebSocket connection failed"**
   ```bash
   # Check if port 8000 is available
   lsof -i :8000
   # Try different port
   uvicorn app:app --port 8001
   ```

4. **"Screenshots not appearing"**
   ```python
   # Enable debugging
   logging.basicConfig(level=logging.DEBUG)
   # Check browser visibility
   headless=False  # Make sure browser is visible
   ```

5. **"Element not found errors"**
   ```python
   # Add more wait time
   await self.page.wait_for_selector(selector, timeout=30000)
   # Use more robust selectors
   await self.page.wait_for_load_state('networkidle')
   ```

## 📈 Advanced Features

### 1. Multi-tab Support
```python
async def create_new_tab(self):
    """Create and switch to new browser tab"""
    new_page = await self.context.new_page()
    return new_page

async def switch_tab(self, tab_index):
    """Switch between browser tabs"""
    pages = self.context.pages
    if tab_index < len(pages):
        self.page = pages[tab_index]
```

### 2. File Upload/Download Handling
```python
async def handle_file_upload(self, file_path, selector):
    """Handle file uploads"""
    await self.page.set_input_files(selector, file_path)

async def handle_download(self):
    """Handle file downloads"""
    async with self.page.expect_download() as download_info:
        await self.page.click('text=Download')
    download = await download_info.value
    await download.save_as(f"./downloads/{download.suggested_filename}")
```

### 3. Form Auto-fill
```python
async def auto_fill_form(self, form_data):
    """Auto-fill forms with provided data"""
    for field, value in form_data.items():
        try:
            await self.page.fill(f'[name="{field}"]', value)
        except:
            await self.page.fill(f'#{field}', value)
```

### 4. Cookie Management
```python
async def save_cookies(self, file_path):
    """Save browser cookies"""
    cookies = await self.context.cookies()
    with open(file_path, 'w') as f:
        json.dump(cookies, f)

async def load_cookies(self, file_path):
    """Load saved cookies"""
    with open(file_path, 'r') as f:
        cookies = json.load(f)
    await self.context.add_cookies(cookies)
```
