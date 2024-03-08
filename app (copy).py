import os
import interactions
from interactions import ChannelType, GuildText, OptionType, SlashContext, slash_command, slash_option, File, SlashCommandChoice, listen, Task, IntervalTrigger, TimeTrigger
from dotenv import load_dotenv
import json
import re
import requests
import time
import asyncio
import random
import sqlite3
import datetime
from datetime import datetime, timedelta, timezone


load_dotenv()
bottoken=os.getenv("TOKEN")
nodedownmessage = os.getenv("NODEDOWNMESSAGE")
sqlitedblocation = os.getenv("SQLITEDBLOCATION")
con = sqlite3.connect(sqlitedblocation)
cur = con.cursor()

os.makedirs(os.path.dirname(sqlitedblocation), exist_ok=True)

def initsqlite():
	con = sqlite3.connect(sqlitedblocation)
	cur = con.cursor()
	res = cur.execute("SELECT name FROM sqlite_master")
	check = res.fetchone() is None
	if check == True:
		cur.execute("CREATE TABLE verification(owner, account, vernumber, verified, timestamp TIMESTAMP)")
		cur.execute("CREATE TABLE price(price)")
		con.commit()
	else:
		return
		
initsqlite()

def adapt_datetime(ts):
    return ts.strftime("%Y-%m-%d %H:%M:%S.%f")

sqlite3.register_adapter(datetime, adapt_datetime)


bot = interactions.Client(token=bottoken)



	
@interactions.slash_command(name="price", description="Display the price of PascalCoin")

async def price(ctx):
	try:			
		cur.execute("SELECT price FROM price")
		price = cur.fetchone()[0]
		await ctx.send(price)

	except Exception:
		await store_price()
		time.sleep(0.2)
		cur.execute("SELECT price FROM price")
		price = cur.fetchone()[0]
		await ctx.send(f"**PascalCoin price:**\n1 **PASC** = {price} **USD**")
			
	
	
	
@Task.create(IntervalTrigger(minutes=10))
async def store_price():

	url = "https://api.coingecko.com/api/v3/simple/price?ids=pascalcoin&vs_currencies=usd"
	response = requests.get(url)
	   
	if response.status_code == 200:
		data = response.json()
		coin_name = list(data.keys())[0]
		price_usd = data[coin_name]["usd"]
		cur.execute("DELETE FROM price WHERE price")
		cur.execute("INSERT INTO price VALUES(?)", (price_usd,))
		con.commit()


@interactions.slash_command(name="account_info", description="Display information about a PASA")
@slash_option(
name="account",
description="The PASA account number",
opt_type=OptionType.INTEGER,
required=True
)

async def account_info(ctx, account :int):
	address = os.getenv("RPC_ADDRESS")
	port = os.getenv("RPC_PORT")
	url = f"{address}:{port}"
	
	data = {
		"jsonrpc": "2.0",
		"method": "getaccount",
		"params": {"account": account},
		"id": 123
	}
	
	headers = {"Content-Type": "application/json"}
	try:
		response = requests.post(url, json=data, headers=headers)
	except Exception as e:
		await ctx.send(nodedownmessage)
		return
	try:		
		if response.status_code == 200:
			result = json.loads(response.text)
			
			if 'result' in result:
				mainkey = result['result']
				account = mainkey['account']
				balance = mainkey['balance']
				state = mainkey['state']
				name = mainkey['name']
				
				if name == '':
					name = "No Name."
	
				await ctx.send(f"**Name:** {name}\n**Account Number:** {account}\n**Balance:** {balance} PASC\n**Account State:** {state}")
		
			else:
				await ctx.send(f"Invalid account number: {account}")

	except json.JSONDecodeError:
		await ctx.send("Error decoding JSON response from the server.")
	except Exception as e:
		await ctx.send(f"An error occurred: {e}")

@interactions.slash_command(name="operation_finder", description="Find an operation using the OpHash")
@slash_option(
name = "ophash",
description = "The operation hash",
opt_type=OptionType.STRING,
required = True
)

async def operation_info(ctx, ophash: str):
	address = os.getenv("RPC_ADDRESS")
	port = os.getenv("RPC_PORT")
	url = f"{address}:{port}"
	data = {
		"jsonrpc": "2.0",
		"method": "findoperation",
		"params": {"ophash": ophash},
		"id": 123
	}
	
	headers = {"Content-Type": "application/json"}
	try:
		response = requests.post(url, json=data, headers=headers)
	except Exception as e:
		await ctx.send(nodedownmessage)
		return
	
	try:
		result = json.loads(response.text)
		if response.status_code == 200:
			
			
			if 'result' in result:
				mainkey = result['result']
				block = mainkey['block']
				account = mainkey['account']
				signer_account = mainkey['signer_account']
				optxt = mainkey['optxt']
				fee = mainkey['fee']
				enc_payload = mainkey['payload']
				payload = bytes.fromhex(enc_payload).decode('utf-8')
				if payload == "":
					payload = "No payload."
				
				
		
				await ctx.send(f"**OpHash:** {ophash}\n\n**Block:** {block}\n**Account:** {account}\n**Signer Account:** {signer_account}\n**Operation:** {optxt}\n**Payload:** {payload}\n**Fee: {fee} PASC**")
		
			else:
				await ctx.send(f"Invalid OpHash: {ophash}")
				
			
	except requests.exceptions.ConnectionError as e:
		print(e)
	except requests.exceptions.ConnectionRefusedError as e:
		print(e)
	except Exception as e:
		print(e)
		
