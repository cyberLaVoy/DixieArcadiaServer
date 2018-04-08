from http.server import BaseHTTPRequestHandler, HTTPServer
from http import cookies
from games_db import GamesDB
from urllib.parse import parse_qs
from passlib.hash import bcrypt
import json, time, sys

# if set True, will disable all authorization checks on operations
gAutoAuthActive = True

import sessionStore
gSessionStore = sessionStore.SessionStore()

class RequestHandler(BaseHTTPRequestHandler):

    def end_headers(self):
        self.sendCookie()
        self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header("Access-Control-Allow-Credentials", "true")
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.loadSession()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.loadSession()
        pathList = self.path.split('/')
        if pathList[-1] ==  "":
            pathList = pathList[:-1]
        if len(pathList) <= 2:
                if pathList[1][:5] == "games":
                    if "most_popular=true" in pathList[1]:
                        self.handleListTop20Games()
                    else:
                        self.handleGetGames()
                elif pathList[1] == "me":
                    self.handleWhoAmI()
                else:
                    self.handle404()
        elif pathList[1] == "me":
            if pathList[2] == "games":
                self.handleListMyGames()
            else:
                self.handle404()
        elif pathList[1] == "games":
            if "ratings" in self.path:
                self.handleGetRatings()
            elif "tags" in self.path:
                if "tags" in pathList[2]:
                    self.handleListTags()
                else:
                    self.handleRetrieveTags()
            else:
                self.handleGameRetrieve()
        else:
            self.handle404()

    def do_POST(self):
        self.loadSession()
        if self.path == "/games":
            self.handleCreateGame()
        elif self.path == "/tags":
            self.handleAddTag()
        elif self.path == "/ratings":
            self.handleAddRating()
        elif self.path =="/users":
            self.handleUserCreate()
        elif self.path == "/sessions":
            self.handleCreateSession()
        else:
            self.handle404()

    def do_PUT(self):
        self.loadSession()
        pathList = self.path.split('/')
        if pathList[1] == "games":
            self.handleGameUpdate()
        else:
            self.handle404()

    def do_DELETE(self):
        self.loadSession()
        pathList = self.path.split('/')
        if pathList[1] == "games":
            if "tags" in self.path:
                self.handleDeleteTag()
            else:
                self.handleDeleteGame()
        elif pathList[1] == "sessions":
            self.handleDeleteSession()
        else:
            self.handle404()


