import json
import os
from datetime import datetime, timedelta
import pandas as pd
from alpaca_trade_api import REST, TimeFrame
import warnings
warnings.filterwarnings('ignore')

class PortfolioManager:
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
    
    def get_current_prices(self):
        """Get current market prices for all stocks"""
        symbols = list(self.config['stocks'].keys())
        try:
            quotes = self.api.get_latest_quotes(symbols)
            prices = {}
            for symbol in symbols:
                if symbol in quotes:
                    prices[symbol] = float(quotes[symbol].ask_price)
                else:
                    # Fallback to bars if quote fails
                    bars = self.api.get_latest_bar(symbol)
                    prices[symbol] = float(bars.close)
            return prices
        except Exception as e:
            print(f"Error fetching prices: {e}")
            return {}
    
    def get_benchmark_prices(self):
        """Get benchmark ETF prices"""
        benchmarks = list(self.config['benchmarks'].keys())
        try:
            quotes = self.api.get_latest_quotes(benchmarks)
            prices = {}
            for symbol in benchmarks:
                if symbol in quotes:
                    prices[symbol] = float(quotes[symbol].ask_price)
                else:
                    bars = self.api.get_latest_bar(symbol)
                    prices[symbol] = float(bars.close)
            return prices
        except Exception as e:
            print(f"Error fetching benchmark prices: {e}")
            return {}
    
    def calculate_positions(self, prices):
        """Calculate position data based on current prices"""
        positions = {}
        total_positions_value = 0
        
        for symbol, stock_config in self.config['stocks'].items():
            if symbol in prices:
                current_price = prices[symbol]
                entry_price = stock_config['entry_target']
                allocation = stock_config['allocation']
                shares = allocation / entry_price
                
                current_value = shares * current_price
                cost_basis = allocation
                pnl = current_value - cost_basis
                pnl_pct = pnl / cost_basis if cost_basis > 0 else 0
                
                positions[symbol] = {
                    'symbol': symbol,
                    'shares': round(shares, 2),
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'market_value': round(current_value, 2),
                    'cost_basis': cost_basis,
                    'unrealized_pnl': round(pnl, 2),
                    'unrealized_pnl_pct': round(pnl_pct, 4),
                    'sector': stock_config['sector'],
                    'stop_loss': stock_config['stop_loss'],
                    'catalyst': stock_config['catalyst'],
                    'technical_setup': stock_config['technical_setup']
                }
                total_positions_value += current_value
        
        return positions, total_positions_value
    
    def calculate_portfolio_metrics(self, positions_value):
        """Calculate overall portfolio metrics"""
        baseline = self.config['portfolio']['baseline_investment']
        total_allocation = sum([config['allocation'] for config in self.config['stocks'].values()])
        cash = baseline - total_allocation
        
        portfolio_value = positions_value + cash
        total_return = portfolio_value - baseline
        total_return_pct = total_return / baseline if baseline > 0 else 0
        
        return {
            'cash': round(cash, 2),
            'portfolio_value': round(portfolio_value, 2),
            'total_invested': baseline,
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 4),
            'positions_count': len([p for p in self.config['stocks'].keys()]),
            'max_loss': round(baseline * self.config['portfolio']['max_portfolio_loss_pct'], 2)
        }
    
    def save_latest_data(self, positions, portfolio_metrics, benchmark_prices):
        """Save current portfolio state to latest.json"""
        data = {
            'positions': positions,
            'benchmarks': benchmark_prices,
            'last_update': datetime.now().isoformat(),
            'experiment_start': self.config['portfolio']['experiment_start_date'],
            **portfolio_metrics
        }
        
        os.makedirs('docs', exist_ok=True)
        with open('docs/latest.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def update_portfolio_history(self, positions, portfolio_metrics, benchmark_prices):
        """Update portfolio history CSV"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Prepare row data
        row_data = {
            'date': today,
            'portfolio_value': portfolio_metrics['portfolio_value'],
            'cash': portfolio_metrics['cash'],
            'positions_value': portfolio_metrics['portfolio_value'] - portfolio_metrics['cash'],
            'total_invested': portfolio_metrics['total_invested'],
            'total_return': portfolio_metrics['total_return'],
            'total_return_pct': portfolio_metrics['total_return_pct'],
            'positions_count': portfolio_metrics['positions_count']
        }
        
        # Add benchmark data
        for symbol, price in benchmark_prices.items():
            row_data[f'{symbol}_price'] = price
        
        # Add individual stock data
        for symbol, position in positions.items():
            row_data[f'{symbol}_price'] = position['current_price']
            row_data[f'{symbol}_pnl'] = position['unrealized_pnl']
            row_data[f'{symbol}_pnl_pct'] = position['unrealized_pnl_pct']
        
        # Create or update CSV
        os.makedirs('data', exist_ok=True)
        csv_file = 'data/portfolio_history.csv'
        
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            # Update today's row if exists, otherwise append
            if today in df['date'].values:
                df.loc[df['date'] == today, list(row_data.keys())] = list(row_data.values())
            else:
                df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
        else:
            df = pd.DataFrame([row_data])
        
        df.to_csv(csv_file, index=False)
    
    def run_daily_update(self):
        """Main function to run daily portfolio updates"""
        print("=== Daily Portfolio Update ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Get current market data
            prices = self.get_current_prices()
            benchmark_prices = self.get_benchmark_prices()
            
            if not prices:
                print("ERROR: Could not fetch stock prices")
                return False
            
            # Calculate positions and portfolio metrics
            positions, positions_value = self.calculate_positions(prices)
            portfolio_metrics = self.calculate_portfolio_metrics(positions_value)
            
            # Save data
            self.save_latest_data(positions, portfolio_metrics, benchmark_prices)
            self.update_portfolio_history(positions, portfolio_metrics, benchmark_prices)
            
            # Print summary
            print(f"Portfolio Value: ${portfolio_metrics['portfolio_value']:,.2f}")
            print(f"Total Return: ${portfolio_metrics['total_return']:,.2f} ({portfolio_metrics['total_return_pct']:.2%})")
            print(f"Active Positions: {portfolio_metrics['positions_count']}")
            print(f"Cash: ${portfolio_metrics['cash']:,.2f}")
            
            for symbol, position in positions.items():
                pnl_str = f"${position['unrealized_pnl']:,.2f} ({position['unrealized_pnl_pct']:.2%})"
                print(f"{symbol}: ${position['current_price']:,.2f} | P&L: {pnl_str}")
            
            print("Daily update completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR in daily update: {e}")
            return False

if __name__ == "__main__":
    manager = PortfolioManager()
    manager.run_daily_update()
