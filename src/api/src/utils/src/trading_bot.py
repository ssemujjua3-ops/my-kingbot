import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from src.api.pocket_option import PocketOptionClient
from src.database.db import db # Assuming this is available
from src.patterns.candlestick import CandlestickAnalyzer # Assuming this is available
from src.patterns.levels import LevelAnalyzer # Assuming this is available
from src.patterns.indicators import TechnicalIndicators # Assuming this is available
from src.ml.agent import TradingAgent # Assuming this is available
from src.ml.knowledge_learner import KnowledgeLearner # Assuming this is available
from src.utils.tournament import TournamentManager # Ensure this is the only import from utils

class TradingBot:
    def __init__(self, ssid: str = None, demo: bool = True):
        self.client = PocketOptionClient(ssid=ssid, demo=demo)
        self.candlestick_analyzer = CandlestickAnalyzer()
        self.level_analyzer = LevelAnalyzer()
        self.indicators = TechnicalIndicators()
        self.agent = TradingAgent()
        self.knowledge_learner = KnowledgeLearner(db=db)
        self.tournament_manager = TournamentManager(self.client, self.agent, db=db)
        
        self.is_running = False
        self.is_learning = False
        self.is_trading = False
        
        self.current_asset = "EURUSD_otc"
        self.current_timeframe = 60
        self.available_timeframes = [60, 300, 900, 3600]
        
        self.market_data: Dict[str, Dict] = {}
        self.patterns_detected: List[Dict] = []
        self.levels_detected: Dict = {}
        self.indicator_values: Dict = {}
        
        self.trade_history: List[Dict] = []
        self.pending_trades: Dict = {}
        self.trades_this_hour = 0
        self.min_confidence = 0.75 # Agent confidence threshold
        self.loops: Dict[str, asyncio.Task] = {}
        
    def start(self, loop: asyncio.AbstractEventLoop):
        """Initializes and starts all background tasks."""
        if self.is_running:
            logger.warning("Bot is already running.")
            return

        self.is_running = True
        logger.info("Starting Trading Bot...")
        
        # 1. Start the main connection and data loops
        self.loops['main'] = loop.create_task(self._main_loop())
        
        # 2. Start the automated tournament loop
        self.loops['tournament'] = loop.create_task(self._tournament_loop())
        
        # 3. Start the trade execution loop
        self.loops['executor'] = loop.create_task(self._trade_executor_loop())
        
        # 4. Start the learning loop
        self.loops['learner'] = loop.create_task(self._knowledge_learner_loop())

    async def _main_loop(self):
        """Handles connection and market data subscription."""
        if not await self.client.connect():
            self.is_running = False
            logger.error("Connection failed. Bot stopping.")
            return
            
        # ... (rest of main loop for market data subscription)
        
        while self.is_running:
            await asyncio.sleep(5) # Keep connection alive check

    async def _tournament_loop(self):
        """Runs periodically to check and join the daily free tournament."""
        await asyncio.sleep(30) # Initial wait for connection setup
        while self.is_running:
            try:
                # The manager handles the internal 4-hour frequency check
                await self.tournament_manager.join_daily_free_tournament() 
                
                # Check again in 1 hour
                await asyncio.sleep(3600) 
            except asyncio.CancelledError: 
                raise
            except Exception as e:
                logger.error(f"Tournament loop error: {e}")
                await asyncio.sleep(3600)
                
    async def _trade_executor_loop(self):
        """Handles trade execution and pending trade resolution."""
        # ... (implementation of trade executor loop)
        while self.is_running:
            await asyncio.sleep(1)

    async def _knowledge_learner_loop(self):
        """Handles data learning and model training."""
        # ... (implementation of knowledge learner loop)
        while self.is_running:
            await asyncio.sleep(3600) # Learning once per hour
            
    def stop(self):
        """Stops all background tasks."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping Trading Bot...")
        
        # Cancel all running tasks
        for name, task in self.loops.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled {name} loop.")
        
        self.loops = {}
        # Graceful disconnect logic if needed
        
    def set_min_confidence(self, confidence: float):
        self.min_confidence = max(0.5, min(0.95, confidence))
        logger.info(f"Minimum confidence set to: {self.min_confidence:.2%}")
    
    # --- API GETTER METHODS ---
    def get_status(self) -> Dict:
        # ... (implementation from original file)
        return {
            "is_running": self.is_running,
            "is_trading": self.is_trading,
            "is_learning": self.is_learning,
            "connected": self.client.is_connected(),
            "simulation_mode": self.client.is_simulation(),
            "balance": self.client.balance,
            "current_asset": self.current_asset,
            "current_timeframe": self.current_timeframe,
            "patterns_detected": len(self.patterns_detected),
            "trades_this_hour": self.trades_this_hour,
            "pending_trades": len(self.pending_trades),
            "total_trades": len(self.trade_history),
            "agent_stats": self.agent.get_stats(),
            "knowledge_stats": self.knowledge_learner.get_stats()
        }
    
    def get_market_analysis(self) -> Dict:
        # ... (implementation from original file)
        return {
            "patterns": self.patterns_detected[:10],
            "levels": self.levels_detected,
            "indicators": self.indicator_values,
            "trend": self.candlestick_analyzer.get_trend(
                self.market_data.get(self.current_asset, {}).get("candles", [])
            )
        }
    
    def get_trade_stats(self) -> Dict:
        # ... (implementation from original file)
        return {
            "total_trades": len(self.trade_history),
            "total_wins": sum(1 for t in self.trade_history if t.get("outcome") == "win"),
            "total_losses": sum(1 for t in self.trade_history if t.get("outcome") == "loss"),
            "recent_trades": self.trade_history[-10:],
            "win_rate": sum(1 for t in self.trade_history if t.get("outcome") == "win") / len(self.trade_history) if len(self.trade_history) > 0 else 0
        }
