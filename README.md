# Fibonacci Trading Bot

A Fibonacci retracement trading bot that places orders in NinjaTrader based on Fibonacci levels.

## Docker Setup

### Build the Container
```bash
docker build -t fib-trader .
```

### NinjaTrader Connection
The bot needs to connect to NinjaTrader running on your host machine. Use the appropriate command for your operating system:

#### For macOS/Windows:
```bash
docker run -p 36973:36973 --add-host=host.docker.internal:host-gateway ...
```

#### For Linux:
```bash
docker run --network host ...
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
# For macOS/Windows
docker run -p 36973:36973 \
           --add-host=host.docker.internal:host-gateway \
           -v $(pwd)/.env:/app/.env \
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
           --loss-threshold 500 \
           --price-stream-channel "NT8_ES_PRICESTREAM" \
           --fibonacci-ratios "[0,0.23,0.38,0.50,0.618,0.78,1.0,1.23,1.618,2.14,2.618,3.618,-0.23,-0.618,-1.14,-1.618,-2.14,-2.618,-3.618]" \
           --logging-level "INFO"

# For Linux
docker run --network host \
           -v $(pwd)/.env:/app/.env \
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
           --loss-threshold 500 \
           --price-stream-channel "NT8_ES_PRICESTREAM" \
           --fibonacci-ratios "[0,0.23,0.38,0.50,0.618,0.78,1.0,1.23,1.618,2.14,2.618,3.618,-0.23,-0.618,-1.14,-1.618,-2.14,-2.618,-3.618]" \
           --logging-level "INFO"
```

#### Backtest Mode
```bash
# For macOS/Windows
docker run -p 36973:36973 \
           --add-host=host.docker.internal:host-gateway \
           -v $(pwd)/.env:/app/.env \
           -v $(pwd)/configs:/app/configs \
           -v $(pwd)/datasets:/app/datasets \
           --tty \
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
           --loss-threshold 10 \
           --price-stream-channel "NT8_ES_PRICESTREAM" \
           --fibonacci-ratios "[0,0.23,0.38,0.50,0.618,0.78,1.0,1.23,1.618,2.14,2.618,3.618,-0.23,-0.618,-1.14,-1.618,-2.14,-2.618,-3.618]" \
           --logging-level "INFO"

# For Linux
docker run --network host \
           -v $(pwd)/.env:/app/.env \
           -v $(pwd)/configs:/app/configs \
           -v $(pwd)/datasets:/app/datasets \
           --tty \
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
           --loss-threshold 10 \
           --price-stream-channel "NT8_ES_PRICESTREAM" \
           --fibonacci-ratios "[0,0.23,0.38,0.50,0.618,0.78,1.0,1.23,1.618,2.14,2.618,3.618,-0.23,-0.618,-1.14,-1.618,-2.14,-2.618,-3.618]" \
           --logging-level "INFO"
```