@interactions.slash_command(name="link_account", description="Link a PASA with your Discord ID using verification")
@slash_option(name="account", description="The PASA you want to link to Discord", opt_type=OptionType.INTEGER, required = True)

async def link_account(ctx, account : int):
	initsqlite()

	random_number = random.randint(1, 40000)
	timestamp = datetime.now(timezone.utc)

	cur.execute("SELECT * FROM verification WHERE account = ?", (account,))
	exists = cur.fetchone()
	if exists:
		cur.execute("SELECT verified FROM verification WHERE account = ?", (account,))
		verified = cur.fetchone()[0]
		if verified == 1:
			await ctx.send("Account already verified")
			return
		else:
			cur.execute("SELECT vernumber FROM verification WHERE account = ?", (account,))
			vernumber = cur.fetchone()[0]
			await ctx.send(f"Set {vernumber} as your account type.")
			return
	
	cur.execute(f"INSERT INTO verification VALUES(0, ?, ?, 0, ?)", (account, random_number, timestamp))
	con.commit()
	await ctx.send(f"You are going to link the PASA: {account}, by setting its account type to:\n\n{random_number}\n\nUse the command \"/verify\" to successfully link your PASA to your Discord account. Note: You have 2 hours to verify the account or else you have to get a new verification number.")
	
@interactions.slash_command(name="verify", description="Use this to verify that your PASA has the verification number.")
@slash_option(name="account", description="The PASA you want to verify.", opt_type=OptionType.INTEGER, required=True)

async def verify(ctx, account: int):
	initsqlite()
	try:
		cur.execute("SELECT verified FROM verification WHERE account = ?", (account,))
		isverified = cur.fetchone()[0]
		if isverified or isverified == 0:
			if isverified == 1:
				await ctx.send(f"Account {account} already verified.")

				return
			else:
				cur.execute("SELECT vernumber FROM verification WHERE account = ?", (account,))
				vernumber = cur.fetchone()[0]
				address = os.getenv("RPC_ADDRESS")
				port = os.getenv("RPC_PORT")
				url = f"{address}:{port}"
				
				data = {
					"jsonrpc": "2.0",
					"method": "getaccount",
					"params": {"account": account},
					"id": 123
				}
				
				headers = {"Content-Type": "application/json"}
				try:
					response = requests.post(url, json=data, headers=headers)
				except Exception as e:
					await ctx.send(nodedownmessage)
					return
				try:		
					if response.status_code == 200:
						result = json.loads(response.text)
						
						if 'result' in result:
							mainkey = result['result']
							acctype = mainkey['type']
							if acctype == vernumber:
								cur.execute("UPDATE verification SET verified = ? WHERE account =?", (1, account))
								owner = ctx.author.display_name
								cur.execute("UPDATE verification SET owner = ? WHERE account = ?", (owner, account,))
								con.commit()
								await ctx.send("Verification successful! You may change your account type back.")
								accrolecheck = interactions.utils.get(ctx.guild.roles, name=f"{account}")
								if accrolecheck == None:
									accrole = await ctx.guild.create_role(name=f"{account}", color = 16753920 )
									accroleid = accrole.id
									await ctx.author.add_role(accroleid)
								verrolecheck = interactions.utils.get(ctx.guild.roles, name="Verified")
								
								if verrolecheck == None:
									verrole = await ctx.guild.create_role(name="Verified", hoist = True)
									verroleid = verrole.id
									await ctx.author.add_role(verroleid)
									
								else:
									verroleid = verrolecheck.id
									await ctx.author.add_role(verroleid)
									

									


							else:
								await ctx.send("Verification failed.")
		
					
						else:
							await ctx.send(f"Invalid account number: {account}")
				except Exception as e:
					await ctx.send(f"Something went wrong, please try again later.\n{e}")
		else:
			await ctx.send("Please use the \"/link_account\" command first")
			

	except Exception as e:
		await ctx.send("Please use the \"/link_account\" command first.")
		print(e)
	
@Task.create(IntervalTrigger(seconds=1))	
async def delete_expired():
	now = datetime.now(timezone.utc)
	cutoff = now - timedelta(hours=2)
	cur.execute("DELETE FROM verification WHERE timestamp < ? AND verified = 0", (cutoff,))
	con.commit()
	






@listen()
async def on_ready():
	print('bot started')
	await store_price()
	store_price.start()
	delete_expired.start()


bot.start()
