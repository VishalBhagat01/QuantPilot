"""Curated financial facts, trivia, and fast entity extraction for instant AI speculative acknowledgment."""

import re
import random
from typing import Dict, Any

# Popular equities, commodities, and cryptos with verified trivia
POPULAR_ENTITIES: Dict[str, Dict[str, str]] = {
    "AAPL": {
        "name": "Apple Inc.",
        "fact": "Apple was founded on April Fools' Day (April 1, 1976). It became the first publicly traded U.S. company to cross $1T, $2T, and $3T in market capitalization.",
        "keywords": ["apple", "aapl", "iphone", "tim cook", "steve jobs"]
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "fact": "Microsoft went public in March 1986 at $21/share. A single $1,000 investment at its IPO would be worth over $4 million today with reinvested dividends.",
        "keywords": ["microsoft", "msft", "windows", "azure", "satya nadella", "bill gates"]
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "fact": "NVIDIA was founded in 1993 at a Denny's diner in San Jose. Its name derives from 'invidia', the Latin word for envy.",
        "keywords": ["nvidia", "nvda", "jensen huang", "geforce", "cuda", "h100", "blackwell"]
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "fact": "Tesla was named after inventor Nikola Tesla. When it went public in 2010 at $17/share, it was the first American carmaker to IPO since Ford in 1956.",
        "keywords": ["tesla", "tsla", "elon musk", "cybertruck", "model 3", "model y", "gigafactory"]
    },
    "GOOGL": {
        "name": "Alphabet Inc. (Google)",
        "fact": "Google's original name was 'BackRub'. The name 'Google' was a misspelling of 'googol', the number 1 followed by 100 zeros.",
        "keywords": ["google", "googl", "goog", "alphabet", "sundar pichai", "larry page", "sergey brin"]
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "fact": "Jeff Bezos initially wanted to name the company 'Cadabra' (as in Abracadabra), but a lawyer misheard it as 'Cadaver', prompting the change to Amazon.",
        "keywords": ["amazon", "amzn", "bezos", "andy jassy", "aws", "prime"]
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "fact": "Meta's flagship Facebook platform reached 1 billion monthly active users in 2012, just 8 years after being launched from a Harvard dorm room.",
        "keywords": ["meta", "facebook", "zuckerberg", "instagram", "whatsapp", "quest"]
    },
    "NFLX": {
        "name": "Netflix, Inc.",
        "fact": "In 2000, Blockbuster had the opportunity to buy Netflix for just $50 million and turned it down. Netflix is now worth hundreds of billions.",
        "keywords": ["netflix", "nflx", "streaming", "reed hastings"]
    },
    "AMD": {
        "name": "Advanced Micro Devices",
        "fact": "AMD was founded in 1969 by Jerry Sanders and seven colleagues with just $100,000 in capital, starting as a logic chip manufacturer.",
        "keywords": ["amd", "lisa su", "ryzen", "radeon", "epyc"]
    },
    "INTC": {
        "name": "Intel Corporation",
        "fact": "Intel was originally going to be named 'NM Electronics', but the founders combined 'Integrated Electronics' into the iconic portmanteau 'Intel'.",
        "keywords": ["intel", "intc", "pat gelsinger", "core ultra", "x86"]
    },
    "BRK": {
        "name": "Berkshire Hathaway",
        "fact": "Berkshire Hathaway Class A (BRK.A) is the most expensive single stock in the world, trading over $600,000 per share because Warren Buffett refused stock splits.",
        "keywords": ["berkshire", "brk", "buffett", "munger", "omaha"]
    },
    "JPM": {
        "name": "JPMorgan Chase & Co.",
        "fact": "JPMorgan traces its origins back to 1799 and the Manhattan Company, chartered by Aaron Burr to provide clean water to New York City.",
        "keywords": ["jpmorgan", "jpm", "jamie dimon", "chase"]
    },
    "V": {
        "name": "Visa Inc.",
        "fact": "Visa processes over 200 billion transactions each year across more than 200 countries, handling peaks of over 65,000 transaction messages per second.",
        "keywords": ["visa", "payments", "credit card"]
    },
    "WMT": {
        "name": "Walmart Inc.",
        "fact": "Walmart is the world's largest company by revenue, generating over $600 billion annually and employing over 2.1 million associates worldwide.",
        "keywords": ["walmart", "wmt", "sam walton", "retail"]
    },
    "DIS": {
        "name": "The Walt Disney Company",
        "fact": "Walt Disney mortgaged his own home to finance the creation of Disneyland in 1953, turning a concept into a global media and entertainment empire.",
        "keywords": ["disney", "dis", "bob iger", "marvel", "pixar"]
    },
    "BTC": {
        "name": "Bitcoin",
        "fact": "The first commercial Bitcoin transaction occurred in May 2010 when Laszlo Hanyecz bought two Papa John's pizzas for 10,000 Bitcoins.",
        "keywords": ["bitcoin", "btc", "satoshi", "halving", "crypto"]
    },
    "ETH": {
        "name": "Ethereum",
        "fact": "Ethereum was proposed in late 2013 by 19-year-old Vitalik Buterin and introduced the concept of programmable smart contracts to the blockchain.",
        "keywords": ["ethereum", "eth", "vitalik", "smart contract"]
    },
    "GOLD": {
        "name": "Gold Commodity",
        "fact": "All the gold ever mined in human history would fit into a cube measuring roughly 22 meters (72 feet) on each side.",
        "keywords": ["gold", "xau", "bullion", "yellow metal"]
    },
    "SILVER": {
        "name": "Silver Commodity",
        "fact": "Silver is the most electrically conductive of all metals, making it indispensable in modern solar panels, electronics, and medical equipment.",
        "keywords": ["silver", "xag"]
    },
    "SPY": {
        "name": "SPDR S&P 500 ETF Trust",
        "fact": "SPY, launched in January 1993, was the very first exchange-traded fund (ETF) listed in the United States and remains the most actively traded ETF in the world.",
        "keywords": ["spy", "s&p", "s&p 500", "index fund", "voo"]
    },
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "fact": "QQQ tracks the Nasdaq-100 index, representing the 100 largest non-financial companies listed on Nasdaq, heavily tilted towards global innovation leaders.",
        "keywords": ["qqq", "nasdaq", "tech 100"]
    }
}

