import os
import json
import logging
from flask import Flask, request, render_template, jsonify, session
import openai
import secrets
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the flag from environment variable
FLAG = os.environ.get('GZCTF_FLAG', 'flag{test_flag_for_development}')

# Load configuration
def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    logger.info("Configuration loaded successfully")
    return config

# Initialize OpenAI client
config = load_config()
client = openai.OpenAI(
    api_key=config.get('openai_api_key', 'dummy'),
    base_url=config.get('openai_base_url', 'dummy')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400

        # Log the user input for monitoring
        logger.info(f"User input: {user_message}")

        # Rate limiting
        if 'last_request' in session:
            if time.time() - session['last_request'] < 1:
                return jsonify({'error': '请求太频繁，请稍后再试'}), 429
        session['last_request'] = time.time()

        # Replace $FLAG placeholder with actual flag value
        system_prompt = config.get('system_prompt', 'dummy')
        system_prompt = system_prompt.replace('$FLAG', FLAG)

        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=config.get('model', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=config.get('max_tokens', 500),
            temperature=config.get('temperature', 0.7)
        )

        ai_response = response.choices[0].message.content

        # Log the AI response for monitoring
        logger.info(f"AI response: {ai_response}")

        return jsonify({
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })

    except openai.AuthenticationError:
        logger.error("OpenAI authentication failed")
        return jsonify({'error': 'AI 服务认证失败，请检查 API 密钥'})
    except openai.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        return jsonify({'error': 'AI 服务调用超限，请稍后再试'})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': f'处理请求时发生错误: {str(e)}'})

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    config = load_config()
    app.run(host='0.0.0.0', port=5000, debug=False)