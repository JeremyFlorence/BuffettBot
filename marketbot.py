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
    start_datetime = datetime.strptime(start, '%m-%d-%Y')
    end_datetime = datetime.strptime(end, '%m-%d-%Y')
    filtered_data = []
    filtered_datetimes = []

    if start_datetime > end_datetime:
        await bot.say("Error: Start date is after end date!")
        return

    rdelta = relativedelta.relativedelta(end_datetime, start_datetime)
    ts_pandas = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'], output_format='pandas')
    print('Years: ' + str(rdelta.years) + '\n' 
          'Months: ' + str(rdelta.months) + '\n'
          'Days: ' + str(rdelta.days)
          )

    try:
        if rdelta.years >= 2:
            interval = "weekly"
            date_format = "%Y-%m-%d"
            data, metadata = ts_pandas.get_weekly(symbol=symbol)

        elif rdelta.months >= 1 or rdelta.years >= 1:
            interval = "daily"
            date_format = "%Y-%m-%d"
            data, metadata = ts_pandas.get_daily(symbol=symbol, outputsize='full')

        elif rdelta.days >= 5:
            interval = "60min"
            date_format = "%Y-%m-%d %H:%M:%S"
            data, metadata = ts_pandas.get_intraday(symbol=symbol, interval='60min', outputsize='full')

        else:
            interval = "30min"
            data, metadata = ts_pandas.get_intraday(symbol=symbol, interval='30min', outputsize='full')
            date_format = "%Y-%m-%d %H:%M:%S"

    except ValueError:
        await bot.say("There was an error retrieving the data for this range. "
                      "Please make sure you're using valid arguments and try again")
    
    for datapoint_datestr in data['4. close'].keys():
        datapoint_datetime = datetime.strptime(datapoint_datestr, date_format)
        
        if start_datetime <= datapoint_datetime <= end_datetime:
            filtered_datetimes.append(datapoint_datestr)
            filtered_data.append(data['4. close'][datapoint_datestr])

    print(len(filtered_datetimes))
    fig, ax = plt.subplots()
    ax.plot(filtered_datetimes, filtered_data)
    plt.title('Time Series for {} on {} - {}'.format(symbol,
                                                     datetime.strftime(start_datetime, '%m-%d-%Y'),
                                                     datetime.strftime(end_datetime, '%m-%d-%Y')))

    plt.xticks(range(len(filtered_datetimes)), filtered_datetimes, fontsize=6, rotation='45', ha='right')

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