GENERAL_MARKET_FACTS = [
    "The New York Stock Exchange was founded in 1792 under a buttonwood tree on Wall Street with the signing of the historic Buttonwood Agreement.",
    "Warren Buffett bought his first stock (Cities Service Preferred) at age 11 in 1942 for $38 a share and waited for it to reach $40 before selling.",
    "Over 70% of all US stock trading volume is executed by algorithmic trading systems and quantitative algorithms rather than manual humans.",
    "The S&P 500 has historically produced an average annual return of approximately 10% before inflation over the past 90+ years.",
    "The term 'bull market' originated because a bull attacks by thrusting its horns upward, while a 'bear market' refers to a bear swiping downward.",
    "Compound interest was famously described by Albert Einstein as the 'eighth wonder of the world: he who understands it, earns it; he who doesn't, pays it.'",
    "Peter Lynch's famous investment rule: 'Know what you own, and know why you own it.' Never invest in an idea you cannot explain with a crayon.",
    "A standard stock market trading day in the US spans 6.5 hours (9:30 AM to 4:00 PM Eastern Time), during which billions of shares change hands."
]


def detect_query_subject(query: str) -> Dict[str, Any]:
    """
    Rapidly extracts stock ticker or entity from user query (sub-millisecond)
    and returns tailored acknowledgment data and trivia.
    """
    clean = query.lower()

    # 1. Direct keyword search across popular entities
    for ticker, data in POPULAR_ENTITIES.items():
        for kw in data["keywords"]:
            # Match whole words or symbol tokens
            if re.search(r'\b' + re.escape(kw) + r'\b', clean):
                return {
                    "symbol": ticker,
                    "name": data["name"],
                    "fact": data["fact"],
                    "is_specific": True
                }

    # 2. Check for generic capitalized ticker symbols like "AMD", "PLTR", "SOFI"
    ticker_match = re.search(r'\b[A-Z]{2,5}\b', query)
    if ticker_match:
        cand = ticker_match.group(0).upper()
        if cand in POPULAR_ENTITIES:
            data = POPULAR_ENTITIES[cand]
            return {
                "symbol": cand,
                "name": data["name"],
                "fact": data["fact"],
                "is_specific": True
            }
        return {
            "symbol": cand,
            "name": f"{cand} Stock",
            "fact": random.choice(GENERAL_MARKET_FACTS),
            "is_specific": True
        }

    # 3. Fallback to general market facts
    return {
        "symbol": None,
        "name": "Market Research",
        "fact": random.choice(GENERAL_MARKET_FACTS),
        "is_specific": False
    }
