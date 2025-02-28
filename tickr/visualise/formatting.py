import pandas as pd
from rich import print


# Define the file path
file_path = 'datasets/NQ 03-25.Last.txt'  # Replace with the actual path to your file

# Define column names
columns = ['Timestamp', 'Last Price', 'Bid Price', 'Ask Price', 'Volume']

# Read the file into a DataFrame
df = pd.read_csv(file_path, sep=';', header=None, names=columns)

# Convert the Timestamp column into a proper datetime format
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d %H%M%S %f')

# Display the DataFrame
print(df)

df.to_csv('formatted_data.csv', index=False)