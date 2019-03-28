import os
from datetime import date, datetime
from dateutil import relativedelta
from discord.ext import commands
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.cryptocurrencies import CryptoCurrencies
import matplotlib
matplotlib.use('Agg')   # We have to use Agg backend for Heroku
from matplotlib import pyplot as plt

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
    ts = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'])
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
    data, meta_data = ts_pandas.get_intraday(symbol=symbol, interval='5min', outputsize='full')
    filtered_data = []
    filtered_times = []

    for time in data['4. close'].keys():
        if str(date.today()) in time:
            filtered_times.append(time.replace(str(date.today()), ''))
            filtered_data.append(data['4. close'][time])

    fig, ax = plt.subplots()
    ax.plot(filtered_times, filtered_data)
    plt.title('Intraday Times Series for {} (5 min interval) on {}'.format(symbol, str(date.today())))
    
    plt.xticks(filtered_times, filtered_times, fontsize=6, rotation='45', ha='right')
    
    # we want to hide every other label
    for label in ax.xaxis.get_ticklabels()[1::2]:
        label.set_visible(False)

    if os.path.exists('output.png'):
        print('Removing output.png')
        os.remove('output.png')

    plt.savefig('output.png')
    with open('output.png', 'rb') as f:
        await bot.upload(f)
    plt.clf()


@bot.command(pass_context=True)
async def plot_range(ctx, symbol: str, start: str, end: str):
    start_datetime = datetime.strptime(start, '%m/%d/%Y')
    end_datetime = datetime.strptime(end, '%m/%d/%Y')

    if start_datetime > end_datetime:
        await bot.say("Error: Start date is after end date!")
        return

    ts_pandas = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'], output_format='pandas')
    interval = get_interval(start_datetime, end_datetime)

    if not interval:
        await bot.say('Please enter a valid start and end date.')
        return

    await bot.say('Interval: {}'.format(interval))


# Command to get current price of a cryptocurrency given a ticker symbol
@bot.command(pass_context=True)
async def crypto_current_price(ctx, symbol: str, market: str):
    cc = CryptoCurrencies(key=os.environ['ALPHA_VANTAGE_API_KEY'])
    data = cc.get_digital_currency_intraday(symbol=symbol, market=market)
    current_time = max(data[0].keys())
    most_recent_entry = data[0][current_time]
    output_header = "{} ({})".format(symbol, market)
    output = get_nice_output(output_header, current_time, most_recent_entry)
    print(output)
    await bot.say(output)


# Gets a data interval to ensure charts for large date ranges aren't too crowded
# start_date: start date in the range
# end_date: end date in the range
def get_interval(start_date, end_date):
    rdelta = relativedelta.relativedelta(end_date, start_date)
    print(rdelta.years)
    interval = ""
    if rdelta.years > 2:
        interval = "weekly"
    elif rdelta.months > 1:
        interval = "daily"
    elif rdelta.days > 5:
        interval = "60min"
    else:
        interval = "30min"

    return interval


# Turns the raw JSON price data into a nicely formatted string
# symbol: The stock symbol
# date: date/time of the data point
# json_data: Price data in JSON format
def get_nice_output(symbol, date, json_data):
    output = "[{}]: {} \n".format(date, symbol)  # Metadata

    # Put each JSON key/value pair on a line. Format the value as USD
    # unless it is the stock's volume.
    for key in json_data.keys():
        output += "{}: ".format(key)
        if key != "5. volume":
            output += "${:,.2f} \n".format(float(json_data[key]))
        else:
            output += "{}".format(json_data[key])
    return output


discord_token = os.environ['DISCORD_TOKEN']
bot.run(discord_token)
