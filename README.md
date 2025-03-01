### Realtime tick based data streamed from Ninja Trader - Strategies
Realtime tick data is streamed from Ninja trader websockets and dumped onto Redis pub/sub so that downstream bots can consume pricing streams without having to start their own connections or websocket plugins. The data is consumed currently for following strategies:
- Fibonnaci levels based trades

##### The system design flow is the following: 

![diagram-export-01-03-2025-20_57_20](https://github.com/user-attachments/assets/dfb4038b-9e7d-48d5-b106-60c06c6d52a8)
