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


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.CommandInvokeError):
        print(error)
        await bot.send_message(
                            ctx.message.channel,
                            "There was an error retrieving the data for this request."
                            "Please make sure you're using valid arguments and try again"
                            )

@bot.command(pass_context=True)
async def price(ctx, *symbols: str):
    output_msg = ""
    ts = TimeSeries(key=os.environ['ALPHA_VANTAGE_API_KEY'])
    data = ts.get_batch_stock_quotes(symbols)[0]
    for quote in data:
        output_msg += get_formatted_data(quote) + "\n"
    await bot.say(output_msg)


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

    for datapoint_datestr in data['4. close'].keys():
        datapoint_datetime = datetime.strptime(datapoint_datestr, date_format)
        
        if start_datetime <= datapoint_datetime <= end_datetime:
            filtered_datetimes.append(datapoint_datestr)
            filtered_data.append(data['4. close'][datapoint_datestr])

    if len(filtered_data) == 0:
        await bot.say("Oops! It looks like I don't have enough data to plot {} in this range. "
                      " Try using a larger range or choosing a date range that is more recent.".format(symbol))
        return

    fig, ax = plt.subplots()
    ax.plot(filtered_datetimes, filtered_data)
    plt.title('Time Series for {} on {} - {}'.format(symbol,
                                                     datetime.strftime(start_datetime, '%m-%d-%Y'),
                                                     datetime.strftime(end_datetime, '%m-%d-%Y')))
    if len(filtered_datetimes) > 21:
        xlabels = shrink_list(filtered_datetimes, 21)
    else:
        xlabels = filtered_datetimes

    plt.xticks(xlabels, xlabels, fontsize=6, rotation='45', ha='right')

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


def shrink_list(list_to_shrink, target_len):
    shrunken_list = []
    n = int(len(list_to_shrink)/target_len)

    for x in list_to_shrink[0::n]:
        shrunken_list.append(x)

    return shrunken_list


def get_formatted_data(data):
    output = ""

    for key in data.keys():
        output += "{}: ".format(key)
        if key == "2. price":
            output += "${:,.2f} \n".format(float(data[key]))
        else:
            output += "{} \n".format(data[key])

    return output


discord_token = os.environ['DISCORD_TOKEN']
bot.run(discord_token)
