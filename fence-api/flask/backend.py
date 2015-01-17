from pymongo import MongoClient
import math

client = MongoClient()
db = client.assassin
users = db.users

# adds a user and returns their ObjectID Post
def add_user(name, image, loc):
	user = {"name":name,
			"image":image,
			"hunt_id":None,		# person user is hunting
			"prey_id":None,		# person hunting user
			"loc":loc,
			"dir":None
			}
	return users.insert(user)		# unique "_id" field added by default

# most important function
# called whenever a user submits new location data
# handles processing of game information Post
def update_loc(user_id, new_loc):
	# update user location in the DB
	users.update({"_id":user_id}, {"$set": {"loc": new_loc}}, upsert=False)

	cur_user = users.find_one({"_id": user_id})
	# check if we're still being hunted; if not, change prey_id to None
	#if not hunted(cur_user["prey_id"]):
	#	users.update({"_id":user_id}, {"$set": {"prey_id":None}}, upsert=False)
		# DECREMENTED cur_user.prey_id = None

	# if user is not hunting, search for nearby prey and assign one
	if cur_user["hunt_id"] == None:
		nearby = getNearby(user_id)
		if nearby is not None:
			for doc in nearby:
				#print(doc["prey_id"], user_id)
				if doc["prey_id"] is None and doc["_id"] != user_id:
					# If user does not have a target and a target is near
					# and that target does not have someone hunting him, return new target Id
					users.update({"_id":doc["_id"]}, {"$set": {"prey_id":cur_user["_id"]}}, upsert=False)
					users.update({"_id":user_id}, {"$set": {"hunt_id":doc["_id"]}}, upsert=False)

					# DECREMENTED doc.prey_id = cur_user._id
					# DECREMENTED cur_user.hunt_id = doc._id

	# end the game if the players get too far apart
	elif too_far(user_id, cur_user["hunt_id"]):
		# print("executing, motherfucker")
		users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
		# DECREMENTED cur_user.hunt_id = None
		users.update({"_id":cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)
		# DECREMENTED users.find({"_id": user_id}).prey_id = None

# finds users within 1/2 mile get
def getNearby(user_id):
	cur_user = users.find_one({"_id": user_id})
	# Radius of about 1/2 mile
	return db.users.find({"loc": {"$within": {"$center": [cur_user["loc"], float(1)/138]}}})
	# DECREMENTED return users.find({"loc": SON([("$near", cur_user["loc"]), ("$maxDistance", 1/138)])})

# called when user kills his/her target
def killed(user_id):
	users.update({"_id":user_id}, {"$set": {"hunt_id":None}}, upsert=False)
	cur_user = users.find_one({"_id": user_id})
	users.update({"_id": cur_user["hunt_id"]}, {"$set": {"prey_id":None}}, upsert=False)

# determines whether the user assigned to hunt you is still hunting you
# Decremented get
def hunted(prey_id):
	if users.find_one({"_id":prey_id}) != None and users.find_one({"_id":prey_id})["hunt_id"] == None:
		return False
	return True

# determine if the players are too far apart get
def too_far(id_1, id_2):
	user1 = users.find_one({"_id": id_1})
	user2 = users.find_one({"_id": id_2})
	dist = math.sqrt((user2["loc"][0] - user1["loc"][0])**2 + (user2["loc"][1] - user2["loc"][1])**2)
	print(dist)
	if dist > 1/69:
		return True
	return False
