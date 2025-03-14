# Fibonacci Trading Bot

A Fibonacci retracement trading bot that places orders in NinjaTrader based on Fibonacci levels.

## Docker Setup

### Build the Container
```bash
docker build -t fib-trader .
```

### Redis Configuration
Create a `.env` file in the project root with your Redis connection details:
```bash
REDIS_HOST=your-redis-host
REDIS_PORT=6379
```

### Run the Container

#### Production Mode
```bash
docker run -v $(pwd)/.env:/app/.env \
           -v $(pwd)/configs:/app/configs \
           --tty \
           fib-trader python -m tickr.strategies.fibonacci.run production \
           --point-a 123.45 \
           --point-b 123.40 \
           --instrument "NQ SEP24" \
           --quantity 2 \
           --take-profit 15 \
           --stop-loss 20 \
           --reactivation-distance 0.5 \
           --nt-account "APEX2948580000003" \
           --config-file "configs/es.dev.json" \
           --profit-threshold 1000 \
           --loss-threshold 500
```

#### Backtest Mode
```bash
docker run -v $(pwd)/.env:/app/.env \
           -v $(pwd)/configs:/app/configs \
           -v $(pwd)/datasets:/app/datasets \
           --tty \
           -e CONFIG_FILE="configs/es.dev.json"
           fib-trader python -m tickr.strategies.fibonacci.run backtest \
           --filepath "datasets/ES 14-03-2025.Last/ES 03-25.Last.txt" \
           --point-a 5600 \
           --point-b 5556.75 \
           --instrument "ES MAR25" \
           --quantity 2 \
           --take-profit 10 \
           --stop-loss 10 \
           --reactivation-distance 10 \
           --config-file "configs/es.dev.json" \
           --profit-threshold 10 \
           --loss-threshold 10
```

### Terminal Output Configuration
The container is configured with a default terminal width of 200 columns to ensure proper table formatting. You can override this by setting the `COLUMNS` environment variable:

```bash
docker run -e COLUMNS=250 ... fib-trader
```

For proper table formatting, always use the `--tty` flag when running the container. This ensures that tables and other formatted output are displayed correctly.

### Command Line Arguments

#### Production Mode Arguments
| Argument | Description | Example |
|----------|-------------|---------|
| --point-a | Fibonacci Point A | 123.45 |
| --point-b | Fibonacci Point B | 123.40 |
| --instrument | Trading instrument | "NQ SEP24" |
| --quantity | Number of contracts | 2 |
| --take-profit | Take profit points | 15 |
| --stop-loss | Stop loss points | 20 |
| --reactivation-distance | Distance to reactivate levels | 0.5 |
| --nt-account | NinjaTrader account number | "APEX2948580000003" |
| --config-file | Path to configuration file | "configs/es.dev.json" |
| --profit-threshold | Stop trading if total profit exceeds this value | 1000 |
| --loss-threshold | Stop trading if total loss exceeds this value (positive number) | 500 |

#### Backtest Mode Arguments
| Argument | Description | Example |
|----------|-------------|---------|
| --filepath | Path to historical data file | "datasets/ES 14-03-2025.Last/ES 03-25.Last.txt" |
| --point-a | Fibonacci Point A | 5600 |
| --point-b | Fibonacci Point B | 5556.75 |
| --instrument | Trading instrument | "ES MAR25" |
| --quantity | Number of contracts | 2 |
| --take-profit | Take profit points | 10 |
| --stop-loss | Stop loss points | 10 |
| --reactivation-distance | Distance to reactivate levels | 10 |
| --config-file | Path to configuration file | "configs/es.dev.json" |
| --profit-threshold | Stop trading if total profit exceeds this value | 1000 |
| --loss-threshold | Stop trading if total loss exceeds this value (positive number) | 500 |

### Redis Configuration (.env file)
| Variable | Description |
|----------|-------------|
| REDIS_HOST | Redis host address |
| REDIS_PORT | Redis port number |

### Important Notes
1. Make sure to mount your `.env` file when running the container
2. Mount your configs directory to access configuration files
3. For backtest mode, mount your datasets directory to access historical data
4. Redis configuration is loaded from `.env` file
5. All arguments can be modified directly in the command line
6. Use `--tty` flag for proper table formatting
7. Terminal width defaults to 200 columns but can be overridden
8. Profit and loss thresholds are optional - bot will run indefinitely if not specified
9. Loss threshold should be provided as a positive number 