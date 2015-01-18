from flask import Flask, jsonify, abort, url_for, request, make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
import math
import json

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
			"dir":None
			}
	return str(users.insert(user))		# unique "_id" field added by default

@app.route('/backend/get_loc', methods=['POST'])
def get_loc():
	user_id = request.form.get('user_id')
	user_id = string_to_ObjectId(user_id)
	cur_user = users.find_one({"_id": user_id})
	return json.dumps({"lat":cur_user["lat"], "lon":cur_user["lon"]})

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

	cur_user = users.find_one({"_id": user_id})
	# check if we're still being hunted; if not, change prey_id to None
	#if not hunted(cur_user["prey_id"]):
	#	users.update({"_id":user_id}, {"$set": {"prey_id":None}}, upsert=False)
		# DEPRECATED cur_user.prey_id = None

	# if user is not hunting, search for nearby prey and assign one
	if cur_user["hunt_id"] == None:
		nearby = getNearby(user_id)
		if nearby is not None:
			for doc in nearby:
				# print(doc["prey_id"], user_id)
				if doc["prey_id"] is None and doc["_id"] != user_id:
					# If user does not have a target and a target is near
					# and that target does not have someone hunting him, return new target Id
					users.update({"_id":doc["_id"]}, {"$set": {"prey_id":cur_user["_id"]}}, upsert=False)
					users.update({"_id":user_id}, {"$set": {"hunt_id":doc["_id"]}}, upsert=False)

					# DEPRECATED doc.prey_id = cur_user._id
					# DEPRECATED cur_user.hunt_id = doc._id

	# end the game if the players get too far apart
	elif too_far(user_id, cur_user["hunt_id"]):
		# print("executing, motherfucker")
		users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
		# DEPRECATED cur_user.hunt_id = None
		users.update({"_id":cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)
		# DEPRECATED users.find({"_id": user_id}).prey_id = None
	return "Success"

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
	users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
	cur_user = users.find_one({"_id": user_id})
	users.update({"_id": cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)

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
	#id_1 = request.args.get('id_1')
	#id_2 = request.args.get('id_2')
	#id_1 = string_to_ObjectId(id_1)
	#id_2 = string_to_ObjectId(id_2)
	user1 = users.find_one({"_id": id_1})
	user2 = users.find_one({"_id": id_2})
	dist = math.sqrt((user2["loc"][0] - user1["loc"][0])**2 + (user2["loc"][1] - user2["loc"][1])**2)
	print(dist)
	if dist > 1/69:
		return True
	return False

# default path
@app.route('/')
def index():
	return "<b>Running</b>"

if __name__ == '__main__':
	app.debug = True
	app.run(port=8000)