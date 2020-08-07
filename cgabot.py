from dbmanager import DBManager
import telebot
from telebot import util
import requests
import time
import sys
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.ticker import StrMethodFormatter, NullFormatter
from pandas.plotting import register_matplotlib_converters
import io
from config import settings

matplotlib.use('Agg')
register_matplotlib_converters()

devMode = False
TOKEN = settings["TEST_TOKEN"]
TOKEN_DEPLOY=settings["TOKEN"]
URL = "https://api.coingecko.com/api/v3/"
bot = telebot.TeleBot(TOKEN_DEPLOY)
START_MESSAGE = """
This is an unofficial CoinGecko bot using their amazing free API.\n
/price coin-name
/marketcap coin-name
/sentiment coin-name
/change coin-name  
/rank coin-name 
/info coin-name 
e.g.) /info bitcoin ;  /info orion-proocol; /info btc\n
🌟 If a group coin is set, you can send each command as blank as well! 🌟
e.g.) /info  ; /change  .... etc.\n
/chart 👉:📈Get sick charts!📉
Format: /chart coin(optional if groupcoin is set) time(h or d) currency(default btc)
e.g) /chart orn 14d usd ; /chart 12d\n
/setup to set a group coin (Admin only).\n
🦎Powered by CoinGecko API🦎\n
"""
AUTH_USERS = ["administrator", "creator"]
DEV_USERS = {settings["DEVS"]}
groups = ["group", "supergroup"]
chatsDB ={}
chats_id=[]
memory_data=[chatsDB, chats_id]
forbidden_chars=["?", "%", "=","@", "*", "$", ":", "!"]
db = DBManager("chat.db", devMode)
coin_list={"list":[]}
state={"run_task":False}
MINUTE = 60
HOUR = 60*MINUTE
DAY = 24*HOUR
WEEK = DAY * 7
chat_id_DEBUG=settings["DEV_CHAT_ID"]
plt.style.use('./botchart.mplstyle')

def fetch_coins_list():
	r=requests.get(URL + "coins/list")
	print("Fetching list of coins.")
	if(r.status_code==200):
		data=r.json()
		coin_list["list"]=data

def chat_indexed(id):
	for key in memory_data[0]:
		if(key==id):
			return True
	return False

def search_for_coin(name, return_symbol=False):
	if len(name)>0:
		name=name.lower()
		index=0
		matched=[]
		symbol = ""
		for coin in coin_list["list"]:
			if(coin["symbol"]==name or coin["name"].lower()==name or coin["id"].lower()==name):
				matched.append(coin["id"])
				symbol = coin["symbol"]
		if (len(matched)>0):
			top_coin = " "
			top_rank = -1
			for i in matched:
				r = requests.get(URL + f"coins/{i}")
				if(r.status_code==200):
					data=r.json()
					rank=data['market_cap_rank']
					if(rank!=None and rank>top_rank):
						top_rank=rank
						top_coin=data['id']
						symbol = data['symbol']
			if(return_symbol):
				return top_coin, symbol
			else:
				return top_coin
		else:
			return " "
	else:
		return " "

def send_error(e):
	bot.send_message(chat_id_DEBUG, e)


