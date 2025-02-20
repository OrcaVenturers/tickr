run:
	@python -m xyz.strategies.fibs

stream:
	@python -m pricestream.tradovate

subscribe:
	@python -m xyz.pricestream.subscribe

strategy:
	@python -m xyz.strategies.fibonacci.retracement

setup:
	@python -m pip install --upgrade pip
	@pip install --no-cache-dir -r requirements.txt
	@playwright install chromium
	@pip install -e .
	@$(support-libs)