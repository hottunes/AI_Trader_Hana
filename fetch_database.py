import sqlite3
import aiosqlite
from logger_setup import setup_logger

logger = setup_logger(__name__)


def initialize_db(db_path='trading_decisions.sqlite'):
    logger.info(f"Initializing database at path: {db_path}")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                action TEXT,
                rationale_technical_analysis TEXT,
                rationale_news_impact TEXT,
                rationale_market_sentiment TEXT,
                rationale_conclusion TEXT,
                confidence_score REAL
            );
        ''')
        logger.info("Database initialized successfully")
        conn.commit()


async def save_decision_to_db(decision, db_path='trading_decisions.sqlite'):
    logger.info(f"Saving decision to database at path: {db_path}")
    try:
        async with aiosqlite.connect(db_path) as conn:
            async with conn.cursor() as cursor:
                # Extracting data to match the updated table structure
                data_to_insert = (
                    decision['timestamp'],
                    decision['action'],
                    decision['rationale']['technical_analysis'],
                    decision['rationale']['news_impact'],
                    decision['rationale']['market_sentiment'],
                    decision['rationale']['conclusion'],
                    decision['confidence_score']
                )

                await cursor.execute('''
                    INSERT INTO decisions (
                        timestamp, action,
                        rationale_technical_analysis, rationale_news_impact, rationale_market_sentiment,
                        rationale_conclusion, confidence_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', data_to_insert)
                await conn.commit()
            logger.info("Decision saved successfully")
    except aiosqlite.Error as e:
        logger.error(f"Error saving decision to database: {e}")
        raise


async def fetch_recent_decisions(db_path='trading_decisions.sqlite', num_decisions=5):
    logger.info(f"Fetching last {num_decisions} decisions from database at path: {db_path}")
    try:
        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute('''
                SELECT timestamp, action, rationale_technical_analysis, rationale_news_impact, 
                       rationale_market_sentiment, rationale_conclusion, confidence_score 
                FROM decisions 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (num_decisions,)) as cursor:
                decisions = await cursor.fetchall()

            if decisions:
                logger.info(f"Fetched {len(decisions)} decisions from the database")
                formatted_decisions = []
                for decision in decisions:
                    formatted_decision = {
                        "timestamp": decision[0],
                        "action": decision[1],
                        "rationale": {
                            "technical_analysis": decision[2],
                            "news_impact": decision[3],
                            "market_sentiment": decision[4],
                            "conclusion": decision[5]
                        },
                        "confidence_score": decision[6]
                    }
                    formatted_decisions.append(formatted_decision)
                return formatted_decisions
            else:
                logger.info("No decisions found in the database")
                return "No Recent Trading Decisions found."
    except aiosqlite.Error as e:
        logger.error(f"Error fetching decisions from database: {e}")
        raise