def get_chart(range_from_,coin_symbol="",currency="btc"):
    time_value = 30*DAY
    coin_id=range_from_[1]
    if(len(range_from_)>2):
        query=range_from_[2]
        if("d" in query):
            text = query.split("d")
            if(text[0].isdigit()):
                time_value = float(text[0])*DAY
        elif("h" in query):
            text = query.split("h")
            if(text[0].isdigit()):
                time_value = float(text[0])*HOUR
        elif("day" in query):
            text = query.split("day")
            if(text[0].isdigit()):
                time_value = float(text[0])*DAY
        elif("hour" in query):
            text = query.split("hour")
            if(text[0].isdigit()):
                time_value = float(text[0])*HOUR

    URL = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"

    range_to = int(time.time())
    range_from = range_to - time_value
    if(currency!="btc" and coin_symbol !="btc" and currency!="eth"):
        currency="usd"
    elif(currency == "eth"):
    	currency="eth"
    payload={"vs_currency": currency, "from": range_from, "to": range_to}
    r = requests.get(URL,params=payload)
    if(r.status_code==200):
        data=r.json()
        prices=data["prices"]
        volumes=data['total_volumes']
        df=pd.DataFrame(prices, columns=["time", "price"])
        df['time'] = pd.to_datetime(df['time'],unit='ms')
        

        # scale = (1-(max_price - min_price)/max_price)*(0.1)+ ((max_price - min_price)/max_price)*2.0
        # print(scale)
        fig, ax = plt.subplots()
        ax.plot(df[['time']],df[['price']],marker=".", markevery=[-1], markersize=5, markeredgecolor="#ffb700", markeredgewidth=1, markerfacecolor=(0,0,0,0), color="#30f0e3")

        df_sorted=df.sort_values(by=['price'], ascending=0)
       	min_price=df_sorted.at[df_sorted.index[-1],'price']
        max_price=df_sorted.at[df_sorted.index[0],'price']
        current_price=df.at[df.index[-1],'price']
        current_time=df.at[df.index[-1],'time']
        percent = round(((max_price-min_price)/min_price)*100,2)
        percentCurrent = round(((current_price-min_price)/min_price)*100,2)
        ax.yaxis.grid(True,  which="both")
        ax.xaxis.grid(False)
        ax.set_yscale('log')
       	digits =int(min_price)
       	if(digits/10>1):
       		ax.yaxis.set_major_formatter(StrMethodFormatter('{x:.2f}'))
        	ax.yaxis.set_minor_formatter(StrMethodFormatter('{x:.2f}'))
       	else:
	        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:.8f}'))
	        ax.yaxis.set_minor_formatter(StrMethodFormatter('{x:.8f}'))
        ax.yaxis.set_major_locator(ticker.FixedLocator([min_price, max_price]))
        ax.yaxis.set_minor_locator(ticker.NullLocator())
        # ax.annotate(df.at[df.index[-1],'time'],min_price, df.at[df.index[-1],'time'],max_price,arrowprops=dict(arrowstyle="->"), va='center', color="#1e8a74")
        ax.annotate('', xy=(df_sorted.at[df_sorted.index[-1],'time'],max_price), xytext=(df_sorted.at[df_sorted.index[-1],'time'],min_price), arrowprops={'arrowstyle': '->', 'color':"#ffb700",'alpha':0.4}, va='center', alpha=0.4)
        ax.annotate(f" {percent}%", xy=(df_sorted.at[df_sorted.index[-1],'time'],(max_price-min_price)/2+min_price),color="#ffb700",fontsize='10',va='top', ha='left', alpha=0.4)

        ax.annotate('', xy=(current_time,current_price), xytext=(current_time,min_price), arrowprops={'arrowstyle': '->', 'color':"#cfaf5f", 'alpha':0.4}, va='center', alpha=0.4)
        ax.annotate(f" {percentCurrent}%", xy=(current_time,(current_price-min_price)/2+min_price),color="#cfaf5f",fontsize='10',va='top', ha='left', alpha=0.4)
        # ax.yaxis.set_major_locator(ticker.LogLocator(base=scale, numticks=10))
        # ax.yaxis.set_minor_locator(ticker.LogLocator(base=scale, numticks=10))
        # print(max_price*(max_price - min_price)/max_price/10)
        # ax.yaxis.set_major_locator(ticker.MultipleLocator(scale))
        # ax.yaxis.set_minor_locator(ticker.MultipleLocator(scale))
        # if(currency=="btc"):
        # 	ylabels = ['{:,.8f}'.format(y) + currency for y in chart.yticks()]
        # else:
        # 	ylabels = ['${:,.8f}'.format(y) for y in chart.yticks()]

        # chart.set(yticklabels=ylabels)
        # chart.set(xlabel=None, ylabel=None)
        date_time_value = round(((time_value/60)/60),1)
        date_time = "H" if date_time_value<24 else "D"
        date_time_value = date_time_value if date_time_value<24 else int(date_time_value/24)
        fig.suptitle(f"{coin_symbol.upper()}/{currency.upper()} " + str(date_time_value) + date_time)
        for label in ax.get_xticklabels():
        	label.set_ha("right")
        	label.set_rotation(45)

        if(currency=="btc"):
        	if(digits/10>1):
        		ax.text(df.at[df.index[-1],'time'], df.at[df.index[-1],'price'],' {:,.2f}'.format(df.at[df.index[-1],'price'])+currency, color="#ffb700",fontsize='10',va='top', ha='left')
        	else:
        		ax.text(df.at[df.index[-1],'time'], df.at[df.index[-1],'price'],' {:,.8f}'.format(df.at[df.index[-1],'price'])+currency, color="#ffb700",fontsize='10',va='top', ha='left')
        else:
        	if(digits/10>1):
        		ax.text(df.at[df.index[-1],'time'], df.at[df.index[-1],'price'],'${:,.2f}'.format(df.at[df.index[-1],'price']), color="#ffb700",fontsize='10',va='top', ha='left')
        	else:
        		ax.text(df.at[df.index[-1],'time'], df.at[df.index[-1],'price'],' ${:,.8f}'.format(df.at[df.index[-1],'price']),color="#ffb700",fontsize='10',va='top', ha='left')
        fig.text(0.8, 0.9, "*Data provided by CoinGecko",color='#30f0e3', fontsize='7')
        ax.tick_params(axis='x', which='major', labelsize=9)
        bytes_image = io.BytesIO()
        fig.savefig(bytes_image, format='png',bbox_inches="tight")
        plt.close()
        return bytes_image.getvalue()

