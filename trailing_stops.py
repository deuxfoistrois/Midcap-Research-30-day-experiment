import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class TrailingStopManager:
    def __init__(self):
        self.config = self.load_config()
        self.trailing_stops_file = 'data/trailing_stops.json'
        
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
    
    def load_trailing_stops(self):
        """Load current trailing stop data"""
        if os.path.exists(self.trailing_stops_file):
            with open(self.trailing_stops_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_trailing_stops(self, trailing_stops):
        """Save trailing stop data"""
        os.makedirs('data', exist_ok=True)
        with open(self.trailing_stops_file, 'w') as f:
            json.dump(trailing_stops, f, indent=2)
    
    def calculate_gain_percentage(self, current_price, entry_price):
        """Calculate current gain percentage"""
        return (current_price - entry_price) / entry_price if entry_price > 0 else 0
    
    def should_activate_trailing_stop(self, symbol, current_price, entry_price):
        """Check if trailing stop should be activated for a position"""
        gain_pct = self.calculate_gain_percentage(current_price, entry_price)
        trigger_threshold = self.config['portfolio']['trailing_stop_trigger']
        return gain_pct >= trigger_threshold
    
    def calculate_trailing_stop_price(self, highest_price):
        """Calculate trailing stop price (8% below highest price)"""
        trailing_distance = self.config['portfolio']['trailing_stop_distance']
        return highest_price * (1 - trailing_distance)
    
    def update_trailing_stops(self):
        """Update trailing stops based on current prices"""
        latest_data = self.load_latest_data()
        if not latest_data or 'positions' not in latest_data:
            print("No position data available for trailing stop updates")
            return
        
        trailing_stops = self.load_trailing_stops()
        updated_stops = {}
        
        print("=== Trailing Stop Update ===")
        
        for symbol, position in latest_data['positions'].items():
            current_price = position['current_price']
            entry_price = position['entry_price']
            
            # Check if trailing stop should be activated
            if self.should_activate_trailing_stop(symbol, current_price, entry_price):
                
                if symbol not in trailing_stops:
                    # Activate new trailing stop
                    trailing_stops[symbol] = {
                        'activated_date': datetime.now().isoformat(),
                        'activation_price': current_price,
                        'highest_price': current_price,
                        'current_stop_price': self.calculate_trailing_stop_price(current_price),
                        'active': True
                    }
                    print(f"ACTIVATED trailing stop for {symbol} at ${current_price:.2f}")
                    print(f"  Initial stop price: ${trailing_stops[symbol]['current_stop_price']:.2f}")
                
                else:
                    # Update existing trailing stop
                    existing_stop = trailing_stops[symbol]
                    if existing_stop['active']:
                        # Update highest price if current price is higher
                        if current_price > existing_stop['highest_price']:
                            existing_stop['highest_price'] = current_price
                            new_stop_price = self.calculate_trailing_stop_price(current_price)
                            
                            if new_stop_price > existing_stop['current_stop_price']:
                                old_stop = existing_stop['current_stop_price']
                                existing_stop['current_stop_price'] = new_stop_price
                                existing_stop['last_updated'] = datetime.now().isoformat()
                                
                                print(f"UPDATED trailing stop for {symbol}")
                                print(f"  New high: ${current_price:.2f}")
                                print(f"  Stop moved: ${old_stop:.2f} -> ${new_stop_price:.2f}")
                        
                        trailing_stops[symbol] = existing_stop
            
            else:
                # Position hasn't reached 5% gain yet - use original stop loss
                if symbol in trailing_stops:
                    trailing_stops[symbol]['active'] = False
                
                original_stop = self.config['stocks'][symbol]['stop_loss']
                print(f"{symbol}: Using original stop ${original_stop:.2f} (gain: {self.calculate_gain_percentage(current_price, entry_price):.2%})")
            
            # Add to updated stops (whether trailing or original)
            if symbol in trailing_stops and trailing_stops[symbol]['active']:
                updated_stops[symbol] = trailing_stops[symbol]
        
        # Save updated trailing stops
        self.save_trailing_stops(trailing_stops)
        
        return updated_stops
    
    def check_stop_triggers(self):
        """Check if any positions should be stopped out"""
        latest_data = self.load_latest_data()
        trailing_stops = self.load_trailing_stops()
        
        if not latest_data or 'positions' not in latest_data:
            return []
        
        triggered_stops = []
        
        for symbol, position in latest_data['positions'].items():
            current_price = position['current_price']
            
            # Determine which stop price to use
            if symbol in trailing_stops and trailing_stops[symbol]['active']:
                stop_price = trailing_stops[symbol]['current_stop_price']
                stop_type = 'trailing_stop'
            else:
                stop_price = self.config['stocks'][symbol]['stop_loss']
                stop_type = 'fixed_stop'
            
            # Check if current price has hit stop
            if current_price <= stop_price:
                triggered_stops.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'stop_price': stop_price,
                    'stop_type': stop_type,
                    'trigger_time': datetime.now().isoformat(),
                    'shares': position['shares']
                })
                
                print(f"STOP TRIGGERED: {symbol} at ${current_price:.2f} (stop: ${stop_price:.2f})")
        
        return triggered_stops
    
    def generate_stop_report(self):
        """Generate a report of current stop loss status"""
        latest_data = self.load_latest_data()
        trailing_stops = self.load_trailing_stops()
        
        if not latest_data or 'positions' not in latest_data:
            return "No position data available"
        
        report = "=== Current Stop Loss Status ===\n"
        report += f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for symbol, position in latest_data['positions'].items():
            current_price = position['current_price']
            entry_price = position['entry_price']
            gain_pct = self.calculate_gain_percentage(current_price, entry_price)
            
            report += f"{symbol}:\n"
            report += f"  Current Price: ${current_price:.2f}\n"
            report += f"  Entry Price: ${entry_price:.2f}\n"
            report += f"  Current Gain: {gain_pct:.2%}\n"
            
            if symbol in trailing_stops and trailing_stops[symbol]['active']:
                stop_data = trailing_stops[symbol]
                report += f"  Status: TRAILING STOP ACTIVE\n"
                report += f"  Highest Price: ${stop_data['highest_price']:.2f}\n"
                report += f"  Current Stop: ${stop_data['current_stop_price']:.2f}\n"
                report += f"  Activated: {stop_data['activated_date'][:10]}\n"
            else:
                original_stop = self.config['stocks'][symbol]['stop_loss']
                trigger_needed = self.config['portfolio']['trailing_stop_trigger']
                report += f"  Status: Fixed Stop Loss\n"
                report += f"  Stop Price: ${original_stop:.2f}\n"
                report += f"  Trailing Activates at: {trigger_needed:.1%} gain\n"
            
            report += "\n"
        
        return report
    
    def run_trailing_stop_update(self):
        """Main function to run trailing stop management"""
        print("=== Running Trailing Stop Management ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Update trailing stops based on current prices
            updated_stops = self.update_trailing_stops()
            
            # Check for triggered stops
            triggered_stops = self.check_stop_triggers()
            
            if triggered_stops:
                print(f"\nWARNING: {len(triggered_stops)} positions triggered stops!")
                for stop in triggered_stops:
                    print(f"  {stop['symbol']}: ${stop['current_price']:.2f} <= ${stop['stop_price']:.2f}")
            
            # Generate and log report
            report = self.generate_stop_report()
            
            # Save report to logs
            os.makedirs('logs', exist_ok=True)
            with open(f"logs/trailing_stops_{datetime.now().strftime('%Y_%m_%d')}.txt", 'w') as f:
                f.write(report)
            
            print("Trailing stop update completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR in trailing stop update: {e}")
            return False

if __name__ == "__main__":
    manager = TrailingStopManager()
    manager.run_trailing_stop_update()
