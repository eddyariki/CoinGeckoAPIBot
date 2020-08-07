import sqlite3
from sqlite3 import Error
from datetime import datetime
import io

class DBManager:
	def __init__(self, dbname, dev):
		self.development = dev
		try: 
			self.connection = sqlite3.connect(dbname, check_same_thread=False)
			print("Connection to SQLite DB was successful")
			self.cursor = self.connection.cursor()
			self.execute_query("create table", "CREATE TABLE IF NOT EXISTS chat (id integer, coin text, symbol text)")
			self.execute_query("create table", "CREATE UNIQUE INDEX IF NOT EXISTS chat_id on chat (id)")

		except Error as e:
			self.printErr(e)

	def load_in(self):
		data=self.fetch_all()
		memory = {}
		chat_id = []
		for row in data:
			memory[f"{row[0]}"] = {"coin": row[1], "symbol": row[2]}
			chat_id.append(row[0])
		return memory, chat_id
	def execute_query(self, name, query, args=None):
		try: 
			if(args):
				self.cursor.execute(query,args)
			else:
				self.cursor.execute(query)
			self.connection.commit()
			if(self.development):
				print(f"Query '{name}' executed successful")
		except Error as e:
			self.printErr(e, name)

	def update(self, args):
		try:
			# data=self.fetch_id(args(0))
			print(args)
			self.execute_query("update", "UPDATE chat SET coin=?, symbol=? WHERE id=?", args)
		except Error as e:
			print(e)
			self.printErr(e)

	def delete(self,args):
		try:
			self.execute_query("delete", "DELETE FROM chat WHERE id=?", args)
		except Error as e:
			self.printErr(e)
	def insert(self, args):
		try:
			self.execute_query("insert into", "INSERT OR IGNORE INTO  chat (id, coin, symbol) VALUES (?,?,?)", args)
		except Error as e:
			self.printErr(e)

	def fetch_all(self):
		try:
			self.execute_query('fetch all', "SELECT * FROM chat")
			d = self.cursor.fetchall()
			return d
		except Error as e:
			self.printErr(e)

	def fetch_id(self, id):
		try:
			self.execute_query(f'select id={id}', 'SELECT * FROM chat WHERE id=?', (id,))
			d = self.cursor.fetchall()
			return d
		except Error as e:
			self.printErr(e)
	
	def back_up(self):
		try:
			now = datetime.now()
			bck = sqlite3.connect(f"backup/db_{now.strftime('%m%d%H%Y')}.db")
			with bck:
				self.connection.backup(bck, pages=1, progress=None)
			print("Backup saved")
		except Error as e:
			self.printErr(e)

	def printErr(self, e, name=""):
		print(f"----!!!The error '{e}' occurred at {name}")


	def __del__(self):
		self.connection.close()