@bot.message_handler(commands=['help','start'])
def command_help(message):
	bot.send_message(message.chat.id, START_MESSAGE)


#===============ADMIN======================

@bot.message_handler(commands=['setup'])
def command_help(message):
	try:
		user=bot.get_chat_member(message.chat.id, message.from_user.id)
		print(message.chat.type)
		if(user.status in AUTH_USERS or message.chat.type not in groups):
			if(chat_indexed(str(message.chat.id))==False):
				memory_data[0][f"{message.chat.id}"] = {"coin":"", "symbol":""}
				memory_data[1].append(str(message.chat.id))
				db.insert((f"{message.chat.id}","", ""))
				db.back_up()
				welcome_text="🦎First setup initializing. Registering Chat.🦎\n Thanks for using this bot. 🥰\n"
			else:
				print("This chat is already indexed.")
				welcome_text=""
			setup_text =welcome_text+"""
Setup CoinGecko query defaults here.\n
/setcoin :Set coin to track. Type in the coin name to set as group's default.
(e.g. bitcoin, orion-protocol, ethereum)
/groupcoin :Returns the current default coin of this group.
/removecoin :Removes group's default coin.
			"""
			bot.send_message(message.chat.id,setup_text)
		else:
			bot.send_message(message.chat.id, "You need permission to access this command.")
	except Exception as e:
		print(e)
		send_error(e)

@bot.message_handler(commands=['setcoin'])
def command_help(message):
	try:
		user=bot.get_chat_member(message.chat.id, message.from_user.id)
		if(chat_indexed(str(message.chat.id))==False):
			bot.send_message(message.chat.id, "Do /setup to register group.")
		else:

			if(user.status in AUTH_USERS  or message.chat.type not in groups):
				text=message.text
				for i in forbidden_chars:
					text=text.replace(i,'')
				query=text.split(" ")
				if(len(query)>1 and query[1]!=''):
					query[1]=search_for_coin(query[1])
					r = requests.get(URL+"coins/"+ query[1])
					if(r.status_code==404):
						bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
					elif(r.status_code==200):
						data=r.json()
						db.update((data["id"],data['symbol'], str(message.chat.id)))
						db.back_up()
						memory_data[0][f"{message.chat.id}"]["coin"]=data["id"]
						memory_data[0][f"{message.chat.id}"]["symbol"]=data["symbol"]
						bot.send_message(message.chat.id,f"Set group default coin as:\n{data['name']}\nSymbol: ${data['symbol'].upper()}")
				elif(len(query)==1):
					bot.send_message(message.chat.id, "Type in the coin name you want to track.")
			else:
				bot.send_message(message.chat.id, "You need permission to access this command.")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['groupcoin'])