#Game Methods
    def handleGetGames(self):
        db = GamesDB()
        # If there's a query string
        if '?' in self.path:
            parsed_qs = parse_qs(self.path.split("?")[1])
            if "tags_contain" in parsed_qs:
                tag = parsed_qs["tags_contain"][0].upper()
                json_string = json.dumps(db.listGamesWithTagsFilter(tag))
            else:
                # Set arguments that weren't provided to empty string
                if "profile_name_contains" not in parsed_qs:
                    parsed_qs["profile_name_contains"] = ['']
                if "description_contains" not in parsed_qs:
                    parsed_qs["description_contains"] = ['']
                if "game_name_contains" not in parsed_qs:
                    parsed_qs["game_name_contains"] = ['']
                profile_name = parsed_qs["profile_name_contains"][0]
                game_name = parsed_qs["game_name_contains"][0]
                description = parsed_qs["description_contains"][0]
                json_string = json.dumps(db.listGamesWithGeneralFilter(profile_name, game_name , description))
        else:
            json_string = json.dumps(db.listGames())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json_string, "utf-8"))

    def handleCreateGame(self):
        if "userID" in self.mSession or gAutoAuthActive: 
            profile_name = self.mSession.get("profile_name")
            # if auto authentication is active, then post the game under the client user
            if gAutoAuthActive:
                profile_name = "client"
            postData = self.getParsedBody()
            game_name = postData['game_name'][0]
            description = postData['description'][0]
            tags = json.loads(postData['tags'][0])
            db = GamesDB()
            game_id = str(db.createGame(profile_name, game_name, description))
            for tag in tags:
                db.addTag(game_id, tag)
            self.send_response(201)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes(game_id, "utf-8"))
        else:
            self.handle401()

    # handles the authorization before calling updateGame()
    def handleGameUpdate(self):
        if "userID" in self.mSession or self.mSession.get("isAdmin") or gAutoAuthActive:
            db = GamesDB()
            path = self.path.split('/')[2]
            game_id = path.split('?')[0]
            if db.profileNameOwnsGame(self.mSession.get("profile_name"), game_id) or self.mSession.get("isAdmin") or gAutoAuthActive:
                self.updateGame()
            else:
                self.handle403()
        else:
            self.handle401()
    def updateGame(self):
        db = GamesDB()
        path = self.path.split('/')[2]
        game_id = path.split('?')[0]
        game_container = db.getGameInfo(game_id)
        if len(game_container) == 0:
            self.handle404()
            return
        if '?' in self.path:
            parsed_qs = parse_qs(self.path.split("?")[1])
            if parsed_qs.get("increment_plays") == ["true"]:
                if self.mSession.get("isAdmin") or gAutoAuthActive:
                    db.incrementPlays(game_id)
                else:
                    self.handle403()
            elif parsed_qs.get("zip") == ["true"]:
                length = int(self.headers["Content-length"])
                body = self.rfile.read(length)
                db.setGameZip(game_id, body)
            elif parsed_qs.get("thumbnail") == ["true"]:
                length = int(self.headers["Content-length"])
                body = self.rfile.read(length)
                db.setGameThumnail(game_id, body)
            else:
                self.handle404()
        else:
            parsed_qs = self.getParsedBody()
            game_name = game_container[0]["game_name"]
            description = game_container[0]["description"]
            tags = game_container[0]["tags"]
            if "game_name" in parsed_qs:
                game_name = parsed_qs['game_name'][0]
            if "description" in parsed_qs:
                description = parsed_qs['description'][0]
            if "tags" in parsed_qs:
                tags = parsed_qs['tags'][0]
            db.updateGameInfo(game_id, game_name, description, tags)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes(game_id, "utf-8"))


    def handleDeleteGame(self):
        if "userID" in self.mSession or self.mSession.get("isAdmin") or gAutoAuthActive:
            game_id = self.path.split('/')[2]
            db = GamesDB()
            if db.profileNameOwnsGame(self.mSession.get("profile_name"), game_id) or self.mSession.get("isAdmin") or gAutoAuthActive:
                db.deleteGame(game_id)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes("Game succesfully deleted.", "utf-8"))
            else:
                self.handle403()
        else:
            self.handle401()

    def handleGameRetrieve(self):
        db = GamesDB()
        path = self.path.split('/')[2]
        game_id = path.split('?')[0]
        if not db.gameExists(game_id):
            self.handle404()
            return
        if '?' in self.path:
            parsed_qs = parse_qs(self.path.split("?")[1])
            if parsed_qs.get("zip") == ["true"]:
                if self.mSession.get("isAdmin") or gAutoAuthActive:
                    self.handleGameZipRetrieve(game_id)
                else:
                    self.handle403()
            elif parsed_qs.get("thumbnail") == ["true"]:
                self.handleGameThumbnailRetrieve(game_id)
        else:
            gameData = json.dumps(db.getGameInfo(game_id))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(gameData, "utf-8"))
    
    def handleGameZipRetrieve(self, game_id):
        db = GamesDB()
        gameData = db.getGameZip(game_id)['zip']
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(gameData)

    def handleGameThumbnailRetrieve(self, game_id):
        db = GamesDB()
        gameData = db.getGameThumnail(game_id)['thumbnail']
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(gameData)

    def handleListTop20Games(self):
        db = GamesDB()
        top20 = json.dumps(db.listTop20Games())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(top20, "utf-8"))

# Ratings Methods
    def handleAddRating(self):
        if self.mSession.get("isAdmin") or gAutoAuthActive:
            db = GamesDB()
            parsed_body = self.getParsedBody()
            game_id = parsed_body['game_id'][0]
            if not db.gameExists(game_id):
                self.handle404()
                return
            thumb_up = parsed_body['thumb_up'][0]
            thumb_down = parsed_body['thumb_down'][0]
            db.addRating(game_id, thumb_up, thumb_down)
            self.send_response(201)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes("Rating successfully set.", "utf-8"))
        else:
            self.handle403()
    def handleGetRatings(self):
        db = GamesDB()
        path = self.path.split('/')[2]
        game_id = path.split('?')[0]
        if not db.gameExists(game_id):
            self.handle404()
            return
        ratings = json.dumps(db.getRatings(game_id))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(ratings, "utf-8"))


# Tags Methods
    def handleAddTag(self):
        if "userID" in self.mSession or gAutoAuthActive:
            db = GamesDB()
            parsed_body = self.getParsedBody()
            game_id = parsed_body['game_id'][0]
            if db.profileNameOwnsGame(self.mSession.get("profile_name"), game_id) or gAutoAuthActive:
                tag = parsed_body['tag'][0]
                db.addTag(game_id, tag)
                self.send_response(201)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes("Tag successfully added.", "utf-8"))
            else:
                self.handle403()
        else:
            self.handle401()

    def handleDeleteTag(self):
        if "userID" in self.mSession or self.mSession.get("isAdmin") or gAutoAuthActive:
            db = GamesDB()
            game_id = self.path.split('/')[2]
            if db.profileNameOwnsGame(self.mSession.get("profile_name"), game_id) or gAutoAuthActive:
                postData = self.getParsedBody()
                tag = postData['tag'][0]
                db.deleteTag(game_id, tag)
                self.send_response(201)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes("Tag successfully deleted", "utf-8"))
            else:
                self.handle403()
        else:
            self.handle401()

    #sends back all tags in the structure of a list
    def handleRetrieveTags(self):
        db = GamesDB()
        path = self.path.split('/')[2]
        game_id = path.split('?')[0]
        if not db.gameExists(game_id):
            self.handle404()
        else:
            tags = db.getGameTags(game_id)
            jsonData = json.dumps(tags)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(jsonData, "utf-8"))
    def handleListTags(self):
        db = GamesDB()
        tags = db.getDistinctTags()
        jsonData = json.dumps(tags)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(jsonData, "utf-8"))

