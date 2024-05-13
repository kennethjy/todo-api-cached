import random
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import mysql.connector
import datetime

connect = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='1223334444',
    database='todo-db'
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Dictionary to store request counts for each client
request_counts = defaultdict(int)

# Time window for rate limiting (in seconds)
time_window = 60  # Change this value as needed

# Maximum allowed requests per time window
max_requests = 5  # Change this value as needed

# very simple cache so it can be run with a weak server
cache = {}

# Function to check if a client has exceeded the rate limit
def rate_limit_exceeded(client_ip):
    current_time = time.time()
    window_start_time = current_time - time_window
    # Remove old request counts
    for ip, timestamp in list(request_counts.items()):
        if timestamp < window_start_time:
            del request_counts[ip]
    # Check if client has exceeded the limit
    if request_counts[client_ip] >= max_requests:
        return True
    return False

# Middleware to check rate limit before processing each request
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host
    if rate_limit_exceeded(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # Increment request count for the client
    request_counts[client_ip] += 1
    response = await call_next(request)
    return response


def generateID():
    newid = ""
    for _ in range(20):
        newid += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[random.randint(0, 61)]
    return newid


@app.get("/")
def index():
    return {'a':'b'}


@app.get("/gettodoforuser/{uid}")
def gettodoforuser(uid):
    if "uid:" + uid in cache.keys():
        return cache["uid:" +uid]
    try:
        db = connect.cursor()
        db.execute("SELECT * FROM tasks "
                   "WHERE tasks.uid = %s;",
                   (uid,))
        todos = [{"id": i[0],
          "description": i[1],
          "date": i[2],
          "isChecked": i[3]}
         for i in db.fetchall()]
        cache["uid:" + uid] = todos
        return todos
    except:
        return "Not found"


@app.get("/gettodo/{id}/{uid}")
def gettodo(id, uid):
    if "uid:" + uid in cache.keys():
        for i in cache["uid:" + uid]:
            if i["id"] == id:
                return i
    if "id:" + id in cache.keys():
        return cache["id:" + id]

    try:
        db = connect.cursor()
        db.execute("SELECT * FROM tasks "
                   "WHERE tasks.taskid = %s;",
                   (id,))
        item = db.fetchone()
        if item is not None:
            todo = {"id": item[0],
                    "description": item[1],
                    "date": item[2],
                    "isChecked": item[3]}
            return todo
        return None
    except:
        return "Unknown error"


@app.post("/newtodo/{uid}")
def newTodo(uid):
    db = connect.cursor()
    id = generateID()
    db.execute("INSERT INTO tasks (taskid, description, date, isChecked, uid) "
               "VALUES (%s, %s, %s, %s, %s);",
               (id, "New Task", str(datetime.date.today()),
                0, uid))
    connect.commit()
    try:
        cache.pop("uid:" + uid)
    except:
        pass
    return id


@app.delete("/deletetodo/{id}/{uid}")
def deleteTodo(id, uid):
    db = connect.cursor()
    db.execute("DELETE FROM tasks "
               "WHERE taskid = %s;",
               (id,))
    try:
        cache.pop("uid:" + uid)
    except:
        pass
    try:
        cache.pop("id:" + id)
    except:
        pass
    connect.commit()


@app.put("/checktodo/{id}/{uid}")
def checkTodo(id, uid):
    db = connect.cursor()
    db.execute("UPDATE tasks SET isChecked = !isChecked WHERE taskid = %s",
               (id,))
    try:
        cache.pop("uid:" + uid)
    except:
        pass
    try:
        cache.pop("id:" + id)
    except:
        pass
    connect.commit()


@app.put("/changedesc/{id}/{desc}/{uid}")
def changedesc(id, desc, uid):
    db = connect.cursor()
    db.execute("UPDATE tasks SET description = %s WHERE taskid = %s",
               (desc, id))
    connect.commit()
    try:
        cache.pop("uid:" + uid)
    except:
        pass
    try:
        cache.pop("id:" + id)
    except:
        pass


'''
UPLOAD_FOLDER = "uploaded_photos"

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    try:
        # Save the uploaded file to the upload folder
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Return a JSON response with the URL of the uploaded photo
        return file_path
    except Exception as e:
        # Handle any errors that occur during file upload
        return "error"
'''
