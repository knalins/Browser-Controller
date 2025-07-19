# Browser-Controller

Setup Video: https://drive.google.com/file/d/1HhXtPQxRgBDRvmwkIZXekPXCPWf3V6jw/view?usp=sharing

Working Video: https://drive.google.com/file/d/1UDJdXSmgd0EC1bNefYkYyHwXI9jUEqFB/view?usp=sharing


# Browser Control Agent - Setup Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google AI Studio API key (Gemini)

### Installation Steps

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

## 🔐 Security Considerations

### Important Security Notes
- **Never hardcode credentials** in the source code
- Use environment variables for sensitive data
- Consider using OAuth instead of password authentication
- The agent will ask for credentials - only provide them for testing
- In production, implement proper authentication flows

### Recommended Security Practices
```python
import os
from cryptography.fernet import Fernet

# Use environment variables
EMAIL = os.getenv('USER_EMAIL')
# Encrypt sensitive data
key = Fernet.generate_key()
f = Fernet(key)
encrypted_password = f.encrypt(password.encode())
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

### Custom UI Themes
Modify the CSS in the HTML response to customize appearance:
```css
/* Dark theme example */
body {
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    color: white;
}

.chat-container {
    background: rgba(30,30,30,0.95);
}
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

## 🚀 Deployment Options

### 1. Local Development
```bash
python browser_agent.py
```

### 2. Docker Deployment
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install

COPY . .
EXPOSE 8000

CMD ["python", "browser_agent.py"]
```

### 3. Cloud Deployment (Heroku)
```bash
# Procfile
web: python browser_agent.py

# runtime.txt
python-3.9.18
```

## 📊 Performance Optimization

### Tips for Better Performance
1. **Use headless mode in production**:
   ```python
   headless=True  # Faster execution
   ```

2. **Optimize screenshot frequency**:
   ```python
   # Only take screenshots when necessary
   if user_wants_visual_feedback:
       screenshot = await self.take_screenshot()
   ```

3. **Implement caching**:
   ```python
   # Cache page analysis results
   @lru_cache(maxsize=100)
   def analyze_page_cached(self, page_content):
       return self.analyze_page(page_content)
   ```

4. **Connection pooling**:
   ```python
   # Reuse browser contexts
   if not self.context:
       self.context = await self.browser.new_context()
   ```

## 🤝 Contributing

### Adding New Features
1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-automation`
3. Implement your feature
4. Add tests
5. Submit pull request

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Include error handling

## 📝 License

This project is for educational purposes. Please ensure you comply with:
- Website terms of service
- Data protection regulations
- Automation policies of target sites

## 🆘 Support

### Getting Help
- Check the troubleshooting section
- Review GitHub issues
- Join our Discord community
- Email support: your-email@domain.com

### Reporting Issues
Please include:
- Python version
- Operating system
- Error messages
- Steps to reproduce
- Screenshots if applicable

---

## 🎯 Next Steps for Your Assignment

### Enhancements You Can Add

1. **Better Error Handling**:
   - Retry failed actions
   - Graceful fallbacks
   - User-friendly error messages

2. **More Automation Types**:
   - Social media posting
   - Online shopping
   - Form submissions
   - Data scraping

3. **Improved AI Integration**:
   - Better context understanding
   - Multi-step planning
   - Learning from user feedback

4. **Enhanced UI**:
   - Mobile responsiveness
   - Dark/light themes
   - Better screenshot display
   - Progress indicators

5. **Security Features**:
   - Credential encryption
   - Session management
   - Access controls
   - Audit logging

### Evaluation Criteria
Your assignment will likely be evaluated on:
- ✅ **Functionality**: Does it work as specified?
- ✅ **Code Quality**: Clean, readable, well-documented
- ✅ **User Experience**: Intuitive interface, good feedback
- ✅ **Error Handling**: Robust error management  
- ✅ **Innovation**: Creative features beyond requirements
- ✅ **Technical Implementation**: Proper use of technologies

Good luck with your assignment! 🚀