def command_help(message):
	try:
		user=bot.get_chat_member(message.chat.id, message.from_user.id)
		if(chat_indexed(str(message.chat.id))==False):
			bot.send_message(message.chat.id, "Do /setup to register group.")
		else:
			if(user.status in AUTH_USERS  or message.chat.type not in groups):
				if(memory_data[0][f"{message.chat.id}"]["coin"]!=""):
					bot.send_message(message.chat.id, memory_data[0][f"{message.chat.id}"]["coin"])
				else:
					bot.send_message(message.chat.id, "Group coin not set. Do /setcoin")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['removecoin'])
def command_help(message):
	try:
		user=bot.get_chat_member(message.chat.id, message.from_user.id)
		if(chat_indexed(str(message.chat.id))==False):
			bot.send_message(message.chat.id, "Do /setup to register group.")
		else:
			if(user.status in AUTH_USERS  or message.chat.type=="private"):
				memory_data[0][f"{message.chat.id}"]["coin"]=""
				db.update(("","", str(message.chat.id)))
				db.back_up()
				bot.send_message(message.chat.id, "Group coin removed. \nSet again with /setcoin anytime.")
	except Exception as e:
		print(e)
		send_error(e)













#==================NORMAL=========================


@bot.message_handler(commands=['sentiment'])
def command_rank(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i,'')
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
					bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
			elif(r.status_code==200):
				data=r.json()
				up = data['sentiment_votes_up_percentage']
				down = data['sentiment_votes_down_percentage']
				name=data['name']
				bot.send_message(message.chat.id,f"How are people feeling today about {name} ${data['symbol'].upper()}?\n{up}% 😄\n{down}% ☹️")
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['change'])
def command_rank(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i,'')
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
				bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
			elif(r.status_code==200):
				data=r.json()
				mData=data['market_data']
				name=data['name']
				c24h=round(mData["price_change_percentage_24h"],1)
				c7d=round(mData["price_change_percentage_7d"],1)
				c30d=round(mData["price_change_percentage_30d"],1)
				c200d=round(mData["price_change_percentage_200d"],1)
				c1y=round(mData["price_change_percentage_1y"],1)
				bot.send_message(message.chat.id,f"""Price Change {name} ${data['symbol'].upper()}\n24h: {c24h}%\n7d: {c7d}%\n30d: {c30d}%\n200d: {c200d}%\n1yr: {c1y}%""")
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)

