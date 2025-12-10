import os
import asyncio
from flask import Flask, jsonify, request, render_template
from loguru import logger

# Import your main classes
from src.trading_bot import TradingBot 
# Assuming db object is imported from src.database.db. If not, mock it or adjust the import.
try:
    from src.database.db import db 
except ImportError:
    class MockDB:
        def __init__(self): pass
        def init_database(self): pass
        # Add mock methods for all db calls used in the bot
    db = MockDB()
    logger.warning("Mocking Database. Ensure src/database/db.py is present.")


# --- INITIALIZATION ---
app = Flask(__name__, static_folder='.', template_folder='.')

# Read environment variables
BOT_SSID = os.getenv("POCKET_OPTION_SSID")

# Check if SSID is provided. If not, force demo mode.
BOT_DEMO = os.getenv("BOT_DEMO", "False").lower() == "true" if BOT_SSID else True
if BOT_SSID is None or BOT_SSID == "":
    logger.warning("POCKET_OPTION_SSID not set. Running in forced DEMO mode.")

# Initialize bot and asyncio loop
bot = TradingBot(ssid=BOT_SSID, demo=BOT_DEMO)
bot_loop = asyncio.new_event_loop()


# --- THREAD UTILITY ---
# Simple function to safely run an async coroutine in the bot's loop
def run_coro_in_bot_loop(coro):
    future = asyncio.run_coroutine_threadsafe(coro, bot_loop)
    try:
        # Wait for the result, with a timeout
        return future.result(timeout=10)
    except asyncio.TimeoutError:
        logger.error("Async task timed out.")
        return {"error": "Async operation timed out"}, 504
    except Exception as e:
        logger.error(f"Async operation failed: {e}")
        return {"error": str(e)}, 500


# --- ROUTES ---

@app.route('/')
def index():
    """Serves the dashboard HTML."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current status of the bot."""
    return jsonify(bot.get_status())


@app.route('/api/tournaments/free', methods=['GET'])
def get_free_tournaments():
    """Returns a list of all active free tournaments for the dashboard."""
    coro = bot.tournament_manager.get_all_active_free_tournaments()
    result = run_coro_in_bot_loop(coro)
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result), 200


@app.route('/api/control', methods=['POST'])
def bot_control():
    data = request.json
    action = data.get('action')
    
    if action == 'start':
        bot.start(bot_loop)
        return jsonify({"message": "Bot started."}), 200
    
    elif action == 'stop':
        bot.stop()
        return jsonify({"message": "Bot stopped."}), 200
    
    # ... (other control actions)
        
    elif action == 'join_tournament':
        tournament_id = data.get('id')
        coro = bot.tournament_manager.join_tournament_by_id(tournament_id)
        result = run_coro_in_bot_loop(coro)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]

        if result is True:
            return jsonify({"message": f"Successfully joined tournament ID: {tournament_id}"}), 200
        else:
            return jsonify({"message": f"Failed to join tournament ID: {tournament_id}"}), 400

    else:
        return jsonify({"message": f"Unknown action: {action}"}), 400


@app.route('/api/market/analysis', methods=['GET'])
def get_market_analysis():
    """Returns the current market analysis (patterns, levels, etc.)."""
    return jsonify(bot.get_market_analysis())


@app.route('/api/trades/history', methods=['GET'])
def get_trade_stats():
    """Returns trade history and statistics."""
    return jsonify(bot.get_trade_stats())


if __name__ == '__main__':
    # Start the asyncio loop in a separate thread for the bot logic
    import threading
    threading.Thread(target=bot_loop.run_forever, daemon=True).start()

    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