# USERS Methods
    def handleWhoAmI(self):
        if "userID" in self.mSession or gAutoAuthActive:
            me = {}
            isAdmin = self.mSession.get("isAdmin")
            profileName = self.mSession.get("profile_name")
            me["profile_name"] = profileName
            me["is_admin"] = isAdmin
            jsonData = json.dumps(me)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(jsonData, "utf-8"))
        else:
            self.handle401()

    def handleListMyGames(self):
        if "userID" in self.mSession or gAutoAuthActive:
            db = GamesDB()
            me = {}
            isAdmin = self.mSession.get("isAdmin")
            profileName = self.mSession.get("profile_name")
            games = db.listGamesWithGeneralFilter(profileName, "" , "")
            me["profile_name"] = profileName
            me["is_admin"] = isAdmin
            me["games"] = games 
            jsonData = json.dumps(me)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(jsonData, "utf-8"))
        else:
            self.handle401()

    def handleUserCreate(self):
        db = GamesDB()
        parsed_body = self.getParsedBody()
        profile_name = parsed_body["profile_name"][0]
        taken = db.checkProfileName(profile_name)
        if taken:
            self.handle422()
        else:
            password = parsed_body["password"][0]
            encrypted_password = bcrypt.encrypt(password)
            db.createUser(profile_name, encrypted_password)
            self.send_response(201)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes("User Created.", "utf-8"))

# SESSIONS Methods
    def handleCreateSession(self):
        db = GamesDB()
        parsed_body = self.getParsedBody()
        profile_name = parsed_body["profile_name"][0]
        password = parsed_body["password"][0]

        profile_exists = db.checkProfileName(profile_name)
        if profile_exists:
            auth_info = db.getUserAuthInfo(profile_name)
            verified = bcrypt.verify(password, auth_info[0]["encrypted_password"])
            if verified:
                self.mSession["userID"] = auth_info[0]["rowid"]
                user = db.getUser(auth_info[0]["rowid"])
                profile_name = user[0]["profile_name"]
                self.mSession["profile_name"] = profile_name
                isAdmin = db.isAdmin(profile_name)
                self.mSession["isAdmin"] = isAdmin
                user[0]["is_admin"] = isAdmin
                json_string = json.dumps(user)
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json_string, "utf-8"))
            else:
                self.handle401()
        else:
            self.handle401()
    
    def handleDeleteSession(self):
        sessionID = self.mCookie["sessionID"].value
        gSessionStore.deleteSession(sessionID)
        self.send_response(201)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Session successfully deleted", "utf-8"))

    def loadSession(self):
        self.loadCookie()
        if "sessionID" in self.mCookie:
            sessionID = self.mCookie["sessionID"].value
            sessionData = gSessionStore.getSession(sessionID)
            if sessionData is not None:
                self.mSession = sessionData
            else:
                sessionID = gSessionStore.createSession()
                self.mCookie["sessionID"] = sessionID
                self.mSession = gSessionStore.getSession(sessionID)
        else:
            sessionID = gSessionStore.createSession()
            self.mCookie["sessionID"] = sessionID
            self.mSession = gSessionStore.getSession(sessionID)

    def sendCookie(self):
        for morsel in self.mCookie.values():
            self.send_header("Set-Cookie", morsel.OutputString())

    def loadCookie(self):
        if "Cookie" in self.headers:
            self.mCookie = cookies.SimpleCookie(self.headers["Cookie"])
        else:
            self.mCookie = cookies.SimpleCookie()

# General Methods
    def getParsedBody(self):
        length = int(self.headers["Content-length"])
        body = self.rfile.read(length).decode("utf-8")
        parsed_body = parse_qs(body)
        return parsed_body

    def handle404(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Not Found.", "utf-8"))

    def handle422(self):
        self.send_response(422)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Invalid data entry.", "utf-8"))

    def handle401(self):
        self.send_response(401)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("This request requires user authetication.", "utf-8"))

    def handle403(self):
        self.send_response(403)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Not authorized.", "utf-8"))


def main():
    db = GamesDB()
    db.createTables()
    db.addClientUser()
    db = None

    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    listen = ("0.0.0.0", port)
    server = HTTPServer(listen, RequestHandler)

    print("Listening...")
    server.serve_forever()
main()