@bot.message_handler(commands=['marketcap'])
def command_rank(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i,'')
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
				bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
			elif(r.status_code==200):
				data=r.json()

				mData = data['market_data']
				mc = "{:,}".format(mData['market_cap']['usd'])
				rank = data['market_cap_rank']
				name=data['name']
				change = "{:,}".format(mData['market_cap_change_24h'])
				changeP = round(mData['market_cap_change_percentage_24h'],2)
				bot.send_message(message.chat.id,f"""{name} ${data['symbol'].upper()}\nRank: #{rank}\nMarket Cap: ${mc}\n24h Change: ${change} ({changeP}%)""")
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['rank'])
def command_rank(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i,'')
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
				bot.send_message(message.chat.id,"Coin not found. \nFor spaces,make sure to put a '-'")
			elif(r.status_code==200):
				data1 = r.json()
				# print(data1)
				rank = data1['market_cap_rank']
				name=data1['name']
				if(rank!=None):
					payload={"vs_currency": "usd", "page":int(rank/100)+1}
					r = requests.get(URL+"coins/markets", params=payload)
					data=r.json()
					rank100 = rank-int(rank/100)*100
					data.sort(key=lambda x: x['market_cap_rank'])
					coinsList = data[max(rank100-3,0):min(rank100+2, len(data))]
					msg=f"Market Cap Ranking ${data1['symbol'].upper()}"
					for i in range(len(coinsList)):
						if(coinsList[i]['symbol'].upper() == data1['symbol'].upper()):
							if(coinsList[i]['market_cap_rank']==1):
								msg += f"\n#{coinsList[i]['market_cap_rank']} {coinsList[i]['symbol'].upper()} 👑"
							else:
								msg += f"\n#{coinsList[i]['market_cap_rank']} {coinsList[i]['symbol'].upper()} 🚀"
						else:
							msg += f"\n#{coinsList[i]['market_cap_rank']} {coinsList[i]['symbol'].upper()}"
					bot.send_message(message.chat.id,msg)
				else:
					bot.send_message(message.chat.id,f"{name} has no rank. Probably a sh*#coin. *Opinions of @ariki_ariki, not CoinGecko")
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['p','price'])
def command_rank(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i, "")
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
				bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
			else:
				data = r.json()
				mData = data["market_data"]
				price= mData["current_price"]
				name = data["name"]
				price_usd="{:,}".format(price["usd"])
				price_btc=price["btc"]
				bot.send_message(message.chat.id, f"Price of {name} ${data['symbol'].upper()}:\n$USD: {price_usd}\n$BTC: {price_btc:.8f}")
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)
@bot.message_handler(commands=['info'])
def command_help(message):
	try:
		text =message.text
		for i in forbidden_chars:
			text=text.replace(i, "")
		query=text.split(" ")
		valid = False
		if(len(query)==1 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
			valid = True
		elif(len(query)==1):
			valid = False
		elif(len(query)>1 and query[1]!=''):
			query[1]=search_for_coin(query[1])
			valid=True
		if(valid):
			r = requests.get(URL+"coins/"+ query[1])
			if(r.status_code==404):
				bot.send_message(message.chat.id, "Coin not found. \nFor spaces,make sure to put a '-'")
			else:
				data = r.json()
				try:
					mData=data['market_data']
					name=data['name']
					coin_id=data['id']
					symbol=data['symbol'].upper()
					categories=data['categories']
					desc=data['description']["en"]
					rank=data["market_cap_rank"]
					coingecko_score=data['coingecko_score']
					developer_score=data['developer_score']
					community_score=data['community_score']
					liquidity_score=data['liquidity_score']
					public_interest_score=data['public_interest_score']
					circulating_supply=mData['circulating_supply']
					volume=mData['total_volume']['usd']
					total_supply=mData['total_supply']
					if(circulating_supply):
						circulating_supply = "{:,}".format(mData['circulating_supply'])
					else:
						circulating_supply = "unknown"
					if(volume):
						volume="{:,}".format(mData['total_volume']['usd'])
					else:
						volume="unknown"
					if(total_supply):
						total_supply="{:,}".format(mData['total_supply'])
					else:
						total_supply="∞"
					last_updated = mData['last_updated']
					text = f"""-----------------------------
{name} ${symbol}
-----------------------------

🌐🌐🌐🌐🌐🌐🌐🌐🌐🌐
Market Cap Rank: #{rank}
CoinGecko Score: {coingecko_score}
Developer Score: {developer_score}
Community Score: {community_score}
Liquidity Score: {liquidity_score}
Public Interest Score: {public_interest_score}

💰💰💰💰💰💰💰💰💰💰💰
Circulating Supply: {circulating_supply}{symbol}
Total Supply: {total_supply}{symbol}
Volume: ${volume}
(Last updated: {last_updated})

https://www.coingecko.com/en/coins/{coin_id}
"""	
					bot.send_message(message.chat.id,text)
				except Exception as e:
					print(e)
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)

@bot.message_handler(commands=['chart'])
def chart(message):
	try:
		text=message.text
		for i in forbidden_chars:
			text=text.replace(i, "")
		query=text.split(" ")
		valid = False
		three = False
		symbol=""
		if(len(query)==1 or len(query)==2 and memory_data[0][f"{message.chat.id}"]["coin"]!=""):
			if(len(query)==2):
				query=["",memory_data[0][f"{message.chat.id}"]["coin"],query[1]]
				symbol=memory_data[0][f"{message.chat.id}"]["symbol"]
				valid = True
			else:
				query=["",memory_data[0][f"{message.chat.id}"]["coin"]]
				symbol=memory_data[0][f"{message.chat.id}"]["symbol"]
				valid = True
		elif(len(query)>2 and query[1]!=''):
			query[1], symbol=search_for_coin(query[1],True)
			if(query[1]== " "):
				valid = False
			else:
				valid=True
				if(len(query)>3):
					three=True
		if(valid):

			if(three):
				image=get_chart(query, currency=query[3], coin_symbol=symbol)
			else:
				image=get_chart(query,coin_symbol=symbol)
			bot.send_photo(message.chat.id,image)
		else:
			bot.reply_to(message, "Enter a coin name.")
	except KeyError:
		bot.send_message(message.chat.id, "Default coin not set. Enter a coin name.")
	except Exception as e:
		print(e)
		send_error(e)












