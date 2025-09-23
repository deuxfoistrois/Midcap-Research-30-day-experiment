import json
import os
from datetime import datetime
from alpaca_trade_api import REST
import warnings
warnings.filterwarnings('ignore')

def place_initial_portfolio_orders():
    """Place initial buy orders for all configured stocks"""
    print("=== Placing Initial Portfolio Orders ===")
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize Alpaca API
    api = REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
        api_version='v2'
    )
    
    orders_placed = []
    
    for symbol, stock_config in config['stocks'].items():
        try:
            # Get current price
            quote = api.get_latest_quote(symbol)
            current_price = float(quote.ask_price)
            
            # Calculate shares to buy
            allocation = stock_config['allocation']
            shares = int(allocation / current_price)
            
            print(f"Placing order: BUY {shares} shares of {symbol} at ~${current_price:.2f}")
            
            # Place market buy order
            order = api.submit_order(
                symbol=symbol,
                qty=shares,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            orders_placed.append({
                'symbol': symbol,
                'shares': shares,
                'estimated_price': current_price,
                'order_id': order.id,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"Order placed successfully: {order.id}")
            
        except Exception as e:
            print(f"Error placing order for {symbol}: {e}")
    
    print(f"\nTotal orders placed: {len(orders_placed)}")
    for order in orders_placed:
        print(f"{order['symbol']}: {order['shares']} shares @ ${order['estimated_price']:.2f}")
    
    return orders_placed

if __name__ == "__main__":
    place_initial_portfolio_orders()
