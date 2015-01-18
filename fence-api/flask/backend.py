from flask import Flask, jsonify, abort, url_for, request, make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
import math
import json
import calendar
from time import gmtime
import time

client = MongoClient()
db = client.assassin
users = db.users

app = Flask(__name__)

# adds a user and returns their ObjectID Post
@app.route('/backend/add_user', methods=['POST'])
def add_user():
	lat = float(request.form.get('lat'))
	lon = float(request.form.get('lon'))
	#return str(lat) + str(lon)
	loc = [lat, lon]
	user = {"name":request.form.get('name'),
			"image":request.form.get('image'),
			"hunt_id":None,		# person user is hunting
			"prey_id":None,		# person hunting user
			"loc":loc,
			"dir":None,
			"last_connect":int(calendar.timegm(time.gmtime())),
			"recently_killed":False
			}
	return str(users.insert(user))		# unique "_id" field added by default

@app.route('/backend/get_loc', methods=['POST'])
def get_loc():
	user_id = request.form.get('user_id')
	user_id = string_to_ObjectId(user_id)
	cur_user = users.find_one({"_id": user_id})
	return json.dumps({"lat":cur_user["loc"][0], "lon":cur_user["loc"][1]})

# most important function
# called whenever a user submits new location data
# handles processing of game information Post
@app.route('/backend/update_loc', methods=['POST'])
def update_loc():
	user_id = request.form.get('user_id')
	user_id = string_to_ObjectId(user_id)
	lat = float(request.form.get('lat'))
	lon = float(request.form.get('lon'))
	new_loc = [lat, lon]
	# update user location in the DB
	users.update({"_id":user_id}, {"$set": {"loc": new_loc}}, upsert=False)
	users.update({"_id":user_id}, {"$set": {"last_connect": int(calendar.timegm(time.gmtime()))}}, upsert=False)

	# removes disconnected users
	users.remove({"last_connect": {"$lt": int(calendar.timegm(time.gmtime()))-300}})

	# Checks if the user needs to be told they were killed
	cur_user = users.find_one({"_id": user_id})
	if cur_user["recently_killed"]:
		users.update({"_id":user_id}, {"$set": {"recently_killed": False}}, upsert=False)
		return json.dumps({"Life":"DEAD"})

	# check if we're still being hunted; if not, change prey_id to None
	#if not hunted(cur_user["prey_id"]):
	#	users.update({"_id":user_id}, {"$set": {"prey_id":None}}, upsert=False)
		# DEPRECATED cur_user.prey_id = None

	# if user is not hunting, search for nearby prey and assign one
	if cur_user["hunt_id"] is None:
		nearby = getNearby(user_id)
		if nearby is not None:
			for doc in nearby:
				# print(doc["prey_id"], user_id)
				if doc["hunt_id"] == user_id:
					users.update({"_id":user_id}, {"$set": {"prey_id":doc["_id"]}}, upsert=False)
					val1 = None
					if cur_user["prey_id"] is not None:
						val1 = str(cur_user["prey_id"])
					val2 = None
					if cur_user["hunt_id"] is not None:
						val2 = str(cur_user["hunt_id"])
					val3 = None
					val4 = None
					if val2 is not None:
						hunt = users.find_one(cur_user["hunt_id"])
						val3 = hunt["loc"][0]
						val4 = hunt["loc"][1]
					return json.dumps({"hunt_id": val2, "prey_id": val1, "hunt_lat":val3, "hunt_lon":val4})
				elif doc["prey_id"] is None and doc["_id"] != user_id:
					# If user does not have a target and a target is near
					# and that target does not have someone hunting him, return new target Id
					users.update({"_id":doc["_id"]}, {"$set": {"prey_id":cur_user["_id"]}}, upsert=False)
					users.update({"_id":user_id}, {"$set": {"hunt_id":doc["_id"]}}, upsert=False)
					cur_user = users.find_one({"_id": user_id})
					hunt = users.find_one(cur_user["hunt_id"])

					val = None
					if cur_user["prey_id"] is not None:
						val = str(cur_user["prey_id"])
					return json.dumps({"hunt_id": str(doc["_id"]), "prey_id": val, "hunt_lat":hunt["loc"][0], "hunt_lon":hunt["loc"][1]})

					# DEPRECATED doc.prey_id = cur_user._id
					# DEPRECATED cur_user.hunt_id = doc._id

	# end the game if the players get too far apart
	elif too_far(user_id, cur_user["hunt_id"]):
		# print("executing, motherfucker")
		users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
		# DEPRECATED cur_user.hunt_id = None
		users.update({"_id":cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)
		# DEPRECATED users.find({"_id": user_id}).prey_id = None
		cur_user = users.find_one({"_id": user_id})

		val1 = None
		if cur_user["prey_id"] is not None:
			val1 = str(cur_user["prey_id"])
		return json.dumps({"hunt_id": None, "prey_id": val1, "hunt_lat":None, "hunt_lon":None})

	cur_user = users.find_one({"_id": user_id})
	val1 = None
	if cur_user["prey_id"] is not None:
		val1 = str(cur_user["prey_id"])
	val2 = None
	if cur_user["hunt_id"] is not None:
		val2 = str(cur_user["hunt_id"])
	val3 = None
	val4 = None
	if val2 is not None:
		hunt = users.find_one(cur_user["hunt_id"])
		val3 = hunt["loc"][0]
		val4 = hunt["loc"][1]
	return json.dumps({"hunt_id": val2, "prey_id": val1, "hunt_lat":val3, "hunt_lon":val4})

def string_to_ObjectId(string):
	return ObjectId(string)

# finds users within 1/2 mile get
#@app.route('/backend/getNearby', methods=['GET'])
def getNearby(user_id):
	#user_id = request.args.get('user_id')
	#user_id = string_to_ObjectId(user_id)
	cur_user = users.find_one({"_id": user_id})
	# Radius of about 1/2 mile
	return db.users.find({"loc": {"$within": {"$center": [cur_user["loc"], float(1)/138]}}})
	# DEPRECATED return users.find({"loc": SON([("$near", cur_user["loc"]), ("$maxDistance", 1/138)])})

# called when user kills his/her target POST
@app.route('/backend/killed', methods=['POST'])
def killed():
	user_id = request.form.get('user_id')
	user_id = string_to_ObjectId(user_id)
	cur_user = users.find_one({"_id": user_id})
	users.update({"_id": cur_user["hunt_id"]}, {"$set": {"recently_killed":True}}, upsert=False)		# Will notify user of death on next update
	print(str(user_id) + "   KILLED   " + str(cur_user["hunt_id"]))
	users.update({"_id": cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)
	users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
	return "Success"

@app.route('/backend/app_closed', methods=['POST'])
def app_closed():
	user_id = request.form.get('user_id')
	user_id = string_to_ObjectId(user_id)
	users.remove({"_id": user_id})
	return "Success"

# determines whether the user assigned to hunt you is still hunting you
# Deprecated get
#@app.route('/backend/whetherStillHunted', methods=['GET'])
def hunted(prey_id):
	#prey_id = request.args.get('prey_id')
	#prey_id = string_to_ObjectId(prey_id)
	if users.find_one({"_id":prey_id}) != None and users.find_one({"_id":prey_id})["hunt_id"] == None:
		return False
	return True

# determine if the players are too far apart get
#@app.route('/backend/too_far', methods=['GET'])
def too_far(id_1, id_2):
	if id_1 is None or id_2 is None:
		return False
	#id_1 = request.args.get('id_1')
	#id_2 = request.args.get('id_2')
	#id_1 = string_to_ObjectId(id_1)
	#id_2 = string_to_ObjectId(id_2)
	user1 = users.find_one({"_id": id_1})
	user2 = users.find_one({"_id": id_2})
	dist = math.fabs(math.sqrt((user2["loc"][0] - user1["loc"][0])**2 + (user2["loc"][1] - user2["loc"][1])**2))
	#print(dist)
	if dist > float(1)/69:
		return True
	return False

# default path
@app.route('/')
def index():
	return "<b>Running</b>"

if __name__ == '__main__':
	app.debug = True
	app.run(port=8000)