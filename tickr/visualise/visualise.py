import plotly.graph_objects as go
import pandas as pd

# Read CSV file
df = pd.read_csv('formatted_data.csv')

# Fibonacci levels dictionary
fib_levels = {
    0.618: 21766,
    1.618: 21872,
    1.42: 21851,
    2.92: 22009,
    2.3: 21944,
    2.618: 21977,
    3.618: 22083,
    4.92: 22220,
    -0.618: 21636,
    -1.618: 21530,
    -2.618: 21425,
    -3.618: 21319
}

# Create figure
fig = go.Figure()

# Add price data as a line chart
fig.add_trace(go.Scatter(
    x=df['Timestamp'],
    y=df['Last Price'],
    mode='lines',
    name='Last Price',
    hovertemplate='%{y}'  # Ensures full price is shown in the tooltip
))

# Add dotted horizontal lines for Fibonacci levels
for key, value in fib_levels.items():
    fig.add_shape(
        type="line",
        x0=df["Timestamp"].min(),
        x1=df["Timestamp"].max(),
        y0=value,
        y1=value,
        line=dict(
            color="gray",
            width=1,
            dash="dot"
        )
    )
    
    # Add text label at the end of the chart
    fig.add_annotation(
        x=df["Timestamp"].max(),
        y=value,
        text=str(key),  # Label with the Fibonacci level
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(size=12, color="black")
    )

# Update layout to prevent y-axis abbreviations
fig.update_layout(
    title='9-NQ 09-24.Last',
    xaxis_title='Timestamp',
    yaxis_title='Price',
    showlegend=True,
    yaxis=dict(
        tickformat="d"  # Display full numbers instead of abbreviated format (e.g., 18595 instead of 18.59k)
    )
)

# Show figure
fig.show()