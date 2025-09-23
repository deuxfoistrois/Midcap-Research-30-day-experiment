import json
import os
from datetime import datetime, timedelta
from alpaca_trade_api import REST
import warnings
warnings.filterwarnings('ignore')

class AlpacaSync:
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
    
    def get_alpaca_positions(self):
        """Get current positions from Alpaca account"""
        try:
            positions = self.api.list_positions()
            alpaca_positions = {}
            
            for pos in positions:
                symbol = pos.symbol
                if symbol in self.config['stocks']:
                    alpaca_positions[symbol] = {
                        'symbol': symbol,
                        'qty': float(pos.qty),
                        'market_value': float(pos.market_value),
                        'unrealized_pl': float(pos.unrealized_pl),
                        'unrealized_plpc': float(pos.unrealized_plpc),
                        'avg_entry_price': float(pos.avg_entry_price),
                        'current_price': float(pos.current_price)
                    }
            
            return alpaca_positions
        except Exception as e:
            print(f"Error fetching Alpaca positions: {e}")
            return {}
    
    def get_alpaca_orders(self):
        """Get recent orders from Alpaca"""
        try:
            orders = self.api.list_orders(
                status='all',
                limit=100,
                after=(datetime.now() - timedelta(days=7)).isoformat()
            )
            
            relevant_orders = []
            for order in orders:
                if order.symbol in self.config['stocks']:
                    relevant_orders.append({
                        'symbol': order.symbol,
                        'id': order.id,
                        'side': order.side,
                        'qty': float(order.qty),
                        'status': order.status,
                        'order_type': order.order_type,
                        'filled_qty': float(order.filled_qty or 0),
                        'filled_avg_price': float(order.filled_avg_price or 0),
                        'submitted_at': order.submitted_at,
                        'filled_at': order.filled_at,
                        'stop_price': float(order.stop_price) if order.stop_price else None
                    })
            
            return relevant_orders
        except Exception as e:
            print(f"Error fetching Alpaca orders: {e}")
            return []
    
    def get_current_price(self, symbol):
        """Get current market price for a symbol"""
        try:
            quote = self.api.get_latest_quote(symbol)
            return float(quote.ask_price)
        except:
            bar = self.api.get_latest_bar(symbol)
            return float(bar.close)
    
    def sync_positions_to_alpaca(self):
        """Project repo positions to Alpaca paper account"""
        print("=== Syncing Positions to Alpaca ===")
        
        latest_data = self.load_latest_data()
        if not latest_data or 'positions' not in latest_data:
            print("No repo position data to sync")
            return False
        
        alpaca_positions = self.get_alpaca_positions()
        
        orders_placed = []
        
        # Check each repo position
        for symbol, repo_position in latest_data['positions'].items():
            repo_shares = int(repo_position['shares'])
            alpaca_shares = int(alpaca_positions.get(symbol, {}).get('qty', 0))
            
            difference = repo_shares - alpaca_shares
            
            if abs(difference) > 0:
                try:
                    if difference > 0:
                        # Need to buy more shares
                        print(f"Buying {difference} shares of {symbol} to match repo")
                        order = self.api.submit_order(
                            symbol=symbol,
                            qty=difference,
                            side='buy',
                            type='market',
                            time_in_force='day'
                        )
                        orders_placed.append(('buy', symbol, difference, order.id))
                        
                    else:
                        # Need to sell shares
                        shares_to_sell = abs(difference)
                        print(f"Selling {shares_to_sell} shares of {symbol} to match repo")
                        order = self.api.submit_order(
                            symbol=symbol,
                            qty=shares_to_sell,
                            side='sell',
                            type='market',
                            time_in_force='day'
                        )
                        orders_placed.append(('sell', symbol, shares_to_sell, order.id))
                
                except Exception as e:
                    print(f"Error placing sync order for {symbol}: {e}")
            else:
                print(f"{symbol}: Alpaca matches repo ({alpaca_shares} shares)")
        
        if orders_placed:
            print(f"Placed {len(orders_placed)} sync orders")
            self.log_sync_orders(orders_placed)
        
        return len(orders_placed) > 0
    
    def update_stop_loss_orders(self):
        """Update stop loss orders on Alpaca to match repo/trailing stops"""
        print("=== Updating Stop Loss Orders ===")
        
        # Load trailing stops data
        try:
            with open('data/trailing_stops.json', 'r') as f:
                trailing_stops = json.load(f)
        except FileNotFoundError:
            trailing_stops = {}
        
        alpaca_positions = self.get_alpaca_positions()
        
        for symbol, position in alpaca_positions.items():
            shares = int(position['qty'])
            
            # Determine stop price
            if symbol in trailing_stops and trailing_stops[symbol].get('active', False):
                stop_price = trailing_stops[symbol]['current_stop_price']
                stop_type = 'trailing'
            else:
                stop_price = self.config['stocks'][symbol]['stop_loss']
                stop_type = 'fixed'
            
            try:
                # Cancel existing stop orders for this symbol
                existing_orders = self.api.list_orders(
                    status='open',
                    symbols=[symbol]
                )
                
                for order in existing_orders:
                    if order.order_type == 'stop' and order.side == 'sell':
                        self.api.cancel_order(order.id)
                        print(f"Cancelled old stop order for {symbol}")
                
                # Place new stop order
                if shares > 0:
                    order = self.api.submit_order(
                        symbol=symbol,
                        qty=shares,
                        side='sell',
                        type='stop',
                        time_in_force='gtc',
                        stop_price=stop_price
                    )
                    print(f"Set {stop_type} stop for {symbol}: {shares} shares at ${stop_price:.2f}")
            
            except Exception as e:
                print(f"Error updating stop for {symbol}: {e}")
    
    def detect_executed_stops(self):
        """Detect if any stop losses were executed by checking recent orders"""
        print("=== Checking for Stop Loss Executions ===")
        
        latest_data = self.load_latest_data()
        if not latest_data or 'positions' not in latest_data:
            print("No repo position data for comparison")
            return []
        
        # Get recent orders to check for stop executions
        recent_orders = self.get_alpaca_orders()
        
        executed_stops = []
        
        # Look for filled stop orders in the last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for order in recent_orders:
            if (order['order_type'] == 'stop' and 
                order['side'] == 'sell' and 
                order['status'] == 'filled' and
                order['filled_at'] and
                datetime.fromisoformat(order['filled_at'].replace('Z', '+00:00')) > cutoff_time):
                
                symbol = order['symbol']
                
                # Check if this position still exists in repo (shouldn't if stop executed)
                if symbol in latest_data['positions']:
                    executed_stops.append({
                        'symbol': symbol,
                        'execution_time': order['filled_at'],
                        'filled_qty': order['filled_qty'],
                        'filled_price': order['filled_avg_price'],
                        'stop_price': order['stop_price'],
                        'proceeds': order['filled_qty'] * order['filled_avg_price'],
                        'order_id': order['id']
                    })
                    
                    print(f"STOP EXECUTED: {symbol} - {order['filled_qty']} shares at ${order['filled_avg_price']:.2f}")
        
        return executed_stops
    
    def update_repo_after_stop_execution(self, executed_stops):
        """Update repo data after detecting stop loss executions"""
        if not executed_stops:
            return False
        
        latest_data = self.load_latest_data()
        if not latest_data:
            return False
        
        print(f"=== Updating Repo After {len(executed_stops)} Stop Executions ===")
        
        total_proceeds = 0
        
        for execution in executed_stops:
            symbol = execution['symbol']
            proceeds = execution['proceeds']
            
            print(f"Processing {symbol} stop execution:")
            print(f"  Sold {execution['filled_qty']} shares at ${execution['filled_price']:.2f}")
            print(f"  Proceeds: ${proceeds:,.2f}")
            
            # Remove position from repo
            if symbol in latest_data['positions']:
                del latest_data['positions'][symbol]
            
            # Add proceeds to cash
            total_proceeds += proceeds
            
            # Log the execution
            self.log_stop_execution(execution)
        
        # Update portfolio metrics
        latest_data['cash'] = latest_data.get('cash', 0) + total_proceeds
        latest_data['positions_count'] = len(latest_data['positions'])
        
        # Recalculate portfolio value
        positions_value = sum([pos['market_value'] for pos in latest_data['positions'].values()])
        latest_data['portfolio_value'] = positions_value + latest_data['cash']
        
        # Recalculate returns
        baseline = self.config['portfolio']['baseline_investment']
        latest_data['total_return'] = latest_data['portfolio_value'] - baseline
        latest_data['total_return_pct'] = latest_data['total_return'] / baseline
        
        # Update timestamp
        latest_data['last_update'] = datetime.now().isoformat()
        latest_data['last_sync_check'] = datetime.now().isoformat()
        
        # Save updated data
        with open('docs/latest.json', 'w') as f:
            json.dump(latest_data, f, indent=2)
        
        print(f"Repo updated with ${total_proceeds:,.2f} in stop loss proceeds")
        print(f"New portfolio value: ${latest_data['portfolio_value']:,.2f}")
        print(f"New total return: ${latest_data['total_return']:,.2f} ({latest_data['total_return_pct']:.2%})")
        
        return True
    
    def log_sync_orders(self, orders):
        """Log sync orders to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'position_sync',
            'orders': [
                {
                    'side': side,
                    'symbol': symbol, 
                    'qty': qty,
                    'order_id': order_id
                }
                for side, symbol, qty, order_id in orders
            ]
        }
        
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/sync_{datetime.now().strftime('%Y_%m')}.json"
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def log_stop_execution(self, execution):
        """Log stop loss execution"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'stop_execution',
            'symbol': execution['symbol'],
            'execution_time': execution['execution_time'],
            'filled_qty': execution['filled_qty'],
            'filled_price': execution['filled_price'],
            'stop_price': execution['stop_price'],
            'proceeds': execution['proceeds'],
            'alpaca_order_id': execution['order_id']
        }
        
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/executions_{datetime.now().strftime('%Y_%m')}.json"
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def run_full_sync(self):
        """Main sync function - runs all synchronization tasks"""
        print("=== Full Alpaca Synchronization ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Check account connectivity
            account = self.api.get_account()
            print(f"Connected to Alpaca - Account equity: ${float(account.equity):,.2f}")
            
            # Step 1: Check for executed stop losses
            executed_stops = self.detect_executed_stops()
            if executed_stops:
                self.update_repo_after_stop_execution(executed_stops)
            
            # Step 2: Sync positions to Alpaca
            self.sync_positions_to_alpaca()
            
            # Step 3: Update stop loss orders
            self.update_stop_loss_orders()
            
            print("Full synchronization completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR during synchronization: {e}")
            return False

if __name__ == "__main__":
    sync = AlpacaSync()
    sync.run_full_sync()
