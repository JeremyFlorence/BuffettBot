import os
import asyncio
from pprint import pprint
import discord
from discord.ext import commands
from alpha_vantage.timeseries import TimeSeries
import matplotlib

matplotlib.use('Agg')

bot = commands.Bot(command_prefix='$') 

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

# Command to see the most recent price data of a stock
@bot.command(pass_context=True)
async def current_price(ctx, symbol_input: str):
    data = ts.get_intraday(symbol=symbol_input, interval='1min', outputsize='compact')
    current_time = max(data[0].keys())
    most_recent_entry = data[0][current_time]
    output = get_nice_output(symbol_input, current_time, most_recent_entry)
    print(output)
    await bot.say(output)

# Command to plot current day price data at an interval of 1min
@bot.command(pass_context=True)
async def plot_today(ctx, symbol: str):
    ts_pandas = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'], output_format='pandas')
    data, meta_data = ts_pandas.get_intraday(symbol=symbol,interval='1min', outputsize='full')
    data['4. close'].plot()
    matplotlib.pyplot.title('Intraday Times Series for {} (1 min interval)'.format(symbol))

    if (os.path.exists('output.png')):
        print('Removing output.png')
        os.remove('output.png')

    matplotlib.pyplot.savefig('output.png')
    with open('output.png', 'rb') as f:
        await bot.upload(f)
    matplotlib.pyplot.clf()
    

# Turns the raw JSON price data into a nicely formatted string
# symbol: The stock symbol
# date: date/time of the data point
# json_data: Price data in JSON format
def get_nice_output(symbol, date, json_data):
    output = "[{}]: {} \n".format(date, symbol) # Metadata

    # Put each JSON key/value pair on a line. Format the value as USD
    # unless it is the stock's volume.
    for key in json_data.keys():
        output += "{}: ".format(key)
        if (key != "5. volume"):
            output += "${:,.2f} \n".format(float(json_data[key]))
        else:
            output += "{}".format(json_data[key])
    return output

def is_prod():
    if 'DISCORD_TOKEN' in os.environ:
        return True
    else:
        return False



ts = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'])
discord_token = ''
if (is_prod()):
    discord_token = os.environ['DISCORD_TOKEN']
else:
    discord_token = os.environ['DISCORD_TOKEN_DEV']

bot.run(discord_token)