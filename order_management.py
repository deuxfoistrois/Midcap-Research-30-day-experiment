import json
import os
from datetime import datetime
from alpaca_trade_api import REST, TimeFrame
import warnings
warnings.filterwarnings('ignore')

class OrderManager:
    def __init__(self):
        self.config = self.load_config()
        self.api = REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
            api_version='v2'
        )
        
    def load_config(self):
        """Load portfolio configuration"""
        with open('config.json', 'r') as f:
            return json.load(f)
    
    def load_latest_data(self):
        """Load latest portfolio state"""
        try:
            with open('docs/latest.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def get_current_price(self, symbol):
        """Get current market price for a symbol"""
        try:
            quote = self.api.get_latest_quote(symbol)
            return float(quote.ask_price)
        except:
            bar = self.api.get_latest_bar(symbol)
            return float(bar.close)
    
    def calculate_position_size(self, symbol, allocation, current_price):
        """Calculate number of shares to buy based on allocation"""
        shares = allocation / current_price
        return int(shares)  # Round down to avoid over-allocation
    
    def place_initial_orders(self):
        """Place initial buy orders for all configured stocks"""
        print("=== Placing Initial Portfolio Orders ===")
        
        orders_placed = []
        
        for symbol, stock_config in self.config['stocks'].items():
            try:
                current_price = self.get_current_price(symbol)
                allocation = stock_config['allocation']
                shares = self.calculate_position_size(symbol, allocation, current_price)
                
                if shares > 0:
                    # Place market buy order
                    order = self.api.submit_order(
                        symbol=symbol,
                        qty=shares,
                        side='buy',
                        type='market',
                        time_in_force='day'
                    )
                    
                    orders_placed.append({
                        'symbol': symbol,
                        'order_id': order.id,
                        'shares': shares,
                        'estimated_price': current_price,
                        'allocation': allocation,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    print(f"Order placed: BUY {shares} shares of {symbol} at ~${current_price:.2f}")
                
            except Exception as e:
                print(f"Error placing order for {symbol}: {e}")
        
        # Log orders
        self.log_orders(orders_placed, 'initial_buy')
        
        return orders_placed
    
    def place_stop_loss_orders(self):
        """Place stop loss orders for all positions"""
        print("=== Placing Stop Loss Orders ===")
        
        latest_data = self.load_latest_data()
        if not latest_data or 'positions' not in latest_data:
            print("No position data available for stop loss orders")
            return []
        
        stop_orders = []
        
        for symbol, position in latest_data['positions'].items():
            try:
                shares = int(position['shares'])
                stop_price = self.config['stocks'][symbol]['stop_loss']
                
                # Place stop loss order
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=shares,
                    side='sell',
                    type='stop',
                    time_in_force='gtc',  # Good till canceled
                    stop_price=stop_price
                )
                
                stop_orders.append({
                    'symbol': symbol,
                    'order_id': order.id,
                    'shares': shares,
                    'stop_price': stop_price,
                    'timestamp': datetime.now().isoformat()
                })
                
                print(f"Stop loss set: SELL {shares} shares of {symbol} at ${stop_price:.2f}")
                
            except Exception as e:
                print(f"Error placing stop loss for {symbol}: {e}")
        
        # Log stop orders
        self.log_orders(stop_orders, 'stop_loss')
        
        return stop_orders
    
    def update_trailing_stop_orders(self):
        """Update stop loss orders with trailing stops"""
        from trailing_stops import TrailingStopManager
        
        print("=== Updating Trailing Stop Orders ===")
        
        trailing_manager = TrailingStopManager()
        trailing_stops = trailing_manager.load_trailing_stops()
        
        updated_orders = []
        
        for symbol, stop_data in trailing_stops.items():
            if stop_data.get('active', False):
                try:
                    # Cancel existing stop loss orders for this symbol
                    existing_orders = self.api.list_orders(
                        status='open',
                        symbols=[symbol]
                    )
                    
                    for order in existing_orders:
                        if order.order_type == 'stop' and order.side == 'sell':
                            self.api.cancel_order(order.id)
                            print(f"Cancelled old stop order for {symbol}")
                    
                    # Get current position size
                    positions = self.api.list_positions()
                    position_qty = 0
                    for pos in positions:
                        if pos.symbol == symbol:
                            position_qty = int(float(pos.qty))
                            break
                    
                    if position_qty > 0:
                        # Place new trailing stop order
                        new_stop_price = stop_data['current_stop_price']
                        
                        order = self.api.submit_order(
                            symbol=symbol,
                            qty=position_qty,
                            side='sell',
                            type='stop',
                            time_in_force='gtc',
                            stop_price=new_stop_price
                        )
                        
                        updated_orders.append({
                            'symbol': symbol,
                            'order_id': order.id,
                            'shares': position_qty,
                            'stop_price': new_stop_price,
                            'stop_type': 'trailing',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        print(f"Updated trailing stop: {symbol} at ${new_stop_price:.2f}")
                
                except Exception as e:
                    print(f"Error updating trailing stop for {symbol}: {e}")
        
        # Log updated orders
        if updated_orders:
            self.log_orders(updated_orders, 'trailing_stop_update')
        
        return updated_orders
    
    def check_order_status(self):
        """Check status of recent orders"""
        print("=== Checking Order Status ===")
        
        try:
            # Get recent orders
            orders = self.api.list_orders(
                status='all',
                limit=50
            )
            
            recent_orders = []
            for order in orders:
                if order.symbol in self.config['stocks']:
                    recent_orders.append({
                        'symbol': order.symbol,
                        'order_id': order.id,
                        'side': order.side,
                        'qty': order.qty,
                        'type': order.order_type,
                        'status': order.status,
                        'filled_qty': order.filled_qty or 0,
                        'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                        'submitted_at': order.submitted_at,
                        'filled_at': order.filled_at
                    })
            
            # Print order status
            for order in recent_orders[-10:]:  # Last 10 orders
                status = order['status']
                symbol = order['symbol']
                side = order['side'].upper()
                qty = order['qty']
                
                if order['filled_avg_price']:
                    price_info = f"at ${order['filled_avg_price']:.2f}"
                else:
                    price_info = ""
                
                print(f"{status.upper()}: {side} {qty} {symbol} {price_info}")
            
            return recent_orders
            
        except Exception as e:
            print(f"Error checking order status: {e}")
            return []
    
    def log_orders(self, orders, order_type):
        """Log orders to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'order_type': order_type,
            'orders': orders,
            'total_orders': len(orders)
        }
        
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/orders_{datetime.now().strftime('%Y_%m')}.json"
        
        # Load existing log or create new
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def emergency_liquidate_position(self, symbol):
        """Emergency liquidation of a specific position"""
        print(f"=== EMERGENCY LIQUIDATION: {symbol} ===")
        
        try:
            # Get current position
            positions = self.api.list_positions()
            position_qty = 0
            
            for pos in positions:
                if pos.symbol == symbol:
                    position_qty = int(float(pos.qty))
                    break
            
            if position_qty > 0:
                # Cancel any existing orders for this symbol
                orders = self.api.list_orders(status='open', symbols=[symbol])
                for order in orders:
                    self.api.cancel_order(order.id)
                    print(f"Cancelled order {order.id}")
                
                # Place market sell order
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=position_qty,
                    side='sell',
                    type='market',
                    time_in_force='day'
                )
                
                print(f"EMERGENCY SELL: {position_qty} shares of {symbol}")
                print(f"Order ID: {order.id}")
                
                # Log emergency liquidation
                self.log_orders([{
                    'symbol': symbol,
                    'order_id': order.id,
                    'shares': position_qty,
                    'order_type': 'emergency_liquidation',
                    'timestamp': datetime.now().isoformat()
                }], 'emergency_liquidation')
                
                return order
            else:
                print(f"No position found for {symbol}")
                return None
                
        except Exception as e:
            print(f"Error in emergency liquidation for {symbol}: {e}")
            return None

if __name__ == "__main__":
    manager = OrderManager()
    
    # Check what operation to perform based on command line arguments
    import sys
    
    if len(sys.argv) > 1:
        operation = sys.argv[1]
        
        if operation == 'initial':
            manager.place_initial_orders()
        elif operation == 'stops':
            manager.place_stop_loss_orders()
        elif operation == 'update_trailing':
            manager.update_trailing_stop_orders()
        elif operation == 'status':
            manager.check_order_status()
        elif operation.startswith('liquidate_'):
            symbol = operation.split('_')[1]
            manager.emergency_liquidate_position(symbol)
    else:
        print("Usage: python order_management.py [initial|stops|update_trailing|status|liquidate_SYMBOL]")
        manager.check_order_status()