#==============Super Admin=================

@bot.message_handler(commands=['dev'])
def command(message):
	if(message.from_user.username in DEV_USERS):
		bot.send_message(message.chat.id,"/db_size\n/show_db\n/load_db\n/delete_db\n/backup_db\n/send_global\n/fetchcoins\n/runtask\n/endtask\n/taskrunning")
@bot.message_handler(commands=['db_size'])
def command_help(message):
	if(message.from_user.username in DEV_USERS):
		bot.send_message(message.chat.id, len(memory_data[1]))
@bot.message_handler(commands=['show_db'])
def command_help(message):
	if(message.from_user.username in DEV_USERS):
		data = db.fetch_all()
		print(data)
		if(len(data)>0):
			bot.send_message(message.chat.id, str(data))
		else:
			bot.send_message(message.chat.id, "Database is empty, or an error occurred.")

@bot.message_handler(commands=["load_db"])
def command_help(message):
	if(message.from_user.username in DEV_USERS):
		memory_data[0], memory_data[1]=db.load_in()
		# print(memory_data[0], memory_data[1])
		bot.send_message(message.chat.id, str(memory_data[1][:20]))

@bot.message_handler(commands=["delete_db"])
def command_help(message):

	if(message.from_user.username in DEV_USERS):
		db.back_up()
		db.delete((str(message.chat.id),))
		bot.send_message(message.chat.id, "Deleted DataBase.")

@bot.message_handler(commands=["backup_db"])
def command_help(message):
	if(message.from_user.username in DEV_USERS):
		db.back_up()
		bot.send_message(message.chat.id, "Backed up DataBase.")


@bot.message_handler(commands=["send_global"])
def command_help(message):
	if(message.from_user.username in DEV_USERS):
		text = message.text.split(" ")
		for i in memory_data[1]:
			bot.send_message(i,"Message from developer: "+ " ".join(text[1:]))

@bot.message_handler(commands=["fetchcoins"])
def fetchcoins(message):
	if(message.from_user.username in DEV_USERS):
		fetch_coins_list()
		bot.send_message(message.chat.id,"Fetched all coins.")

@bot.message_handler(commands=["runtask"])
def run_task(message):
	if(message.from_user.username in DEV_USERS):
		index=0
		if(state["run_task"]==False):
			state["run_task"]=True
			while state["run_task"]:
				bot.send_message(message.chat.id, f"Task: {index}")
				index+=1
				fetch_coins_list()
				time.sleep(43200)

@bot.message_handler(commands=["endtask"])
def end_task(message):
	if(message.from_user.username in DEV_USERS):
		state["run_task"]=False
		bot.send_message(message.chat.id, "Ending task")

@bot.message_handler(commands=["taskrunning"])
def task_running(message):
	if(message.from_user.username in DEV_USERS):
		truth ="Yes" if state["run_task"] else "No"
		bot.send_message(message.chat.id, truth)

if __name__ == '__main__':
	memory_data[0], memory_data[1]=db.load_in()
	fetch_coins_list()
	while True:
		asking=True
		try:
			print("Polling Started")
			time.sleep(1)
			bot.polling()

		except KeyboardInterrupt:
			#Exit
			while asking:
				try:
					close=input("Are you sure you want to close? [y]/[n]: \n")

					if(close=="y"):
						print("Cleaning up...")
						db.back_up()
						db.connection.close()
						asking = False
						sys.exit()
					else:
						asking = False
						pass
				except (EOFError, KeyboardInterrupt):
					pass
		except Exception as e:
			print(f"Error '{e}' occurred.")
			try:
				send_error(e)
			except Exception as e:
				print(e)
			time.sleep(10)



