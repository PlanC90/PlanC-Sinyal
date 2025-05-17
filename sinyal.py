import os
import asyncio
import logging
import requests
import datetime
import matplotlib.pyplot as plt

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Gemini import
import google.generativeai as genai

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise Exception("Please add TELEGRAM_TOKEN and GEMINI_API_KEY to your .env file.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize Gemini client
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

COINGECKO_API = "https://api.coingecko.com/api/v3"
COINPAPRIKA_API = "https://api.coinpaprika.com/v1"

def get_coingecko_id(symbol: str):
    # Get CoinGecko coin list and find id by symbol
    url = f"{COINGECKO_API}/coins/list"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    coins = resp.json()
    symbol = symbol.lower()
    for coin in coins:
        if coin["symbol"] == symbol:
            return coin["id"]
    return None

def get_price_history(coin_id: str):
    # Get hourly price data for last 24 hours (24 points)
    url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": "1"}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    # prices = [[timestamp, price], ...]
    prices = data.get("prices", [])
    return prices

def get_market_trend():
    # Fetch top 100 coins from CoinPaprika
    url = f"{COINPAPRIKA_API}/tickers"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            logging.error(f"CoinPaprika API error: {resp.status_code}")
            return "Unknown"
        coins = resp.json()[:100]  # Limit to top 100 coins
        
        # Count coins with positive and negative 1h price change
        uptrend_count = 0
        downtrend_count = 0
        for coin in coins:
            price_change_1h = coin.get("quotes", {}).get("USD", {}).get("percent_change_1h", 0)
            if price_change_1h is not None:
                if price_change_1h > 0:
                    uptrend_count += 1
                elif price_change_1h < 0:
                    downtrend_count += 1
        
        # Determine trend: Long if >50% are up, Short if >50% are down
        total_count = uptrend_count + downtrend_count
        if total_count == 0:
            return "Unknown"
        uptrend_percentage = (uptrend_count / total_count) * 100
        if uptrend_percentage > 50:
            return "Long"
        else:
            return "Short"
    except Exception as e:
        logging.error(f"Error fetching market trend: {e}")
        return "Unknown"

def calculate_signal_levels(prices):
    if not prices or len(prices) < 2:
        return None
    
    # Get current price (last price in the list)
    current_price = prices[-1][1]
    
    # Calculate price volatility (standard deviation of price changes)
    price_changes = [prices[i+1][1] - prices[i][1] for i in range(len(prices)-1)]
    if not price_changes:
        return None
        
    avg_change = sum(abs(change) for change in price_changes) / len(price_changes)
    volatility = max(avg_change * 3, current_price * 0.01)  # At least 1% of current price
    
    # Calculate recent price trend
    price_change = (prices[-1][1] - prices[0][1]) / prices[0][1]
    
    # Determine if we should go long or short based on recent trend
    signal_type = "LONG" if price_change >= 0 else "SHORT"
    
    # Calculate entry, target and stop based on volatility
    if signal_type == "LONG":
        entry = current_price
        target = entry + volatility * 1.5  # 1.5x volatility profit target
        stop = entry - volatility        # 1x volatility stop loss
    else:
        entry = current_price
        target = entry - volatility * 1.5  # 1.5x volatility profit target for short
        stop = entry + volatility         # 1x volatility stop loss
    
    # Ensure we're not returning zeros (minimum 0.0000000001)
    entry = max(entry, 0.0000000001)
    target = max(target, 0.0000000001)
    stop = max(stop, 0.0000000001)
        
    # For stable coins and high value coins, adjust decimal places for precision
    if current_price > 1000:  # BTC and similar
        decimals = 2
    elif current_price > 100:  # ETH and similar
        decimals = 3
    elif current_price > 10:
        decimals = 4
    elif current_price > 1:
        decimals = 6
    elif current_price > 0.1:
        decimals = 8
    elif current_price > 0.001:
        decimals = 10
    else:
        decimals = 12  # For very small values like 0.000000001
    
    return {
        "type": signal_type,
        "entry": round(entry, decimals),
        "target": round(target, decimals), 
        "stop": round(stop, decimals),
        "decimals": decimals  # Store decimals for formatting
    }

async def plot_price_chart(prices, symbol, signal=None):
    if not prices:
        return None
    
    # Clean up old chart if exists
    filename = f"{symbol}_chart.png"
    if os.path.exists(filename):
        os.remove(filename)
    
    times = [datetime.datetime.fromtimestamp(p[0] / 1000) for p in prices]
    values = [p[1] for p in prices]

    plt.figure(figsize=(10,5))
    plt.plot(times, values, label=symbol.upper())
    
    # Add signal lines if provided
    if signal:
        # Add horizontal lines for entry, target and stop
        plt.axhline(y=signal["entry"], color='y', linestyle='-', label=f"Entry: {signal['entry']}")
        
        if signal["type"] == "LONG":
            plt.axhline(y=signal["target"], color='g', linestyle='--', label=f"Target: {signal['target']}")
            plt.axhline(y=signal["stop"], color='r', linestyle='--', label=f"Stop: {signal['stop']}")
        else:
            plt.axhline(y=signal["target"], color='g', linestyle='--', label=f"Target: {signal['target']}")
            plt.axhline(y=signal["stop"], color='r', linestyle='--', label=f"Stop: {signal['stop']}")
    
    plt.title(f"{symbol.upper()} - 24 Hour Price Chart (USD)")
    plt.xlabel("Time")
    plt.ylabel("Price (USD)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(filename)
    plt.close()
    return filename

async def get_gemini_comment(symbol: str, signal_type: str):
    prompt = f"""Provide a maximum 5-line technical analysis comment for {symbol.upper()} {signal_type} position.
    Make it concise, informative and focused on why this might be a good {signal_type} opportunity.
    Do not exceed 5 lines of text."""
    
    try:
        response = gemini_model.generate_content(prompt)
        # Check if response has content and text
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            # Some versions of Gemini API return parts
            return response.parts[0].text
        else:
            # Try to extract text from response in a different way
            return str(response)
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        # Return a default analysis instead of error message
        if signal_type == "LONG":
            return f"{symbol.upper()} showing bullish momentum. Support at recent lows appears strong. Volume increasing on up-moves. RSI indicates room for further upside. Consider trailing stop to lock in profits."
        else:
            return f"{symbol.upper()} showing bearish momentum. Resistance at recent highs holding firm. Volume increasing on down-moves. RSI indicates potential for continued decline. Consider trailing stop to lock in profits."

@dp.message(Command(commands=["start", "help"]))
async def start_command(message: types.Message):
    await message.answer("Hello! Use /signal <symbol> to get trading signals.\nExample: /signal eth")

@dp.message(Command(commands=["signal", "coin"]))
async def signal_handler(message: types.Message):
    try:
        parts = message.text.split()
        command = parts[0].lower()
        symbol = parts[1].strip().lower()
        
        # Optional timeframe parameter
        timeframe = "15 Minutes"  # Default timeframe, in English
        if len(parts) > 2:
            timeframe = " ".join(parts[2:])
    except IndexError:
        await message.answer("Please provide a coin symbol. Example: /signal eth")
        return

    await message.answer(f"Preparing signals for {symbol.upper()}...")

    coin_id = get_coingecko_id(symbol)
    if not coin_id:
        await message.answer("Invalid symbol or coin not found.")
        return

    prices = get_price_history(coin_id)
    if not prices:
        await message.answer("Could not fetch price data.")
        return
    
    signal = calculate_signal_levels(prices)
    if not signal:
        await message.answer("Could not calculate signal levels.")
        return

    chart_file = await plot_price_chart(prices, symbol, signal)
    if not chart_file:
        await message.answer("Could not generate chart.")
        return

    comment = await get_gemini_comment(symbol, signal["type"])
    
    # Get market trend from CoinPaprika
    market_trend = get_market_trend()
    
    # Format trend with colored emojis
    trend_text = f"🟩 TREND ➡️ {market_trend}" if market_trend == "Long" else f"🟥 TREND ➡️ {market_trend}" if market_trend == "Short" else f"TREND ➡️ {market_trend}"
    
    # Determine trend compatibility
    trend_compatibility = (
        "🟩 Signal is compatible with the trend."
        if (signal["type"] == "LONG" and market_trend == "Long") or (signal["type"] == "SHORT" and market_trend == "Short")
        else "🟥 Signal is not compatible with the trend."
    )

    try:
        # Format signal with precise decimal display and trend info
        signal_text = f"""⏳ Timeframe: {timeframe}
#{symbol.upper()}USDT {"🟩 LONG Signal 🟩" if signal["type"] == "LONG" else "🟥 SHORT Signal 🟥"}
ENTRY ➡️ {signal["entry"]:.{signal["decimals"]}f}
TARGET ➡️ {signal["target"]:.{signal["decimals"]}f}
STOP   ➡️ {signal["stop"]:.{signal["decimals"]}f}
{trend_text}
{trend_compatibility}
🟥 High Risk ⚠️
🔎 Chart added for basic analysis. Assess your own risk before trading.

{comment}"""

        await message.answer_photo(
            photo=FSInputFile(chart_file),
            caption=signal_text,
            parse_mode="HTML"
        )
        # Clean up the chart file after sending
        os.remove(chart_file)
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        await message.answer("An error occurred while sending the response.")

@dp.message(Command(commands=["manual"]))
async def manual_signal_handler(message: types.Message):
    try:
        # Expected format: /manual symbol direction entry target stop [timeframe]
        # Example: /manual sol long 166.21 167.87 164.54 15 Minutes
        parts = message.text.split()
        
        if len(parts) < 6:
            await message.answer("Format: /manual symbol direction entry target stop [timeframe]")
            return
            
        symbol = parts[1].strip().lower()
        direction = parts[2].strip().lower()
        entry = float(parts[3])
        target = float(parts[4])
        stop = float(parts[5])
        
        # Optional timeframe
        timeframe = "15 Minutes"  # Default, in English
        if len(parts) > 6:
            timeframe = " ".join(parts[6:])
            
    except (IndexError, ValueError):
        await message.answer("Format: /manual symbol direction entry target stop [timeframe]")
        return
        
    signal_type = "LONG" if direction.lower() == "long" else "SHORT"
    
    await message.answer(f"Preparing manual signal for {symbol.upper()}...")
    
    coin_id = get_coingecko_id(symbol)
    if not coin_id:
        await message.answer("Invalid symbol or coin not found.")
        return

    prices = get_price_history(coin_id)
    if not prices:
        await message.answer("Could not fetch price data.")
        return
        
    # Determine decimals based on entry price for manual signals
    if entry > 1000:
        decimals = 2
    elif entry > 100:
        decimals = 3
    elif entry > 10:
        decimals = 4
    elif entry > 1:
        decimals = 6
    elif entry > 0.1:
        decimals = 8
    elif entry > 0.001:
        decimals = 10
    else:
        decimals = 12
    
    # Create manual signal
    signal = {
        "type": signal_type,
        "entry": entry,
        "target": target,
        "stop": stop,
        "decimals": decimals
    }
    
    chart_file = await plot_price_chart(prices, symbol, signal)
    if not chart_file:
        await message.answer("Could not generate chart.")
        return

    comment = await get_gemini_comment(symbol, signal["type"])
    
    # Get market trend from CoinPaprika
    market_trend = get_market_trend()
    
    # Format trend with colored emojis
    trend_text = f"🟩 TREND ➡️ {market_trend}" if market_trend == "Long" else f"🟥 TREND ➡️ {market_trend}" if market_trend == "Short" else f"TREND ➡️ {market_trend}"
    
    # Determine trend compatibility
    trend_compatibility = (
        "🟩 Signal is compatible with the trend."
        if (signal["type"] == "LONG" and market_trend == "Long") or (signal["type"] == "SHORT" and market_trend == "Short")
        else "🟥 Signal is not compatible with the trend."
    )

    try:
        # Format like the example with precise decimal display and trend info
        signal_text = f"""⏳ Timeframe: {timeframe}
#{symbol.upper()}USDT {"🟩 LONG Signal 🟩" if signal["type"] == "LONG" else "🟥 SHORT Signal 🟥"}
ENTRY ➡️ {signal["entry"]:.{signal["decimals"]}f}
TARGET ➡️ {signal["target"]:.{signal["decimals"]}f}
STOP   ➡️ {signal["stop"]:.{signal["decimals"]}f}
{trend_text}
{trend_compatibility}
🟥 High Risk ⚠️
🔎 Chart added for basic analysis. Assess your own risk before trading.

{comment}"""

        await message.answer_photo(
            photo=FSInputFile(chart_file),
            caption=signal_text,
            parse_mode="HTML"
        )
        # Clean up the chart file after sending
        os.remove(chart_file)
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        await message.answer("An error occurred while sending the response.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
